from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import requests

from .config import Settings, load_settings


class TikTokAuthError(RuntimeError):
    pass


PKCE_ALLOWED_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"


@dataclass(frozen=True)
class TokenBundle:
    access_token: str
    refresh_token: str
    expires_in: int | None = None
    refresh_expires_in: int | None = None
    open_id: str | None = None
    scope: str | None = None


class TikTokAuthClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()

    def generate_state(self) -> str:
        return secrets.token_urlsafe(24)

    @staticmethod
    def generate_code_verifier(length: int = 64) -> str:
        if length < 43 or length > 128:
            raise ValueError("PKCE code_verifier length must be 43-128")
        return "".join(secrets.choice(PKCE_ALLOWED_CHARS) for _ in range(length))

    @staticmethod
    def code_challenge_from_verifier(code_verifier: str) -> str:
        # TikTok uses SHA256 hex (not standard base64url) for code_challenge S256
        return hashlib.sha256(code_verifier.encode("utf-8")).hexdigest()

    def build_authorize_url(
        self,
        state: str | None = None,
        code_challenge: str | None = None,
    ) -> tuple[str, str]:
        state_value = state or self.generate_state()
        params = {
            "client_key": self.settings.tiktok_client_id,
            "scope": self.settings.tiktok_scopes,
            "response_type": "code",
            "redirect_uri": self.settings.tiktok_redirect_uri,
            "state": state_value,
        }
        if code_challenge:
            params["code_challenge"] = code_challenge
            params["code_challenge_method"] = "S256"
        query = urlencode(params, safe=",")
        return f"https://www.tiktok.com/v2/auth/authorize/?{query}", state_value

    def exchange_code_for_tokens(self, code: str, code_verifier: str | None = None) -> TokenBundle:
        payload = {
            "client_key": self.settings.tiktok_client_id,
            "client_secret": self.settings.tiktok_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.settings.tiktok_redirect_uri,
        }
        if code_verifier:
            payload["code_verifier"] = code_verifier
        body = self._post_token(payload)
        return self._parse_token_bundle(body)

    def refresh_access_token(self, refresh_token: str) -> TokenBundle:
        payload = {
            "client_key": self.settings.tiktok_client_id,
            "client_secret": self.settings.tiktok_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        body = self._post_token(payload)
        return self._parse_token_bundle(body)

    def _post_token(self, payload: dict[str, str]) -> dict:
        response = requests.post(
            self.settings.tiktok_token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=payload,
            timeout=self.settings.tiktok_request_timeout_seconds,
        )
        if response.status_code >= 400:
            raise TikTokAuthError(
                f"Token request failed ({response.status_code}): {response.text}"
            )

        body = response.json()
        if "error" in body and body["error"]:
            raise TikTokAuthError(f"TikTok auth error: {body['error']}")
        return body

    def _parse_token_bundle(self, body: dict) -> TokenBundle:
        data = body.get("data", {}) if "data" in body else body
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")

        if not access_token or not refresh_token:
            raise TikTokAuthError(f"Token response missing fields: {body}")

        return TokenBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=data.get("expires_in"),
            refresh_expires_in=data.get("refresh_expires_in"),
            open_id=data.get("open_id"),
            scope=data.get("scope"),
        )
