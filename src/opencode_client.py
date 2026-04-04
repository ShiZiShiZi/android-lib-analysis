"""opencode serve HTTP API 客户端"""
import asyncio
import json
import logging
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Optional

import httpx

logger = logging.getLogger(__name__)

OPENCODE_SERVER = "http://localhost:4096"


class OpenCodeClient:
    """封装 opencode serve HTTP API 调用。"""

    def __init__(self, base_url: str = OPENCODE_SERVER, timeout: float = 1800):
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def create_session(self, cwd: Optional[str] = None) -> str:
        """创建新 session，返回 session_id。"""
        payload = {}
        if cwd:
            payload["cwd"] = cwd
        resp = await self._client.post(f"{self.base_url}/session", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["id"]

    async def send_message(
        self,
        session_id: str,
        prompt: str,
        agent: str = "android-analyzer",
    ) -> dict:
        """发送消息到 session，等待完成，返回结果。"""
        resp = await self._client.post(
            f"{self.base_url}/session/{session_id}/message",
            json={"parts": [{"type": "text", "text": prompt}], "agent": agent},
        )
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception as e:
            raise ValueError(f"opencode 返回无效响应: {e}")

    async def get_session(self, session_id: str) -> dict:
        """获取 session 状态。"""
        resp = await self._client.get(f"{self.base_url}/session/{session_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_session_messages(self, session_id: str, limit: int = 50) -> list:
        """获取 session 的消息列表。"""
        resp = await self._client.get(f"{self.base_url}/session/{session_id}/message?limit={limit}")
        resp.raise_for_status()
        return resp.json()

    async def delete_session(self, session_id: str) -> bool:
        """删除 session。"""
        resp = await self._client.delete(f"{self.base_url}/session/{session_id}")
        return resp.status_code == 200

    async def run_agent(
        self,
        prompt: str,
        agent: str = "android-analyzer",
        cwd: Optional[str] = None,
        on_session_created: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> tuple[dict, str]:
        """一次性执行：创建 session → 发送消息 → 返回 (结果, session_id)。"""
        session_id = await self.create_session(cwd)
        
        if on_session_created:
            await on_session_created(session_id)
        
        result = await self.send_message(session_id, prompt, agent)
        return result, session_id

    @staticmethod
    def extract_text_from_response(response: dict) -> str:
        """从 API 响应中提取文本输出。"""
        parts = response.get("parts", [])
        texts = []
        for part in parts:
            if part.get("type") == "text":
                texts.append(part.get("text", ""))
        return "\n".join(texts)


PROJECT_DIR = Path(__file__).parent.parent
LOG_DIR = PROJECT_DIR / "logs"


async def run_full_analysis(
    repo_path: str,
    git_url: str,
    sub_path: Optional[str] = None,
    on_log: Optional[Callable[[str], Awaitable[None]]] = None,
    on_session_created: Optional[Callable[[str], Awaitable[None]]] = None,
    server_url: Optional[str] = None,
) -> tuple[dict, Optional[str]]:
    """全量分析：调用 opencode serve API，结果写入临时文件。
    
    返回: (report_dict, session_id)
    """
    result_file = Path(tempfile.gettempdir()) / f"android_full_{uuid.uuid4().hex}.json"
    
    if sub_path:
        analysis_path = f"{repo_path}/{sub_path}"
        prompt = (
            f"分析路径 {analysis_path} 下的 Android 库，该目录已存在，直接读取即可，禁止执行 git clone 或任何下载操作。"
            f"注意：这是一个 monorepo 中的子包，仓库根目录在 {repo_path}，包目录在 {sub_path}。"
            f"完成全部八步分析后，将最终 JSON 写入文件 {result_file}，禁止在对话中直接输出 JSON。"
            f"JSON 中的 repo_url 字段填写：{git_url}。"
        )
    else:
        analysis_path = repo_path
        prompt = (
            f"分析路径 {analysis_path} 下的 Android 库，该目录已存在，直接读取即可，禁止执行 git clone 或任何下载操作。"
            f"完成全部八步分析后，将最终 JSON 写入文件 {result_file}，禁止在对话中直接输出 JSON。"
            f"JSON 中的 repo_url 字段填写：{git_url}。"
        )

    base_url = server_url or OPENCODE_SERVER
    session_id = None
    
    async with OpenCodeClient(base_url=base_url) as client:
        result, session_id = await client.run_agent(
            prompt,
            agent="android-analyzer",
            cwd=repo_path,
            on_session_created=on_session_created
        )

        if on_log:
            output = OpenCodeClient.extract_text_from_response(result)
            if output:
                await on_log(output)

    if not result_file.exists():
        raise ValueError("android-analyzer 未生成结果文件")

    try:
        raw = result_file.read_text(encoding="utf-8")
        result_file.unlink(missing_ok=True)
        report = json.loads(raw)
        if not isinstance(report, dict):
            raise ValueError("结果文件不是 JSON 对象")
        report.setdefault("analyzed_at", datetime.now(timezone.utc).isoformat())
        return report, session_id
    except json.JSONDecodeError as e:
        result_file.unlink(missing_ok=True)
        raise ValueError(f"结果文件 JSON 解析失败: {e}")