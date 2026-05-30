"""Orquestração da varredura (§6 do PROJETO_v3).

Fluxo por execução:
  1. Para cada monitor ativo, roda cada portal ativo (com auto-escalada de tier)
     e faz upsert dos anúncios no MERCADO GLOBAL (dedup por hash).
  2. Recalcula o score sobre TODO o mercado (FIPE como fallback em grupos pequenos).
  3. Para cada monitor, casa os anúncios e notifica os novos acima do threshold.
Degradação graciosa: um portal que falha é logado e pulado, sem derrubar o resto.
"""
from __future__ import annotations

import logging
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import (
    FetchError,
    SearchCriteria,
    fetcher_para_tier,
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
from app.services.fipe import FipeClient, valor_fipe
from app.services.filters import passa_filtros
from app.services.scoring import ScoreInput, ScoreParams, calcular_scores, faixa_de_km
from app.services.settings_service import get_score_params

log = logging.getLogger(__name__)
MAX_TIER_AUTO = AccessTier.HTTP  # MVP só escala até o nível 1 (httpx)


# --------------------------------------------------------------------------- #
# 1) Coleta + upsert no mercado global
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
        existente.ultimo_visto_em = agora
        existente.ativo = True
        return False
    db.add(VehicleListing(portal_id=portal_id, primeiro_visto_em=agora,
                          ultimo_visto_em=agora, **dados))
    db.flush()  # grava já p/ o próximo SELECT detectar duplicata (autoflush=False)
    return True


def collect_for_monitor(db: Session, monitor: Monitor) -> int:
    """Roda todos os portais ativos para os critérios do monitor. Retorna nº coletado."""
    criteria = SearchCriteria.from_dict(monitor.criterios_json or {})
    portais = db.scalars(select(Portal).where(Portal.ativo.is_(True))).all()
    total = 0

    for portal in portais:
        conn = get_connector(portal.slug)
        if not conn:
            continue
        t0 = time.monotonic()
        tier = AccessTier(portal.min_tier)
        status, qtd, erro = "ok", 0, None
        try:
            if tier > MAX_TIER_AUTO:
                raise FetchError(f"requer nível {tier} (não habilitado no MVP)")
            fetch = fetcher_para_tier(tier)
            raws = conn.search(criteria, fetch)
            for raw in raws:
                if _upsert_listing(db, portal.id, to_listing_dict(raw)):
                    total += 1
                qtd += 1
            db.commit()
        except (FetchError, NotImplementedError) as e:
            status, erro = "falha", str(e)
            db.rollback()
            log.warning("portal %s falhou: %s", portal.slug, e)
        except Exception as e:  # parsing inesperado — não derruba a varredura
            status, erro = "erro", f"{type(e).__name__}: {e}"
            db.rollback()
            log.exception("erro no portal %s", portal.slug)

        db.add(ScrapeLog(
            portal_id=portal.id, monitor_id=monitor.id, tier_usado=int(tier),
            status=status, qtd_resultados=qtd, erro=erro,
            duracao_ms=int((time.monotonic() - t0) * 1000),
        ))
        db.commit()
    return total


# --------------------------------------------------------------------------- #
# 2) Recálculo do score sobre o mercado global
# --------------------------------------------------------------------------- #


def recompute_scores(db: Session, params: ScoreParams, usar_fipe: bool = True) -> None:
    listings = db.scalars(
        select(VehicleListing).where(VehicleListing.ativo.is_(True))
    ).all()
    if not listings:
        return

    # FIPE só para grupos pequenos sem valor ainda (evita martelar a API).
    # Em busca ao vivo passamos usar_fipe=False (grupo focado já tem volume p/ MERCADO).
    por_grupo = Counter(l.grupo_chave for l in listings)
    fc = FipeClient() if usar_fipe else None
    try:
        for l in listings:
            if (usar_fipe and l.fipe_valor is None
                    and por_grupo[l.grupo_chave] < params.min_grupo):
                l.fipe_valor = valor_fipe(
                    db, l.marca, l.modelo, l.ano_modelo, l.versao, client=fc
                )
            l.faixa_km = faixa_de_km(l.km, params.faixas_km)
    finally:
        if fc:
            fc.close()

    inputs = [
        ScoreInput(id=l.id, grupo_chave=l.grupo_chave or "?", preco=l.preco,
                   km=l.km, fipe_valor=l.fipe_valor)
        for l in listings if l.preco
    ]
    resultados = {r.id: r for r in calcular_scores(inputs, params)}

    # mantém no máximo 1 ListingScore por anúncio (atualiza ou cria)
    existentes = {
        s.listing_id: s
        for s in db.scalars(select(ListingScore)).all()
    }
    agora = datetime.now(timezone.utc)
    for lid, r in resultados.items():
        s = existentes.get(lid)
        if s is None:
            s = ListingScore(listing_id=lid)
            db.add(s)
        s.preco_ref = r.preco_ref
        s.desconto = r.desconto
        s.origem_score = r.origem_score
        s.score = r.score
        s.calculado_em = agora
    db.commit()


# --------------------------------------------------------------------------- #
# 3) Match por monitor + notificação
# --------------------------------------------------------------------------- #


def match_and_notify(db: Session, monitor: Monitor, params: ScoreParams) -> int:
    """Casa anúncios com o monitor, ordena por score, notifica os novos. Retorna nº notificado."""
    crit = monitor.criterios_json or {}
    threshold = monitor.threshold_desconto or params.threshold_desconto

    # join listing + score
    rows = db.execute(
        select(VehicleListing, ListingScore)
        .join(ListingScore, ListingScore.listing_id == VehicleListing.id)
        .where(VehicleListing.ativo.is_(True))
    ).all()

    candidatos = [
        (l, s) for (l, s) in rows
        if s.desconto is not None and s.desconto >= threshold and passa_filtros(l, crit)
    ]
    candidatos.sort(key=lambda ls: ls[1].score or 0, reverse=True)

    notificados = 0
    for pos, (listing, score) in enumerate(candidatos, start=1):
        novo = notifications.registrar_match(db, monitor, listing, score.desconto, pos)
        if novo and "email" in (monitor.canais_notif or []):
            if notifications.enviar_email(db, monitor, listing, score, pos):
                notificados += 1
    db.commit()
    return notificados


# --------------------------------------------------------------------------- #
# Orquestrador
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# Busca AO VIVO (on-demand) — entra em todos os portais em paralelo
# --------------------------------------------------------------------------- #


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


def _score_focado(db: Session, listings: list[VehicleListing], params: ScoreParams) -> None:
    """Scoreia APENAS o conjunto da busca, reprocessando a FIPE FRESCA.

    Não reusa fipe_valor antigo do anúncio (que pode estar errado de varreduras
    passadas). Grupos com volume usam MERCADO; singletons resolvem FIPE na hora,
    de forma conservadora (resolver devolve None se versão/ano não casam).
    """
    if not listings:
        return
    # agrupa por grupo_chave (carros idênticos)
    grupos: dict[str, list] = {}
    for l in listings:
        grupos.setdefault(l.grupo_chave or "?", []).append(l)

    # FIPE só p/ grupos pequenos, UMA vez por grupo e com teto (evita lentidão/403)
    MAX_FIPE = 12
    fipe_por_grupo: dict[str, int | None] = {}
    fc = FipeClient()
    try:
        resolvidos = 0
        for chave, grp in grupos.items():
            if len(grp) >= params.min_grupo:
                continue  # tem volume → MERCADO, sem FIPE
            rep = grp[0]
            if resolvidos < MAX_FIPE and rep.marca and rep.ano_modelo:
                val, _cod = fc.resolver(rep.marca, rep.modelo, rep.ano_modelo, rep.versao)
                fipe_por_grupo[chave] = val
                resolvidos += 1
    finally:
        fc.close()

    inputs = []
    for l in listings:
        usa_mercado = len(grupos[l.grupo_chave or "?"]) >= params.min_grupo
        l.fipe_valor = None if usa_mercado else fipe_por_grupo.get(l.grupo_chave or "?")
        l.faixa_km = faixa_de_km(l.km, params.faixas_km)
        if l.preco:
            inputs.append(ScoreInput(id=l.id, grupo_chave=l.grupo_chave or "?",
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


def buscar_ao_vivo(db: Session, criterios: dict, ordenar: str = "preco_asc") -> dict:
    """Entra em TODOS os portais ativos ao vivo, traz tudo, e filtra pelo critério.

    Coleta em paralelo (rede), persiste no mercado, scoreia o conjunto filtrado com
    FIPE FRESCA (conservadora) e retorna os anúncios na ordem pedida (default: preço
    menor→maior, igual aos portais).
    """
    params = get_score_params(db)
    criteria = SearchCriteria.from_dict(criterios)
    portais = db.scalars(select(Portal).where(Portal.ativo.is_(True))).all()

    # 1) coleta paralela (somente rede, sem tocar no DB nas threads)
    coletas: dict[int, tuple] = {}
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(portais)))) as ex:
        futs = {ex.submit(_fetch_portal_raws, p, criteria): p for p in portais}
        for fut in as_completed(futs):
            p = futs[fut]
            coletas[p.id] = (p, *fut.result())

    # 2) upsert no mercado + logs
    portais_status = []
    for _pid, (p, raws, status, erro, dur) in coletas.items():
        for raw in raws:
            _upsert_listing(db, p.id, to_listing_dict(raw))
        db.add(ScrapeLog(portal_id=p.id, tier_usado=int(p.min_tier), status=status,
                         qtd_resultados=len(raws), erro=erro, duracao_ms=dur))
        portais_status.append({"portal": p.slug, "status": status,
                               "qtd": len(raws), "erro": erro})
    db.commit()

    # 3) filtra o mercado pelos critérios e scoreia SÓ o resultado (FIPE fresca)
    todos = db.scalars(select(VehicleListing).where(VehicleListing.ativo.is_(True))).all()
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


def run_active_monitors(db: Session) -> dict:
    params = get_score_params(db)
    ativos = db.scalars(
        select(Monitor).where(Monitor.status == MonitorStatus.ATIVO.value)
    ).all()

    coletados = 0
    for m in ativos:
        coletados += collect_for_monitor(db, m)

    recompute_scores(db, params)

    notificados = 0
    for m in ativos:
        notificados += match_and_notify(db, m, params)
        m.ultima_exec_em = datetime.now(timezone.utc)
    db.commit()

    resumo = {"monitores": len(ativos), "novos_anuncios": coletados,
              "notificados": notificados}
    log.info("varredura concluída: %s", resumo)
    return resumo
