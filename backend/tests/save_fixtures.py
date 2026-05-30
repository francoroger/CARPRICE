"""Salva HTML real dos portais como fixtures p/ testes de parsing offline.
Rodar manualmente quando precisar atualizar: python tests/save_fixtures.py
"""
import pathlib

from app.collectors.base import HttpFetcher, SearchCriteria
from app.collectors.registry import REGISTRY

FIX = pathlib.Path(__file__).parent / "fixtures"
FIX.mkdir(exist_ok=True)

crit = SearchCriteria(uf="SP", cidade="sao-paulo")
fetch = HttpFetcher()

for slug in ["carrosp", "napista", "comprecar", "icarros", "localiza", "mobiauto"]:
    conn = REGISTRY[slug]
    url = conn.build_search_url(crit)
    try:
        html = fetch.get(url)
        (FIX / f"{slug}.html").write_text(html, encoding="utf-8")
        print(f"{slug}: salvo {len(html)//1024} KB")
    except Exception as e:
        print(f"{slug}: FALHOU {e}")
