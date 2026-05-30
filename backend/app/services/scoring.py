"""Engine de Score — Custo-Benefício (§4.4 do PROJETO_v3).

Núcleo puro e testável (sem DB nem rede). Recebe uma lista de anúncios e os
parâmetros, devolve um resultado de score por anúncio.

Passos:
  1. Agrupa por `grupo_chave` (versão + ano-modelo).
  2. Segmenta cada grupo em faixas de km.
  3. preco_ref = mediana (ou média) dos preços da faixa, se a faixa tiver
     >= min_grupo anúncios (origem MERCADO). Senão, fallback FIPE.
  4. desconto = (preco_ref - preco) / preco_ref.
  5. score = desconto + bonus_km (bônus leve para desempatar por menor km).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median


@dataclass
class ScoreInput:
    id: int
    grupo_chave: str
    preco: int
    km: int | None = None
    fipe_valor: int | None = None


@dataclass
class ScoreResult:
    id: int
    preco_ref: int | None
    desconto: float | None
    origem_score: str | None      # "MERCADO" | "FIPE" | None
    score: float | None
    faixa_km: str | None


@dataclass
class ScoreParams:
    faixas_km: list[int] = field(default_factory=lambda: [30000, 60000, 90000, 120000])
    min_grupo: int = 3
    w_km: float = 0.05
    threshold_desconto: float = 0.08
    metrica_ref: str = "mediana"

    @classmethod
    def from_dict(cls, d: dict) -> "ScoreParams":
        return cls(
            faixas_km=list(d.get("faixas_km", [30000, 60000, 90000, 120000])),
            min_grupo=int(d.get("min_grupo", 3)),
            w_km=float(d.get("w_km", 0.05)),
            threshold_desconto=float(d.get("threshold_desconto", 0.08)),
            metrica_ref=str(d.get("metrica_ref", "mediana")),
        )


def faixa_de_km(km: int | None, cortes: list[int]) -> str:
    """Rótulo da faixa de km. Ex.: cortes [30k,60k] → '0-30k', '30k-60k', '60k+'."""
    if km is None:
        return "sem_km"
    cortes = sorted(cortes)
    anterior = 0
    for corte in cortes:
        if km < corte:
            return f"{anterior // 1000}k-{corte // 1000}k"
        anterior = corte
    return f"{anterior // 1000}k+"


def _referencia(precos: list[int], metrica: str) -> float:
    return mean(precos) if metrica == "media" else median(precos)


def calcular_scores(
    anuncios: list[ScoreInput], params: ScoreParams
) -> list[ScoreResult]:
    """Calcula o score de cada anúncio dentro do conjunto (mercado global)."""
    # 1) agrupa por grupo_chave
    grupos: dict[str, list[ScoreInput]] = {}
    for a in anuncios:
        grupos.setdefault(a.grupo_chave, []).append(a)

    resultados: list[ScoreResult] = []

    for _chave, itens in grupos.items():
        # 2) segmenta por faixa de km
        por_faixa: dict[str, list[ScoreInput]] = {}
        for a in itens:
            f = faixa_de_km(a.km, params.faixas_km)
            por_faixa.setdefault(f, []).append(a)

        # km mediano do grupo (para o bônus de desempate)
        kms_grupo = [a.km for a in itens if a.km is not None]
        km_ref_grupo = median(kms_grupo) if kms_grupo else None

        for faixa, lista in por_faixa.items():
            precos = [a.preco for a in lista if a.preco]
            usa_mercado = len(precos) >= params.min_grupo

            if usa_mercado:
                preco_ref_mercado = _referencia(precos, params.metrica_ref)

            for a in lista:
                preco_ref: float | None = None
                origem: str | None = None

                if usa_mercado:
                    preco_ref = preco_ref_mercado
                    origem = "MERCADO"
                elif a.fipe_valor:
                    # fallback FIPE: grupo/faixa pequeno demais p/ estatística
                    preco_ref = float(a.fipe_valor)
                    origem = "FIPE"

                if preco_ref and a.preco and preco_ref > 0:
                    desconto = (preco_ref - a.preco) / preco_ref
                    score = desconto + _bonus_km(a.km, km_ref_grupo, params.w_km)
                    resultados.append(
                        ScoreResult(
                            id=a.id,
                            preco_ref=round(preco_ref),
                            desconto=round(desconto, 4),
                            origem_score=origem,
                            score=round(score, 4),
                            faixa_km=faixa,
                        )
                    )
                else:
                    # sem referência (grupo pequeno e sem FIPE) → score indefinido
                    resultados.append(
                        ScoreResult(
                            id=a.id,
                            preco_ref=None,
                            desconto=None,
                            origem_score=None,
                            score=None,
                            faixa_km=faixa,
                        )
                    )

    return resultados


def _bonus_km(km: int | None, km_ref_grupo: float | None, w_km: float) -> float:
    """Ajuste leve de desempate por km (faixa -w_km..+w_km).

    Monotônico em relação à mediana de km do grupo: abaixo da mediana → bônus
    positivo, acima → pequeno desconto. Serve só para desempatar anúncios com
    desconto parecido, preferindo sempre o de menor quilometragem.
    """
    if km is None or km_ref_grupo is None or km_ref_grupo <= 0:
        return 0.0
    rel = (km_ref_grupo - km) / km_ref_grupo  # >0 se abaixo da mediana
    rel = max(-1.0, min(1.0, rel))
    return w_km * rel


def rankear(resultados: list[ScoreResult]) -> list[ScoreResult]:
    """Ordena por score decrescente; anúncios sem score vão para o fim."""
    return sorted(
        resultados,
        key=lambda r: (r.score is not None, r.score if r.score is not None else 0),
        reverse=True,
    )
