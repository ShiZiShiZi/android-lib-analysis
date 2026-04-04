"""串行分析任务队列。

使用多 server 模式：
- 10 个 opencode serve 实例
- 每个任务完成后自动重启 server
- 确保 session 上下文干净，内存不累积
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.opencode_client import LOG_DIR, run_full_analysis
from src.github_downloader import REPOS_DIR, get_package_path
from src.github_parser import parse_github_url
from src.server_pool import ServerPool, get_server_pool
from web import db as database

logger = logging.getLogger(__name__)

CONCURRENCY = 10
TASK_TIMEOUT = 1800

running_runs: set[int] = set()
run_session_map: dict[int, tuple[str, str]] = {}
run_last_update: dict[int, float] = {}


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
        run_last_update[run_id] = time.time()

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

        package_path = get_package_path(repo_dir, sub_path)
        log_dir = LOG_DIR / str(run_id)
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            try:
                await database.update_run(run_id, "failed", error_msg=f"Cannot create log dir: {e}")
            except Exception as db_e:
                logger.error(f"更新 run {run_id} 失败: {db_e}")
            return

        log_path = log_dir / "analysis.log"
        log_fh = open(log_path, "w", encoding="utf-8", buffering=8192)

        async def on_log(line: str) -> None:
            log_fh.write(line + "\n")
            run_last_update[run_id] = time.time()

        async def on_session_created(session_id: str) -> None:
            run_session_map[run_id] = (session_id, server.url if server else "")
            run_last_update[run_id] = time.time()

        running_runs.add(run_id)
        report = None
        session_id = None
        run_error = None
        server = None

        try:
            pool = await get_server_pool()
            server = await pool.get_server()
            logger.info("[run:%d] 使用 server:%d (端口 %d)", run_id, server.db_index, server.port)

            report, session_id = await asyncio.wait_for(
                run_full_analysis(
                    repo_path=str(repo_dir),
                    git_url=library_name,
                    sub_path=sub_path,
                    on_log=on_log,
                    on_session_created=on_session_created,
                    server_url=server.url
                ),
                timeout=TASK_TIMEOUT
            )
        except asyncio.TimeoutError:
            run_error = f"任务超时（{TASK_TIMEOUT//60}分钟）"
        except Exception as exc:
            run_error = str(exc)[:500]
        finally:
            log_fh.close()
            running_runs.discard(run_id)
            run_last_update.pop(run_id, None)
            run_session_map.pop(run_id, None)

            if server:
                pool = await get_server_pool()
                pool.release_server(server)

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