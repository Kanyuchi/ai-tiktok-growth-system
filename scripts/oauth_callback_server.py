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
    service: str = "tiktok"  # set before starting server

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]

        if code:
            CallbackHandler.oauth_code = code
            body = f"✅ {self.service.title()} auth code received. You can close this window and return to terminal."
            self.send_response(200)
        else:
            error = params.get("error", ["unknown"])[0]
            body = f"❌ No code found. Error: {error}"
            self.send_response(400)

        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

        print(f"[{self.service.upper()}] code: {code}")
        print(f"[{self.service.upper()}] state: {state}")

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="OAuth callback listener")
    parser.add_argument(
        "--service",
        choices=["tiktok", "canva"],
        default="tiktok",
        help="Which OAuth service to listen for (default: tiktok)",
    )
    args = parser.parse_args()

    settings = load_settings()

    if args.service == "canva":
        uri = urlparse(settings.canva_redirect_uri)
        code_file = PROJECT_ROOT / ".canva_code.txt"
    else:
        uri = urlparse(settings.tiktok_redirect_uri)
        code_file = PROJECT_ROOT / ".oauth_code.txt"

    host = uri.hostname or "127.0.0.1"
    port = uri.port or 3000

    if not uri.scheme.startswith("http"):
        raise RuntimeError("Redirect URI must be an http(s) URL")

    CallbackHandler.service = args.service

    server = HTTPServer((host, port), CallbackHandler)
    print(f"[{args.service.upper()}] Listening on {host}:{port}{uri.path or '/'}")
    print("Authorize in your browser — this server will capture the code and exit.")

    while CallbackHandler.oauth_code is None:
        server.handle_request()

    code_file.write_text(CallbackHandler.oauth_code + "\n", encoding="utf-8")
    print(f"Saved code to {code_file}")


if __name__ == "__main__":
    main()
