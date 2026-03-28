"""FastAPI 入口：路由、lifespan。"""
import asyncio
import csv
import io
import json
import logging
import os
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from email.utils import formatdate

from src.analyzer import LOG_DIR
from src.proxy import start_proxy, stop_proxy
from src.github_downloader import REPOS_DIR, clone_repo, get_package_path, get_repo_size_mb, cleanup_repo, get_commit_sha
from src.github_parser import parse_github_url, GitHubRepoInfo
from web import db as database
from web.queue import CONCURRENCY, analysis_queue, running_runs

logger = logging.getLogger(__name__)

_DIR = Path(__file__).parent
PROJECT_DIR = _DIR.parent

_download_tasks: dict[int, asyncio.Task] = {}
_repo_locks: dict[str, asyncio.Lock] = {}
_DOWNLOAD_SEMAPHORE: Optional[asyncio.Semaphore] = None
_DOWNLOAD_LOCKS: dict[int, asyncio.Lock] = {}


def _is_download_running(library_id: int) -> bool:
    task = _download_tasks.get(library_id)
    return task is not None and not task.done()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _DOWNLOAD_SEMAPHORE
    _DOWNLOAD_SEMAPHORE = asyncio.Semaphore(3)
    
    # 启动时验证配置文件
    config_path = Path.home() / ".config/opencode/opencode.json"
    if not config_path.exists():
        logger.error(f"启动失败：opencode 配置文件不存在: {config_path}")
        raise RuntimeError(f"opencode 配置文件不存在: {config_path}")

    try:
        base_config = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        logger.error(f"启动失败：opencode 配置文件格式错误: {e}")
        raise RuntimeError(f"opencode 配置文件格式错误: {e}")

    await database.init_db()
    dl_reset, run_reset = await database.reset_stale_states()
    if dl_reset or run_reset:
        logger.warning("重置了 %d 个下载 / %d 个分析任务（服务重启）", dl_reset, run_reset)

    real_url = base_config["provider"]["bailian-coding-plan"]["options"]["baseURL"]
    proxy = start_proxy(real_url, port=0, verbose=False)
    if proxy is None:
        logger.error("启动失败：代理启动失败")
        raise RuntimeError("Failed to start proxy")

    proxy_port = proxy.server_address[1]
    logger.info("代理已启动，端口 %d → %s", proxy_port, real_url)

    worker_tasks = [
        asyncio.create_task(analysis_queue.worker()) for _ in range(CONCURRENCY)
    ]
    yield

    for t in worker_tasks:
        t.cancel()
    for t in worker_tasks:
        try:
            await t
        except asyncio.CancelledError:
            pass
    stop_proxy(proxy)
    await database.close_db()


