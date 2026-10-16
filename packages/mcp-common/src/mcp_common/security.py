import json
import hashlib
import time
import re
from typing import Dict, Any, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
from .errors import InvalidApprovalTokenError

# Key generation
def generate_ed25519_keypair() -> Tuple[str, str]:
    """Generates a new Ed25519 private/public keypair in hex format."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    priv_hex = private_key.private_bytes_raw().hex()
    pub_hex = public_key.public_bytes_raw().hex()
    return priv_hex, pub_hex

def compute_payload_hash(payload: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 hash of a JSON-serializable dictionary."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

def sign_payload_hash(payload_hash: str, private_key_hex: str) -> str:
    """Signs a payload hash string using an Ed25519 private key in hex."""
    priv_bytes = bytes.fromhex(private_key_hex)
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
    signature = private_key.sign(payload_hash.encode('utf-8'))
    return signature.hex()

def verify_approval_token(
    token_dict: Dict[str, Any],
    expected_payload_hash: str,
    expected_tenant_id: str,
    expected_tool_name: str,
    public_key_hex: str,
) -> bool:
    """
    Cryptographically verifies an approval token:
    1. Checks expiration.
    2. Checks tenant binding.
    3. Checks tool binding.
    4. Checks exact payload hash match.
    5. Verifies Ed25519 signature over payload_hash.
    """
    expires_at = token_dict.get("expires_at", 0)
    current_time = int(time.time())
    if current_time > expires_at:
        raise InvalidApprovalTokenError(f"Token expired at {expires_at} (current time {current_time})")

    if token_dict.get("tenant_id") != expected_tenant_id:
        raise InvalidApprovalTokenError("Tenant ID mismatch on approval token")

    if token_dict.get("tool_name") != expected_tool_name:
        raise InvalidApprovalTokenError("Tool name mismatch on approval token")

    token_payload_hash = token_dict.get("payload_hash")
    if token_payload_hash != expected_payload_hash:
        raise InvalidApprovalTokenError(
            f"Payload hash mismatch! Token is bound to {token_payload_hash}, but execution payload is {expected_payload_hash}"
        )

    signature_hex = token_dict.get("signature")
    if not signature_hex:
        raise InvalidApprovalTokenError("Missing signature on approval token")

    try:
        pub_bytes = bytes.fromhex(public_key_hex)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(bytes.fromhex(signature_hex), expected_payload_hash.encode('utf-8'))
    except InvalidSignature:
        raise InvalidApprovalTokenError("Invalid Ed25519 cryptographic signature")
    except Exception as e:
        raise InvalidApprovalTokenError(f"Cryptographic verification error: {str(e)}")

    return True

SECRET_PATTERNS = [
    (re.compile(r"(?i)(api[_-]?key|secret|password|access[_-]?token|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"), r"\1: [REDACTED]"),
    (re.compile(r"ghp_[a-zA-Z0-9]{36}"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"ey[a-zA-Z0-9_-]{10,}\.ey[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"), "[REDACTED_JWT]"),
]

def redact_secrets(text: str) -> str:
    """Redacts common credentials, tokens, and keys from traces/logs."""
    if not isinstance(text, str):
        return text
    redacted = text
    for pattern, repl in SECRET_PATTERNS:
        redacted = pattern.sub(repl, redacted)
    return redacted
