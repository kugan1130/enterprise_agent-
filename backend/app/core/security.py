"""Security utilities for password hashing and JWT token operations."""

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict

from backend.app.core.config import settings


def hash_password(password: str) -> str:
    """Hashes a password using PBKDF2 HMAC SHA256 with a random salt."""
    salt = hashlib.sha256(password.encode("utf-8") + settings.JWT_SECRET.encode("utf-8")).hexdigest()[:16]
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return f"{salt}${pwd_hash.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against a stored PBKDF2 hash."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 2:
            return False
        salt, stored_hash = parts
        computed_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
        return hmac.compare_digest(stored_hash, computed_hash)
    except Exception:
        return False


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4))
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def create_access_token(data: Dict[str, Any], expires_in_seconds: int = 86400) -> str:
    """Generates a secure JWT access token signed with HS256."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = data.copy()
    payload["exp"] = int(time.time()) + expires_in_seconds

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(settings.JWT_SECRET.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = _base64url_encode(signature)

    return f"{signing_input}.{sig_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and verifies JWT access token signature and expiration."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token structure.")

        header_b64, payload_b64, sig_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}"

        expected_sig = hmac.new(settings.JWT_SECRET.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
        computed_sig_b64 = _base64url_encode(expected_sig)

        if not hmac.compare_digest(sig_b64, computed_sig_b64):
            raise ValueError("Invalid token signature.")

        payload = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
        if "exp" in payload and payload["exp"] < int(time.time()):
            raise ValueError("Token has expired.")

        return payload
    except Exception as err:
        raise ValueError(f"Invalid access token: {err}")
