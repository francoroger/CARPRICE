"""Criação das tabelas e seed inicial (portais + parâmetros + monitor demo)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import DEFAULT_SCORE_PARAMS, SCORE_PARAMS_KEY
from app.database import Base, SessionLocal, engine
from app.models import AccessTier, Monitor, Portal, Setting

# Portais conhecidos (validados no spike). Os de anti-bot entram desativados.
PORTAIS = [
    ("Napista", "napista", AccessTier.HTTP, True),
    ("CarroSP", "carrosp", AccessTier.HTTP, True),
    ("Comprecar", "comprecar", AccessTier.HTTP, True),
    ("iCarros", "icarros", AccessTier.HTTP, True),
    ("Localiza Seminovos", "localiza", AccessTier.HTTP, True),
    ("Mobiauto", "mobiauto", AccessTier.HTTP, True),
    # Fase 2/3 — exigem nível mais alto, ficam desativados no MVP:
    ("Webmotors", "webmotors", AccessTier.UNBLOCKER, False),
    ("OLX Autos", "olx", AccessTier.UNBLOCKER, False),
    ("Movida Seminovos", "movida", AccessTier.UNBLOCKER, False),
]


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed(db)
    finally:
        db.close()


def _seed(db: Session) -> None:
    for nome, slug, tier, ativo in PORTAIS:
        if not db.scalar(select(Portal).where(Portal.slug == slug)):
            db.add(Portal(nome=nome, slug=slug, min_tier=int(tier), ativo=ativo,
                          rate_limit_s=2.0, config_json={}))

    if not db.scalar(select(Setting).where(Setting.chave == SCORE_PARAMS_KEY)):
        db.add(Setting(chave=SCORE_PARAMS_KEY, valor_json=DEFAULT_SCORE_PARAMS))

    if not db.scalar(select(Monitor)):
        db.add(Monitor(
            nome="Demo — Onix em SP",
            criterios_json={"modelo": "onix", "uf": "SP", "cidade": "sao-paulo",
                            "preco_max": 90000, "km_max": 100000},
            frequencia_min=60,
            threshold_desconto=0.08,
            canais_notif=["email"],
            status="ativo",
        ))
    db.commit()


if __name__ == "__main__":
    init_db()
    print("banco inicializado e seed aplicado")
