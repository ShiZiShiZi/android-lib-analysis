import asyncio
import json
import logging
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from src.proxy import start_proxy, stop_proxy

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent
LOG_DIR = PROJECT_DIR / "logs"
OUTPUT_DIR = PROJECT_DIR / "output"


@dataclass
class AnalysisResult:
    """分析结果"""
    report: dict
    thinking: str
    content: str


def _make_opencode_env(tmp_home: Path, proxy_port: int) -> dict:
    """构造 opencode 运行所需的隔离环境变量。"""
    config_path = Path.home() / ".config/opencode/opencode.json"
    if not config_path.exists():
        raise FileNotFoundError(f"opencode 配置文件不存在: {config_path}")

    tmp_cfg_dir = tmp_home / ".config" / "opencode"
    tmp_cfg_dir.mkdir(parents=True)
    try:
        run_config = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"opencode 配置文件格式错误: {e}")
    run_config["provider"]["bailian-coding-plan"]["options"]["baseURL"] = (
        f"http://127.0.0.1:{proxy_port}"
    )
    for model_cfg in run_config.get("provider", {}).get("bailian-coding-plan", {}).get("models", {}).values():
        if model_cfg.get("limit"):
            model_cfg["limit"]["output"] = 32768
        thinking = model_cfg.get("options", {}).get("thinking")
        if isinstance(thinking, dict) and "budgetTokens" in thinking:
            thinking["budgetTokens"] = 1024
    (tmp_cfg_dir / "opencode.json").write_text(json.dumps(run_config, indent=4))

    tmp_opencode_data = tmp_home / ".local" / "share" / "opencode"
    tmp_opencode_data.mkdir(parents=True)
    global_bin = Path.home() / ".local" / "share" / "opencode" / "bin"
    if global_bin.exists():
        try:
            (tmp_opencode_data / "bin").symlink_to(global_bin)
        except (FileExistsError, OSError) as e:
            logger.warning(f"创建 bin 符号链接失败（非致命）: {e}")

    return {
        **os.environ,
        "HOME":            str(tmp_home),
        "XDG_CONFIG_HOME": str(tmp_home / ".config"),
        "XDG_DATA_HOME":   str(tmp_home / ".local" / "share"),
        "XDG_CACHE_HOME":  str(tmp_home / ".cache"),
        "XDG_STATE_HOME":  str(tmp_home / ".local" / "state"),
    }


def _format_event_for_log(event_type: str, part: dict) -> str:
    """格式化单个事件为日志文本"""
    if event_type in ("thinking", "reasoning"):
        text = part.get("text", "")
        return text + "\n" if text else ""
    
    elif event_type == "text":
        text = part.get("text", "")
        return text + "\n" if text else ""
    
    return ""


def _extract_json_from_content(content: str) -> Optional[dict]:
    """从 content 中提取 JSON（作为后备方案）"""
    json_match = re.search(r'```json\s*\n([\s\S]*?)\n```', content)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    json_match = re.search(r'\{[\s\S]*"cloud_services"[\s\S]*"payment"[\s\S]*"license"[\s\S]*\}', content)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    return None


