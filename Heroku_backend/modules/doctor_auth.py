"""
doctor_auth.py — Shared-login auth for the Doctor Portal.

* Credentials come from the environment (DOCTOR_USERNAME / DOCTOR_PASSWORD).
* Tokens are signed + expiring (itsdangerous URLSafeTimedSerializer, 8 hours).
* Failed logins are limited in memory: 5 per IP per 5 minutes.
"""
import hmac
import os
import secrets
import threading
import time
from functools import wraps

from flask import jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

TOKEN_MAX_AGE = 8 * 60 * 60          # 8 hours
MAX_FAILED = 5
WINDOW_SECONDS = 5 * 60              # 5 minutes

_fallback_secret = secrets.token_hex(32)   # used only if SECRET_KEY is not set
_failed: dict = {}                          # ip -> [timestamps]
_lock = threading.Lock()


def _serializer() -> URLSafeTimedSerializer:
    secret = os.environ.get("SECRET_KEY") or _fallback_secret
    return URLSafeTimedSerializer(secret, salt="doctor-portal")


def _client_ip() -> str:
    return request.remote_addr or "unknown"


def _recent_failures(ip: str) -> list:
    now = time.time()
    with _lock:
        recent = [t for t in _failed.get(ip, []) if now - t < WINDOW_SECONDS]
        _failed[ip] = recent
        return list(recent)


def is_rate_limited(ip: str) -> bool:
    return len(_recent_failures(ip)) >= MAX_FAILED


def record_failure(ip: str) -> None:
    with _lock:
        _failed.setdefault(ip, []).append(time.time())


def clear_failures(ip: str) -> None:
    with _lock:
        _failed.pop(ip, None)


def reset_rate_limits() -> None:
    """Test helper."""
    with _lock:
        _failed.clear()


def check_credentials(username: str, password: str) -> bool:
    expected_user = os.environ.get("DOCTOR_USERNAME", "doctor")
    expected_pass = os.environ.get("DOCTOR_PASSWORD", "change-me-123")
    # Compare both fields every time (no short-circuit) using constant-time compare.
    user_ok = hmac.compare_digest(str(username).encode("utf-8"), expected_user.encode("utf-8"))
    pass_ok = hmac.compare_digest(str(password).encode("utf-8"), expected_pass.encode("utf-8"))
    return user_ok and pass_ok


def create_token() -> str:
    return _serializer().dumps({"role": "doctor"})


def verify_token(token: str) -> bool:
    try:
        data = _serializer().loads(token, max_age=TOKEN_MAX_AGE)
        return isinstance(data, dict) and data.get("role") == "doctor"
    except (BadSignature, SignatureExpired):
        return False


def _unauthorized(message="Authentication required"):
    return jsonify({"error": {"code": "UNAUTHORIZED", "message": message}}), 401


def require_doctor(fn):
    """Decorator: requires 'Authorization: Bearer <token>' with a valid, unexpired token."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return _unauthorized()
        token = header[len("Bearer "):].strip()
        if not token or not verify_token(token):
            return _unauthorized("Invalid or expired token")
        return fn(*args, **kwargs)
    return wrapper

