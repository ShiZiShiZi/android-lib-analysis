"""GitHub URL 解析器：从各种格式的 GitHub URL 中提取 owner/repo/branch/path"""
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


@dataclass
class GitHubRepoInfo:
    """GitHub 仓库信息"""
    owner: str
    repo: str
    branch: Optional[str] = None
    sub_path: Optional[str] = None
    original_url: str = ""
    
    @property
    def clone_url(self) -> str:
        """返回用于 git clone 的 URL"""
        return f"https://github.com/{self.owner}/{self.repo}.git"
    
    @property
    def repo_dir_name(self) -> str:
        """返回本地存储目录名（owner-repo 格式，避免冲突）"""
        return f"{self.owner}-{self.repo}"
    
    @property
    def github_url(self) -> str:
        """返回 GitHub 仓库主页 URL"""
        return f"https://github.com/{self.owner}/{self.repo}"


def parse_github_url(url: str) -> Optional[GitHubRepoInfo]:
    """
    解析 GitHub URL，支持多种格式：
    
    格式1: https://github.com/owner/repo
    格式2: https://github.com/owner/repo/tree/branch
    格式3: https://github.com/owner/repo/tree/branch/path/to/package
    格式4: git@github.com:owner/repo.git
    格式5: https://github.com/owner/repo.git
    
    Returns:
        GitHubRepoInfo 或 None（解析失败）
    """
    if not url or not url.strip():
        return None
    
    url = url.strip()
    
    # 格式4: git@github.com:owner/repo.git
    ssh_pattern = r'^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$'
    match = re.match(ssh_pattern, url)
    if match:
        return GitHubRepoInfo(
            owner=match.group(1),
            repo=match.group(2),
            original_url=url
        )
    
    # 尝试解析为 HTTP(S) URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    parsed = urlparse(url)
    
    if parsed.netloc not in ('github.com', 'www.github.com'):
        return None
    
    path_parts = [p for p in parsed.path.split('/') if p]
    
    if len(path_parts) < 2:
        return None
    
    owner = path_parts[0]
    repo = path_parts[1]
    
    # 移除 .git 后缀
    if repo.endswith('.git'):
        repo = repo[:-4]
    
    branch = None
    sub_path = None
    
    # 检查是否有 tree/blob 指向特定分支和路径
    # 格式: /owner/repo/tree/branch/path/to/package
    if len(path_parts) >= 4 and path_parts[2] in ('tree', 'blob', 'commit'):
        branch = path_parts[3]
        if len(path_parts) > 4:
            sub_path = '/'.join(path_parts[4:])
    
    return GitHubRepoInfo(
        owner=owner,
        repo=repo,
        branch=branch,
        sub_path=sub_path,
        original_url=url
    )


def validate_github_url(url: str) -> tuple[bool, str]:
    """
    验证 GitHub URL 是否有效
    
    Returns:
        (is_valid, error_message)
    """
    if not url or not url.strip():
        return False, "URL 不能为空"
    
    info = parse_github_url(url)
    if not info:
        return False, f"无法解析 GitHub URL: {url}"
    
    return True, ""


# 测试用例
if __name__ == "__main__":
    test_urls = [
        "https://github.com/expo/expo",
        "https://github.com/expo/expo/tree/main",
        "https://github.com/expo/expo/tree/main/packages/expo-background-fetch",
        "https://github.com/react-native-maps/react-native-maps",
        "https://github.com/software-mansion/react-native-reanimated/tree/main/packages/react-native-reanimated",
        "git@github.com:invertase/react-native-firebase.git",
        "https://github.com/expo/expo.git",
        "https://github.com/expo/expo/tree/sdk-51/packages/expo-camera",
    ]
    
    for url in test_urls:
        info = parse_github_url(url)
        if info:
            print(f"URL: {url}")
            print(f"  owner: {info.owner}, repo: {info.repo}")
            print(f"  branch: {info.branch}, sub_path: {info.sub_path}")
            print(f"  clone_url: {info.clone_url}")
            print()
        else:
            print(f"解析失败: {url}")