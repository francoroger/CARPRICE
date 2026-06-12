"""Operações: logs de varredura, disparo manual e STATUS em tempo real."""
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import ScrapeLog
from app.schemas import ScrapeLogRead
from app.services.scrape import run_active_monitors

router = APIRouter(prefix="/api", tags=["ops"])

# Estado da varredura em andamento (1 worker → dict em memória basta).
# O frontend faz polling em GET /scrape/status p/ mostrar progresso de verdade.
VARREDURA: dict = {
    "estado": "ocioso",          # "ocioso" | "rodando"
    "iniciado_em": None,
    "monitores_total": 0,
    "monitores_feitos": 0,
    "monitor_atual": None,
    "resumo": None,              # resumo da última varredura concluída
    "erro": None,
}


@router.get("/scrape-logs", response_model=list[ScrapeLogRead])
def logs(db: Session = Depends(get_db), limit: int = 50):
    return db.scalars(
        select(ScrapeLog).order_by(ScrapeLog.executado_em.desc()).limit(limit)
    ).all()


def _run_now() -> None:
    db = SessionLocal()
    try:
        resumo = run_active_monitors(db, progresso=VARREDURA.update)
        VARREDURA.update(estado="ocioso", resumo=resumo, monitor_atual=None)
    except Exception as e:  # noqa: BLE001 — status precisa voltar a ocioso sempre
        VARREDURA.update(estado="ocioso", erro=str(e), monitor_atual=None)
    finally:
        db.close()


@router.post("/scrape/run")
def disparar(background: BackgroundTasks):
    """Dispara uma varredura imediata em segundo plano (1 por vez)."""
    if VARREDURA["estado"] == "rodando":
        return {"status": "ja_rodando"}
    VARREDURA.update(
        estado="rodando", erro=None, resumo=None, monitores_feitos=0,
        monitores_total=0, monitor_atual=None,
        iniciado_em=datetime.now(timezone.utc).isoformat(),
    )
    background.add_task(_run_now)
    return {"status": "varredura iniciada"}


@router.get("/scrape/status")
def status_varredura():
    """Progresso da varredura: o frontend faz polling p/ feedback em tempo real."""
    return VARREDURA