app = FastAPI(lifespan=lifespan, title="React Native Library Analyzer")
app.mount("/static", StaticFiles(directory=str(_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(_DIR / "templates"))


def _human_size(mb: Optional[float]) -> str:
    if mb is None:
        return "?"
    if mb < 1:
        return f"{mb * 1024:.0f} KB"
    if mb < 1024:
        return f"{mb:.1f} MB"
    return f"{mb / 1024:.1f} GB"


templates.env.filters["human_size"] = _human_size


def _to_json_pretty(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


templates.env.filters["to_json_pretty"] = _to_json_pretty


def _local_time(dt_str: str) -> str:
    """将时间字符串格式化为北京时间显示"""
    if not dt_str:
        return "—"
    from datetime import datetime, timezone, timedelta
    beijing_tz = timezone(timedelta(hours=8))
    try:
        # 带时区的 ISO 格式
        if 'T' in dt_str and ('+' in dt_str or dt_str.endswith('Z')):
            dt_str = dt_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(dt_str)
            return dt.astimezone(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")
        # 不带时区的时间字符串，假设是 UTC 时间
        dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S")
        dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(beijing_tz).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return dt_str[:19] if len(dt_str) >= 19 else dt_str


templates.env.filters["local_time"] = _local_time


def _static_v(filename: str) -> str:
    try:
        mtime = int((_DIR / "static" / filename).stat().st_mtime)
    except OSError:
        mtime = 0
    return f"/static/{filename}?v={mtime}"


templates.env.globals["static_v"] = _static_v


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _do_download(library_id: int, force: bool = False) -> None:
    dl_lock = _DOWNLOAD_LOCKS.setdefault(library_id, asyncio.Lock())
    async with dl_lock:
        if _DOWNLOAD_SEMAPHORE is None:
            raise RuntimeError("下载信号量未初始化")
        
        library = await database.get_library(library_id)
        if not library:
            logger.error(f"Library {library_id} not found")
            return
        
        if not force and library.get("dl_status") == "done":
            repo_dir = REPOS_DIR
            repo_info = parse_github_url(library.get("git_url", ""))
            if repo_info and (REPOS_DIR / repo_info.repo_dir_name).exists():
                logger.info(f"Library {library_id} 已下载完成，跳过")
                return
        
        started_at = datetime.now(timezone.utc).isoformat()
        try:
            await database.update_library_dl(library_id, "running", started_at=started_at)
        except Exception as e:
            logger.error(f"更新下载状态失败: {e}")
            return
        
        async with _DOWNLOAD_SEMAPHORE:
            try:
                loop = asyncio.get_running_loop()
                git_url = library["git_url"]
                sub_path = library.get("sub_path")

                if not git_url:
                    raise ValueError("缺少 git_url")

                repo_info = parse_github_url(git_url)
                if not repo_info:
                    raise ValueError(f"无法解析 GitHub URL: {git_url}")

                repo_lock = _repo_locks.setdefault(repo_info.repo_dir_name, asyncio.Lock())
                async with repo_lock:
                    repo_dir = REPOS_DIR / repo_info.repo_dir_name
                    await loop.run_in_executor(None, lambda: clone_repo(repo_info, force=force))

                repo_dir = REPOS_DIR / repo_info.repo_dir_name
                package_path = get_package_path(repo_dir, sub_path)
                size_mb = await loop.run_in_executor(None, get_repo_size_mb, repo_dir)
                commit_sha = await loop.run_in_executor(None, get_commit_sha, repo_dir)

                done_at = datetime.now(timezone.utc).isoformat()
                try:
                    await database.update_library_dl(
                        library_id, "done",
                        error="",
                        repo_size_mb=size_mb,
                        done_at=done_at,
                        commit_sha=commit_sha
                    )
                except Exception as e:
                    logger.error(f"更新下载完成状态失败: {e}")

            except Exception as exc:
                logger.error("Download failed for library %d: %s", library_id, exc)
                try:
                    await database.update_library_dl(library_id, "failed", error=str(exc)[:500])
                except Exception as e:
                    logger.error(f"更新下载失败状态失败: {e}")


def _start_download(library_id: int, force: bool = False) -> None:
    async def _run():
        try:
            await _do_download(library_id, force=force)
        except asyncio.CancelledError:
            logger.info(f"Download task for library {library_id} cancelled by user")
            try:
                await database.update_library_dl(library_id, "failed", error="用户已取消")
            except Exception as e:
                logger.error(f"更新取消状态失败: {e}")
        except Exception as exc:
            logger.exception("Unexpected error in download task for library %d: %s", library_id, exc)
            try:
                await database.update_library_dl(library_id, "failed", error=str(exc)[:500])
            except Exception as e:
                logger.error(f"更新异常状态失败: {e}")
        finally:
            _download_tasks.pop(library_id, None)
    task = asyncio.create_task(_run())
    _download_tasks[library_id] = task


# ── Page routes ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    page: int = 1,
    per_page: int = 10,
    q: str = "",
    dl: str = "all",
    run: str = "all",
):
    per_page = max(10, min(per_page, 1000))
    page = max(1, page)

    libraries, total = await database.list_libraries_paged(
        page=page, per_page=per_page, q=q,
        dl_status=dl, run_status=run,
    )

    total_pages = max(1, (total + per_page - 1) // per_page)

    return templates.TemplateResponse("index.html", {
        "request": request,
        "libraries": libraries,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": total_pages,
        "q": q,
        "dl": dl,
        "run": run,
        "queue_size": analysis_queue.size,
        "current_task": analysis_queue.current,
        "dl_running_count": await database.count_downloads_running(),
    })


@app.get("/import", response_class=HTMLResponse)
async def import_page(request: Request):
    return templates.TemplateResponse("import.html", {"request": request})


@app.get("/libraries/{library_id}", response_class=HTMLResponse)
async def library_detail(request: Request, library_id: int):
    library = await database.get_library(library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    runs = await database.list_runs_for_library(library_id)
    latest_run = runs[0] if runs else None
    result = None
    if latest_run and latest_run.get("result"):
        r = latest_run["result"]
        result = json.loads(r) if isinstance(r, str) else r
    return templates.TemplateResponse("library.html", {
        "request": request,
        "library": library,
        "runs": runs,
        "latest_run": latest_run,
        "result": result,
    })


# ── API: Import ────────────────────────────────────────────────────────────────

@app.post("/api/libraries/import")
async def import_libraries(body: dict):
    libraries_in = body.get("libraries", [])
    imported, skipped, errors = [], [], []
    
    for lib in libraries_in:
        name = (lib.get("name") or "").strip()
        git_url = (lib.get("git_url") or "").strip()
        sub_path = lib.get("sub_path") or None
        
        if not name:
            continue
        
        if git_url:
            repo_info = parse_github_url(git_url)
            if repo_info and repo_info.sub_path and not sub_path:
                sub_path = repo_info.sub_path
        
        try:
            if await database.get_library_by_name(name):
                skipped.append(name)
                continue
            lib_id = await database.create_library(name, git_url=git_url, sub_path=sub_path)
            imported.append({"name": name, "id": lib_id, "git_url": git_url, "sub_path": sub_path})
        except Exception as exc:
            errors.append({"name": name, "error": str(exc)})
    
    return JSONResponse({"imported": imported, "skipped": skipped, "errors": errors})


@app.post("/api/libraries/import-excel")
async def import_from_excel(file: UploadFile = File(...)):
    try:
        import pandas as pd
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))
        
        if 'name' not in df.columns:
            return JSONResponse({"error": "Excel 缺少 'name' 列"}, status_code=400)
        
        libraries_in = []
        for _, row in df.iterrows():
            name = str(row.get('name', '')).strip()
            git_url = str(row.get('git_url', row.get('github_url', ''))).strip()
            sub_path = str(row.get('sub_path', '')).strip() or None
            
            if name and git_url:
                libraries_in.append({"name": name, "git_url": git_url, "sub_path": sub_path})
        
        return await import_libraries({"libraries": libraries_in})
        
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/libraries/template")
async def download_template():
    try:
        import pandas as pd
        df = pd.DataFrame({
            'name': ['expo-camera', '@react-native-firebase/app', 'react-native-maps'],
            'git_url': [
                'https://github.com/expo/expo/tree/main/packages/expo-camera',
                'https://github.com/invertase/react-native-firebase/tree/main/packages/app',
                'https://github.com/react-native-maps/react-native-maps',
            ],
            'sub_path': ['', '', ''],
        })
        
        buf = io.BytesIO()
        df.to_excel(buf, index=False, engine='openpyxl')
        buf.seek(0)
        
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="import_template.xlsx"'},
        )
    except ImportError:
        return JSONResponse({"error": "需要安装 pandas 和 openpyxl"}, status_code=500)


# ── API: library CRUD ──────────────────────────────────────────────────────────

@app.get("/api/libraries/{library_id}/status")
async def library_status(library_id: int):
    library = await database.get_library(library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    runs = await database.list_runs_for_library(library_id)
    latest_run = runs[0] if runs else None
    return JSONResponse({"library": library, "latest_run": latest_run})


@app.delete("/api/libraries/{library_id}")
async def delete_library(library_id: int):
    library = await database.get_library(library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    
    git_url = library.get("git_url")
    should_cleanup = False
    if git_url:
        repo_info = parse_github_url(git_url)
        if repo_info:
            count = await database.count_libraries_by_git_url(git_url)
            if count <= 1:
                should_cleanup = True
    
    if should_cleanup:
        try:
            cleanup_repo(repo_info.repo_dir_name)
        except Exception as e:
            logger.warning(f"cleanup repo on delete failed: {e}")
    
    await database.delete_library(library_id)
    return JSONResponse({"ok": True, "cleaned_repo": should_cleanup})


# ── API: download ─────────────────────────────────────────────────────────────

@app.post("/api/libraries/{library_id}/download")
async def download_library(library_id: int, body: dict = None):
    library = await database.get_library(library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    
    if _is_download_running(library_id):
        return JSONResponse({"ok": True, "queued": "already_running"})
    
    force = (body or {}).get("force", False)
    _start_download(library_id, force=force)
    return JSONResponse({"ok": True, "queued": True, "force": force})


@app.post("/api/libraries/download-batch")
async def download_batch(body: dict):
    force = body.get("force", False)
    queued_ids = []
    already_running_ids = []
    for lib_id in body.get("library_ids", []):
        library = await database.get_library(lib_id)
        if not library:
            continue
        if _is_download_running(lib_id):
            already_running_ids.append(lib_id)
            continue
        _start_download(lib_id, force=force)
        queued_ids.append(lib_id)
    return JSONResponse({"ok": True, "queued_ids": queued_ids, "already_running_ids": already_running_ids, "force": force})


# ── API: analysis ─────────────────────────────────────────────────────────────

@app.post("/api/libraries/{library_id}/analyze")
async def analyze_library(library_id: int):
    library = await database.get_library(library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    
    if _is_download_running(library_id):
        return JSONResponse({"ok": False, "error": "download_in_progress"}, status_code=400)
    
    git_url = library.get("git_url")
    if not git_url:
        raise HTTPException(status_code=400, detail="缺少 git_url")
    
    repo_info = parse_github_url(git_url)
    if not repo_info:
        raise HTTPException(status_code=400, detail="无法解析 git_url")
    
    repo_dir = REPOS_DIR / repo_info.repo_dir_name
    if library.get("dl_status") != "done" or not repo_dir.exists():
        raise HTTPException(status_code=400, detail="请先下载仓库")
    
    run_id = await database.create_run(library_id)
    await analysis_queue.enqueue(library_id, run_id)
    return JSONResponse({"ok": True, "run_id": run_id})


@app.post("/api/libraries/analyze-batch")
async def analyze_batch(body: dict):
    force = body.get("force", False)
    run_ids = []
    skipped_no_download = []
    for lib_id in body.get("library_ids", []):
        library = await database.get_library(lib_id)
        if not library:
            continue
        if not force:
            runs = await database.list_runs_for_library(lib_id)
            if runs and runs[0]["status"] == "done":
                continue
        
        if _is_download_running(lib_id):
            continue
        
        git_url = library.get("git_url")
        if not git_url:
            continue
        repo_info = parse_github_url(git_url)
        if not repo_info:
            continue
        
        repo_dir = REPOS_DIR / repo_info.repo_dir_name
        if library.get("dl_status") != "done" or not repo_dir.exists():
            skipped_no_download.append(lib_id)
            continue
        
        run_id = await database.create_run(lib_id)
        await analysis_queue.enqueue(lib_id, run_id)
        run_ids.append(run_id)
    return JSONResponse({"ok": True, "run_ids": run_ids, "skipped_no_download": skipped_no_download})


@app.post("/api/runs/{run_id}/rerun")
async def rerun(run_id: int):
    run = await database.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    library = await database.get_library(run["library_id"])
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")

    lib_id = run["library_id"]
    
    if _is_download_running(lib_id):
        return JSONResponse({"ok": False, "error": "download_in_progress"}, status_code=400)

    git_url = library.get("git_url")
    if not git_url:
        raise HTTPException(status_code=400, detail="缺少 git_url")
    repo_info = parse_github_url(git_url)
    if not repo_info:
        raise HTTPException(status_code=400, detail="无法解析 git_url")

    repo_dir = REPOS_DIR / repo_info.repo_dir_name
    if library.get("dl_status") != "done" or not repo_dir.exists():
        raise HTTPException(status_code=400, detail="请先下载仓库")
    
    new_run_id = await database.create_run(run["library_id"])
    await analysis_queue.enqueue(run["library_id"], new_run_id)
    return JSONResponse({"ok": True, "run_id": new_run_id})


@app.get("/api/libraries/{library_id}/runs")
async def get_runs(library_id: int):
    runs = await database.list_runs_for_library(library_id)
    return JSONResponse({"runs": runs})


@app.get("/api/runs/{run_id}")
async def get_run(run_id: int):
    run = await database.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return JSONResponse({"run": run})


@app.get("/api/runs/{run_id}/logs")
async def get_run_logs(run_id: int, since: int = 0):
    is_running = run_id in running_runs
    log_file = LOG_DIR / str(run_id) / "analysis.log"

    if not log_file.exists():
        return JSONResponse({"lines": [], "total": 0, "done": True})

    mtime = log_file.stat().st_mtime
    last_modified = formatdate(mtime, usegmt=True)

    content = log_file.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    response = JSONResponse({"lines": lines[since:], "total": len(lines), "done": not is_running})
    response.headers['Last-Modified'] = last_modified
    return response


@app.get("/api/system/status")
async def system_status():
    return JSONResponse({
        "queue_size": analysis_queue.size,
        "current_task": analysis_queue.current,
    })


@app.get("/api/tasks")
async def list_tasks():
    downloads = []
    for lib_id, task in list(_download_tasks.items()):
        if task.done():
            continue
        library = await database.get_library(lib_id)
        downloads.append({
            "library_id": lib_id,
            "name": library["name"] if library else f"Library #{lib_id}",
        })
    
    analysis_current = []
    for item in analysis_queue.current:
        library = await database.get_library(item["library_id"])
        run = await database.get_run(item["run_id"])
        analysis_current.append({
            "library_id": item["library_id"],
            "run_id": item["run_id"],
            "name": library["name"] if library else f"Library #{item['library_id']}",
            "created_at": run["created_at"] if run else None,
            "is_current": True,
        })
    
    analysis_pending = []
    for item in analysis_queue.list_pending():
        library = await database.get_library(item["library_id"])
        run = await database.get_run(item["run_id"])
        analysis_pending.append({
            "library_id": item["library_id"],
            "run_id": item["run_id"],
            "name": library["name"] if library else f"Library #{item['library_id']}",
            "created_at": run["created_at"] if run else None,
            "is_current": False,
        })
    
    return JSONResponse({
        "downloads": downloads,
        "analysis_current": analysis_current,
        "analysis_pending": analysis_pending,
    })


@app.delete("/api/tasks/download/{library_id}")
async def cancel_download_task(library_id: int):
    task = _download_tasks.pop(library_id, None)
    if task and not task.done():
        task.cancel()
    await database.update_library_dl(library_id, "failed", error="用户已取消")
    return JSONResponse({"ok": True})


@app.delete("/api/tasks/analysis/{run_id}")
async def cancel_analysis_task(run_id: int):
    ok = analysis_queue.cancel_pending(run_id)
    if ok:
        now = datetime.now(timezone.utc).isoformat()
        await database.update_run(run_id, "failed", error_msg="用户已取消", finished_at=now, duration_ms=0)
    return JSONResponse({"ok": ok})


@app.get("/api/system/library-counts")
async def library_counts():
    return JSONResponse({
        "dl": await database.get_dl_status_counts(),
        "run": await database.get_run_status_counts(),
    })


# ── Export ────────────────────────────────────────────────────────────────────

CATEGORY_ZH = {
    "payment": "支付", "map_location": "地图定位",
    "push_notification": "推送通知", "im_chat": "即时通讯",
    "audio_video_call": "音视频通话", "storage": "存储",
    "file_media": "文件媒体", "networking": "网络",
    "auth_security": "认证安全", "analytics": "数据分析",
    "ads": "广告", "social_share": "社交分享",
    "ui_component": "UI组件", "device_sensor": "设备传感器",
    "bluetooth_hardware": "蓝牙硬件", "ar_xr": "AR/XR",
    "ai_ml": "AI/ML", "platform_utility": "平台工具",
}


@app.get("/export")
async def export_csv():
    libraries = await database.list_libraries()

    buf = io.StringIO()
    w = csv.writer(buf)
    
    HDR = ["名称", "GitHub URL", "子路径", "Commit", "下载状态", "分析状态",
           "云拓扑", "涉及付费", "许可证", "移动平台", "功能分类"]
    w.writerow(HDR)

    DL_ZH  = {"pending": "待下载", "running": "下载中", "done": "已下载", "failed": "下载失败", "cleaned": "已清理"}
    RUN_ZH = {"pending": "待分析", "running": "分析中", "done": "已完成", "failed": "分析失败"}

    for lib in libraries:
        if lib.get("run_status") != "done":
            continue
        runs = await database.list_runs_for_library(lib["id"])
        if not runs or not runs[0].get("result"):
            continue
        result_json = runs[0]["result"]
        if isinstance(result_json, str):
            result_json = json.loads(result_json)

        cs = result_json.get("cloud_services", {})
        pay = result_json.get("payment", {})
        lic = result_json.get("license", {})
        mp = result_json.get("mobile_platform", {})
        ft = result_json.get("features", {})

        w.writerow([
            lib["name"],
            lib.get("git_url", ""),
            lib.get("sub_path", ""),
            lib.get("commit_sha", ""),
            DL_ZH.get(lib.get("dl_status", ""), lib.get("dl_status", "")),
            RUN_ZH.get(lib.get("run_status", ""), lib.get("run_status", "") or "未分析"),
            cs.get("topology", ""),
            "是" if pay.get("involves_payment") else "否",
            lic.get("declared_license", ""),
            mp.get("label", ""),
            " | ".join(ft.get("taxonomy1", {}).get("categories", [])),
        ])

    return Response(
        content="\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="libraries_export.csv"'},
    )


@app.get("/export/json")
async def export_json():
    libraries = await database.list_libraries()
    result = []
    for lib in libraries:
        if lib.get("run_status") != "done":
            continue
        runs = await database.list_runs_for_library(lib["id"])
        if not runs or not runs[0].get("result"):
            continue
        result_json = runs[0]["result"]
        if isinstance(result_json, str):
            result_json = json.loads(result_json)
        result.append({
            "name": lib["name"],
            "git_url": lib.get("git_url"),
            "sub_path": lib.get("sub_path"),
            "commit_sha": lib.get("commit_sha"),
            **result_json,
        })
    return Response(
        content=json.dumps(result, ensure_ascii=False, indent=2),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="libraries_export.json"'},
    )


# ── Log APIs ───────────────────────────────────────────────────────────────────

@app.get("/api/runs/{run_id}/thinking")
async def get_thinking_log(run_id: int):
    """获取模型思考日志"""
    log_file = LOG_DIR / str(run_id) / "thinking.log"
    if not log_file.exists():
        return JSONResponse({"thinking": "", "exists": False})
    return JSONResponse({"thinking": log_file.read_text(encoding="utf-8"), "exists": True})


@app.get("/api/libraries/{library_id}/result")
async def get_result_file(library_id: int):
    """获取结果 JSON 文件"""
    library = await database.get_library(library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    
    safe_name = library["name"].replace("/", "_").replace("@", "")
    result_file = OUTPUT_DIR / f"{safe_name}.json"
    if not result_file.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return Response(
        content=result_file.read_text(encoding="utf-8"),
        media_type="application/json"
    )