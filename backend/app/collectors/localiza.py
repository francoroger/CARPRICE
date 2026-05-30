"""Conector Localiza Seminovos (Nível 1) — via __NEXT_DATA__.

O site é Next.js e embute os anúncios estruturados em
`props.pageProps.products` no HTML SSR. Isso entrega ~23 anúncios COMPLETOS
(marca/modelo/versão/km/ano/preço em campos próprios) — muito melhor que raspar
o DOM (que só pegava ~5 e com texto ruidoso).
"""
from __future__ import annotations

from app.collectors.base import (
    PortalConnector,
    RawListing,
    SearchCriteria,
    extrair_next_data,
    slug,
)

BASE = "https://seminovos.localiza.com"


def _title(s) -> str | None:
    return str(s).title() if s else None


class LocalizaConnector(PortalConnector):
    slug = "localiza"
    nome = "Localiza Seminovos"
    rate_limit_s = 2.5

    def build_search_url(self, criteria: SearchCriteria) -> str:
        if criteria.uf:
            cidade = slug(criteria.cidade or "sao-paulo")
            return f"{BASE}/carros/{criteria.uf.lower()}-{cidade}"
        return f"{BASE}/carros"

    def parse_listings(self, html: str) -> list[RawListing]:
        data = extrair_next_data(html)
        if not data:
            return []
        produtos = (data.get("props", {}).get("pageProps", {}) or {}).get("products", [])
        out: list[RawListing] = []
        for p in produtos:
            preco = p.get("preco")
            if not preco:
                continue
            url = p.get("pdpUrl") or BASE
            out.append(
                RawListing(
                    portal_slug=self.slug,
                    url=url,
                    titulo=" ".join(filter(None, [
                        _title(p.get("marcaDescricao")),
                        _title(p.get("modeloFamiliaDescricao")),
                        p.get("modeloDescricaoReduzida"),
                    ])) or None,
                    marca=_title(p.get("marcaDescricao")),
                    modelo=_title(p.get("modeloFamiliaDescricao")),
                    versao=p.get("modeloDescricaoReduzida") or p.get("modeloDescricao"),
                    ano_fab=p.get("anoFabricacao"),
                    ano_modelo=p.get("anoModelo"),
                    preco=int(preco),
                    km=p.get("odometro"),
                    cambio=_title(p.get("tipoTransmissaoDescricao")),
                    combustivel=_title(p.get("tipoCombustivelDescricao")),
                    cidade=_title(p.get("cidadeDescricao")),
                    uf=p.get("siglaEstado"),
                    foto_url=p.get("fotoUrl"),
                )
            )
        return out
