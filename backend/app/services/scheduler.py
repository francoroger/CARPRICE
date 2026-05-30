"""Agendador (APScheduler) que dispara a varredura periódica."""
from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import SessionLocal
from app.services.scrape import run_active_monitors

log = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _job() -> None:
    db = SessionLocal()
    try:
        run_active_monitors(db)
    except Exception:
        log.exception("falha na varredura agendada")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    global _scheduler
    if not settings.scheduler_enabled:
        log.info("scheduler desabilitado por configuração")
        return None
    if _scheduler:
        return _scheduler
    _scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    _scheduler.add_job(
        _job,
        "interval",
        minutes=settings.scrape_default_interval_min,
        id="varredura",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.start()
    log.info("scheduler iniciado (cada %s min)", settings.scrape_default_interval_min)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
