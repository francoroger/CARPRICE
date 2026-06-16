"""Autenticação: hash de senha (pbkdf2_sha256, puro-python) + JWT (HS256)."""
from __future__ import annotations

import time

import jwt
from passlib.context import CryptContext

from app.config import settings

# pbkdf2_sha256: sem dependência binária (evita dores de bcrypt no deploy).
_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_senha(senha: str) -> str:
    return _pwd.hash(senha)


def verifica_senha(senha: str, senha_hash: str) -> bool:
    try:
        return _pwd.verify(senha, senha_hash)
    except Exception:  # noqa: BLE001 — hash inválido/legado
        return False


def cria_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "iat": int(time.time()),
        "exp": int(time.time()) + settings.jwt_expira_dias * 86400,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def user_id_do_token(token: str) -> int | None:
    try:
        dados = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return int(dados["sub"])
    except Exception:  # noqa: BLE001 — expirado/inválido
        return None
