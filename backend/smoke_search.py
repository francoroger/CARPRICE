"""Smoke da busca ao vivo: coleta paralela + filtros."""
import time

from app.database import SessionLocal
from app.seed import init_db
from app.services.scrape import buscar_ao_vivo

init_db()
db = SessionLocal()
try:
    # busca focada: Honda HR-V em SP, usados, até R$ 150k
    crit = {"marca": "honda", "modelo": "hr-v", "uf": "SP", "cidade": "sao-paulo",
            "preco_max": 150000, "condicao": "usado"}
    t0 = time.monotonic()
    r = buscar_ao_vivo(db, crit)
    dt = time.monotonic() - t0
    print(f"\nBusca levou {dt:.1f}s | total filtrado: {r['total']}")
    print("portais:")
    for p in r["portais"]:
        print(f"   {p['portal']:10} {p['status']:6} {p['qtd']:>3} anúncios"
              + (f"  ({p['erro'][:40]})" if p['erro'] else ""))
    print("\nTop resultados:")
    for l, s, slug in r["rows"][:8]:
        print(f"   [{slug:9}] R$ {l.preco!s:>8} | {l.km!s:>7}km | {l.ano_modelo} | "
              f"desc={(s.desconto or 0)*100:5.1f}% [{s.origem_score or '-'}] | "
              f"{(l.versao or '')[:35]}")
finally:
    db.close()
