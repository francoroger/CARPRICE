"""Conector iCarros (Nível 1). Cards `.offer-card`.

URL de listagem real: /ache/listaanuncios.jsp (carros.jsp redireciona p/ home).
O link do anúncio traz cidade-uf e marca: /comprar/{cidade}-{uf}/{marca}/...
"""
from __future__ import annotations

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

BASE = "https://www.icarros.com.br"


class ICarrosConnector(PortalConnector):
    slug = "icarros"
    nome = "iCarros"
    rate_limit_s = 2.0

    def build_search_url(self, criteria: SearchCriteria) -> str:
        if criteria.uf:
            cidade = slug(criteria.cidade or "sao-paulo")
            return f"{BASE}/comprar/usados/carros/{criteria.uf.lower()}-{cidade}"
        return f"{BASE}/ache/listaanuncios.jsp"

    def parse_listings(self, html: str) -> list[RawListing]:
        soup = BeautifulSoup(html, "lxml")
        out: list[RawListing] = []
        seen: set[str] = set()
        for card in soup.select(".offer-card"):
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

            titulo_el = card.select_one("[class*='title'], h2, h3")
            titulo = titulo_el.get_text(" ", strip=True) if titulo_el else None

            marca, cidade, uf = _da_url(href)
            img = card.find("img")
            out.append(
                RawListing(
                    portal_slug=self.slug,
                    url=url,
                    titulo=titulo,
                    marca=marca,
                    versao=titulo,
                    ano_modelo=extrai_ano(texto),
                    preco=preco,
                    km=extrai_km(texto),
                    cidade=cidade,
                    uf=uf,
                    foto_url=(img.get("src") or img.get("data-src")) if img else None,
                )
            )
        return out


def _da_url(href: str | None):
    if not href:
        return None, None, None
    partes = [p for p in href.split("?")[0].split("/") if p]
    try:
        i = partes.index("comprar")
        loc = partes[i + 1]  # cidade-uf
        marca = partes[i + 2] if len(partes) > i + 2 else None
        *cidade, uf = loc.rsplit("-", 1)
        return (
            marca.replace("-", " ").title() if marca else None,
            "-".join(cidade).replace("-", " ").title() if cidade else None,
            uf.upper() if len(uf) == 2 else None,
        )
    except (ValueError, IndexError):
        return None, None, None
