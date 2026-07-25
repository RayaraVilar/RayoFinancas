from __future__ import annotations

import asyncio
import hmac
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import Settings
from app.modules.identity.security import OAuthFlowState, pkce_challenge

GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
# Google recommends allowing a small clock skew when validating time-based claims.
# Keep this bounded: it compensates for host/container drift without accepting stale tokens.
GOOGLE_ID_TOKEN_CLOCK_SKEW_SECONDS = 60


class GoogleOAuthError(Exception):
    """Safe OAuth failure without provider payloads or tokens."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def classify_id_token_error(error: ValueError) -> str:
    message = str(error).casefold()
    if "audience" in message:
        return "wrong_audience"
    if "used too early" in message or "not yet valid" in message:
        return "token_used_too_early"
    if "expired" in message:
        return "token_expired"
    if "issuer" in message:
        return "wrong_issuer"
    if "certificate" in message or "key id" in message:
        return "certificate_validation_failed"
    return "id_token_verification_failed"


@dataclass(frozen=True)
class GoogleIdentityClaims:
    subject: str
    email: str
    display_name: str
    avatar_url: str | None


class GoogleIdentityProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.google_oauth_configured:
            raise GoogleOAuthError("not_configured", "Google OAuth is not configured.")
        self._client_id = settings.google_client_id or ""
        self._client_secret = (
            settings.google_client_secret.get_secret_value()
            if settings.google_client_secret
            else ""
        )
        self._redirect_uri = settings.google_redirect_uri

    def authorization_url(self, flow: OAuthFlowState) -> str:
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": flow.state,
                "nonce": flow.nonce,
                "code_challenge": pkce_challenge(flow.code_verifier),
                "code_challenge_method": "S256",
                "access_type": "online",
                "prompt": "select_account",
            }
        )
        return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}"

    async def exchange_code(
        self,
        code: str,
        flow: OAuthFlowState,
    ) -> GoogleIdentityClaims:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    GOOGLE_TOKEN_ENDPOINT,
                    data={
                        "code": code,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "redirect_uri": self._redirect_uri,
                        "grant_type": "authorization_code",
                        "code_verifier": flow.code_verifier,
                    },
                )
                response.raise_for_status()
                token_payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GoogleOAuthError("code_exchange_failed", "Google code exchange failed.") from exc

        raw_id_token = token_payload.get("id_token")
        if not isinstance(raw_id_token, str):
            raise GoogleOAuthError(
                "missing_id_token",
                "Google response did not include an ID token.",
            )

        try:
            claims: dict[str, Any] = await asyncio.to_thread(
                id_token.verify_oauth2_token,
                raw_id_token,
                google_requests.Request(),
                self._client_id,
                clock_skew_in_seconds=GOOGLE_ID_TOKEN_CLOCK_SKEW_SECONDS,
            )
        except ValueError as exc:
            raise GoogleOAuthError(
                classify_id_token_error(exc),
                "Google ID token verification failed.",
            ) from exc

        nonce = claims.get("nonce")
        if not isinstance(nonce, str) or not hmac.compare_digest(nonce, flow.nonce):
            raise GoogleOAuthError("nonce_verification_failed", "Google nonce verification failed.")
        if claims.get("email_verified") is not True:
            raise GoogleOAuthError("email_not_verified", "Google email is not verified.")

        subject = claims.get("sub")
        email = claims.get("email")
        display_name = claims.get("name")
        picture = claims.get("picture")
        if not isinstance(subject, str) or not subject:
            raise GoogleOAuthError("incomplete_claims", "Google identity claims are incomplete.")
        if not isinstance(email, str) or not email:
            raise GoogleOAuthError("incomplete_claims", "Google identity claims are incomplete.")

        return GoogleIdentityClaims(
            subject=subject,
            email=email,
            display_name=(
                display_name if isinstance(display_name, str) and display_name else email
            ),
            avatar_url=picture if isinstance(picture, str) else None,
        )
