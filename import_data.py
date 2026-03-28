"""从导出的 JSON 回填 analysis_runs.result 字段"""
import asyncio
import json
import sys
from pathlib import Path

import aiosqlite

DB_PATH = Path(__file__).parent / "plugins.db"

RESULT_KEYS = ["cloud_services", "payment", "license", "mobile_platform",
               "features", "ecosystem", "dependency_analysis", "code_stats"]


async def import_data(json_path: str):
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    assert isinstance(data, list), "期望 JSON 为列表"

    async with aiosqlite.connect(DB_PATH) as db:
        plugin_count = 0
        run_count = 0

        for item in data:
            name = item["name"]
            run_status = item.get("run_status", "")
            if run_status != "done":
                continue

            # 查找 plugin
            cur = await db.execute("SELECT id FROM plugins WHERE name=?", (name,))
            row = await cur.fetchone()
            if not row:
                # 插件不存在则新建
                await db.execute(
                    "INSERT INTO plugins (name, dl_status) VALUES (?, ?)",
                    (name, item.get("dl_status", "cleaned"))
                )
                cur = await db.execute("SELECT id FROM plugins WHERE name=?", (name,))
                row = await cur.fetchone()
                plugin_count += 1
            plugin_id = row[0]

            # 组装 result JSON
            result = {k: item[k] for k in RESULT_KEYS if k in item}
            result_json = json.dumps(result, ensure_ascii=False)

            # 更新最新一条 analysis_run 的 result
            cur2 = await db.execute(
                "SELECT id FROM analysis_runs WHERE plugin_id=? ORDER BY id DESC LIMIT 1",
                (plugin_id,)
            )
            existing = await cur2.fetchone()
            if existing:
                await db.execute(
                    "UPDATE analysis_runs SET result=?, status='done' WHERE id=?",
                    (result_json, existing[0])
                )
            else:
                await db.execute(
                    "INSERT INTO analysis_runs (plugin_id, status, result) VALUES (?, 'done', ?)",
                    (plugin_id, result_json)
                )
            run_count += 1

        await db.commit()
        print(f"✓ 回填完成：{plugin_count} 新插件，{run_count} 条分析记录已更新")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("用法: python3 import_data.py <json文件路径>")
        sys.exit(1)
    asyncio.run(import_data(path))
