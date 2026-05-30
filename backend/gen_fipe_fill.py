"""Preenche as marcas que vieram vazias no catálogo FIPE (retry + backoff no 403)."""
import json, time
from app.services.fipe import FipeClient

path = "app/data/fipe_modelos.json"
cat = json.load(open(path, encoding="utf-8"))
vazias = [(c, v["nome"]) for c, v in cat.items() if not v["modelos"]]
print(f"marcas vazias: {len(vazias)} -> {[n for _,n in vazias]}")

fc = FipeClient()
for cod, nome in vazias:
    ok = False
    for tent in range(4):
        try:
            time.sleep(1.5)
            mods = fc._get_modelos(int(cod))
            cat[cod]["modelos"] = [{"Label": x["Label"], "Value": x["Value"]} for x in mods]
            print(f"  OK {nome}: {len(mods)} modelos")
            ok = True
            break
        except Exception as e:
            # limpa cache da falha e espera mais
            fc._modelos.pop(int(cod), None)
            print(f"  {nome} tent{tent+1}: {str(e)[:40]} — espera {5*(tent+1)}s")
            time.sleep(5 * (tent + 1))
    if not ok:
        print(f"  !! {nome} segue vazia")
fc.close()

json.dump(cat, open(path, "w", encoding="utf-8"), ensure_ascii=False)
restantes = [v["nome"] for v in cat.values() if not v["modelos"]]
total = sum(len(v["modelos"]) for v in cat.values())
print(f"\ntotal modelos: {total} | ainda vazias: {restantes}")
