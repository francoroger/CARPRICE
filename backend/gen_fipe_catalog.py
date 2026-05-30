"""Gera o catálogo FIPE estático (marcas + modelos brutos) para embutir no backend.
Roda de um IP onde a FIPE responde (residencial). Salva app/data/fipe_modelos.json.
"""
import json, os, time
from app.services.fipe import FipeClient

fc = FipeClient()
marcas = fc._get_marcas()  # [{Label, Value}]
print(f"marcas: {len(marcas)}")

catalogo = {}
for i, m in enumerate(marcas, 1):
    cod = str(m["Value"])
    try:
        modelos = fc._get_modelos(int(m["Value"]))  # [{Label, Value}]
        catalogo[cod] = {"nome": m["Label"],
                         "modelos": [{"Label": x["Label"], "Value": x["Value"]} for x in modelos]}
        if i % 20 == 0:
            print(f"  {i}/{len(marcas)} ({m['Label']}: {len(modelos)} modelos)")
    except Exception as e:
        print(f"  FALHA {m['Label']}: {e}")
        catalogo[cod] = {"nome": m["Label"], "modelos": []}
    time.sleep(0.05)
fc.close()

os.makedirs("app/data", exist_ok=True)
path = "app/data/fipe_modelos.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(catalogo, f, ensure_ascii=False)
kb = os.path.getsize(path) // 1024
total_mod = sum(len(v["modelos"]) for v in catalogo.values())
print(f"\nSalvo {path}: {len(catalogo)} marcas, {total_mod} modelos, {kb} KB")
