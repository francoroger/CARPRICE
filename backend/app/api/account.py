"""Dados do usuário logado: carros salvos e histórico de buscas (server-side)."""
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import SavedListing, SearchHistory, User
from app.schemas import (
    SavedListingCreate,
    SavedListingRead,
    SearchHistoryCreate,
    SearchHistoryRead,
)

router = APIRouter(prefix="/api/account", tags=["account"])
MAX_HIST = 50


# --- carros salvos --- #
@router.get("/saved", response_model=list[SavedListingRead])
def listar_salvos(user: User = Depends(usuario_atual), db: Session = Depends(get_db)):
    return db.scalars(
        select(SavedListing).where(SavedListing.user_id == user.id)
        .order_by(SavedListing.salvo_em.desc())
    ).all()


@router.post("/saved", response_model=SavedListingRead)
def salvar(payload: SavedListingCreate, user: User = Depends(usuario_atual),
           db: Session = Depends(get_db)):
    existe = db.scalar(select(SavedListing).where(
        SavedListing.user_id == user.id, SavedListing.url == payload.url))
    if existe:
        existe.dados_json = payload.dados or existe.dados_json
        db.commit(); db.refresh(existe)
        return existe
    s = SavedListing(user_id=user.id, url=payload.url, dados_json=payload.dados or {})
    db.add(s); db.commit(); db.refresh(s)
    return s


@router.delete("/saved", status_code=204)
def remover_salvo(url: str, user: User = Depends(usuario_atual),
                  db: Session = Depends(get_db)):
    db.execute(delete(SavedListing).where(
        SavedListing.user_id == user.id, SavedListing.url == url))
    db.commit()


# --- histórico de buscas --- #
@router.get("/history", response_model=list[SearchHistoryRead])
def listar_historico(user: User = Depends(usuario_atual), db: Session = Depends(get_db)):
    return db.scalars(
        select(SearchHistory).where(SearchHistory.user_id == user.id)
        .order_by(SearchHistory.criado_em.desc())
    ).all()


@router.post("/history", response_model=SearchHistoryRead)
def registrar_historico(payload: SearchHistoryCreate, user: User = Depends(usuario_atual),
                        db: Session = Depends(get_db)):
    # dedup: remove buscas idênticas anteriores
    anteriores = db.scalars(select(SearchHistory).where(
        SearchHistory.user_id == user.id)).all()
    for a in anteriores:
        if a.criterios_json == payload.criterios:
            db.delete(a)
    h = SearchHistory(user_id=user.id, criterios_json=payload.criterios,
                      filtro_json=payload.filtro, label=payload.label, total=payload.total)
    db.add(h)
    db.flush()
    # mantém só as MAX_HIST mais recentes
    todas = db.scalars(select(SearchHistory).where(SearchHistory.user_id == user.id)
                       .order_by(SearchHistory.criado_em.desc())).all()
    for velha in todas[MAX_HIST:]:
        db.delete(velha)
    db.commit(); db.refresh(h)
    return h


@router.delete("/history/{hid}", status_code=204)
def remover_historico(hid: int, user: User = Depends(usuario_atual),
                      db: Session = Depends(get_db)):
    h = db.get(SearchHistory, hid)
    if h and h.user_id == user.id:
        db.delete(h); db.commit()


@router.delete("/history", status_code=204)
def limpar_historico(user: User = Depends(usuario_atual), db: Session = Depends(get_db)):
    db.execute(delete(SearchHistory).where(SearchHistory.user_id == user.id))
    db.commit()
