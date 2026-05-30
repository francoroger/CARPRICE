"""Valida o wiring da API sem abrir porta (TestClient in-process)."""
import os

os.environ["SCHEDULER_ENABLED"] = "false"  # evita thread do scheduler no teste

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

with TestClient(app) as c:
    print("health:", c.get("/api/health").json())

    monitors = c.get("/api/monitors").json()
    print(f"monitors: {len(monitors)} | ex:", monitors[0]["nome"] if monitors else None)

    portals = c.get("/api/settings/portals").json()
    ativos = [p["slug"] for p in portals if p["ativo"]]
    print(f"portals: {len(portals)} | ativos: {ativos}")

    score = c.get("/api/settings/score").json()
    print("score params:", score)

    listings = c.get("/api/listings?limit=5").json()
    print(f"listings rankeados: {len(listings)}")
    for l in listings[:3]:
        print(f"   [{l['portal_slug']}] R$ {l['preco']} | desc={l['desconto']} | {l['origem_score']}")

    # cria e remove um monitor (CRUD)
    novo = c.post("/api/monitors", json={
        "nome": "Teste API", "criterios_json": {"modelo": "civic", "uf": "SP"},
        "threshold_desconto": 0.1,
    })
    print("POST monitor:", novo.status_code, novo.json()["id"])
    mid = novo.json()["id"]
    patched = c.patch(f"/api/monitors/{mid}", json={"status": "pausado"})
    print("PATCH status:", patched.json()["status"])
    print("DELETE:", c.delete(f"/api/monitors/{mid}").status_code)

    print("scrape-logs:", len(c.get("/api/scrape-logs").json()))
print("\nOK — API responde em todos os endpoints")
