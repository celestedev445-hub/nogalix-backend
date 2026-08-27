import secrets
import time
from threading import Lock
from typing import Dict, Tuple

OTP_LENGTH = 6
OTP_MAX_ATTEMPTS = 5
OTP_ATTEMPT_DECAY_SECONDS = 15 * 60

_lock = Lock()
# key -> (count, expires_at_monotonic)
_attempts: Dict[str, Tuple[int, float]] = {}


def generate_otp_code(length: int = OTP_LENGTH) -> str:
    max_value = (10**length) - 1
    return str(secrets.randbelow(max_value + 1)).zfill(length)


def _key(purpose: str, email: str) -> str:
    return f"{purpose}:{email.lower().strip()}"


def has_too_many_otp_attempts(purpose: str, email: str) -> bool:
    key = _key(purpose, email)
    now = time.monotonic()
    with _lock:
        row = _attempts.get(key)
        if not row:
            return False
        count, expires_at = row
        if now > expires_at:
            _attempts.pop(key, None)
            return False
        return count >= OTP_MAX_ATTEMPTS


def record_otp_attempt(purpose: str, email: str) -> None:
    key = _key(purpose, email)
    now = time.monotonic()
    with _lock:
        row = _attempts.get(key)
        if not row or now > row[1]:
            _attempts[key] = (1, now + OTP_ATTEMPT_DECAY_SECONDS)
            return
        _attempts[key] = (row[0] + 1, row[1])


def clear_otp_attempts(purpose: str, email: str) -> None:
    with _lock:
        _attempts.pop(_key(purpose, email), None)
