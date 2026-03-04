from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

from .config import Settings, load_settings


class CanvaAuthError(RuntimeError):
    pass


PKCE_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"


@dataclass(frozen=True)
class CanvaTokenBundle:
    access_token: str
    refresh_token: str
    expires_in: int | None = None
    token_type: str | None = None


class CanvaAuthClient:
    AUTH_URL = "https://www.canva.com/api/oauth/authorize"
    TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()

    def generate_state(self) -> str:
        return secrets.token_urlsafe(24)

    @staticmethod
    def generate_code_verifier(length: int = 64) -> str:
        return "".join(secrets.choice(PKCE_CHARS) for _ in range(length))

    @staticmethod
    def code_challenge_from_verifier(code_verifier: str) -> str:
        # Canva uses standard RFC 7636 S256: BASE64URL(SHA256(verifier))
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    def build_authorize_url(self, state: str | None = None, code_challenge: str | None = None) -> tuple[str, str]:
        state_value = state or self.generate_state()
        params = {
            "code_challenge_method": "s256",
            "response_type": "code",
            "client_id": self.settings.canva_client_id,
            "scope": self.settings.canva_scopes,
            "redirect_uri": self.settings.canva_redirect_uri,
            "state": state_value,
        }
        if code_challenge:
            params["code_challenge"] = code_challenge
        query = urlencode(params)
        return f"{self.AUTH_URL}?{query}", state_value

    def exchange_code_for_tokens(self, code: str, code_verifier: str) -> CanvaTokenBundle:
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": self.settings.canva_redirect_uri,
        }
        return self._parse_bundle(self._post_token(payload))

    def refresh_access_token(self, refresh_token: str) -> CanvaTokenBundle:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        return self._parse_bundle(self._post_token(payload))

    def _post_token(self, payload: dict) -> dict:
        credentials = base64.b64encode(
            f"{self.settings.canva_client_id}:{self.settings.canva_client_secret}".encode()
        ).decode()
        response = requests.post(
            self.TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=payload,
            timeout=30,
        )
        if response.status_code >= 400:
            raise CanvaAuthError(f"Token request failed ({response.status_code}): {response.text}")
        body = response.json()
        if "error" in body:
            raise CanvaAuthError(f"Canva auth error: {body['error']} — {body.get('error_description', '')}")
        return body

    @staticmethod
    def _parse_bundle(body: dict) -> CanvaTokenBundle:
        access_token = body.get("access_token")
        refresh_token = body.get("refresh_token")
        if not access_token or not refresh_token:
            raise CanvaAuthError(f"Token response missing fields: {body}")
        return CanvaTokenBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=body.get("expires_in"),
            token_type=body.get("token_type"),
        )
