"""Listagem de anúncios rankeados (com desconto e origem do score)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ListingScore, Portal, VehicleListing
from app.schemas import ListingRead

router = APIRouter(prefix="/api/listings", tags=["listings"])


@router.get("", response_model=list[ListingRead])
def rankeados(
    db: Session = Depends(get_db),
    origem: str | None = Query(None, description="MERCADO ou FIPE"),
    desconto_min: float | None = Query(None),
    limit: int = Query(100, le=500),
):
    q = (
        select(VehicleListing, ListingScore, Portal.slug)
        .join(ListingScore, ListingScore.listing_id == VehicleListing.id)
        .join(Portal, Portal.id == VehicleListing.portal_id)
        .where(VehicleListing.ativo.is_(True))
        .order_by(ListingScore.score.desc().nullslast())
        .limit(limit)
    )
    if origem:
        q = q.where(ListingScore.origem_score == origem)
    if desconto_min is not None:
        q = q.where(ListingScore.desconto >= desconto_min)

    out = []
    for listing, score, slug in db.execute(q).all():
        out.append(ListingRead(
            id=listing.id, portal_slug=slug, url=listing.url, titulo=listing.versao,
            marca=listing.marca, modelo=listing.modelo, versao=listing.versao,
            ano_modelo=listing.ano_modelo, preco=listing.preco, km=listing.km,
            faixa_km=listing.faixa_km, cidade=listing.cidade, uf=listing.uf,
            foto_url=listing.foto_url, preco_ref=score.preco_ref,
            desconto=score.desconto, origem_score=score.origem_score, score=score.score,
        ))
    return out
