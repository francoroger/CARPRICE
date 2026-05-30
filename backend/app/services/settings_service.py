"""Acesso à tabela settings (parâmetros globais)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import DEFAULT_SCORE_PARAMS, SCORE_PARAMS_KEY
from app.models import Setting
from app.services.scoring import ScoreParams


def get_setting(db: Session, chave: str, default=None):
    s = db.scalar(select(Setting).where(Setting.chave == chave))
    return s.valor_json if s else default


def set_setting(db: Session, chave: str, valor) -> Setting:
    s = db.scalar(select(Setting).where(Setting.chave == chave))
    if s:
        s.valor_json = valor
    else:
        s = Setting(chave=chave, valor_json=valor)
        db.add(s)
    db.commit()
    return s


def get_score_params(db: Session) -> ScoreParams:
    d = get_setting(db, SCORE_PARAMS_KEY, None) or {}
    merged = {**DEFAULT_SCORE_PARAMS, **d}
    return ScoreParams.from_dict(merged)
