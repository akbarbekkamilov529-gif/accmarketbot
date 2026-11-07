from __future__ import annotations

import base64
import hashlib
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings

NONCE_SIZE = 12
_KEY_BYTES = 32


class CredentialCipher:
    """AES-GCM authenticated encryption for credential material.

    Stored format: base64(nonce || ciphertext || tag)
    """

    def __init__(self, key: bytes) -> None:
        if len(key) != _KEY_BYTES:
            raise ValueError("AES-GCM key must be exactly 32 bytes")
        self._aes = AESGCM(key)

    def encrypt(self, plaintext: str, aad: bytes | None = None) -> str:
        if plaintext is None:
            plaintext = ""
        nonce = os.urandom(NONCE_SIZE)
        ciphertext = self._aes.encrypt(nonce, plaintext.encode("utf-8"), aad or b"")
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, token: str, aad: bytes | None = None) -> str:
        try:
            raw = base64.b64decode(token.encode("ascii"), validate=True)
        except Exception as exc:  # noqa: BLE001
            raise ValueError("Invalid ciphertext encoding") from exc
        if len(raw) < NONCE_SIZE + 16:
            raise ValueError("Invalid ciphertext payload")
        nonce, ciphertext = raw[:NONCE_SIZE], raw[NONCE_SIZE:]
        return self._aes.decrypt(nonce, ciphertext, aad or b"").decode("utf-8")


def _decode_key(material: str) -> bytes:
    material = (material or "").strip()
    if not material:
        raise ValueError(
            "CREDENTIAL_ENCRYPTION_KEY is not configured. "
            "Generate one with: python -c \"import os,base64;print(base64.b64encode(os.urandom(32)).decode())\""
        )

    try:
        decoded = base64.b64decode(material, validate=True)
        if len(decoded) == _KEY_BYTES:
            return decoded
    except Exception:  # noqa: BLE001
        pass

    if len(material) == 64:
        try:
            decoded = bytes.fromhex(material)
            if len(decoded) == _KEY_BYTES:
                return decoded
        except ValueError:
            pass

    # Last-resort deterministic derivation for operator-provided passphrases.
    # The README recommends a base64-encoded 32-byte random key.
    return hashlib.sha256(material.encode("utf-8")).digest()


@lru_cache(maxsize=1)
def get_cipher() -> CredentialCipher:
    settings = get_settings()
    return CredentialCipher(_decode_key(settings.credential_encryption_key))


def account_aad(account_id: int) -> bytes:
    return f"account:{account_id}".encode("ascii")


def encrypt_for_account(account_id: int, plaintext: str) -> str:
    return get_cipher().encrypt(plaintext, account_aad(account_id))


def decrypt_for_account(account_id: int, token: str) -> str:
    return get_cipher().decrypt(token, account_aad(account_id))


def generate_key() -> str:
    return base64.b64encode(os.urandom(_KEY_BYTES)).decode("ascii")
