"""Estados e municípios (via IBGE) para os dropdowns de localização."""
import logging

import httpx
from fastapi import APIRouter, HTTPException, Query

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/localidades", tags=["localidades"])

IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades"
_estados: list[dict] | None = None
_municipios: dict[str, list[str]] = {}


@router.get("/estados")
def estados():
    """[{sigla, nome}] dos 27 estados (ordenado por nome)."""
    global _estados
    if _estados is None:
        try:
            with httpx.Client(timeout=15) as c:
                data = c.get(f"{IBGE}/estados", params={"orderBy": "nome"}).json()
            _estados = [{"sigla": e["sigla"], "nome": e["nome"]} for e in data]
        except Exception as e:
            log.warning("IBGE estados falhou: %s", e)
            raise HTTPException(502, "IBGE indisponível")
    return _estados


@router.get("/municipios")
def municipios(uf: str = Query(..., min_length=2, max_length=2)):
    """Nomes dos municípios de um estado (ordenado)."""
    uf = uf.upper()
    if uf not in _municipios:
        try:
            with httpx.Client(timeout=20) as c:
                data = c.get(f"{IBGE}/estados/{uf}/municipios").json()
            _municipios[uf] = sorted(m["nome"] for m in data)
        except Exception as e:
            log.warning("IBGE municípios %s falhou: %s", uf, e)
            raise HTTPException(502, "IBGE indisponível")
    return _municipios[uf]
