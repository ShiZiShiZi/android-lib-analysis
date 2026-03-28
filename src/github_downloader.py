"""GitHub 仓库克隆器：从 GitHub 克隆仓库到本地"""
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from src.github_parser import GitHubRepoInfo, parse_github_url

logger = logging.getLogger(__name__)

PROJECT_DIR = Path(__file__).parent.parent
REPOS_DIR = PROJECT_DIR / "repos"


def ensure_repos_dir() -> None:
    """确保 repos 目录存在"""
    REPOS_DIR.mkdir(parents=True, exist_ok=True)


def clone_repo(
    repo_info: GitHubRepoInfo,
    depth: int = 1,
    timeout: int = 600,
    use_ssh: bool = True,
    force: bool = False,
) -> Path:
    """
    克隆 GitHub 仓库到本地
    
    Args:
        repo_info: GitHub 仓库信息
        depth: git clone depth，默认 1（shallow clone）
        timeout: 超时时间（秒）
        use_ssh: 是否使用 SSH 方式克隆，默认 True
        force: 是否强制删除已存在的目录重新克隆，默认 False
    
    Returns:
        本地仓库路径
    
    Raises:
        RuntimeError: 克隆失败
    """
    ensure_repos_dir()
    
    repo_dir = REPOS_DIR / repo_info.repo_dir_name
    
    if repo_dir.exists():
        if force:
            logger.info(f"强制删除已存在的目录: {repo_dir}")
            shutil.rmtree(repo_dir)
        else:
            logger.info(f"目录已存在，跳过克隆: {repo_dir}")
            return repo_dir
    
    # 构建 clone URL（优先 SSH）
    clone_url = repo_info.clone_url
    if use_ssh:
        clone_url = f"git@github.com:{repo_info.owner}/{repo_info.repo}.git"
    
    # 构建 git clone 命令
    cmd = [
        "git", "clone",
        "--depth", str(depth),
    ]
    
    # 如果指定了分支，添加 --branch 参数
    if repo_info.branch:
        cmd.extend(["--branch", repo_info.branch])
    
    cmd.extend([
        clone_url,
        str(repo_dir),
    ])
    
    logger.info(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "未知错误"
            raise RuntimeError(f"git clone 失败: {error_msg}")
        
        logger.info(f"克隆成功: {repo_dir}")
        return repo_dir
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"git clone 超时（{timeout}秒）")
    except FileNotFoundError:
        raise RuntimeError("未找到 git 命令，请确保已安装 git")


def clone_from_url(
    github_url: str,
    depth: int = 1,
    timeout: int = 600,
    use_ssh: bool = True,
    force: bool = False,
) -> tuple[Path, GitHubRepoInfo]:
    """
    从 GitHub URL 克隆仓库
    
    Args:
        github_url: GitHub URL
        depth: git clone depth
        timeout: 超时时间（秒）
        use_ssh: 是否使用 SSH 方式克隆，默认 True
        force: 是否强制删除已存在的目录重新克隆，默认 False
    
    Returns:
        (本地仓库路径, GitHubRepoInfo)
    
    Raises:
        ValueError: URL 解析失败
        RuntimeError: 克隆失败
    """
    repo_info = parse_github_url(github_url)
    if not repo_info:
        raise ValueError(f"无法解析 GitHub URL: {github_url}")
    
    repo_path = clone_repo(repo_info, depth=depth, timeout=timeout, use_ssh=use_ssh, force=force)
    return repo_path, repo_info


def get_package_path(repo_dir: Path, sub_path: Optional[str] = None) -> Path:
    """
    获取包的实际路径
    
    Args:
        repo_dir: 仓库根目录
        sub_path: 子路径（可能为空）
    
    Returns:
        包的完整路径
    """
    if sub_path:
        package_path = repo_dir / sub_path
        if not package_path.exists():
            raise RuntimeError(f"子路径不存在: {package_path}")
        return package_path
    return repo_dir


def get_repo_size_mb(repo_dir: Path) -> float:
    """计算目录大小（MB）"""
    if not repo_dir.exists():
        return 0.0
    
    total = 0
    for dirpath, _, filenames in os.walk(repo_dir):
        for fn in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, fn))
            except OSError:
                pass
    return total / (1024 * 1024)


def cleanup_repo(repo_dir_name: str) -> None:
    """删除仓库目录"""
    repo_dir = REPOS_DIR / repo_dir_name
    if repo_dir.exists():
        shutil.rmtree(repo_dir, ignore_errors=True)
        logger.info(f"已删除仓库目录: {repo_dir}")


def get_commit_sha(repo_dir: Path) -> Optional[str]:
    """获取当前 commit SHA"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()[:8]  # 返回短 SHA
    except Exception:
        pass
    return None


if __name__ == "__main__":
    # 测试
    import sys
    logging.basicConfig(level=logging.INFO)
    
    test_urls = [
        "https://github.com/expo/expo/tree/main/packages/expo-background-fetch",
        "https://github.com/react-native-maps/react-native-maps",
    ]
    
    for url in test_urls:
        print(f"\n测试: {url}")
        try:
            repo_path, info = clone_from_url(url)
            print(f"  克隆到: {repo_path}")
            print(f"  子路径: {info.sub_path}")
            if info.sub_path:
                pkg_path = get_package_path(repo_path, info.sub_path)
                print(f"  包路径: {pkg_path}")
            commit = get_commit_sha(repo_path)
            print(f"  commit: {commit}")
            cleanup_repo(info.repo_dir_name)
        except Exception as e:
            print(f"  错误: {e}")