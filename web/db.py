"""SQLite schema + async CRUD (aiosqlite)"""
import json
from pathlib import Path
from typing import Optional

import aiosqlite

DB_PATH = Path(__file__).parent.parent / "android_libraries.db"

_db: Optional[aiosqlite.Connection] = None

_CREATE_SQL = [
    """CREATE TABLE IF NOT EXISTS libraries (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT UNIQUE NOT NULL,
        git_url         TEXT,
        sub_path        TEXT,
        import_time     DATETIME DEFAULT CURRENT_TIMESTAMP,
        dl_status       TEXT DEFAULT 'pending',
        dl_error        TEXT,
        dl_started_at   DATETIME,
        dl_done_at      DATETIME,
        repo_size_mb    REAL,
        commit_sha      TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS analysis_runs (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        library_id   INTEGER REFERENCES libraries(id),
        created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
        started_at   DATETIME,
        finished_at  DATETIME,
        status       TEXT DEFAULT 'pending',
        duration_ms  INTEGER,
        result       TEXT,
        error_msg    TEXT
    )""",
]


async def init_db() -> None:
    global _db
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA synchronous=NORMAL")
    await _db.execute("PRAGMA busy_timeout=10000")
    for sql in _CREATE_SQL:
        await _db.execute(sql)
    await _db.commit()

    # 迁移：添加 started_at 列（如果不存在）
    try:
        await _db.execute("ALTER TABLE analysis_runs ADD COLUMN started_at DATETIME")
        await _db.commit()
    except aiosqlite.OperationalError:
        pass  # 列已存在

    # 创建索引
    await _db.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_library_created
        ON analysis_runs(library_id, created_at DESC)
    """)
    await _db.execute("""
        CREATE INDEX IF NOT EXISTS idx_runs_status
        ON analysis_runs(status)
    """)
    await _db.execute("""
        CREATE INDEX IF NOT EXISTS idx_libraries_dl_status
        ON libraries(dl_status)
    """)
    await _db.commit()


async def close_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None


def _row(row) -> Optional[dict]:
    return dict(row) if row is not None else None


# ── Libraries ──────────────────────────────────────────────────────────────────

async def create_library(name: str, git_url: Optional[str] = None, sub_path: Optional[str] = None) -> int:
    cur = await _db.execute(
        "INSERT INTO libraries (name, git_url, sub_path) VALUES (?, ?, ?)",
        (name, git_url, sub_path),
    )
    await _db.commit()
    return cur.lastrowid


async def get_library(library_id: int) -> Optional[dict]:
    cur = await _db.execute("SELECT * FROM libraries WHERE id = ?", (library_id,))
    return _row(await cur.fetchone())


async def get_library_by_name(name: str) -> Optional[dict]:
    cur = await _db.execute("SELECT * FROM libraries WHERE name = ?", (name,))
    return _row(await cur.fetchone())


async def list_libraries() -> list[dict]:
    """All libraries with their most recent run info (LEFT JOIN)."""
    cur = await _db.execute("""
        SELECT
            l.*,
            r.id        AS run_id,
            r.status    AS run_status,
            r.finished_at  AS run_finished_at,
            r.error_msg AS run_error_msg,
            r.duration_ms  AS run_duration_ms
        FROM libraries l
        LEFT JOIN analysis_runs r ON r.id = (
            SELECT id FROM analysis_runs
            WHERE library_id = l.id
            ORDER BY created_at DESC
            LIMIT 1
        )
        ORDER BY l.import_time DESC
    """)
    return [_row(r) for r in await cur.fetchall()]


async def list_libraries_paged(
    page: int = 1,
    per_page: int = 10,
    q: str = "",
    dl_status: str = "all",
    run_status: str = "all",
) -> tuple[list[dict], int]:
    """分页 + 过滤查询，返回 (items, total_count)。"""
    conds: list[str] = []
    params: list = []

    if q:
        conds.append("l.name LIKE ?")
        params.append(f"%{q}%")
    if dl_status != "all":
        conds.append("l.dl_status = ?")
        params.append(dl_status)
    if run_status == "none":
        conds.append("r.id IS NULL")
    elif run_status != "all":
        conds.append("r.status = ?")
        params.append(run_status)

    where = ("WHERE " + " AND ".join(conds)) if conds else ""

    join_frag = f"""
        FROM libraries l
        LEFT JOIN analysis_runs r ON r.id = (
            SELECT id FROM analysis_runs
            WHERE library_id = l.id
            ORDER BY created_at DESC
            LIMIT 1
        )
        {where}
    """

    cur = await _db.execute(f"SELECT COUNT(*) {join_frag}", params)
    total: int = (await cur.fetchone())[0]

    offset = (page - 1) * per_page
    cur = await _db.execute(
        f"""SELECT l.*,
                   r.id           AS run_id,
                   r.status       AS run_status,
                   r.finished_at  AS run_finished_at,
                   r.error_msg    AS run_error_msg,
                   r.duration_ms  AS run_duration_ms
            {join_frag}
            ORDER BY l.import_time DESC
            LIMIT ? OFFSET ?""",
        params + [per_page, offset],
    )
    items = [_row(r) for r in await cur.fetchall()]
    return items, total


async def update_library_dl(
    library_id: int,
    status: str,
    error: Optional[str] = None,
    repo_size_mb: Optional[float] = None,
    started_at: Optional[str] = None,
    done_at: Optional[str] = None,
    commit_sha: Optional[str] = None,
) -> None:
    fields = ["dl_status = ?"]
    params: list = [status]
    if error is not None:
        fields.append("dl_error = ?")
        params.append(error[:2000])
    if repo_size_mb is not None:
        fields.append("repo_size_mb = ?")
        params.append(repo_size_mb)
    if started_at is not None:
        fields.append("dl_started_at = ?")
        params.append(started_at)
    if done_at is not None:
        fields.append("dl_done_at = ?")
        params.append(done_at)
    if commit_sha is not None:
        fields.append("commit_sha = ?")
        params.append(commit_sha)
    params.append(library_id)
    await _db.execute(
        f"UPDATE libraries SET {', '.join(fields)} WHERE id = ?", params
    )
    await _db.commit()


async def delete_library(library_id: int) -> None:
    await _db.execute("DELETE FROM analysis_runs WHERE library_id = ?", (library_id,))
    await _db.execute("DELETE FROM libraries WHERE id = ?", (library_id,))
    await _db.commit()


async def count_libraries_by_git_url(git_url: str) -> int:
    """返回使用同一个 git_url 的 library 数量（用于判断 monorepo 共享）"""
    async with _db.execute(
        "SELECT COUNT(*) FROM libraries WHERE git_url = ?", (git_url,)
    ) as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


# ── Analysis Runs ─────────────────────────────────────────────────────────────

async def create_run(library_id: int) -> int:
    cur = await _db.execute(
        "INSERT INTO analysis_runs (library_id) VALUES (?)", (library_id,)
    )
    await _db.commit()
    return cur.lastrowid


async def get_run(run_id: int) -> Optional[dict]:
    cur = await _db.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,))
    return _row(await cur.fetchone())


async def list_runs_for_library(library_id: int) -> list[dict]:
    cur = await _db.execute(
        "SELECT * FROM analysis_runs WHERE library_id = ? ORDER BY created_at DESC",
        (library_id,),
    )
    return [_row(r) for r in await cur.fetchall()]


async def update_run(
    run_id: int,
    status: str,
    error_msg: Optional[str] = None,
    result: Optional[dict] = None,
    duration_ms: Optional[int] = None,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
) -> None:
    fields = ["status = ?"]
    params: list = [status]
    if error_msg is not None:
        fields.append("error_msg = ?")
        params.append(error_msg)
    if result is not None:
        fields.append("result = ?")
        params.append(json.dumps(result, ensure_ascii=False))
    if duration_ms is not None:
        fields.append("duration_ms = ?")
        params.append(duration_ms)
    if started_at is not None:
        fields.append("started_at = ?")
        params.append(started_at)
    if finished_at is not None:
        fields.append("finished_at = ?")
        params.append(finished_at)
        # 自动计算 duration_ms
        if duration_ms is None:
            # 从 started_at 或 created_at 计算
            cur = await _db.execute(
                "SELECT started_at, created_at FROM analysis_runs WHERE id = ?", (run_id,)
            )
            row = await cur.fetchone()
            if row:
                start_time = row[0] or row[1]  # started_at or created_at
                if start_time:
                    from datetime import datetime
                    try:
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        end_dt = datetime.fromisoformat(finished_at.replace('Z', '+00:00'))
                        calc_ms = int((end_dt - start_dt).total_seconds() * 1000)
                        fields.append("duration_ms = ?")
                        params.append(calc_ms)
                    except Exception:
                        pass
    params.append(run_id)
    await _db.execute(
        f"UPDATE analysis_runs SET {', '.join(fields)} WHERE id = ?", params
    )
    await _db.commit()


# ── Status helpers ────────────────────────────────────────────────────────────

async def count_downloads_running() -> int:
    """返回当前 dl_status='running' 的库数量。"""
    async with _db.execute(
        "SELECT COUNT(*) FROM libraries WHERE dl_status='running'"
    ) as cur:
        row = await cur.fetchone()
        return row[0] if row else 0


async def list_downloads_running() -> list[dict]:
    """返回当前 dl_status='running' 的库列表。"""
    async with _db.execute(
        "SELECT id, name, dl_started_at FROM libraries WHERE dl_status='running'"
    ) as cur:
        return [_row(r) for r in await cur.fetchall()]


async def get_dl_status_counts() -> dict[str, int]:
    async with _db.execute(
        "SELECT dl_status, COUNT(*) FROM libraries GROUP BY dl_status"
    ) as cur:
        return {row[0]: row[1] for row in await cur.fetchall()}


async def get_run_status_counts() -> dict[str, int]:
    """最新一次 run 的 status 分布（无 run 的库计入 'none'）。"""
    async with _db.execute("""
        SELECT COALESCE(r.status, 'none') AS s, COUNT(l.id)
        FROM libraries l
        LEFT JOIN analysis_runs r ON r.id = (
            SELECT id FROM analysis_runs
            WHERE library_id = l.id
            ORDER BY created_at DESC LIMIT 1
        )
        GROUP BY s
    """) as cur:
        return {row[0]: row[1] for row in await cur.fetchall()}


async def reset_stale_states() -> tuple[int, int]:
    """重置因服务崩溃/重启遗留的 stale 状态。
    Returns: (dl_reset_count, run_reset_count)
    """
    cur = await _db.execute(
        "UPDATE libraries SET dl_status='pending', dl_error='服务重启，下载中断' "
        "WHERE dl_status='running'"
    )
    dl_count = cur.rowcount
    cur = await _db.execute(
        "UPDATE analysis_runs SET status='failed', error_msg='服务重启，任务中断' "
        "WHERE status IN ('running', 'pending')"
    )
    run_count = cur.rowcount
    await _db.commit()
    return dl_count, run_count