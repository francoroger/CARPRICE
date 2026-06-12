"""Conector Napista (Nível 1).

Os cards `.styles_listingCard__*` NÃO têm <a> interno — o link `/anuncios/{uuid}`
está no elemento que envolve o card. Selecionamos direto pelos <a> do anúncio.
Texto do card: "<Marca Modelo Versão> R$ <preço> <ano> <km> km <Cidade, UF>".
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.collectors.base import (
    Fetcher,
    FetchError,
    PortalConnector,
    RawListing,
    SearchCriteria,
    extrai_ano,
    extrai_km,
    extrai_preco,
    slug,
)

BASE = "https://napista.com.br"
MAX_PAGINAS = 5  # ?pn=N (5×48 ≈ 240 anúncios; busca sequencial com early-stop)


class NapistaConnector(PortalConnector):
    slug = "napista"
    nome = "Napista"
    rate_limit_s = 2.0

    def build_search_url(self, criteria: SearchCriteria) -> str:
        # filtro de modelo é por CAMINHO: /busca/{marca}/{modelo}
        if criteria.marca and criteria.modelo:
            return f"{BASE}/busca/{slug(criteria.marca)}/{slug(criteria.modelo)}"
        if criteria.marca:
            return f"{BASE}/busca/{slug(criteria.marca)}"
        return f"{BASE}/busca/carro"

    def search(self, criteria: SearchCriteria, fetch: Fetcher) -> list[RawListing]:
        """Pagina via ?pn=N até não surgir anúncio novo (sem total na página)."""
        url = self.build_search_url(criteria)
        out: list[RawListing] = []
        vistos: set[str] = set()
        for pn in range(1, MAX_PAGINAS + 1):
            page_url = url if pn == 1 else f"{url}?pn={pn}"
            try:
                listings = self.parse_listings(fetch.get(page_url))
            except FetchError:
                break
            novos = [l for l in listings if l.url not in vistos]
            if not novos:
                break  # página repetida/vazia → fim
            for l in novos:
                vistos.add(l.url)
            out.extend(novos)
        return out

    def parse_listings(self, html: str) -> list[RawListing]:
        soup = BeautifulSoup(html, "lxml")
        # Lazy-load: só os ~8 primeiros cards têm <img src> no SSR. Mas o JSON-LD
        # da página traz a foto de TODOS: "@id":".../anuncios/{uuid}","image":"..."
        fotos_ld = dict(re.findall(
            r'"@id":"https://napista\.com\.br(/anuncios/[0-9a-f-]+)","image":"([^"]+)"',
            html,
        ))
        out: list[RawListing] = []
        seen: set[str] = set()
        for a in soup.select("a[href*='/anuncios/']"):
            texto = a.get_text(" ", strip=True)
            preco = extrai_preco(texto)
            if not preco:
                continue
            href = a["href"]
            url = href if href.startswith("http") else BASE + href
            if url in seen:
                continue
            seen.add(url)

            cidade, uf = _cidade_uf(texto)
            # título = trecho antes do R$
            titulo = texto.split("R$")[0].strip() or None
            img = a.find("img")
            foto = (img.get("src") or img.get("data-src")) if img else None
            if not foto:
                foto = fotos_ld.get(href if href.startswith("/") else href.removeprefix(BASE))
            out.append(
                RawListing(
                    portal_slug=self.slug,
                    url=url,
                    titulo=titulo,
                    versao=titulo,
                    ano_modelo=extrai_ano(texto),
                    preco=preco,
                    km=extrai_km(texto),
                    cidade=cidade,
                    uf=uf,
                    foto_url=foto,
                )
            )
        return out


def _cidade_uf(texto: str):
    m = re.search(r"([A-Za-zÀ-ú\s]+),\s*([A-Z]{2})\b", texto)
    if m:
        return m.group(1).strip(), m.group(2)
    return None, None
