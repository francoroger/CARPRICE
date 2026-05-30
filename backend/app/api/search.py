"""Busca AO VIVO (on-demand) em todos os portais."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.collectors.base import marca_canonica
from app.database import get_db
from app.schemas import ListingRead, SearchRequest, SearchResponse
from app.services.scrape import buscar_ao_vivo

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search", response_model=SearchResponse)
def buscar(req: SearchRequest, db: Session = Depends(get_db)):
    """Entra nos portais ativos ao vivo, traz tudo e filtra pelos critérios.

    Marca/modelo orientam a coleta; os demais campos filtram o resultado.
    """
    dados = req.model_dump()
    ordenar = dados.pop("ordenar", "preco_asc")
    criterios = {k: v for k, v in dados.items() if v not in (None, "")}
    if criterios.get("marca"):  # 'VW - VolksWagen' (FIPE) → 'Volkswagen' (portais)
        criterios["marca"] = marca_canonica(criterios["marca"])
    resultado = buscar_ao_vivo(db, criterios, ordenar=ordenar)

    # devolve tudo (até um teto alto) — o total real vai no cabeçalho
    LIMITE = 1000
    resultados = [
        ListingRead(
            id=l.id, portal_slug=slug, url=l.url, titulo=l.versao,
            marca=l.marca, modelo=l.modelo, versao=l.versao, ano_modelo=l.ano_modelo,
            preco=l.preco, km=l.km, faixa_km=l.faixa_km, cidade=l.cidade, uf=l.uf,
            foto_url=l.foto_url, preco_ref=s.preco_ref, desconto=s.desconto,
            origem_score=s.origem_score, score=s.score,
        )
        for (l, s, slug) in resultado["rows"][:LIMITE]
    ]
    return SearchResponse(
        total=resultado["total"], portais=resultado["portais"], resultados=resultados
    )
