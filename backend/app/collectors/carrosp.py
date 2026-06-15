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
MAX_PAGINAS = 8  # teto p/ velocidade (≈170 anúncios); páginas buscadas em paralelo


class CarroSPConnector(PortalConnector):
    slug = "carrosp"
    nome = "CarroSP"
    rate_limit_s = 2.0

    def build_search_url(self, criteria: SearchCriteria) -> str:
        # GEOGRAFIA: o CarroSP filtra por CIDADE no caminho (/carros/{cidade}-{uf}/…)
        # e NÃO tem filtro por estado. Sem cidade específica usamos a URL "todas as
        # cidades" (/carros/{marca}/{modelo}/) — antes forçávamos a capital
        # (sao-paulo-sp) e perdíamos o interior (Commander caía de 125 → 21).
        loc = (f"{_slug(criteria.cidade)}-{criteria.uf.lower()}/"
               if criteria.cidade and criteria.uf else "")
        if criteria.marca and criteria.modelo:
            base = f"{BASE}/carros/{loc}{_slug(criteria.marca)}/{_slug(criteria.modelo)}/"
        elif criteria.marca:  # só marca → traz a marca toda (não /todos/)
            base = f"{BASE}/carros/{loc}{_slug(criteria.marca)}/"
        else:
            base = f"{BASE}/carros/{loc}todos/"

        # FILTROS NO SERVIDOR do CarroSP — sem isso, ano/preço/km específicos podem
        # não aparecer nas 1ªs páginas (a ordem é por relevância, não por ano) e a
        # busca "Gol 2018" voltava vazia mesmo havendo anúncios.
        params: list[tuple[str, int]] = []
        if criteria.raio_km and criteria.cidade:
            params.append(("distancia", int(criteria.raio_km)))   # raio km
        if criteria.ano_min:
            params.append(("ano1", int(criteria.ano_min)))
        if criteria.ano_max:
            params.append(("ano2", int(criteria.ano_max)))
        if criteria.km_min:
            params.append(("kmIni", int(criteria.km_min)))
        if criteria.km_max:
            params.append(("kmFim", int(criteria.km_max)))
        if criteria.preco_min:
            params.append(("precoIni", int(criteria.preco_min)))
        if criteria.preco_max:
            params.append(("precoFim", int(criteria.preco_max)))
        if criteria.condicao == "0km":
            params.append(("zero", 1))
        elif criteria.condicao == "usado":
            params.append(("usado", 1))
        if params:
            base += "?" + "&".join(f"{k}={v}" for k, v in params)
        return base

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
                    cidade=_cidade_do_card(card),
                    # CarroSP é um portal de São Paulo: o inventário é de SP (cidades
                    # do interior). O card traz só a cidade, sem UF → assumimos SP,
                    # o que mantém o filtro por estado correto p/ buscas em SP.
                    uf="SP",
                    foto_url=foto,
                )
            )
        return out


def _cidade_do_card(card) -> str | None:
    """Cidade exibida no card (ao lado do pin). Ex.: 'Campinas'."""
    el = card.select_one(".text-dark.ml-1") or card.select_one(".text-color-2.card-info")
    if not el:
        return None
    cidade = el.get_text(" ", strip=True)
    return cidade or None


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
    # ano = o ÚLTIMO segmento que é um ano plausível (evita ler o ID como ano,
    # que acontece quando a versão tem barras a mais ou falta um segmento).
    ano = None
    for s in seg:
        if re.fullmatch(r"(19|20)\d{2}", s):
            ano = int(s)
    return (
        marca.title() if marca else None,
        modelo.title() if modelo else None,
        versao,
        ano,
    )
