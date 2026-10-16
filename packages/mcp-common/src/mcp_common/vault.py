"""
Local secrets vault: AES-256-GCM envelope for third-party tokens (Meta, etc.).

The key comes from APP_MASTER_KEY (64 hex chars). Ciphertexts are self-describing
("v1:<nonce>:<ciphertext>") so the key can be rotated later by adding a version.
Plaintext tokens must never be logged, returned to the browser or put in LLM context.
"""
import base64
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_DEV_FALLBACK_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


class VaultError(Exception):
    pass


def _key(master_key_hex: Optional[str] = None) -> bytes:
    raw = (master_key_hex or os.getenv("APP_MASTER_KEY") or _DEV_FALLBACK_KEY).strip()
    try:
        key = bytes.fromhex(raw)
    except ValueError:
        raise VaultError("APP_MASTER_KEY must be hex")
    if len(key) != 32:
        raise VaultError("APP_MASTER_KEY must be 32 bytes (64 hex chars)")
    return key


def encrypt_secret(plaintext: str, associated_data: str = "", master_key_hex: Optional[str] = None) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(_key(master_key_hex)).encrypt(nonce, plaintext.encode(), associated_data.encode() or None)
    return "v1:" + base64.urlsafe_b64encode(nonce).decode() + ":" + base64.urlsafe_b64encode(ct).decode()


def decrypt_secret(token: str, associated_data: str = "", master_key_hex: Optional[str] = None) -> str:
    try:
        version, nonce_b64, ct_b64 = token.split(":", 2)
        if version != "v1":
            raise VaultError(f"Unknown vault version {version}")
        nonce = base64.urlsafe_b64decode(nonce_b64)
        ct = base64.urlsafe_b64decode(ct_b64)
        return AESGCM(_key(master_key_hex)).decrypt(nonce, ct, associated_data.encode() or None).decode()
    except VaultError:
        raise
    except Exception:
        raise VaultError("Could not decrypt secret (wrong key or tampered data)")
