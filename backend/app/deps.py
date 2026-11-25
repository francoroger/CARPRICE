"""Dependências de autenticação para as rotas FastAPI."""
from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.services.auth_service import user_id_do_token


def usuario_opcional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    """Usuário do token Bearer, ou None se não autenticado (modo convidado)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    uid = user_id_do_token(authorization.split(" ", 1)[1].strip())
    return db.get(User, uid) if uid else None


def usuario_atual(user: User | None = Depends(usuario_opcional)) -> User:
    """Exige autenticação — 401 se não houver token válido."""
    if not user:
        raise HTTPException(401, "não autenticado")
    return user


def usuario_admin(user: User = Depends(usuario_atual)) -> User:
    """Exige um administrador (ADMIN_EMAILS). Sem lista configurada, basta estar logado."""
    admins = settings.admin_emails_list
    if admins and user.email.lower() not in admins:
        raise HTTPException(403, "apenas administradores podem alterar as configurações")
    return user


def eh_admin(user: User | None) -> bool:
    if not user:
        return False
    admins = settings.admin_emails_list
    return not admins or user.email.lower() in admins
