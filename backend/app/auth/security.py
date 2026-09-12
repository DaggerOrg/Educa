"""Password hashing and JWT issuance for the mini prototype.

Stdlib PBKDF2 rather than bcrypt/argon2, to avoid an extra native
dependency in a demo backend -- same "zero external dependencies" spirit
as ../store.py. Swap for passlib[bcrypt] or argon2-cffi (and move
JWT_SECRET out of an env-var fallback into a real secrets manager) before
this ever holds real user data.
"""
import hashlib
import os
import secrets
import time

import jwt

# Dev-only fallback so the app still boots with zero setup, same as the
# rest of this prototype -- set a real JWT_SECRET (Infisical, per
# docs/README.md's ANTHROPIC_API_KEY pattern) before deploying anywhere
# reachable by anyone but you.
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-only-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days

_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, _, digest_hex = stored.partition("$")
    if not salt or not digest_hex:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _PBKDF2_ITERATIONS)
    return secrets.compare_digest(candidate.hex(), digest_hex)


def create_access_token(user_id: str) -> str:
    now = int(time.time())
    payload = {"sub": user_id, "iat": now, "exp": now + JWT_TTL_SECONDS}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """Returns the user id (`sub`); raises jwt.PyJWTError on an invalid or expired token."""
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    return payload["sub"]
