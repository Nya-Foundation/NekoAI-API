"""Access key derivation and per-request header helpers."""

import base64
import random
import string
from datetime import datetime, timezone
from hashlib import blake2b

import argon2

from .types import User


def encode_access_key(user: User) -> str:
    """
    Generate hashed access key from the user's username and password using the blake2 and argon2 algorithms.

    Parameters
    ----------
    user : `nekoai.types.User`
        User object containing username and password

    Returns
    -------
    `str`
        Hashed access key
    """
    pre_salt = f"{user.password[:6]}{user.username}novelai_data_access_key"

    blake = blake2b(digest_size=16)
    blake.update(pre_salt.encode())
    salt = blake.digest()

    raw = argon2.low_level.hash_secret_raw(
        secret=user.password.encode(),
        salt=salt,
        time_cost=2,
        memory_cost=int(2000000 / 1024),
        parallelism=1,
        hash_len=64,
        type=argon2.low_level.Type.ID,
    )
    hashed = base64.urlsafe_b64encode(raw).decode()

    return hashed[:64]


def generate_x_correlation_id() -> str:
    chars = string.ascii_letters + string.digits  # A–Z a–z 0–9
    return "".join(random.choices(chars, k=6))


def generate_x_initiated_at() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(now.microsecond / 1000):03d}Z"


def prep_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of `headers` with fresh per-request tracking headers."""
    headers = dict(headers)
    headers["x-correlation-id"] = generate_x_correlation_id()
    headers["x-initiated-at"] = generate_x_initiated_at()
    return headers
