"""Operações: logs de varredura e disparo manual."""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.models import ScrapeLog
from app.schemas import ScrapeLogRead
from app.services.scrape import run_active_monitors

router = APIRouter(prefix="/api", tags=["ops"])


@router.get("/scrape-logs", response_model=list[ScrapeLogRead])
def logs(db: Session = Depends(get_db), limit: int = 50):
    return db.scalars(
        select(ScrapeLog).order_by(ScrapeLog.executado_em.desc()).limit(limit)
    ).all()


def _run_now() -> None:
    db = SessionLocal()
    try:
        run_active_monitors(db)
    finally:
        db.close()


@router.post("/scrape/run")
def disparar(background: BackgroundTasks):
    """Dispara uma varredura imediata em segundo plano."""
    background.add_task(_run_now)
    return {"status": "varredura iniciada"}
