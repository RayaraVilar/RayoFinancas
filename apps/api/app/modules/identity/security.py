from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import asdict, dataclass

from cryptography.fernet import Fernet, InvalidToken


def generate_token(byte_length: int = 32) -> str:
    return secrets.token_urlsafe(byte_length)


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class OAuthFlowState:
    state: str
    nonce: str
    code_verifier: str


def new_oauth_flow() -> OAuthFlowState:
    return OAuthFlowState(
        state=generate_token(),
        nonce=generate_token(),
        code_verifier=generate_token(64),
    )


class OAuthFlowCodec:
    def __init__(self, secret_key: str) -> None:
        key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode("utf-8")).digest())
        self._fernet = Fernet(key)

    def encode(self, flow: OAuthFlowState) -> str:
        payload = json.dumps(asdict(flow), separators=(",", ":")).encode("utf-8")
        return self._fernet.encrypt(payload).decode("ascii")

    def decode(self, token: str, ttl_seconds: int) -> OAuthFlowState | None:
        try:
            payload = self._fernet.decrypt(token.encode("ascii"), ttl=ttl_seconds)
            data = json.loads(payload)
            return OAuthFlowState(
                state=data["state"],
                nonce=data["nonce"],
                code_verifier=data["code_verifier"],
            )
        except (InvalidToken, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
