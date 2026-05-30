"""Conector Mobiauto (Nível 1) — via __NEXT_DATA__.

Next.js: os anúncios vêm em `props.pageProps.deals.results`, com marca/modelo/ano/
versão/câmbio/combustível estruturados em `trim` e cidade/UF em `dealer.location`.
"""
from __future__ import annotations

from app.collectors.base import (
    PortalConnector,
    RawListing,
    SearchCriteria,
    extrair_next_data,
    slug,
)

BASE = "https://www.mobiauto.com.br"
IMG = "https://image1.mobiauto.com.br/images/api/images/v1.0/{}/transform/fl_progressive"


class MobiautoConnector(PortalConnector):
    slug = "mobiauto"
    nome = "Mobiauto"
    rate_limit_s = 2.0

    def build_search_url(self, criteria: SearchCriteria) -> str:
        partes = ["comprar"]
        if criteria.marca:
            partes.append(slug(criteria.marca))
            if criteria.modelo:
                partes.append(slug(criteria.modelo))
            return f"{BASE}/{'/'.join(partes)}"
        return f"{BASE}/comprar/carros"

    def parse_listings(self, html: str) -> list[RawListing]:
        data = extrair_next_data(html)
        if not data:
            return []
        deals = (data.get("props", {}).get("pageProps", {}) or {}).get("deals", {})
        results = deals.get("results", []) if isinstance(deals, dict) else []

        out: list[RawListing] = []
        for d in results:
            preco = d.get("price")
            trim = d.get("trim") or {}
            if not preco or not trim:
                continue
            make = (trim.get("make") or {}).get("name")
            model = (trim.get("model") or {}).get("name")
            ano_modelo = (trim.get("model") or {}).get("year")
            loc = (d.get("dealer") or {}).get("location") or {}
            imgs = d.get("images") or []
            foto = IMG.format(imgs[0]["imageId"]) if imgs else None

            out.append(
                RawListing(
                    portal_slug=self.slug,
                    url=_deal_url(d, make, model, ano_modelo, loc),
                    titulo=" ".join(filter(None, [make, model, trim.get("name")])) or None,
                    marca=make,
                    modelo=model,
                    versao=trim.get("name"),
                    ano_fab=trim.get("productionYear"),
                    ano_modelo=ano_modelo,
                    preco=int(preco),
                    km=d.get("km"),
                    cambio=(trim.get("transmission") or {}).get("name"),
                    combustivel=(trim.get("fuel") or {}).get("name"),
                    cidade=loc.get("city"),
                    uf=loc.get("state"),
                    foto_url=foto,
                )
            )
        return out


def _deal_url(d: dict, make, model, ano, loc) -> str:
    """URL canônica do anúncio (o roteador do Mobiauto resolve pelo id final)."""
    partes = [
        "comprar", "carro",
        (loc.get("state") or "").lower(), slug(loc.get("city")),
        slug(make), slug(model), slug(d.get("trim", {}).get("name")),
        str(ano or ""), str(d.get("id") or ""),
    ]
    return f"{BASE}/" + "/".join(p for p in partes if p)
