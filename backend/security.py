"""Authentication, role checks and encryption helpers.

NFR coverage: Security (password hashing, signed tokens, encryption at rest)
and Privacy (per-user isolation relies on the identity established here).
Only the Python standard library plus `cryptography` (Fernet) is used.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, Request

TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", str(8 * 3600)))
_SECRETS_FILE = Path(__file__).with_name(".secrets.json")


def _load_generated_secrets() -> dict:
    if _SECRETS_FILE.exists():
        return json.loads(_SECRETS_FILE.read_text())
    generated = {
        "JWT_SECRET": secrets.token_urlsafe(48),
        "DATA_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    }
    _SECRETS_FILE.write_text(json.dumps(generated))
    return generated


def _secret(name: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    return _load_generated_secrets()[name]


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ---- passwords -------------------------------------------------------------
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt, digest = stored.split("$")
        candidate = hashlib.scrypt(
            password.encode(), salt=_unb64(salt), n=2**14, r=8, p=1
        )
        return hmac.compare_digest(candidate, _unb64(digest))
    except Exception:
        return False


# ---- signed tokens (HS256 JWT) --------------------------------------------
def create_token(user_id: int, role: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(
        json.dumps(
            {"sub": user_id, "role": role, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
        ).encode()
    )
    signature = hmac.new(
        _secret("JWT_SECRET").encode(), f"{header}.{payload}".encode(), hashlib.sha256
    ).digest()
    return f"{header}.{payload}.{_b64(signature)}"


def decode_token(token: str) -> dict | None:
    try:
        header, payload, signature = token.split(".")
        expected = hmac.new(
            _secret("JWT_SECRET").encode(),
            f"{header}.{payload}".encode(),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(expected, _unb64(signature)):
            return None
        claims = json.loads(_unb64(payload))
        if claims["exp"] < time.time():
            return None
        return claims
    except Exception:
        return None


# ---- encryption at rest ----------------------------------------------------
def _fernet() -> Fernet:
    return Fernet(_secret("DATA_ENCRYPTION_KEY").encode())


def encrypt_json(value: dict) -> str:
    return _fernet().encrypt(json.dumps(value).encode()).decode()


def decrypt_json(token: str) -> dict:
    try:
        return json.loads(_fernet().decrypt(token.encode()))
    except InvalidToken as exc:
        raise ValueError("Stored record could not be decrypted.") from exc


# ---- FastAPI dependencies --------------------------------------------------
def current_user(request: Request) -> dict:
    import store  # local import avoids a circular dependency

    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required.")
    claims = decode_token(header[7:])
    if claims is None:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    user = store.get_user(claims["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found.")
    return user


def require_surgeon(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "surgeon":
        raise HTTPException(status_code=403, detail="Surgeon account required.")
    return user


def require_admin(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required.")
    return user
