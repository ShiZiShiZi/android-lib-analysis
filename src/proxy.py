"""
透明 HTTP 代理，用于修复 Bailian API SSE 流中 message_start 事件缺少 usage 字段的问题。

opencode → http://127.0.0.1:8765 → 真实 Bailian endpoint
"""
import http.client
import http.server
import json
import ssl
import threading
import urllib.parse


class _ProxyHandler(http.server.BaseHTTPRequestHandler):
    target_base: str = ""  # 由 start_proxy 绑定到子类
    verbose: bool = False

    def do_GET(self):
        self._proxy("GET")

    def do_POST(self):
        self._proxy("POST")

    def _proxy(self, method: str) -> None:
        parsed = urllib.parse.urlparse(self.server.target_base)
        host = parsed.netloc
        upstream_path = parsed.path.rstrip("/") + self.path

        if self.verbose:
            print(f"[proxy] {method} {self.path} → {parsed.scheme}://{host}{upstream_path}",
                  file=__import__("sys").stderr)

        # 读请求体
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else None

        # 转发 headers（跳过 Host / Content-Length，由 http.client 自动处理）
        fwd_headers = {
            k: v for k, v in self.headers.items()
            if k.lower() not in ("host", "content-length")
        }

        if parsed.scheme == "https":
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            conn = http.client.HTTPSConnection(host, context=ctx, timeout=300)
        else:
            conn = http.client.HTTPConnection(host, timeout=300)

        try:
            conn.request(method, upstream_path, body=body, headers=fwd_headers)
            resp = conn.getresponse()
            content_type = resp.getheader("Content-Type", "")

            self.send_response(resp.status)

            # 转发 headers，跳过长度/编码相关字段（由代理层自行控制）
            for k, v in resp.getheaders():
                if k.lower() in ("transfer-encoding", "connection", "content-length"):
                    continue
                self.send_header(k, v)

            if "text/event-stream" in content_type:
                self.end_headers()
                self._stream_sse(resp)
            else:
                data = resp.read()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except Exception as exc:
            try:
                self.send_error(502, str(exc))
            except Exception:
                pass
        finally:
            conn.close()

    def _stream_sse(self, resp: http.client.HTTPResponse) -> None:
        """逐 SSE event 读取并转发，对 message_start 事件注入缺失的 usage 字段。"""
        current: list[str] = []
        while True:
            raw = resp.readline()
            if not raw:
                # 流结束：刷出残余 event
                if current:
                    self._flush_event(current)
                break
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if line == "":
                # 空行 = SSE event 分隔符
                if current:
                    self._flush_event(current)
                    current = []
            else:
                current.append(line)

    def _flush_event(self, lines: list[str]) -> None:
        """修补后将 event 写入客户端，格式：lines joined by \n，以 \n\n 结尾。"""
        patched = _patch_event(lines, verbose=self.verbose)
        try:
            self.wfile.write(("\n".join(patched) + "\n\n").encode("utf-8"))
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):  # noqa: A002
        pass  # 屏蔽 BaseHTTPRequestHandler 的默认标准输出日志


def _patch_event(lines: list[str], verbose: bool = False) -> list[str]:
    """若 data 行是 message_start 且缺 usage，注入 usage={input_tokens:0, output_tokens:0}。"""
    result = []
    for line in lines:
        if line.startswith("data: "):
            try:
                obj = json.loads(line[6:])
                if (
                    obj.get("type") == "message_start"
                    and isinstance(obj.get("message"), dict)
                    and "usage" not in obj["message"]
                ):
                    obj["message"]["usage"] = {
                        "input_tokens": 0,
                        "output_tokens": 0,
                    }
                    line = "data: " + json.dumps(
                        obj, ensure_ascii=False, separators=(",", ":")
                    )
            except (json.JSONDecodeError, KeyError, TypeError):
                pass  # 安全降级，原样透传
        result.append(line)
    return result


def start_proxy(target_url: str, port: int = 0, verbose: bool = False) -> http.server.HTTPServer:
    """
    启动透明代理，监听 127.0.0.1:<port>，将请求转发到 target_url。
    返回 HTTPServer 实例（后台 daemon 线程运行）。
    """
    class Handler(_ProxyHandler):
        pass

    Handler.target_base = target_url
    Handler.verbose = verbose

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    server.target_base = target_url  # 供 _proxy() 读取
    # poll_interval=0.05 → stop_proxy() 最多阻塞 50ms（默认 0.5s 会阻塞 500ms）
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.05), daemon=True)
    thread.start()
    return server


def stop_proxy(server: http.server.HTTPServer) -> None:
    """停止代理服务器。"""
    server.shutdown()
