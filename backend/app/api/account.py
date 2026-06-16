"""Dados do usuário logado: carros salvos e histórico de buscas (server-side)."""
from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import (
    ListingScore,
    Monitor,
    MonitorMatch,
    Portal,
    SavedListing,
    SearchHistory,
    User,
    VehicleListing,
)
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


# --- alertas: carros que os monitores DO usuário encontraram (acima do threshold) --- #
@router.get("/alerts")
def alertas(user: User = Depends(usuario_atual), db: Session = Depends(get_db)):
    rows = db.execute(
        select(MonitorMatch, VehicleListing, ListingScore, Monitor, Portal.slug)
        .join(VehicleListing, VehicleListing.id == MonitorMatch.listing_id)
        .join(Monitor, Monitor.id == MonitorMatch.monitor_id)
        .join(Portal, Portal.id == VehicleListing.portal_id)
        .outerjoin(ListingScore, ListingScore.listing_id == VehicleListing.id)
        .where(Monitor.user_id == user.id, VehicleListing.ativo.is_(True))
        .order_by(MonitorMatch.criado_em.desc())
        .limit(60)
    ).all()
    return [
        {
            "id": match.id,
            "monitor": mon.nome,
            "quando": match.criado_em,
            "url": l.url, "versao": l.versao, "titulo": l.titulo,
            "marca": l.marca, "modelo": l.modelo, "ano_modelo": l.ano_modelo,
            "preco": l.preco, "km": l.km, "cidade": l.cidade, "uf": l.uf,
            "foto_url": l.foto_url, "portal_slug": slug,
            "preco_ref": s.preco_ref if s else None,
            "desconto": (s.desconto if s else None) or match.desconto,
            "origem_score": s.origem_score if s else None,
        }
        for (match, l, s, mon, slug) in rows
    ]
