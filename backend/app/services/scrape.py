"""Orquestração da coleta — busca ao vivo E varredura dos monitores.

UM pipeline só (`buscar_ao_vivo`): coleta paralela nos portais ativos, filtros no
servidor onde o portal suporta (CarroSP: ano/km/preço/raio), marca canônica,
cache-first e score focado. A varredura (`run_active_monitors`) roda esse mesmo
pipeline por monitor e notifica os matches novos acima do threshold.
Degradação graciosa: um portal que falha é logado e pulado, sem derrubar o resto.
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import (
    FetchError,
    SearchCriteria,
    fetcher_para_tier,
    marca_canonica,
)
from app.collectors.normalize import to_listing_dict
from app.collectors.registry import get_connector
from app.models import (
    AccessTier,
    ListingScore,
    Monitor,
    MonitorStatus,
    Portal,
    ScrapeLog,
    VehicleListing,
)
from app.services import notifications
from app.services.fipe import get_fipe_client
from app.services.filters import passa_filtros
from app.services.scoring import ScoreInput, ScoreParams, calcular_scores, faixa_de_km
from app.services.settings_service import get_score_params

log = logging.getLogger(__name__)
MAX_TIER_AUTO = AccessTier.HTTP  # MVP só escala até o nível 1 (httpx)


# --------------------------------------------------------------------------- #
# Upsert no mercado global (dedup por hash)
# --------------------------------------------------------------------------- #


def _upsert_listing(db: Session, portal_id: int, dados: dict) -> bool:
    """Insere ou atualiza por hash_dedup. Retorna True se for anúncio NOVO."""
    existente = db.scalar(
        select(VehicleListing).where(VehicleListing.hash_dedup == dados["hash_dedup"])
    )
    agora = datetime.now(timezone.utc)
    if existente:
        existente.preco = dados["preco"]
        existente.km = dados["km"]
        # campos que podem ter melhorado entre coletas (ex.: foto que era lazy)
        if dados.get("foto_url"):
            existente.foto_url = dados["foto_url"]
        if dados.get("cidade") and not existente.cidade:
            existente.cidade = dados["cidade"]
            existente.uf = dados.get("uf") or existente.uf
        existente.ultimo_visto_em = agora
        existente.ativo = True
        return False
    db.add(VehicleListing(portal_id=portal_id, primeiro_visto_em=agora,
                          ultimo_visto_em=agora, **dados))
    db.flush()  # grava já p/ o próximo SELECT detectar duplicata (autoflush=False)
    return True


# --------------------------------------------------------------------------- #
# Busca AO VIVO (on-demand) — entra em todos os portais em paralelo
# A VARREDURA dos monitores usa este MESMO pipeline (run_active_monitors).
# --------------------------------------------------------------------------- #


def normalizar_criterios(criterios: dict) -> dict:
    """Critérios prontos p/ coleta + filtro, venham da Busca ou de um monitor salvo.

    - tira chaves vazias (None/""/[]),
    - marca FIPE → canônica ('VW - VolksWagen' → 'Volkswagen'): sem isso a URL dos
      portais e o pós-filtro não casam nada (monitor criado pelo formulário guarda
      o rótulo da FIPE no criterios_json).
    """
    crit = {k: v for k, v in (criterios or {}).items() if v not in (None, "", [])}
    if crit.get("marca"):
        crit["marca"] = marca_canonica(crit["marca"])
    return crit


def _fetch_portal_raws(portal: Portal, criteria: SearchCriteria):
    """Coleta de UM portal (só rede, sem DB — seguro para rodar em thread)."""
    conn = get_connector(portal.slug)
    t0 = time.monotonic()
    tier = AccessTier(portal.min_tier)
    if not conn:
        return [], "sem_conector", "conector não registrado", 0
    try:
        if tier > MAX_TIER_AUTO:
            raise FetchError(f"requer nível {tier} (não habilitado)")
        raws = conn.search(criteria, fetcher_para_tier(tier))
        return raws, "ok", None, int((time.monotonic() - t0) * 1000)
    except (FetchError, NotImplementedError) as e:
        return [], "falha", str(e), int((time.monotonic() - t0) * 1000)
    except Exception as e:  # parsing inesperado
        log.exception("busca ao vivo: erro no portal %s", portal.slug)
        return [], "erro", f"{type(e).__name__}: {e}", int((time.monotonic() - t0) * 1000)


def _grupo_modelo(l: VehicleListing) -> str:
    """Chave modelo+ano (mesmo carro, qualquer versão) — 2º nível da referência.

    A família é o 1º token-NOME do modelo/versão: pula cilindrada ('1.0 16v')
    e a marca repetida no título ('Volkswagen Gol ...' → 'gol'). Sem família
    identificável, NÃO agrupa além da versão (evita juntar carros diferentes).
    """
    marca = (l.marca or "").lower()
    base = l.modelo or l.versao or ""
    fam = None
    for t in base.split():
        if any(c.isdigit() for c in t):
            continue  # cilindrada/ano/16v
        tl = t.lower().strip(".-")
        if marca and (tl == marca or tl in marca.split()):
            continue  # marca repetida no título
        fam = tl
        break
    if not fam:
        return f"{marca}|{l.grupo_chave or '?'}"
    return f"{marca}|{fam}|{l.ano_modelo or '?'}"


def _score_focado(db: Session, listings: list[VehicleListing], params: ScoreParams) -> None:
    """Scoreia APENAS o conjunto da busca com o engine de Preço de Mercado.

    Referência hierárquica (versão+ano → modelo+ano) calculada DENTRO do engine;
    a FIPE só é consultada p/ anúncios em que NENHUM nível tem volume (e com teto,
    p/ não travar a busca — no Render o circuit-breaker já pula tudo).
    """
    if not listings:
        return
    n_versao: dict[str, int] = {}
    n_modelo: dict[str, int] = {}
    for l in listings:
        n_versao[l.grupo_chave or "?"] = n_versao.get(l.grupo_chave or "?", 0) + 1
        gm = _grupo_modelo(l)
        n_modelo[gm] = n_modelo.get(gm, 0) + 1

    # FIPE só p/ quem não tem comparável em nível nenhum, 1x por grupo, com teto
    MAX_FIPE = 12
    fipe_por_grupo: dict[str, int | None] = {}
    fc = get_fipe_client()
    usa_fipe = fc.valor_disponivel()  # no Render a FIPE bloqueia → pula (rápido)
    resolvidos = 0
    for l in listings:
        chave = l.grupo_chave or "?"
        if (n_versao[chave] >= params.min_grupo
                or n_modelo[_grupo_modelo(l)] >= params.min_grupo
                or chave in fipe_por_grupo):
            continue
        if usa_fipe and resolvidos < MAX_FIPE and l.marca and l.ano_modelo:
            val, _cod = fc.resolver(l.marca, l.modelo, l.ano_modelo, l.versao)
            fipe_por_grupo[chave] = val
            resolvidos += 1

    inputs = []
    for l in listings:
        chave = l.grupo_chave or "?"
        l.fipe_valor = fipe_por_grupo.get(chave)
        l.faixa_km = faixa_de_km(l.km, params.faixas_km)
        if l.preco:
            inputs.append(ScoreInput(id=l.id, grupo_versao=chave,
                                     grupo_modelo=_grupo_modelo(l),
                                     preco=l.preco, km=l.km, fipe_valor=l.fipe_valor))

    resultados = {r.id: r for r in calcular_scores(inputs, params)}
    ids = [l.id for l in listings]
    existentes = {s.listing_id: s for s in db.scalars(
        select(ListingScore).where(ListingScore.listing_id.in_(ids))).all()}
    agora = datetime.now(timezone.utc)
    for lid, r in resultados.items():
        s = existentes.get(lid) or ListingScore(listing_id=lid)
        if lid not in existentes:
            db.add(s)
        s.preco_ref, s.desconto = r.preco_ref, r.desconto
        s.origem_score, s.score, s.calculado_em = r.origem_score, r.score, agora
    db.commit()


CACHE_MIN = 30  # resultados coletados há menos que isso são servidos do cache (instantâneo)
MERCADO_DIAS = 45   # só considera anúncios vistos nos últimos N dias
MERCADO_MAX = 4000  # teto de linhas carregadas (evita OOM no free tier ao crescer o banco)


def _mercado_ativo(db: Session, criterios: dict) -> list[VehicleListing]:
    """Anúncios ativos e RECENTES p/ o critério — filtra no SQL (não carrega o banco
    inteiro na memória). Filtra por marca (comparáveis de score são da mesma marca)
    e recência; teto de segurança de memória. O `passa_filtros` refina em Python.
    """
    corte = datetime.now(timezone.utc) - timedelta(days=MERCADO_DIAS)
    q = select(VehicleListing).where(
        VehicleListing.ativo.is_(True),
        VehicleListing.ultimo_visto_em >= corte,
    )
    if criterios.get("marca"):
        q = q.where(VehicleListing.marca.ilike(f"%{criterios['marca']}%"))
    q = q.order_by(VehicleListing.ultimo_visto_em.desc()).limit(MERCADO_MAX)
    return list(db.scalars(q).all())


def buscar_ao_vivo(db: Session, criterios: dict, ordenar: str = "preco_asc",
                   forcar: bool = False) -> dict:
    """Busca multi-portal com CACHE-FIRST.

    Se já há resultados recentes (< CACHE_MIN) para o critério, devolve na hora.
    Senão (ou se `forcar`), coleta ao vivo em paralelo, persiste e scoreia.
    """
    params = get_score_params(db)
    criterios = normalizar_criterios(criterios)
    criteria = SearchCriteria.from_dict(criterios)

    def _naive(dt):
        return dt.replace(tzinfo=None) if (dt and dt.tzinfo) else dt

    # cache-first: olha o mercado já coletado (filtrado no SQL p/ não estourar memória)
    todos = _mercado_ativo(db, criterios)
    matched_listings = [l for l in todos if passa_filtros(l, criterios)]
    corte = datetime.utcnow() - timedelta(minutes=CACHE_MIN)
    frescos = [l for l in matched_listings if l.ultimo_visto_em and _naive(l.ultimo_visto_em) >= corte]
    cacheado = (not forcar) and len(frescos) >= 10

    if cacheado:
        portais_status = [{"portal": "cache", "status": "cache",
                           "qtd": len(matched_listings), "erro": None}]
    else:
        # coleta paralela (rede, sem DB nas threads) → upsert → re-filtra
        portais = db.scalars(select(Portal).where(Portal.ativo.is_(True))).all()
        coletas: dict[int, tuple] = {}
        with ThreadPoolExecutor(max_workers=min(8, max(1, len(portais)))) as ex:
            futs = {ex.submit(_fetch_portal_raws, p, criteria): p for p in portais}
            for fut in as_completed(futs):
                p = futs[fut]
                coletas[p.id] = (p, *fut.result())
        portais_status = []
        for _pid, (p, raws, status, erro, dur) in coletas.items():
            for raw in raws:
                _upsert_listing(db, p.id, to_listing_dict(raw))
            db.add(ScrapeLog(portal_id=p.id, tier_usado=int(p.min_tier), status=status,
                             qtd_resultados=len(raws), erro=erro, duracao_ms=dur))
            portais_status.append({"portal": p.slug, "status": status,
                                   "qtd": len(raws), "erro": erro})
        db.commit()
        todos = _mercado_ativo(db, criterios)
        matched_listings = [l for l in todos if passa_filtros(l, criterios)]

    _score_focado(db, matched_listings, params)

    # 4) monta retorno rankeado
    rows = db.execute(
        select(VehicleListing, ListingScore, Portal.slug)
        .join(ListingScore, ListingScore.listing_id == VehicleListing.id)
        .join(Portal, Portal.id == VehicleListing.portal_id)
        .where(VehicleListing.id.in_([l.id for l in matched_listings]))
    ).all()
    rows = list(rows)
    if ordenar == "desconto":
        # custo-benefício: maior desconto primeiro; sem-ref por preço no fim
        com = sorted([r for r in rows if r[1].score is not None],
                     key=lambda r: r[1].score, reverse=True)
        sem = sorted([r for r in rows if r[1].score is None],
                     key=lambda r: r[0].preco or 10**12)
        rows = com + sem
    elif ordenar == "preco_desc":
        rows.sort(key=lambda r: r[0].preco or 0, reverse=True)
    else:  # preco_asc (default — igual aos portais)
        rows.sort(key=lambda r: r[0].preco or 10**12)

    return {"portais": portais_status, "total": len(rows), "rows": rows}


def run_active_monitors(db: Session, progresso=None) -> dict:
    """Varredura dos monitores = o MESMO pipeline da busca ao vivo, por monitor.

    Cada monitor roda `buscar_ao_vivo` com seus critérios → coleta paralela nos 6
    portais, filtros no servidor do CarroSP (ano/km/preço/raio), marca canônica,
    cache-first (monitores com critérios parecidos reaproveitam a coleta) e score
    focado. Depois notifica os matches NOVOS acima do threshold (anti-spam em
    MonitorMatch/Notification).

    `progresso(dict)`: callback opcional p/ reportar andamento (status na UI).
    """
    avisa = progresso or (lambda _d: None)
    params = get_score_params(db)
    ativos = db.scalars(
        select(Monitor).where(Monitor.status == MonitorStatus.ATIVO.value)
    ).all()
    avisa({"monitores_total": len(ativos), "monitores_feitos": 0})

    total_resultados = 0
    notificados = 0
    for i, m in enumerate(ativos, start=1):
        avisa({"monitor_atual": m.nome or f"monitor #{m.id}"})
        try:
            resultado = buscar_ao_vivo(db, dict(m.criterios_json or {}),
                                       ordenar="desconto")
        except Exception:
            log.exception("varredura do monitor %s falhou — segue p/ o próximo", m.id)
            avisa({"monitores_feitos": i})
            continue
        total_resultados += resultado["total"]

        threshold = (m.threshold_desconto if m.threshold_desconto is not None
                     else params.threshold_desconto)
        candidatos = [(l, s) for (l, s, _slug) in resultado["rows"]
                      if s.desconto is not None and s.desconto >= threshold]
        for pos, (listing, score) in enumerate(candidatos, start=1):
            novo = notifications.registrar_match(db, m, listing, score.desconto, pos)
            if novo and "email" in (m.canais_notif or []):
                if notifications.enviar_email(db, m, listing, score, pos):
                    notificados += 1
        m.ultima_exec_em = datetime.now(timezone.utc)
        db.commit()
        avisa({"monitores_feitos": i})

    resumo = {"monitores": len(ativos), "resultados": total_resultados,
              "notificados": notificados}
    log.info("varredura concluída: %s", resumo)
    return resumo
