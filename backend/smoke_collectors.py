"""Smoke test: roda o Fetcher Nível 1 + cada conector + normalização, ao vivo."""
import sys

from app.collectors.base import HttpFetcher, FetchError, SearchCriteria
from app.collectors.normalize import grupo_chave, hash_dedup
from app.collectors.registry import all_connectors

crit = SearchCriteria(uf="SP", cidade="sao-paulo")
fetch = HttpFetcher()

for conn in all_connectors():
    url = conn.build_search_url(crit)
    try:
        raws = conn.search(crit, fetch)
        amostra = raws[0] if raws else None
        print(f"\n[{conn.slug:10}] {len(raws):>3} anúncios | {url}")
        if amostra:
            print(f"    ex: R$ {amostra.preco} | {amostra.km} km | ano {amostra.ano_modelo}"
                  f" | {(amostra.versao or amostra.titulo or '')[:45]}")
            print(f"    grupo='{grupo_chave(amostra)}' | hash={hash_dedup(amostra)[:12]}")
    except FetchError as e:
        print(f"\n[{conn.slug:10}]  FALHA (degrada graciosamente): {e} | {url}")
    except Exception as e:
        print(f"\n[{conn.slug:10}]  ERRO INESPERADO: {type(e).__name__}: {e}", file=sys.stderr)
