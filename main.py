#!/usr/bin/env python3
"""
Android Library Analyzer
用法：python main.py <github_url> [--output <file>] [--keep] [--verbose]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from src.github_downloader import cleanup_repo, clone_from_url, get_package_path
from src.proxy import start_proxy, stop_proxy

PROJECT_DIR = Path(__file__).parent
OUTPUT_DIR = PROJECT_DIR / "output"


def run_opencode(repo_path: Path, repo_url: str, verbose: bool, extra_env: dict) -> str:
    prompt = (
        f"分析路径 {repo_path} 下的 Android 三方库，该目录已存在，直接读取即可，禁止执行 git clone 或任何下载操作。"
        f"请依次使用 license-check、mobile-platform-check、cloud-service-check、payment-check、features-check、ecosystem-check、dependency-analysis、code-stats-check 八个 skill 完成分析，"
        f"最终只输出一个 JSON 对象，字段包含 repo_url、analyzed_at、cloud_services、payment、license、mobile_platform、features、ecosystem、dependency_analysis、code_stats。"
        f"输出 JSON 中的 repo_url 字段填写：{repo_url}。"
    )
    cmd = [
        "opencode", "run",
        "--agent", "android-analyzer",
        prompt,
    ]
    env = {**os.environ, **extra_env}
    if verbose:
        print(f"[opencode] 执行命令: {' '.join(cmd)}", file=sys.stderr)

    if verbose:
        proc = subprocess.Popen(
            cmd,
            cwd=str(PROJECT_DIR),
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=True,
            env=env,
        )
        stdout_lines = []
        try:
            for line in proc.stdout:
                print(line, end="", file=sys.stderr)
                stdout_lines.append(line)
        except BrokenPipeError:
            pass
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

        stdout = "".join(stdout_lines)
        returncode = proc.returncode
    else:
        try:
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_DIR),
                capture_output=True,
                text=True,
                timeout=900,
                env=env,
            )
            stdout = result.stdout
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            print(f"[opencode] 超时（900秒）", file=sys.stderr)
            return ""

    if verbose:
        print(f"[opencode] 返回码: {returncode}", file=sys.stderr)

    if returncode not in (0, -9, -15):
        print(f"[opencode] 警告：非零返回码 {returncode}，可能分析失败或被中断", file=sys.stderr)

    return stdout


_REQUIRED_KEYS = {"repo_url", "cloud_services", "payment", "license", "mobile_platform", "features", "ecosystem", "dependency_analysis", "code_stats"}


def extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text)
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", text):
        try:
            obj, _ = decoder.raw_decode(text, m.start())
            if isinstance(obj, dict) and _REQUIRED_KEYS.issubset(obj):
                return obj
        except json.JSONDecodeError:
            continue
    raise ValueError(f"输出中未找到包含所有必要字段 {_REQUIRED_KEYS} 的 JSON 对象")


def _serialize_report(report: dict) -> str:
    def json_serializer(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        elif isinstance(obj, (set, frozenset)):
            return list(obj)
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(report, ensure_ascii=False, indent=2, default=json_serializer)


def main():
    parser = argparse.ArgumentParser(description="分析 Android 三方库")
    parser.add_argument("url", help="GitHub URL（如 https://github.com/square/okhttp 或 https://github.com/square/okhttp/tree/master/okhttp-bom）")
    parser.add_argument("--output", "-o", help="JSON 输出路径（默认 output/<repo_name>.json）")
    parser.add_argument("--keep", action="store_true", help="分析完成后保留克隆的临时目录")
    parser.add_argument("--verbose", "-v", action="store_true", help="打印调试信息")
    args = parser.parse_args()

    github_url = args.url
    print(f"正在从 GitHub 克隆 {github_url} ...")
    try:
        repo_path, repo_info = clone_from_url(github_url, use_ssh=False)
    except (ValueError, RuntimeError) as e:
        print(f"克隆失败: {e}", file=sys.stderr)
        sys.exit(1)

    if repo_info.sub_path:
        package_path = get_package_path(repo_path, repo_info.sub_path)
        print(f"克隆完成: {repo_path}，分析子路径: {package_path}")
    else:
        package_path = repo_path
        print(f"克隆完成: {repo_path}")

    try:
        config_path = Path.home() / ".config/opencode/opencode.json"
        if not config_path.exists():
            print(f"错误：opencode 配置文件不存在: {config_path}", file=sys.stderr)
            sys.exit(1)

        try:
            config = json.loads(config_path.read_text())
        except json.JSONDecodeError as e:
            print(f"错误：opencode 配置文件格式错误: {e}", file=sys.stderr)
            sys.exit(1)

        real_url = config["provider"]["bailian-coding-plan"]["options"]["baseURL"]
        proxy = None
        tmp_home = None
        try:
            proxy = start_proxy(real_url, port=0, verbose=args.verbose)
            if proxy is None:
                print("错误：代理启动失败", file=sys.stderr)
                sys.exit(1)

            actual_port = proxy.server_address[1]

            tmp_home = Path(tempfile.mkdtemp(prefix="opencode_run_"))
            tmp_cfg_dir = tmp_home / ".config" / "opencode"
            tmp_cfg_dir.mkdir(parents=True)
            run_config = json.loads(config_path.read_text())
            run_config["provider"]["bailian-coding-plan"]["options"]["baseURL"] = (
                f"http://127.0.0.1:{actual_port}"
            )
            (tmp_cfg_dir / "opencode.json").write_text(json.dumps(run_config, indent=4))

            tmp_opencode_data = tmp_home / ".local" / "share" / "opencode"
            tmp_opencode_data.mkdir(parents=True)
            global_bin = Path.home() / ".local" / "share" / "opencode" / "bin"
            if global_bin.exists():
                try:
                    (tmp_opencode_data / "bin").symlink_to(global_bin)
                except (FileExistsError, OSError) as e:
                    print(f"警告：创建 bin 符号链接失败（非致命）: {e}", file=sys.stderr)

            print("正在分析（可能需要数分钟）...")
            raw_output = run_opencode(
                package_path, github_url, args.verbose, {
                    "HOME": str(tmp_home),
                    "XDG_CONFIG_HOME": str(tmp_home / ".config"),
                    "XDG_DATA_HOME":   str(tmp_home / ".local" / "share"),
                    "XDG_CACHE_HOME":  str(tmp_home / ".cache"),
                    "XDG_STATE_HOME":  str(tmp_home / ".local" / "state"),
                }
            )
        finally:
            if proxy is not None:
                try:
                    stop_proxy(proxy)
                except Exception as e:
                    print(f"警告：停止代理失败: {e}", file=sys.stderr)
            if tmp_home is not None:
                try:
                    shutil.rmtree(tmp_home, ignore_errors=True)
                except Exception as e:
                    print(f"警告：清理临时目录失败: {e}", file=sys.stderr)

        if args.verbose:
            print(f"[raw output]\n{raw_output}", file=sys.stderr)

        try:
            report = extract_json(raw_output)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"JSON 解析失败: {e}", file=sys.stderr)
            print("原始输出已写入 output/raw_output.txt", file=sys.stderr)
            OUTPUT_DIR.mkdir(exist_ok=True)
            (OUTPUT_DIR / "raw_output.txt").write_text(raw_output, encoding="utf-8")
            sys.exit(1)

        report.setdefault("analyzed_at", datetime.now(timezone.utc).isoformat())

        OUTPUT_DIR.mkdir(exist_ok=True)
        if args.output:
            out_path = Path(args.output)
        else:
            safe_name = repo_info.repo_dir_name.replace("/", "-").replace("@", "")
            out_path = OUTPUT_DIR / f"{safe_name}.json"

        try:
            out_path.write_text(_serialize_report(report), encoding="utf-8")
            print(f"分析完成，报告已写入: {out_path}")
            print(json.dumps(report, ensure_ascii=False, indent=2))
        except (IOError, OSError, TypeError) as e:
            print(f"错误：无法写入报告文件: {e}", file=sys.stderr)
            sys.exit(1)

    finally:
        if not args.keep:
            try:
                cleanup_repo(repo_info.repo_dir_name)
                if args.verbose:
                    print(f"[cleanup] 已删除临时目录 {repo_path}", file=sys.stderr)
            except Exception as e:
                print(f"警告：清理临时目录失败: {e}", file=sys.stderr)
        else:
            print(f"临时目录保留在: {repo_path}")


if __name__ == "__main__":
    main()