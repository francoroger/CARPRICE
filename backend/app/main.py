"""Aplicação FastAPI — CarPrice."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import account, auth, fipe, localidades, monitors, ops, search, settings_api
from app.config import settings
from app.seed import init_db
from app.services.scheduler import shutdown_scheduler, start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Boot RESILIENTE: um soluço do banco/scheduler no arranque não pode derrubar
    # o serviço inteiro (senão o Render entra em crash-loop → "Exited with status").
    try:
        init_db()
    except Exception:
        log.exception("init_db falhou no boot — seguindo; o pool reconecta por requisição")
    try:
        start_scheduler()
    except Exception:
        log.exception("scheduler não iniciou")
    yield
    try:
        shutdown_scheduler()
    except Exception:
        pass


app = FastAPI(title="CarPrice — Monitoramento de Preços de Carros", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,  # sem cookies; permite allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(account.router)
app.include_router(monitors.router)
app.include_router(settings_api.router)
app.include_router(ops.router)
app.include_router(fipe.router)
app.include_router(search.router)
app.include_router(localidades.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
