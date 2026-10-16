import time
import pytest
from mcp_common import (
    generate_ed25519_keypair,
    compute_payload_hash,
    sign_payload_hash,
    verify_approval_token,
    InvalidApprovalTokenError,
    redact_secrets,
)

def test_keypair_generation_and_signing():
    priv, pub = generate_ed25519_keypair()
    assert len(priv) == 64
    assert len(pub) == 64

    payload = {"campaign": "launch_123", "budget": 500}
    payload_hash = compute_payload_hash(payload)
    assert len(payload_hash) == 64

    sig = sign_payload_hash(payload_hash, priv)
    assert len(sig) == 128  # 64 bytes in hex

    token_dict = {
        "tenant_id": "tenant-abc",
        "tool_name": "publish_media",
        "payload_hash": payload_hash,
        "expires_at": int(time.time()) + 60,
        "signature": sig,
    }

    # Successful verification
    assert verify_approval_token(
        token_dict=token_dict,
        expected_payload_hash=payload_hash,
        expected_tenant_id="tenant-abc",
        expected_tool_name="publish_media",
        public_key_hex=pub,
    ) is True

def test_token_payload_tampering_rejected():
    priv, pub = generate_ed25519_keypair()
    payload = {"budget": 100}
    payload_hash = compute_payload_hash(payload)
    sig = sign_payload_hash(payload_hash, priv)

    # Attacker tries to use token for budget: 10000
    tampered_payload = {"budget": 10000}
    tampered_hash = compute_payload_hash(tampered_payload)

    token_dict = {
        "tenant_id": "tenant-abc",
        "tool_name": "set_budget",
        "payload_hash": payload_hash,
        "expires_at": int(time.time()) + 60,
        "signature": sig,
    }

    with pytest.raises(InvalidApprovalTokenError, match="Payload hash mismatch"):
        verify_approval_token(
            token_dict=token_dict,
            expected_payload_hash=tampered_hash,
            expected_tenant_id="tenant-abc",
            expected_tool_name="set_budget",
            public_key_hex=pub,
        )

def test_token_expiration_rejected():
    priv, pub = generate_ed25519_keypair()
    payload_hash = compute_payload_hash({"action": "post"})
    sig = sign_payload_hash(payload_hash, priv)

    expired_token = {
        "tenant_id": "tenant-abc",
        "tool_name": "publish_media",
        "payload_hash": payload_hash,
        "expires_at": int(time.time()) - 10,  # Expired in past
        "signature": sig,
    }

    with pytest.raises(InvalidApprovalTokenError, match="Token expired"):
        verify_approval_token(
            token_dict=expired_token,
            expected_payload_hash=payload_hash,
            expected_tenant_id="tenant-abc",
            expected_tool_name="publish_media",
            public_key_hex=pub,
        )

def test_secret_redaction():
    raw_log = "Error connecting with api_key: 'AIzaSyD-1234567890abcdef' and bearer: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.xyz"
    redacted = redact_secrets(raw_log)
    assert "AIzaSyD-1234567890abcdef" not in redacted
    assert "[REDACTED]" in redacted
