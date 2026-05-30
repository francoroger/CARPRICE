"""Normalização: RawListing → dict pronto para VehicleListing.

Calcula a `grupo_chave` (chave de carros idênticos: versão + ano-modelo) e o
`hash_dedup` (identidade do anúncio entre portais).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

from app.collectors.base import RawListing


def _norm_txt(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = s.lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# palavras de ruído que não são marca (aparecem no início de títulos de alguns portais)
_RUIDO_MARCA = {"mais", "pesquisado", "foto", "360", "novo", "nova", "oferta", "destaque"}


def derivar_marca(raw: RawListing) -> str | None:
    """Marca explícita ou, na falta, a 1ª palavra significativa do título."""
    if raw.marca:
        return raw.marca
    for tok in (raw.titulo or "").split():
        t = _norm_txt(tok)
        if t and t not in _RUIDO_MARCA and not t.isdigit():
            return tok.strip().title()
    return None


def grupo_chave(raw: RawListing) -> str:
    """Chave de agrupamento de idênticos: versão (ou marca+modelo) + ano-modelo."""
    base = " ".join(
        filter(None, [_norm_txt(raw.marca), _norm_txt(raw.modelo), _norm_txt(raw.versao)])
    ).strip()
    if not base:
        base = _norm_txt(raw.titulo)
    ano = raw.ano_modelo or raw.ano_fab or "?"
    return f"{base}|{ano}"


def hash_dedup(raw: RawListing) -> str:
    """Identidade do anúncio: versão+ano+km+preço+localização (resiste a re-coleta)."""
    chave = "|".join(
        str(x)
        for x in [
            raw.portal_slug,
            _norm_txt(raw.versao or raw.titulo),
            raw.ano_modelo,
            raw.km,
            raw.preco,
            _norm_txt(raw.cidade),
            raw.uf,
        ]
    )
    return hashlib.sha256(chave.encode()).hexdigest()


def to_listing_dict(raw: RawListing) -> dict:
    """Campos para criar/atualizar um VehicleListing (sem portal_id/score)."""
    return {
        "url": raw.url,
        "marca": derivar_marca(raw),
        "modelo": raw.modelo,
        "versao": raw.versao,
        "ano_fab": raw.ano_fab,
        "ano_modelo": raw.ano_modelo,
        "preco": raw.preco,
        "km": raw.km,
        "cambio": raw.cambio,
        "combustivel": raw.combustivel,
        "cidade": raw.cidade,
        "uf": raw.uf,
        "foto_url": raw.foto_url,
        "grupo_chave": grupo_chave(raw),
        "hash_dedup": hash_dedup(raw),
    }