async def _run_opencode_streaming(
    cmd: list[str],
    env: dict,
    timeout: int,
    on_event: Optional[Callable[[str, str, str], None]] = None,
) -> tuple[str, int]:
    """
    启动 opencode 子进程，流式处理输出。

    Args:
        cmd: 命令及参数
        env: 环境变量
        timeout: 超时秒数
        on_event: 事件回调 (event_type, formatted_text, raw_line)

    Returns:
        (完整 stdout, 进程 PID)
    """
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(PROJECT_DIR),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        limit=10 * 1024 * 1024,
    )

    if proc.pid is None:
        raise RuntimeError("Failed to start opencode process")

    async def read_stdout() -> None:
        assert proc.stdout
        try:
            async for raw in proc.stdout:
                line = raw.decode("utf-8", errors="replace")
                stdout_lines.append(line)

                if on_event and line.strip():
                    try:
                        event = json.loads(line)
                        event_type = event.get("type", "")
                        part = event.get("part", {})
                        formatted = _format_event_for_log(event_type, part)
                        if formatted:
                            on_event(event_type, formatted, line)
                    except json.JSONDecodeError:
                        if on_event:
                            on_event("raw", line, line)
        except asyncio.CancelledError:
            logger.debug("read_stdout cancelled")
            raise

    async def read_stderr() -> None:
        assert proc.stderr
        try:
            async for raw in proc.stderr:
                stderr_lines.append(raw.decode("utf-8", errors="replace"))
        except asyncio.CancelledError:
            logger.debug("read_stderr cancelled")
            raise

    try:
        await asyncio.wait_for(
            asyncio.gather(read_stdout(), read_stderr(), proc.wait()),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning(f"opencode 进程 {proc.pid} 超时，杀掉进程及其子进程")
        proc.kill()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            logger.error(f"进程 {proc.pid} 无法正常终止，强制杀掉")
        raise RuntimeError(f"opencode 超时（{timeout}秒）")
    except Exception as e:
        logger.error(f"opencode 进程 {proc.pid} 异常: {e}，杀掉进程及其子进程")
        proc.kill()
        try:
            await asyncio.wait_for(proc.wait(), timeout=5)
        except asyncio.TimeoutError:
            logger.error(f"进程 {proc.pid} 无法正常终止，强制杀掉")
        raise
    finally:
        # 确保进程被清理（即使在异常情况下）
        if proc.returncode is None:
            try:
                proc.kill()
                await asyncio.wait_for(proc.wait(), timeout=2)
            except (ProcessLookupError, asyncio.TimeoutError):
                logger.debug(f"进程 {proc.pid} 已被清理或无法杀掉")

    if proc.returncode not in (0, -9, -15):  # 0: 成功, -9: SIGKILL, -15: SIGTERM
        stderr_excerpt = "".join(stderr_lines)[:500]
        raise RuntimeError(f"opencode 返回码: {proc.returncode}\n{stderr_excerpt}")

    return "".join(stdout_lines), proc.pid


async def run_full_analysis(
    repo_path: str,
    git_url: str,
    sub_path: Optional[str] = None,
    log_dir: Optional[Path] = None,
) -> AnalysisResult:
    """
    全量分析：使用 rn-analyzer agent，实时写入日志。

    Args:
        repo_path: 仓库根目录路径
        git_url: 库名或标识
        sub_path: 包在仓库中的相对路径（monorepo 支持）
        log_dir: 日志目录路径（用于实时写入）

    Returns:
        AnalysisResult: 包含 report, thinking, content
    """
    result_file = Path(tempfile.gettempdir()) / f"rn_full_{uuid.uuid4().hex}.json"

    if sub_path:
        analysis_path = f"{repo_path}/{sub_path}"
        prompt = (
            f"分析路径 {analysis_path} 下的 React Native 库，该目录已存在，直接读取即可，禁止执行 git clone 或任何下载操作。"
            f"注意：这是一个 monorepo 中的子包，仓库根目录在 {repo_path}，包目录在 {sub_path}。"
            f"完成全部八步分析后，将最终 JSON 写入文件 {result_file}，禁止在对话中直接输出 JSON。"
            f"JSON 中的 repo_url 字段填写：{git_url}。"
        )
    else:
        analysis_path = repo_path
        prompt = (
            f"分析路径 {analysis_path} 下的 React Native 库，该目录已存在，直接读取即可，禁止执行 git clone 或任何下载操作。"
            f"完成全部八步分析后，将最终 JSON 写入文件 {result_file}，禁止在对话中直接输出 JSON。"
            f"JSON 中的 repo_url 字段填写：{git_url}。"
        )

    config_path = Path.home() / ".config/opencode/opencode.json"
    if not config_path.exists():
        raise FileNotFoundError(f"opencode 配置文件不存在: {config_path}")

    try:
        base_config = json.loads(config_path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"opencode 配置文件格式错误: {e}")

    real_url = base_config["provider"]["bailian-coding-plan"]["options"]["baseURL"]

    thinking_parts: list[str] = []
    content_parts: list[str] = []

    thinking_file = None
    content_file = None
    opencode_pid = None

    if log_dir:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            thinking_file = open(log_dir / "thinking.log", "w", encoding="utf-8")
            content_file = open(log_dir / "analysis.log", "w", encoding="utf-8")
        except (IOError, OSError) as e:
            raise RuntimeError(f"无法创建日志文件: {e}")

    def on_event(event_type: str, formatted: str, raw_line: str) -> None:
        """事件回调，需要处理文件可能已关闭的情况"""
        try:
            if event_type in ("thinking", "reasoning"):
                thinking_parts.append(formatted)
                if thinking_file and not thinking_file.closed:
                    thinking_file.write(formatted)
                    thinking_file.flush()
            elif event_type in ("text", "raw"):
                content_parts.append(formatted)
                if content_file and not content_file.closed:
                    content_file.write(formatted)
                    content_file.flush()
        except (IOError, ValueError) as e:
            logger.warning(f"事件回调中的文件操作失败: {e}")

    proxy = None
    tmp_home = None
    try:
        proxy = start_proxy(real_url, port=0, verbose=False)
        if proxy is None or proxy.server_address is None:
            raise RuntimeError("代理启动失败")
        proxy_port = proxy.server_address[1]

        tmp_home = Path(tempfile.mkdtemp(prefix="oc_full_"))
        env = _make_opencode_env(tmp_home, proxy_port)
        cmd = [
            "opencode", "run",
            "--thinking",
            "--format", "json",
            "--agent", "rn-analyzer",
            prompt
        ]
        stdout, opencode_pid = await _run_opencode_streaming(cmd, env, timeout=1800, on_event=on_event)
    except Exception as e:
        logger.error(f"分析失败: {e}")
        raise
    finally:
        # 分层清理：先清理日志文件，再清理代理，最后清理临时目录
        try:
            if thinking_file and not thinking_file.closed:
                thinking_file.close()
        except Exception as e:
            logger.warning(f"关闭 thinking_file 失败: {e}")

        try:
            if content_file and not content_file.closed:
                content_file.close()
        except Exception as e:
            logger.warning(f"关闭 content_file 失败: {e}")

        # 清理 opencode 进程（精确 kill 指定 PID，避免误杀其他进程）
        if opencode_pid:
            try:
                os.kill(opencode_pid, 9)  # SIGKILL
            except (ProcessLookupError, OSError):
                logger.debug(f"进程 {opencode_pid} 已不存在或无法杀掉")

        # 停止代理
        if proxy:
            try:
                stop_proxy(proxy)
            except Exception as e:
                logger.warning(f"停止代理失败: {e}")

        # 清理临时目录
        if tmp_home:
            try:
                shutil.rmtree(tmp_home, ignore_errors=True)
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")

    thinking = "".join(thinking_parts)
    content = "".join(content_parts)

    report = None
    if result_file.exists():
        try:
            raw = result_file.read_text(encoding="utf-8")
            result_file.unlink(missing_ok=True)
            report = json.loads(raw)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"结果文件读取失败: {e}")

    if report is None:
        report = _extract_json_from_content(content)

    if report is None:
        raise ValueError("rn-analyzer 未生成有效结果，请检查 agent 日志")

    if not isinstance(report, dict):
        raise ValueError(f"结果不是 JSON 对象，得到: {type(report).__name__}")

    report.setdefault("analyzed_at", datetime.now(timezone.utc).isoformat())

    if not thinking:
        thinking = "（未捕获到思考过程，可能模型未启用 thinking 模式）"

    return AnalysisResult(
        report=report,
        thinking=thinking,
        content=content,
    )