"""Embute os ANOS-MODELO de cada versão no catálogo FIPE (vínculo ano<->versão).

Para cada modelo (versão) do catálogo consulta ConsultarAnoModelo e grava
`"anos": [2024, 2023, ...]` (anos distintos, desc). Resumível: pula quem já tem
`anos`, salva a cada marca, faz retry/backoff no 403 da FIPE.

Rodar de um IP onde a FIPE responde (residencial). No Render a FIPE bloqueia, por
isso o dado precisa estar embutido no JSON estático — igual aos modelos.
"""
import json
import pathlib
import time

from app.services.fipe import FipeClient

PATH = pathlib.Path("app/data/fipe_modelos.json")
cat = json.loads(PATH.read_text(encoding="utf-8"))

fc = FipeClient()
ref = fc._ref_atual()
print(f"ref FIPE: {ref}")


def anos_de(cod_marca: int, cod_modelo: int) -> list[int]:
    """Anos-modelo distintos de uma versão (ex.: ['2014-5','2013-5'] -> [2014,2013])."""
    raw = fc._get_anos(cod_marca, cod_modelo)
    anos = set()
    for a in raw:
        v = str(a.get("Value", ""))
        ystr = v.split("-")[0]
        if ystr.isdigit():
            y = int(ystr)
            if y == 32000:        # "Zero KM" -> ano corrente
                continue
            if 1980 <= y <= 2030:
                anos.add(y)
    return sorted(anos, reverse=True)


total_marcas = len(cat)
for i, (cod, v) in enumerate(cat.items(), 1):
    cm = int(cod)
    mods = v["modelos"]
    faltam = [m for m in mods if "anos" not in m]
    if not faltam:
        continue
    print(f"[{i}/{total_marcas}] {v['nome']}: {len(faltam)}/{len(mods)} versoes")
    for m in faltam:
        for tent in range(4):
            try:
                m["anos"] = anos_de(cm, int(m["Value"]))
                break
            except Exception as e:  # noqa: BLE001
                fc._anos.pop((cm, int(m["Value"])), None)
                espera = 4 * (tent + 1)
                print(f"    {str(m['Label'])[:30]} tent{tent+1}: {str(e)[:40]} — {espera}s")
                time.sleep(espera)
        else:
            m["anos"] = []  # desiste dessa versão; segue
    # salva incremental ao fim de cada marca (resumível)
    PATH.write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")

fc.close()

com = sum(1 for v in cat.values() for m in v["modelos"] if m.get("anos"))
tot = sum(len(v["modelos"]) for v in cat.values())
print(f"\nversoes com anos: {com}/{tot}")
