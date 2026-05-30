"""Conector CarroSP (Nível 1). Cards `div.veiculo-item`.

A URL do anúncio já vem estruturada:
  /comprar/{categoria}/{marca}/{modelo}/{versao}/{ano}/{id}/
— extraímos marca, modelo, versão e ano dela, sem depender do título.
"""
from __future__ import annotations

import math
import re
from concurrent.futures import ThreadPoolExecutor

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
    slug as _slug,
    so_digitos,
)

BASE = "https://www.carrosp.com.br"
ITENS_POR_PAGINA = 21
MAX_PAGINAS = 20  # teto p/ limitar tempo (≈420 anúncios por portal/busca)


def _local(criteria: SearchCriteria) -> str:
    if criteria.cidade and criteria.uf:
        return f"{_slug(criteria.cidade)}-{criteria.uf.lower()}"
    if criteria.uf:
        return f"sao-paulo-{criteria.uf.lower()}"  # fallback razoável
    return "sao-paulo-sp"


class CarroSPConnector(PortalConnector):
    slug = "carrosp"
    nome = "CarroSP"
    rate_limit_s = 2.0

    def build_search_url(self, criteria: SearchCriteria) -> str:
        loc = _local(criteria)
        if criteria.marca and criteria.modelo:
            return f"{BASE}/carros/{loc}/{_slug(criteria.marca)}/{_slug(criteria.modelo)}/"
        if criteria.marca:  # só marca → traz a marca toda (não /todos/)
            return f"{BASE}/carros/{loc}/{_slug(criteria.marca)}/"
        return f"{BASE}/carros/{loc}/todos/"

    def search(self, criteria: SearchCriteria, fetch: Fetcher) -> list[RawListing]:
        """Pagina via ?page=N: lê o total na 1ª página e busca o resto em paralelo."""
        url = self.build_search_url(criteria)
        html1 = fetch.get(url)
        out = self.parse_listings(html1)

        total = _total_anuncios(html1)
        n_pags = min(MAX_PAGINAS, math.ceil(total / ITENS_POR_PAGINA)) if total else 1
        if n_pags <= 1:
            return out

        sep = "&" if "?" in url else "?"

        def pega(p: int) -> list[RawListing]:
            try:
                return self.parse_listings(fetch.get(f"{url}{sep}page={p}"))
            except FetchError:
                return []

        with ThreadPoolExecutor(max_workers=6) as ex:
            for extra in ex.map(pega, range(2, n_pags + 1)):
                out.extend(extra)
        return out

    def parse_listings(self, html: str) -> list[RawListing]:
        soup = BeautifulSoup(html, "lxml")
        out: list[RawListing] = []
        for card in soup.select("div.veiculo-item"):
            texto = card.get_text(" ", strip=True)
            preco = extrai_preco(texto)
            if not preco:
                continue
            a = card.find("a", href=True)
            href = a["href"] if a else None
            url = href if (href or "").startswith("http") else (BASE + href if href else BASE)

            marca = modelo = versao = None
            ano_modelo = None
            if href:
                marca, modelo, versao, ano_modelo = _campos_da_url(href)

            img = card.find("img")
            foto = (img.get("src") or img.get("data-src")) if img else None

            out.append(
                RawListing(
                    portal_slug=self.slug,
                    url=url,
                    titulo=" ".join(filter(None, [marca, modelo, versao])) or None,
                    marca=marca,
                    modelo=modelo,
                    versao=versao,
                    ano_modelo=ano_modelo or extrai_ano(texto),
                    preco=preco,
                    km=extrai_km(texto),
                    foto_url=foto,
                )
            )
        return out


def _total_anuncios(html: str) -> int | None:
    """Lê 'N veículos encontrados' para saber quantas páginas paginar."""
    m = re.search(r'([\d\.]+)\s*ve[ií]culos?\s+encontrados', html, re.I)
    return so_digitos(m.group(1)) if m else None


def _campos_da_url(href: str) -> tuple[str | None, str | None, str | None, int | None]:
    """/comprar/{cat}/{marca}/{modelo}/{versao}/{ano}/{id}/ → marca, modelo, versao, ano."""
    partes = [p for p in href.split("?")[0].split("/") if p]
    try:
        i = partes.index("comprar")
    except ValueError:
        return None, None, None, None
    seg = partes[i + 1 :]
    # seg = [categoria, marca, modelo, versao, ano, id]
    def get(idx):
        return seg[idx].replace("-", " ") if len(seg) > idx else None

    marca = get(1)
    modelo = get(2)
    versao = get(3)
    ano = so_digitos(seg[4]) if len(seg) > 4 and seg[4].isdigit() else None
    return (
        marca.title() if marca else None,
        modelo.title() if modelo else None,
        versao,
        ano,
    )
