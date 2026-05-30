"""Filtros em cascata (marca → modelo → versão) a partir da FIPE oficial."""
import logging

from fastapi import APIRouter, HTTPException, Query

from app.services.fipe import get_fipe_client

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/fipe", tags=["fipe"])


@router.get("/marcas")
def marcas():
    """Todas as marcas: [{codigo, nome}]."""
    try:
        return get_fipe_client().marcas()
    except Exception as e:
        log.warning("FIPE marcas falhou: %s", e)
        raise HTTPException(502, "FIPE indisponível no momento")


@router.get("/modelos")
def modelos(marca: str = Query(..., description="código FIPE da marca")):
    """Famílias de modelo da marca: ['ARGO', 'MOBI', ...]."""
    try:
        return get_fipe_client().modelos_familias(int(marca))
    except Exception as e:
        log.warning("FIPE modelos falhou: %s", e)
        raise HTTPException(502, "FIPE indisponível no momento")


@router.get("/versoes")
def versoes(
    marca: str = Query(..., description="código FIPE da marca"),
    modelo: str = Query(..., description="família do modelo (ex.: ARGO)"),
):
    """Versões da família: [{codigo, nome}]."""
    try:
        return get_fipe_client().versoes(int(marca), modelo)
    except Exception as e:
        log.warning("FIPE versoes falhou: %s", e)
        raise HTTPException(502, "FIPE indisponível no momento")
