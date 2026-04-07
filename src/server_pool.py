"""opencode serve 多实例管理

支持多个 opencode serve 实例，每个任务完成后重启，确保上下文干净。

使用方式:
    pool = ServerPool(count=10, base_port=4096)
    await pool.start_all()
    
    server = await pool.get_server()
    async with server.client() as client:
        result = await client.run_agent(...)
    
    await pool.stop_all()
"""
import asyncio
import logging
import os
import shutil
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPENCODE_BIN = "/opt/homebrew/bin/opencode"


@dataclass
class ServerInstance:
    """单个 opencode serve 实例"""
    port: int
    db_index: int
    proc: Optional[asyncio.subprocess.Process] = None
    active_tasks: int = 0      # 当前运行中的任务数（用于负载均衡）
    completed_tasks: int = 0   # 本次启动后累计完成的任务数（用于重启判断）
    max_tasks: int = 1         # 每次重启允许的最大任务数
    _home_dir: Optional[Path] = None
    _child_pid: Optional[int] = None  # 记录子进程 PID，防止误杀其他进程
    
    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"
    
    @property
    def home_dir(self) -> Path:
        if self._home_dir is None:
            self._home_dir = Path(f"/tmp/opencode_server_{self.db_index}")
        return self._home_dir
    
    @property
    def db_path(self) -> Path:
        return self.home_dir / ".local" / "share" / "opencode"
    
    def _setup_home(self) -> None:
        """设置独立的 HOME 目录"""
        home = self.home_dir
        
        if home.exists():
            shutil.rmtree(home)
        
        home.mkdir(parents=True, exist_ok=True)
        
        config_src = Path.home() / ".config" / "opencode" / "opencode.json"
        config_dst = home / ".config" / "opencode" / "opencode.json"
        config_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(config_src, config_dst)
        
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        global_cache = Path.home() / ".local" / "share" / "opencode" / "bin"
        if global_cache.exists():
            local_cache = self.db_path / "bin"
            if not local_cache.exists():
                local_cache.symlink_to(global_cache)
    
    async def _kill_existing_server(self) -> bool:
        """启动前清理：只 kill 端口上的 opencode 进程，防止误杀 uvicorn 主进程"""
        try:
            result = await asyncio.create_subprocess_exec(
                "lsof", "-ti", f":{self.port}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            stdout, _ = await result.communicate()
            pids = stdout.decode().strip().split()
            
            if pids:
                killed_pids = []
                for pid in pids:
                    pid_int = int(pid)
                    
                    try:
                        check = await asyncio.create_subprocess_exec(
                            "ps", "-p", str(pid_int), "-o", "comm=",
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        comm_out, _ = await check.communicate()
                        proc_name = comm_out.decode().strip()
                        
                        if "opencode" in proc_name:
                            os.kill(pid_int, signal.SIGTERM)
                            killed_pids.append(str(pid_int))
                        else:
                            logger.debug("[server:%d] 跳过非 opencode 进程 (PID: %d, 名称: %s)", 
                                         self.db_index, pid_int, proc_name)
                    except ProcessLookupError:
                        pass
                    except Exception as e:
                        logger.debug("[server:%d] 检查进程 %d 失败: %s", self.db_index, pid_int, e)
                
                if killed_pids:
                    await asyncio.sleep(0.5)
                    logger.info("[server:%d] 已 kill 旧 opencode 进程 (PID: %s)", self.db_index, ", ".join(killed_pids))
                    return True
        except Exception as e:
            logger.debug("[server:%d] 查找旧进程失败: %s", self.db_index, e)
        return False
    
    async def start(self, wait_seconds: float = 30.0) -> bool:
        """启动 server 实例"""
        await self._kill_existing_server()
        
        self._setup_home()
        
        env = os.environ.copy()
        env["HOME"] = str(self.home_dir)
        
        log_file = self.home_dir / "server.log"
        self.proc = await asyncio.create_subprocess_exec(
            OPENCODE_BIN,
            "serve",
            "--port", str(self.port),
            stdout=open(log_file, "w"),
            stderr=open(log_file, "w"),
            env=env,
        )
        self._child_pid = self.proc.pid  # 记录子进程 PID
        
        for _ in range(int(wait_seconds * 10)):
            try:
                async with httpx.AsyncClient(timeout=2) as client:
                    resp = await client.get(f"{self.url}/agent")
                    if resp.status_code == 200:
                        logger.info("[server:%d] 已启动，端口 %d (PID: %d)", self.db_index, self.port, self._child_pid)
                        return True
            except Exception:
                await asyncio.sleep(0.1)
        
        if self.proc.returncode is not None:
            logger.error("[server:%d] 启动失败，返回码: %d", self.db_index, self.proc.returncode)
            try:
                with open(log_file) as f:
                    lines = f.readlines()[-10:]
                    for line in lines:
                        logger.error("[server:%d] %s", self.db_index, line.strip())
            except Exception:
                pass
            self._child_pid = None  # 启动失败时清除 PID
            return False
        
        logger.warning("[server:%d] 启动超时", self.db_index)
        return True
    
    async def stop(self) -> None:
        """停止 server 实例，只 kill 自己启动的子进程"""
        if self._child_pid:
            try:
                os.kill(self._child_pid, signal.SIGTERM)
                logger.info("[server:%d] 发送 SIGTERM 到子进程 (PID: %d)", self.db_index, self._child_pid)
                
                if self.proc:
                    try:
                        await asyncio.wait_for(self.proc.wait(), timeout=5)
                        logger.info("[server:%d] 子进程已正常退出", self.db_index)
                    except asyncio.TimeoutError:
                        logger.warning("[server:%d] 子进程未响应 SIGTERM，强制 SIGKILL", self.db_index)
                        try:
                            os.kill(self._child_pid, signal.SIGKILL)
                            await asyncio.wait_for(self.proc.wait(), timeout=2)
                        except (ProcessLookupError, asyncio.TimeoutError):
                            pass
            except ProcessLookupError:
                logger.info("[server:%d] 子进程已不存在 (PID: %d)", self.db_index, self._child_pid)
        
        self.proc = None
        self._child_pid = None
        self.active_tasks = 0
        self.completed_tasks = 0
        logger.info("[server:%d] 已停止", self.db_index)
    
    async def restart(self) -> bool:
        """重启 server 实例"""
        logger.info("[server:%d] 重启中... (已完成任务: %d)", self.db_index, self.completed_tasks)
        await self.stop()
        await asyncio.sleep(0.5)
        result = await self.start()
        return result
    
    def is_running(self) -> bool:
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', self.port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def should_restart(self) -> bool:
        return self.completed_tasks >= self.max_tasks


class ServerPool:
    """管理多个 opencode serve 实例"""
    
    def __init__(self, count: int = 10, base_port: int = 4096, max_tasks_per_server: int = 1):
        self.servers = [
            ServerInstance(
                port=base_port + i,
                db_index=i,
                max_tasks=max_tasks_per_server
            )
            for i in range(count)
        ]
        self._lock = asyncio.Lock()
    
    async def start_all(self) -> int:
        """启动所有 server，返回成功数量"""
        tasks = [s.start() for s in self.servers]
        results = await asyncio.gather(*tasks)
        success = sum(1 for r in results if r)
        logger.info("[pool] 启动完成: %d/%d", success, len(self.servers))
        return success
    
    async def stop_all(self) -> None:
        """停止所有 server"""
        tasks = [s.stop() for s in self.servers]
        await asyncio.gather(*tasks)
        logger.info("[pool] 已停止所有 server")
    
    async def get_server(self) -> ServerInstance:
        """获取一个可用的 server，会自动重启需要重启的 server"""
        async with self._lock:
            min_active = min(s.active_tasks for s in self.servers)
            
            for server in self.servers:
                if server.active_tasks == min_active:
                    if server.should_restart():
                        await server.restart()
                    server.active_tasks += 1
                    return server
            
            return self.servers[0]
    
    def release_server(self, server: ServerInstance) -> None:
        """释放 server（任务完成后调用）"""
        server.active_tasks = max(0, server.active_tasks - 1)
        server.completed_tasks += 1
        
        if server.completed_tasks >= server.max_tasks and server.active_tasks == 0:
            asyncio.create_task(self._restart_server_async(server))
    
    async def _restart_server_async(self, server: ServerInstance) -> None:
        """异步重启 server"""
        try:
            await server.restart()
            print(f"[server:{server.db_index}] 任务完成后自动重启成功")
            logger.info("[server:%d] 任务完成后自动重启成功", server.db_index)
        except Exception as e:
            print(f"[server:{server.db_index}] 自动重启失败: {e}")
            logger.error("[server:%d] 自动重启失败: %s", server.db_index, e)


_pool: Optional[ServerPool] = None


async def get_server_pool() -> ServerPool:
    """获取全局 server pool 单例"""
    global _pool
    if _pool is None:
        _pool = ServerPool(count=10, base_port=4096, max_tasks_per_server=1)
        await _pool.start_all()
    return _pool


async def ensure_pool_running() -> None:
    """确保 pool 正在运行"""
    pool = await get_server_pool()
    for server in pool.servers:
        if not server.is_running():
            await server.start()