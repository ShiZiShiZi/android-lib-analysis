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

from src.opencode_client import LOG_DIR
from src.github_downloader import REPOS_DIR, clone_repo, get_package_path, get_repo_size_mb, cleanup_repo, get_commit_sha
from src.github_parser import parse_github_url, GitHubRepoInfo
from src.server_pool import get_server_pool
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
    
    await database.init_db()
    dl_reset, run_reset = await database.reset_stale_states()
    if dl_reset or run_reset:
        logger.warning("重置了 %d 个下载 / %d 个分析任务（服务重启）", dl_reset, run_reset)

    pool = await get_server_pool()
    logger.info("ServerPool 已启动: %d 个实例", len(pool.servers))

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
    
    await pool.stop_all()
    await database.close_db()


app = FastAPI(lifespan=lifespan, title="Android Library Analyzer")
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
            'name': ['okhttp', 'retrofit', 'glide'],
            'git_url': [
                'https://github.com/square/okhttp',
                'https://github.com/square/retrofit',
                'https://github.com/bumptech/glide',
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
        
        export_item = {
            "name": lib["name"],
            "git_url": lib.get("git_url"),
            "sub_path": lib.get("sub_path"),
            "commit_sha": lib.get("commit_sha"),
            **result_json,
        }
        
        result.append(export_item)
    return Response(
        content=json.dumps(result, ensure_ascii=False, indent=2),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="libraries_export.json"'},
    )


# ── Log APIs ───────────────────────────────────────────────────────────────────

@app.get("/api/runs/{run_id}/live-status")
async def get_run_live_status(run_id: int):
    """获取运行中的实时状态（通过 opencode serve session API）"""
    from web.queue import run_session_map
    from datetime import datetime
    import httpx
    
    run = await database.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run["status"] in ("done", "failed"):
        return JSONResponse({
            "status": run["status"],
            "finished": True,
            "error_msg": run.get("error_msg"),
            "messages": [],
        })
    
    session_info = run_session_map.get(run_id)
    if not session_info:
        return JSONResponse({
            "status": run["status"],
            "finished": False,
            "messages": [{"type": "info", "text": "任务正在初始化，请稍候..."}],
        })
    
    session_id, server_url = session_info
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{server_url}/session/{session_id}/message?limit=100")
            resp.raise_for_status()
            try:
                messages = resp.json()
            except Exception:
                return JSONResponse({
                    "status": run["status"],
                    "finished": False,
                    "messages": [{"type": "error", "text": "opencode 返回无效响应"}],
                })
    except Exception as e:
        return JSONResponse({
            "status": run["status"],
            "finished": False,
            "messages": [{"type": "error", "text": f"无法连接 opencode: {str(e)[:80]}"}],
        })
    
    if not messages:
        return JSONResponse({
            "status": run["status"],
            "finished": False,
            "messages": [{"type": "info", "text": "暂无消息"}],
        })
    
    formatted_messages = []
    finished = False
    
    for msg in messages:
        info = msg.get("info", {})
        parts = msg.get("parts", [])
        
        if info.get("finish") == "stop":
            finished = True
        
        for p in parts:
            p_type = p.get("type")
            
            if p_type == "step-start":
                continue
            elif p_type == "step-finish":
                continue
            elif p_type == "tool":
                state = p.get("state", {})
                tool_name = p.get("tool", "unknown")
                tool_status = state.get("status", "unknown")
                
                time_info = state.get("time", {})
                start_time = time_info.get("start", 0)
                time_str = datetime.fromtimestamp(start_time / 1000).strftime("%H:%M:%S") if start_time else ""
                
                title = state.get("title", "")
                command = ""
                output_preview = ""
                
                if tool_name == "bash":
                    inp = state.get("input", {})
                    command = inp.get("command", "")[:200]
                    desc = inp.get("description", "")
                    if not title and desc:
                        title = desc
                    out = state.get("output", "") or state.get("metadata", {}).get("output", "")
                    if out:
                        lines = out.strip().split("\n")[:3]
                        output_preview = "\n".join(lines)[:300]
                elif tool_name == "read":
                    inp = state.get("input", {})
                    file_path = inp.get("file_path", "")
                    if not title and file_path:
                        title = f"读取 {file_path.split('/')[-1]}"
                elif tool_name == "glob":
                    inp = state.get("input", {})
                    pattern = inp.get("pattern", "")
                    if not title and pattern:
                        title = f"搜索 {pattern}"
                elif tool_name == "grep":
                    inp = state.get("input", {})
                    pattern = inp.get("pattern", "")
                    if not title and pattern:
                        title = f"查找 {pattern[:50]}"
                elif tool_name == "write":
                    inp = state.get("input", {})
                    file_path = inp.get("file_path", "")
                    if not title and file_path:
                        title = f"写入 {file_path.split('/')[-1]}"
                elif tool_name == "skill":
                    inp = state.get("input", {})
                    skill_name = inp.get("name", "")
                    if not title and skill_name:
                        title = f"执行 skill: {skill_name}"
                elif tool_name == "task":
                    inp = state.get("input", {})
                    subagent = inp.get("subagent_type", "")
                    if not title and subagent:
                        title = f"启动子任务: {subagent}"
                
                if not title:
                    title = tool_name
                
                formatted_messages.append({
                    "id": p.get("id", ""),
                    "type": "tool",
                    "tool": tool_name,
                    "status": tool_status,
                    "time": time_str,
                    "title": title[:100],
                    "command": command,
                    "output_preview": output_preview,
                })
            
            elif p_type == "text":
                text = p.get("text", "")
                if text and len(text.strip()) > 0:
                    formatted_messages.append({
                        "id": p.get("id", ""),
                        "type": "text",
                        "time": "",
                        "text": text[:200],
                    })
            
            elif p_type == "reasoning":
                text = p.get("text", "")
                if text and len(text.strip()) > 0:
                    formatted_messages.append({
                        "id": p.get("id", ""),
                        "type": "reasoning",
                        "time": "",
                        "text": text[:200],
                    })
    
    return JSONResponse({
        "status": run["status"],
        "finished": finished,
        "messages": formatted_messages[-50:],
        "session_id": session_id,
    })


# ── System APIs ───────────────────────────────────────────────────────────────

@app.get("/api/system/library-counts")
async def library_counts():
    run_counts = await database.get_run_status_counts()
    dl_counts = await database.get_dl_status_counts()
    return JSONResponse({"run": run_counts, "dl": dl_counts})


# ── Task Management APIs ───────────────────────────────────────────────────────

@app.get("/api/tasks")
async def get_tasks():
    downloads = await database.list_downloads_running()
    analysis_current = analysis_queue.current
    analysis_pending = analysis_queue.list_pending()
    
    enriched_current = []
    for item in analysis_current:
        lib = await database.get_library(item["library_id"])
        run = await database.get_run(item["run_id"])
        enriched_current.append({
            "library_id": item["library_id"],
            "run_id": item["run_id"],
            "name": lib.get("name", "") if lib else "",
            "created_at": run.get("created_at", "") if run else "",
        })
    
    enriched_pending = []
    for item in analysis_pending:
        lib = await database.get_library(item["library_id"])
        run = await database.get_run(item["run_id"])
        enriched_pending.append({
            "library_id": item["library_id"],
            "run_id": item["run_id"],
            "name": lib.get("name", "") if lib else "",
            "created_at": run.get("created_at", "") if run else "",
        })
    
    return JSONResponse({
        "downloads": downloads,
        "analysis_current": enriched_current,
        "analysis_pending": enriched_pending,
    })


@app.delete("/api/tasks/download/{library_id}")
async def cancel_download_task(library_id: int):
    library = await database.get_library(library_id)
    if not library:
        raise HTTPException(status_code=404, detail="Library not found")
    
    task = _download_tasks.get(library_id)
    if task and not task.done():
        task.cancel()
        _download_tasks.pop(library_id, None)
        logger.info(f"Cancelled download for library {library_id}")
        return JSONResponse({"ok": True, "cancelled": True})
    
    if library.get("dl_status") == "running":
        await database.update_library_dl(library_id, "failed", error="用户已取消")
        return JSONResponse({"ok": True, "cancelled": True, "status_reset": True})
    
    return JSONResponse({"ok": False, "error": "no_running_download"}, status_code=400)


@app.delete("/api/tasks/analysis/{run_id}")
async def cancel_analysis_task(run_id: int):
    run = await database.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    if run["status"] == "done" or run["status"] == "failed":
        return JSONResponse({"ok": False, "error": "already_finished"}, status_code=400)
    
    if run["status"] == "running":
        return JSONResponse({"ok": False, "error": "currently_running"}, status_code=400)
    
    cancelled = analysis_queue.cancel_pending(run_id)
    if cancelled:
        await database.update_run(run_id, "failed", error_msg="用户已取消")
        logger.info(f"Cancelled pending analysis run {run_id}")
        return JSONResponse({"ok": True, "cancelled": True})
    
    return JSONResponse({"ok": False, "error": "not_in_queue"}, status_code=400)