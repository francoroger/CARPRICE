"""Motor de acesso em camadas + interface de conectores (§2 do PROJETO_v3).

Separação de responsabilidades:
  - O CONECTOR só sabe construir a URL de busca e PARSEAR HTML → RawListing.
  - O FETCHER encapsula o nível de acesso (httpx, sessão, browser, proxy...).
Trocar de nível NÃO altera o conector. Adicionar um portal novo não toca no núcleo.
"""
from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from app.config import settings
from app.models import AccessTier

log = logging.getLogger(__name__)


@dataclass
class SearchCriteria:
    """Filtros de uma busca (modelados nos filtros do CarroSP).

    `marca`/`modelo`/`uf`/`cidade` orientam a COLETA (montam a URL dos portais);
    os demais campos são PÓS-FILTROS aplicados sobre os anúncios coletados.
    """

    # coleta
    marca: str | None = None
    modelo: str | None = None
    versao: str | None = None
    uf: str | None = None
    cidade: str | None = None
    raio_km: int | None = None     # distância a partir da cidade (onde o portal suporta)
    # pós-filtros
    ano_min: int | None = None
    ano_max: int | None = None
    preco_min: int | None = None
    preco_max: int | None = None
    km_min: int | None = None
    km_max: int | None = None
    cambio: str | None = None        # ex.: "automatico", "manual", "cvt"
    combustivel: str | None = None   # ex.: "flex", "gasolina", "diesel"
    cor: str | None = None
    condicao: str | None = None      # "0km" | "usado" | None (ambos)
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "SearchCriteria":
        campos = {f.name for f in cls.__dataclass_fields__.values()}
        base = {k: v for k, v in d.items() if k in campos}
        base["extra"] = {k: v for k, v in d.items() if k not in campos}
        return cls(**base)


@dataclass
class RawListing:
    """Anúncio cru, antes da normalização."""

    portal_slug: str
    url: str
    titulo: str | None = None
    marca: str | None = None
    modelo: str | None = None
    versao: str | None = None
    ano_fab: int | None = None
    ano_modelo: int | None = None
    preco: int | None = None
    km: int | None = None
    cambio: str | None = None
    combustivel: str | None = None
    cidade: str | None = None
    uf: str | None = None
    foto_url: str | None = None


# --------------------------------------------------------------------------- #
# Fetchers — um por nível de acesso. O conector recebe um Fetcher injetado.
# --------------------------------------------------------------------------- #


class FetchError(Exception):
    """Falha de busca (bloqueio, timeout, etc.) — sinaliza para auto-escalada."""


class Fetcher(ABC):
    tier: AccessTier

    @abstractmethod
    def get(self, url: str) -> str:
        """Retorna o HTML/corpo da URL ou levanta FetchError."""


class HttpFetcher(Fetcher):
    """Nível 1: httpx com headers de navegador. Cobre os portais SSR."""

    tier = AccessTier.HTTP

    def __init__(self) -> None:
        self._headers = {
            "User-Agent": settings.http_user_agent,
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def get(self, url: str) -> str:
        try:
            with httpx.Client(
                headers=self._headers,
                timeout=settings.http_timeout_s,
                follow_redirects=True,
                http2=True,
            ) as c:
                r = c.get(url)
            if r.status_code in (403, 401, 429) or len(r.text) < 500:
                raise FetchError(f"bloqueio/resposta vazia: HTTP {r.status_code}")
            return r.text
        except httpx.HTTPError as e:
            raise FetchError(str(e)) from e


def fetcher_para_tier(tier: AccessTier) -> Fetcher:
    """Fábrica de fetcher. Níveis 2-5 entram nas fases seguintes."""
    if tier == AccessTier.HTTP:
        return HttpFetcher()
    # Fase 2/3: SESSION, BROWSER, PROXY, UNBLOCKER
    raise NotImplementedError(f"Fetcher do nível {tier!r} ainda não implementado")


# --------------------------------------------------------------------------- #
# Conector
# --------------------------------------------------------------------------- #


class PortalConnector(ABC):
    slug: str
    nome: str
    min_tier: AccessTier = AccessTier.HTTP
    rate_limit_s: float = 2.0

    @abstractmethod
    def build_search_url(self, criteria: SearchCriteria) -> str:
        """Monta a URL de busca a partir dos filtros."""

    @abstractmethod
    def parse_listings(self, html: str) -> list[RawListing]:
        """Extrai os anúncios do HTML. PURO — testável com fixture offline."""

    def search(self, criteria: SearchCriteria, fetch: Fetcher) -> list[RawListing]:
        url = self.build_search_url(criteria)
        html = fetch.get(url)
        return self.parse_listings(html)


# --------------------------------------------------------------------------- #
# Utilidades de parsing compartilhadas
# --------------------------------------------------------------------------- #


def so_digitos(s: str | None) -> int | None:
    if not s:
        return None
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else None


def extrai_preco(texto: str) -> int | None:
    """Último valor em R$ do texto (preço final, após o 'de/por')."""
    precos = []
    for m in re.finditer(r"R\$\s*([\d\.]+)(?:,\d{2})?", texto):
        v = so_digitos(m.group(1))
        if v and v > 1000:
            precos.append(v)
    return precos[-1] if precos else None


def extrai_km(texto: str) -> int | None:
    """km aceitando '28.000 km' e 'KM 28.000'; escolhe o maior número plausível."""
    cands = []
    for m in re.finditer(r"([\d\.]+)\s*km\b", texto, re.I):
        cands.append(so_digitos(m.group(1)))
    for m in re.finditer(r"\bkm\s*:?\s*([\d\.]+)", texto, re.I):
        cands.append(so_digitos(m.group(1)))
    cands = [k for k in cands if k is not None]
    return max(cands) if cands else None


def extrair_next_data(html: str) -> dict | None:
    """Extrai o JSON do <script id="__NEXT_DATA__"> (sites Next.js).

    Em portais Next.js os anúncios já vêm estruturados nesse JSON do SSR — é a
    forma mais limpa e estável de coletar (sem raspar DOM nem chamar API à parte).
    """
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except (ValueError, TypeError):
        return None


def marca_canonica(marca: str | None) -> str | None:
    """Nome de marca usável nos portais a partir do rótulo da FIPE.

    A FIPE rotula 'VW - VolksWagen', 'GM - Chevrolet', 'Citroën' etc. Os portais
    usam só 'Volkswagen', 'Chevrolet'. Pega a parte após ' - ' quando existe.
    """
    if not marca:
        return marca
    if " - " in marca:
        marca = marca.split(" - ", 1)[1]
    return marca.strip()


def slug(s: str | None) -> str:
    """Slug para URL: remove acentos e troca não-alfanumérico por hífen.

    'São Paulo' → 'sao-paulo' | 'HR-V' → 'hr-v'.
    """
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = s.strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def extrai_ano(texto: str) -> int | None:
    m = re.search(
        r"\b(20[0-2]\d|19\d{2})\s*/\s*(20[0-2]\d)\b|\b(20[0-2]\d|19\d{2})\b", texto
    )
    if not m:
        return None
    val = m.group(2) or m.group(0)
    return so_digitos(val[:4])
