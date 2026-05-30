"""Parâmetros globais: score params e portais ativos."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import SCORE_PARAMS_KEY
from app.database import get_db
from app.models import Portal
from app.schemas import PortalRead, ScoreParamsRead, SettingUpdate
from app.services.settings_service import get_score_params, get_setting, set_setting

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/score", response_model=ScoreParamsRead)
def ler_score(db: Session = Depends(get_db)):
    return get_score_params(db).__dict__


@router.put("/score", response_model=ScoreParamsRead)
def gravar_score(payload: SettingUpdate, db: Session = Depends(get_db)):
    if not isinstance(payload.valor_json, dict):
        raise HTTPException(400, "score params deve ser um objeto")
    atual = get_setting(db, SCORE_PARAMS_KEY, {}) or {}
    atual.update(payload.valor_json)
    set_setting(db, SCORE_PARAMS_KEY, atual)
    return get_score_params(db).__dict__


@router.get("/portals", response_model=list[PortalRead])
def listar_portais(db: Session = Depends(get_db)):
    return db.scalars(select(Portal).order_by(Portal.nome)).all()


@router.patch("/portals/{slug}", response_model=PortalRead)
def alternar_portal(slug: str, ativo: bool, db: Session = Depends(get_db)):
    p = db.scalar(select(Portal).where(Portal.slug == slug))
    if not p:
        raise HTTPException(404, "portal não encontrado")
    p.ativo = ativo
    db.commit()
    db.refresh(p)
    return p
