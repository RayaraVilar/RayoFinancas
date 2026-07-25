from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


def _cipher(secret_key: str) -> Fernet:
    derived = hashlib.sha256(f"rayo:user-secrets:v1:{secret_key}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_user_secret(value: str, secret_key: str) -> str:
    return _cipher(secret_key).encrypt(value.encode()).decode()


def decrypt_user_secret(value: str, secret_key: str) -> str:
    try:
        return _cipher(secret_key).decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Stored credential cannot be decrypted.") from exc
