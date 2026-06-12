"""Conector iCarros (Nível 1). Cards `.offer-card`.

Busca filtrada NACIONAL: /comprar/usados/{marca}[/{modelo}] (SSR, paginada via
?pag=N) — o pós-filtro de UF corta os de fora, pois o link do anúncio traz
cidade-uf: /comprar/{cidade}-{uf}/{marca}/...
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from app.collectors.base import (
    FetchError,
    Fetcher,
    PortalConnector,
    RawListing,
    SearchCriteria,
    extrai_ano,
    extrai_km,
    extrai_preco,
    slug,
)

BASE = "https://www.icarros.com.br"
MAX_PAGINAS = 5  # 20 cards/página


class ICarrosConnector(PortalConnector):
    slug = "icarros"
    nome = "iCarros"
    rate_limit_s = 2.0

    def build_search_url(self, criteria: SearchCriteria) -> str:
        # /comprar/usados/{marca}[/{modelo}] filtra no servidor (sem UF na URL —
        # resultados nacionais; a UF é cortada no pós-filtro via link do card).
        if criteria.marca:
            url = f"{BASE}/comprar/usados/{slug(criteria.marca)}"
            if criteria.modelo:
                url += f"/{slug(criteria.modelo)}"
            return url
        if criteria.uf:
            cidade = slug(criteria.cidade or "sao-paulo")
            return f"{BASE}/comprar/usados/carros/{criteria.uf.lower()}-{cidade}"
        return f"{BASE}/ache/listaanuncios.jsp"

    def search(self, criteria: SearchCriteria, fetch: Fetcher) -> list[RawListing]:
        """Pagina via ?pag=N até repetir/zerar (20 cards/página)."""
        url = self.build_search_url(criteria)
        out: list[RawListing] = []
        vistos: set[str] = set()
        for pag in range(1, MAX_PAGINAS + 1):
            page_url = url if pag == 1 else f"{url}?pag={pag}"
            try:
                listings = self.parse_listings(fetch.get(page_url))
            except FetchError:
                break
            novos = [l for l in listings if l.url not in vistos]
            if not novos:
                break
            vistos.update(l.url for l in novos)
            out.extend(novos)
        return out

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
