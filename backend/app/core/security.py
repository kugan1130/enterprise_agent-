"""Security utilities for password hashing and JWT token handling."""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from backend.app.core.config import settings


def hash_password(password: str) -> str:
    """Hashes a plaintext password securely using PBKDF2 HMAC SHA256."""
    salt = "enterprise_ai_salt_2026".encode("utf-8")
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return base64.b64encode(key).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored hash."""
    return hmac.compare_digest(hash_password(plain_password), hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed JWT access token containing user claims."""
    to_encode = data.copy()
    if expires_delta:
        expire = time.time() + expires_delta.total_seconds()
    else:
        expire = time.time() + 86400  # Default 24 hours

    to_encode.update({"exp": expire})
    
    header = {"alg": settings.JWT_ALGORITHM, "typ": "JWT"}
    header_bytes = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=")
    payload_bytes = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).rstrip(b"=")

    signature_input = f"{header_bytes.decode()}.${payload_bytes.decode()}".encode()
    signature = hmac.new(settings.JWT_SECRET.encode(), signature_input, hashlib.sha256).digest()
    signature_bytes = base64.urlsafe_b64encode(signature).rstrip(b"=")

    return f"{header_bytes.decode()}.{payload_bytes.decode()}.{signature_bytes.decode()}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT access token signature and expiration."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")

        header_b64, payload_b64, signature_b64 = parts
        signature_input = f"{header_b64}.{payload_b64}".encode()

        expected_sig = base64.urlsafe_b64encode(
            hmac.new(settings.JWT_SECRET.encode(), signature_input, hashlib.sha256).digest()
        ).rstrip(b"=").decode()

        if not hmac.compare_digest(expected_sig, signature_b64):
            raise ValueError("Signature verification failed")

        # Decode payload
        padding = "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
        payload = json.loads(payload_bytes.decode())

        if payload.get("exp") and time.time() > payload["exp"]:
            raise ValueError("Token has expired")

        return payload
    except Exception as err:
        raise ValueError(f"Token validation error: {err}")
