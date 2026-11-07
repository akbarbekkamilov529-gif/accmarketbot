from __future__ import annotations

import base64
import os

import pytest

from app.crypto import CredentialCipher, _decode_key, decrypt_for_account, encrypt_for_account


def test_encrypt_decrypt_roundtrip() -> None:
    cipher = CredentialCipher(os.urandom(32))
    token = cipher.encrypt("my-secret-password", b"account:1")
    assert "my-secret-password" not in token
    assert cipher.decrypt(token, b"account:1") == "my-secret-password"


def test_wrong_aad_fails() -> None:
    cipher = CredentialCipher(os.urandom(32))
    token = cipher.encrypt("secret", b"account:1")
    with pytest.raises(Exception):
        cipher.decrypt(token, b"account:2")


def test_tampered_ciphertext_fails() -> None:
    cipher = CredentialCipher(os.urandom(32))
    token = cipher.encrypt("secret", b"account:1")
    raw = bytearray(base64.b64decode(token))
    raw[-1] ^= 0x01
    tampered = base64.b64encode(bytes(raw)).decode()
    with pytest.raises(Exception):
        cipher.decrypt(tampered, b"account:1")


def test_key_decoding_formats() -> None:
    raw = os.urandom(32)
    assert _decode_key(base64.b64encode(raw).decode()) == raw
    assert _decode_key(raw.hex()) == raw
    assert len(_decode_key("some-operator-passphrase")) == 32


def test_account_helpers_use_aad() -> None:
    token = encrypt_for_account(7, "value")
    assert decrypt_for_account(7, token) == "value"
    with pytest.raises(Exception):
        decrypt_for_account(8, token)
