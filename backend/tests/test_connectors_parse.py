"""Testes de parsing dos conectores (offline, contra fixtures de HTML real).

Detectam quebra quando um portal muda de layout. Para atualizar as fixtures:
    python tests/save_fixtures.py
"""
import pathlib

import pytest

from app.collectors.normalize import grupo_chave, to_listing_dict
from app.collectors.registry import REGISTRY

FIX = pathlib.Path(__file__).parent / "fixtures"

CASOS = {
    "carrosp": {"min": 15},
    "napista": {"min": 20},
    "comprecar": {"min": 15},
    "icarros": {"min": 10},
    "localiza": {"min": 15},   # via __NEXT_DATA__
    "mobiauto": {"min": 15},   # via __NEXT_DATA__
}


def _html(slug: str) -> str:
    p = FIX / f"{slug}.html"
    if not p.exists():
        pytest.skip(f"fixture ausente: {slug}.html (rode tests/save_fixtures.py)")
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("slug,esperado", CASOS.items())
def test_parse_extrai_anuncios(slug, esperado):
    conn = REGISTRY[slug]
    listings = conn.parse_listings(_html(slug))

    assert len(listings) >= esperado["min"], f"{slug}: poucos anúncios"

    # todo anúncio tem URL e preço plausível
    for l in listings:
        assert l.url and l.url.startswith("http"), f"{slug}: URL inválida"
        assert l.preco and l.preco > 1000, f"{slug}: preço inválido {l.preco}"

    # a maioria tem ano e km extraídos
    com_ano = sum(1 for l in listings if l.ano_modelo)
    assert com_ano >= len(listings) * 0.6, f"{slug}: poucos anos extraídos"


@pytest.mark.parametrize("slug", CASOS.keys())
def test_normalizacao_gera_grupo_e_hash(slug):
    conn = REGISTRY[slug]
    listings = conn.parse_listings(_html(slug))
    assert listings
    for l in listings[:5]:
        d = to_listing_dict(l)
        assert d["hash_dedup"] and len(d["hash_dedup"]) == 64
        # grupo_chave não pode ser vazio/só o separador
        assert d["grupo_chave"] and d["grupo_chave"] not in ("|?", "|None")


def test_comprecar_titulo_nao_vazio():
    """Regressão: Comprecar derivava título vazio → grupo_chave '|ano'."""
    conn = REGISTRY["comprecar"]
    listings = conn.parse_listings(_html("comprecar"))
    com_titulo = [l for l in listings if l.versao]
    assert len(com_titulo) >= len(listings) * 0.8
    # o grupo deve conter texto antes do separador
    g = grupo_chave(com_titulo[0])
    assert g.split("|")[0].strip(), "grupo_chave sem parte de modelo"
