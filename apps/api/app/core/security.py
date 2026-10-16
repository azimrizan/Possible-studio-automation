import time
import uuid
import jwt
from typing import Dict, Any, Optional
import bcrypt
from mcp_common import (
    generate_ed25519_keypair,
    compute_payload_hash,
    sign_payload_hash,
)
from .config import settings

# Initialize or load Ed25519 Keypair
if not settings.APPROVAL_PRIVATE_KEY_HEX or not settings.APPROVAL_PUBLIC_KEY_HEX:
    _priv, _pub = generate_ed25519_keypair()
    APPROVAL_PRIVATE_KEY_HEX = _priv
    APPROVAL_PUBLIC_KEY_HEX = _pub
else:
    APPROVAL_PRIVATE_KEY_HEX = settings.APPROVAL_PRIVATE_KEY_HEX
    APPROVAL_PUBLIC_KEY_HEX = settings.APPROVAL_PUBLIC_KEY_HEX

def hash_password(password: str) -> str:
    # Bcrypt maximum length is 72 bytes
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)

def create_access_token(data: Dict[str, Any], expires_delta_minutes: Optional[int] = None) -> str:
    to_encode = data.copy()
    expire_minutes = expires_delta_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire_timestamp = int(time.time()) + (expire_minutes * 60)
    to_encode.update({"exp": expire_timestamp})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

def mint_approval_token(
    tenant_id: str,
    tool_name: str,
    payload: Dict[str, Any],
    ttl_seconds: int = 900,  # 15 minutes TTL
) -> Dict[str, Any]:
    """
    Mints a single-use, hash-bound, Ed25519 cryptographically signed approval token.
    """
    payload_hash = compute_payload_hash(payload)
    token_jti = str(uuid.uuid4())
    expires_at = int(time.time()) + ttl_seconds
    signature = sign_payload_hash(payload_hash, APPROVAL_PRIVATE_KEY_HEX)

    return {
        "token_jti": token_jti,
        "tenant_id": tenant_id,
        "tool_name": tool_name,
        "payload_hash": payload_hash,
        "expires_at": expires_at,
        "signature": signature,
    }
