"""Testes de API: auth, rate limit, proteção admin, escopo de monitores,
frequência da varredura, e-mail-resumo, limpeza e health."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import ratelimit
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import (
    ListingScore,
    Monitor,
    Notification,
    Portal,
    ScrapeLog,
    VehicleListing,
)


@pytest.fixture()
def ctx(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 't.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Sess = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def _db():
        db = Sess()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    ratelimit.zerar()
    monkeypatch.setattr(settings, "admin_emails", "")
    yield TestClient(app), Sess
    app.dependency_overrides.clear()


def _conta(c, email="ana@gmail.com"):
    r = c.post("/api/auth/register", json={"nome": "Ana", "email": email, "senha": "123456"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}, r.json()["user"]


def test_login_rate_limit(ctx):
    c, _ = ctx
    _conta(c)
    for _ in range(10):
        assert c.post("/api/auth/login", json={"email": "ana@gmail.com", "senha": "x"}).status_code == 401
    r = c.post("/api/auth/login", json={"email": "ana@gmail.com", "senha": "x"})
    assert r.status_code == 429 and "aguarde" in r.json()["detail"]


def test_monitor_exige_login_e_e_privado(ctx):
    c, _ = ctx
    corpo = {"nome": "Gol", "criterios_json": {"marca": "VW", "modelo": "GOL"}}
    assert c.post("/api/monitors", json=corpo).status_code == 401      # anônimo não cria
    assert c.get("/api/monitors").json() == []                         # anônimo lista vazio
    ha, _ = _conta(c, "a@gmail.com")
    hb, _ = _conta(c, "b@gmail.com")
    mid = c.post("/api/monitors", json=corpo, headers=ha).json()["id"]
    assert len(c.get("/api/monitors", headers=ha).json()) == 1
    assert c.get("/api/monitors", headers=hb).json() == []             # outro usuário não vê
    assert c.delete(f"/api/monitors/{mid}", headers=hb).status_code == 404
    assert c.delete(f"/api/monitors/{mid}", headers=ha).status_code == 204


def test_frequencia_validada(ctx):
    c, _ = ctx
    h, _ = _conta(c)
    r = c.post("/api/monitors", headers=h,
               json={"nome": "x", "criterios_json": {}, "frequencia_min": 5})
    assert r.status_code == 422                                        # mínimo 15 min


def test_apagar_monitor_com_notificacoes(ctx):
    c, Sess = ctx
    h, user = _conta(c)
    mid = c.post("/api/monitors", headers=h, json={"nome": "x", "criterios_json": {}}).json()["id"]
    db = Sess()
    p = Portal(nome="P", slug="p", min_tier=1, ativo=True, rate_limit_s=1, config_json={})
    db.add(p); db.flush()
    l = VehicleListing(portal_id=p.id, url="u", hash_dedup="h1")
    db.add(l); db.flush()
    db.add(Notification(monitor_id=mid, listing_id=l.id, canal="email", status="ignorado"))
    db.add(ScrapeLog(monitor_id=mid, status="ok", qtd_resultados=1))
    db.commit(); db.close()
    assert c.delete(f"/api/monitors/{mid}", headers=h).status_code == 204


def test_configuracoes_protegidas(ctx, monkeypatch):
    c, Sess = ctx
    db = Sess()
    db.add(Portal(nome="CarroSP", slug="carrosp", min_tier=1, ativo=True, rate_limit_s=1, config_json={}))
    db.commit(); db.close()
    assert c.patch("/api/settings/portals/carrosp?ativo=false").status_code == 401
    assert c.put("/api/settings/score", json={"valor_json": {"min_grupo": 5}}).status_code == 401
    h, user = _conta(c, "dono@gmail.com")
    hx, _ = _conta(c, "intruso@gmail.com")
    monkeypatch.setattr(settings, "admin_emails", "dono@gmail.com")
    assert c.patch("/api/settings/portals/carrosp?ativo=false", headers=hx).status_code == 403
    assert c.patch("/api/settings/portals/carrosp?ativo=false", headers=h).status_code == 200
    assert c.get("/api/auth/me", headers=h).json()["admin"] is True
    assert c.get("/api/auth/me", headers=hx).json()["admin"] is False


def test_varrer_agora_exige_login(ctx):
    c, _ = ctx
    assert c.post("/api/scrape/run").status_code == 401


def test_varredura_respeita_frequencia_e_manda_um_resumo(ctx, monkeypatch):
    from app.services import notifications, scrape

    c, Sess = ctx
    _, user = _conta(c)
    db = Sess()
    p = Portal(nome="P", slug="p", min_tier=1, ativo=True, rate_limit_s=1, config_json={})
    db.add(p); db.flush()
    agora = datetime.now(timezone.utc)
    m_vencido = Monitor(user_id=user["id"], nome="vencido", criterios_json={},
                        frequencia_min=60, ultima_exec_em=agora - timedelta(hours=2))
    m_recente = Monitor(user_id=user["id"], nome="recente", criterios_json={},
                        frequencia_min=60, ultima_exec_em=agora - timedelta(minutes=10))
    m_anonimo = Monitor(user_id=None, nome="anonimo", criterios_json={})
    db.add_all([m_vencido, m_recente, m_anonimo]); db.flush()
    carros = []
    for i in range(3):
        l = VehicleListing(portal_id=p.id, url=f"u{i}", hash_dedup=f"h{i}", preco=40000)
        db.add(l); db.flush()
        s = ListingScore(listing_id=l.id, desconto=0.15, preco_ref=47000, score=0.15)
        db.add(s); db.flush()
        carros.append((l, s, "p"))
    db.commit()

    rodados, resumos = [], []
    monkeypatch.setattr(scrape, "buscar_ao_vivo",
                        lambda db, crit, ordenar: (rodados.append(1) or
                                                   {"rows": carros, "total": len(carros)}))
    monkeypatch.setattr(notifications, "enviar_resumo",
                        lambda db, m, itens: resumos.append((m.nome, len(itens))) or True)

    res = scrape.run_active_monitors(db, somente_vencidos=True)
    assert res["monitores"] == 1 and len(rodados) == 1     # só o vencido (nem o anônimo)
    assert resumos == [("vencido", 3)]                     # UM e-mail com os 3 carros
    # 2ª rodada: matches já registrados → nada novo, nenhum e-mail
    scrape.run_active_monitors(db, user_id=user["id"], somente_vencidos=False)
    assert resumos == [("vencido", 3), ("recente", 3)]
    db.close()


def test_limpeza(ctx):
    from app.services.scrape import limpeza

    _, Sess = ctx
    db = Sess()
    p = Portal(nome="P", slug="p", min_tier=1, ativo=True, rate_limit_s=1, config_json={})
    db.add(p); db.flush()
    velho = datetime.now(timezone.utc) - timedelta(days=90)
    db.add(VehicleListing(portal_id=p.id, url="a", hash_dedup="a", ultimo_visto_em=velho))
    db.add(VehicleListing(portal_id=p.id, url="b", hash_dedup="b"))
    db.add(ScrapeLog(status="ok", qtd_resultados=0, executado_em=velho))
    db.commit()
    res = limpeza(db)
    assert res == {"anuncios_inativados": 1, "logs_apagados": 1}
    db.close()


def test_health_reporta_banco(ctx):
    c, _ = ctx
    r = c.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and "banco" in r.json()
