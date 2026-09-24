"""Password and session-token primitives.

Input: passwords or high-entropy generated tokens; output: one-way hashes.
Security: Argon2id for passwords; SHA-256 is used only for random session tokens.
"""

import hashlib
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

password_hasher = PasswordHasher()
USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128


def normalize_username(username: str) -> str:
    normalized = username.lower()
    if username != username.strip() or not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("Invalid username")
    return normalized


def valid_password(password: str) -> bool:
    return MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH


def hash_password(password: str) -> str:
    if not valid_password(password):
        raise ValueError("Password length out of bounds")
    return password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def generate_temporary_password() -> str:
    return secrets.token_urlsafe(24)


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()
