"""串行分析任务队列。"""
import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from src.analyzer import LOG_DIR, OUTPUT_DIR, run_full_analysis
from src.github_downloader import REPOS_DIR, get_package_path
from src.github_parser import parse_github_url
from web import db as database

logger = logging.getLogger(__name__)

CONCURRENCY = 10

running_runs: set[int] = set()
_repo_refs: dict[str, int] = defaultdict(int)  # repo_dir_name -> ref count
_repo_locks: dict[str, asyncio.Lock] = {}      # repo_dir_name -> lock


class AnalysisQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue = asyncio.Queue()
        self._in_progress: list[dict] = []
        self._pending: list[dict] = []
        self._cancelled: set[int] = set()

    @property
    def size(self) -> int:
        return len(self._pending)

    @property
    def current(self) -> list[dict]:
        return list(self._in_progress)

    async def enqueue(self, library_id: int, run_id: int) -> None:
        self._pending.append({"library_id": library_id, "run_id": run_id})
        await self._queue.put((library_id, run_id))

    def list_pending(self) -> list[dict]:
        return list(self._pending)

    def cancel_pending(self, run_id: int) -> bool:
        if not any(p["run_id"] == run_id for p in self._pending):
            return False
        self._cancelled.add(run_id)
        self._pending = [p for p in self._pending if p["run_id"] != run_id]
        return True

    async def worker(self) -> None:
        while True:
            library_id, run_id = await self._queue.get()
            self._pending = [p for p in self._pending if p["run_id"] != run_id]
            if run_id in self._cancelled:
                self._cancelled.discard(run_id)
                self._queue.task_done()
                continue
            item = {"library_id": library_id, "run_id": run_id}
            self._in_progress.append(item)
            try:
                await self._process(library_id, run_id)
            except Exception as exc:
                logger.exception("Unexpected error in queue worker: %s", exc)
            finally:
                self._queue.task_done()
                self._in_progress.remove(item)

    async def _process(self, library_id: int, run_id: int) -> None:
        library = await database.get_library(library_id)
        if not library:
            try:
                await database.update_run(run_id, "failed", error_msg="Library not found")
            except Exception as e:
                logger.error(f"更新 run {run_id} 失败: {e}")
            return

        started_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        try:
            await database.update_run(run_id, "running", started_at=started_at)
        except Exception as e:
            logger.error(f"更新 run {run_id} 为 running 失败: {e}")
            return

        git_url = library.get("git_url")
        sub_path = library.get("sub_path")
        library_name = library.get("name", "unknown")

        if not git_url:
            try:
                await database.update_run(run_id, "failed", error_msg="Missing git_url")
            except Exception as e:
                logger.error(f"更新 run {run_id} 失败: {e}")
            return

        repo_info = parse_github_url(git_url)
        if not repo_info:
            try:
                await database.update_run(run_id, "failed", error_msg=f"Cannot parse git_url: {git_url}")
            except Exception as e:
                logger.error(f"更新 run {run_id} 失败: {e}")
            return

        repo_dir = REPOS_DIR / repo_info.repo_dir_name
        if not repo_dir.exists():
            try:
                await database.update_run(run_id, "failed", error_msg="Repository not downloaded")
            except Exception as e:
                logger.error(f"更新 run {run_id} 失败: {e}")
            return

        # 增加仓库引用计数（必须在 try-finally 中确保平衡）
        lock = _repo_locks.setdefault(repo_info.repo_dir_name, asyncio.Lock())
        async with lock:
            _repo_refs[repo_info.repo_dir_name] += 1

        try:
            package_path = get_package_path(repo_dir, sub_path)
        except Exception as e:
            try:
                await database.update_run(run_id, "failed", error_msg=f"Package path not found: {e}")
            except Exception as db_e:
                logger.error(f"更新 run {run_id} 失败: {db_e}")
            # 减少引用计数（异常路径）
            async with lock:
                _repo_refs[repo_info.repo_dir_name] -= 1
                if _repo_refs[repo_info.repo_dir_name] <= 0:
                    del _repo_refs[repo_info.repo_dir_name]
            return

        # 创建日志目录
        log_dir = LOG_DIR / str(run_id)
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            try:
                await database.update_run(run_id, "failed", error_msg=f"Cannot create log dir: {e}")
            except Exception as db_e:
                logger.error(f"更新 run {run_id} 失败: {db_e}")
            async with lock:
                _repo_refs[repo_info.repo_dir_name] -= 1
                if _repo_refs[repo_info.repo_dir_name] <= 0:
                    del _repo_refs[repo_info.repo_dir_name]
            return

        running_runs.add(run_id)
        report = None
        run_error = None
        result = None

        try:
            result = await run_full_analysis(
                repo_path=str(repo_dir),
                sub_path=sub_path,
                git_url=library_name,
                log_dir=log_dir,
            )
            report = result.report

            # 写入 output/{name}.json（需要处理磁盘满等异常）
            try:
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                safe_name = library_name.replace("/", "_").replace("@", "")
                output_file = OUTPUT_DIR / f"{safe_name}.json"
                output_data = {
                    "library": {
                        "name": library_name,
                        "git_url": git_url,
                        "sub_path": sub_path,
                        "commit_sha": library.get("commit_sha"),
                        "analyzed_at": datetime.now(timezone.utc).isoformat(),
                    },
                    "result": report,
                }
                output_json = json.dumps(output_data, ensure_ascii=False, indent=2)
                output_file.write_text(output_json, encoding="utf-8")
                logger.info(f"结果已写入: {output_file}")
            except (IOError, OSError) as e:
                logger.error(f"写入结果文件失败: {e}")
                run_error = f"Output file write failed: {str(e)[:500]}"

        except Exception as exc:
            run_error = str(exc)[:500]
        finally:
            running_runs.discard(run_id)

        if run_error:
            try:
                await database.update_run(run_id, "failed",
                    error_msg=run_error,
                    finished_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
            except Exception as e:
                logger.error(f"更新 run {run_id} 为 failed 失败: {e}")
        else:
            try:
                await database.update_run(run_id, "done",
                    result=report,
                    finished_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
            except Exception as e:
                logger.error(f"更新 run {run_id} 为 done 失败: {e}")


analysis_queue = AnalysisQueue()