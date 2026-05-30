"""Conector Comprecar (Nível 1). Cards `.card.vehicle`.

km vem escrito "KM 28.000" (antes do número) — tratado pelo extrai_km compartilhado.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.collectors.base import (
    PortalConnector,
    RawListing,
    SearchCriteria,
    extrai_ano,
    extrai_km,
    extrai_preco,
    slug,
)

BASE = "https://www.comprecar.com.br"


class ComprecarConnector(PortalConnector):
    slug = "comprecar"
    nome = "Comprecar"
    rate_limit_s = 2.0

    def build_search_url(self, criteria: SearchCriteria) -> str:
        cidade = slug(criteria.cidade or "sao-paulo")
        return f"{BASE}/carros-usados/{cidade}"

    def parse_listings(self, html: str) -> list[RawListing]:
        soup = BeautifulSoup(html, "lxml")
        out: list[RawListing] = []
        seen: set[str] = set()
        for card in soup.select(".card.vehicle"):
            texto = card.get_text(" ", strip=True)
            preco = extrai_preco(texto)
            if not preco:
                continue
            a = card.find("a", href=True)
            href = a["href"] if a else None
            url = href if (href or "").startswith("http") else (BASE + (href or ""))
            if url in seen:
                continue
            seen.add(url)

            titulo_el = card.select_one(".card-title, h2, h3, [class*='title']")
            titulo = titulo_el.get_text(" ", strip=True) if titulo_el else None
            if not titulo:
                # deriva do texto cru: remove nav e pega o trecho antes do ano
                limpo = re.sub(r"^(?:Pr[oó]xima|Anterior|\s)+", "", texto)
                m = re.match(r"(.+?)\s+(?:20[0-2]\d|19\d{2})\b", limpo)
                titulo = (m.group(1) if m else limpo.split("R$")[0]).strip() or None
            img = card.find("img")
            out.append(
                RawListing(
                    portal_slug=self.slug,
                    url=url,
                    titulo=titulo,
                    versao=titulo,
                    ano_modelo=extrai_ano(texto),
                    preco=preco,
                    km=extrai_km(texto),
                    foto_url=(img.get("src") or img.get("data-src")) if img else None,
                )
            )
        return out
