"""Autenticação: registro, login e dados do usuário logado."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import User
from app.schemas import AuthResponse, LoginRequest, RegisterRequest, UserRead
from app.services.auth_service import cria_token, hash_senha, verifica_senha

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "e-mail já cadastrado")
    if len(payload.senha) < 6:
        raise HTTPException(400, "senha precisa de ao menos 6 caracteres")
    user = User(nome=payload.nome.strip() or email, email=email,
                senha_hash=hash_senha(payload.senha))
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(token=cria_token(user.id), user=UserRead.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verifica_senha(payload.senha, user.senha_hash):
        raise HTTPException(401, "e-mail ou senha inválidos")
    return AuthResponse(token=cria_token(user.id), user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(usuario_atual)):
    return user
