from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

from tiktok_ai_analytics.config import load_settings


class CallbackHandler(BaseHTTPRequestHandler):
    oauth_code: str | None = None

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]

        if code:
            CallbackHandler.oauth_code = code
            body = "Auth code received. You can close this window and return to terminal."
            self.send_response(200)
        else:
            body = "No code found in callback URL."
            self.send_response(400)

        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

        print("code:", code)
        print("state:", state)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    settings = load_settings()
    uri = urlparse(settings.tiktok_redirect_uri)

    host = uri.hostname or "localhost"
    port = uri.port or 3000

    if not uri.scheme.startswith("http"):
        raise RuntimeError("TIKTOK_REDIRECT_URI must be an http(s) URL")

    server = HTTPServer((host, port), CallbackHandler)
    print(f"Listening for OAuth callback on {host}:{port} {uri.path or '/'}")
    print("After authorizing, this server will print your code and exit.")

    while CallbackHandler.oauth_code is None:
        server.handle_request()

    code_path = PROJECT_ROOT / ".oauth_code.txt"
    code_path.write_text(CallbackHandler.oauth_code + "\n", encoding="utf-8")
    print(f"Saved code to {code_path}")


if __name__ == "__main__":
    main()
