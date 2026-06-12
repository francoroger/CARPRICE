"""Engine de Preço de Mercado — "este carro está caro ou barato pro que ele é?"

Núcleo puro e testável (sem DB nem rede). MODELO NOVO (v0.10), calibrado numa
análise de 3.887 anúncios reais coletados:

  - dispersão de preço dentro de modelo+ano: ±11,5% (define os rótulos: ≥10%
    abaixo da referência é negócio raro; ±5% é o "preço justo");
  - efeito da km medido: ≈ -0,4% por 10.000 km (a km AJUSTA a referência — não
    fragmenta mais o grupo em faixas, que era o que deixava quase tudo sem score);
  - cobertura: agrupar só por versão+ano deixava 29% dos anúncios sem comparável;
    com a hierarquia versão → modelo a cobertura vai a ~88%.

Como funciona, por anúncio:
  1. REFERÊNCIA (hierarquia, usa a 1ª com volume >= min_grupo):
       VERSAO  = mediana dos preços de mesma versão+ano   (mais precisa)
       MODELO  = mediana dos preços de mesmo modelo+ano   (mais cobertura)
       FIPE    = valor FIPE (último recurso, se disponível)
  2. AJUSTE DE KM: referência corrigida pela km do carro vs a km mediana do
     grupo (alpha_km por 10.000 km, com teto cap_km).
  3. desconto = (preço_justo - preço) / preço_justo  → "% abaixo do mercado".
     score = desconto (ordenação direta; sem bônus escondido).
  `origem_score` carrega a transparência: "VERSAO:8" = comparado com 8 anúncios
  da mesma versão. O frontend traduz em rótulos (Excelente negócio/Bom preço/...).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median


@dataclass
class ScoreInput:
    id: int
    grupo_versao: str            # versão + ano (carros idênticos)
    grupo_modelo: str            # modelo + ano (mesmo carro, qualquer versão)
    preco: int
    km: int | None = None
    fipe_valor: int | None = None


@dataclass
class ScoreResult:
    id: int
    preco_ref: int | None        # preço justo (já ajustado pela km)
    desconto: float | None       # + = abaixo do mercado, - = acima
    origem_score: str | None     # "VERSAO:n" | "MODELO:n" | "FIPE" | None
    score: float | None          # = desconto (ordenação)


@dataclass
class ScoreParams:
    min_grupo: int = 3           # nº mínimo de comparáveis p/ referência de mercado
    alpha_km: float = 0.005      # fração do preço por 10.000 km de diferença
    cap_km: float = 0.10         # teto do ajuste de km (±10%)
    threshold_desconto: float = 0.08  # desconto mínimo p/ monitor notificar
    faixas_km: list[int] = field(default_factory=lambda: [30000, 60000, 90000, 120000])

    @classmethod
    def from_dict(cls, d: dict) -> "ScoreParams":
        return cls(
            min_grupo=int(d.get("min_grupo", 3)),
            alpha_km=float(d.get("alpha_km", 0.005)),
            cap_km=float(d.get("cap_km", 0.10)),
            threshold_desconto=float(d.get("threshold_desconto", 0.08)),
            faixas_km=list(d.get("faixas_km", [30000, 60000, 90000, 120000])),
        )


def faixa_de_km(km: int | None, cortes: list[int]) -> str:
    """Rótulo da faixa de km (só EXIBIÇÃO — não entra mais no cálculo)."""
    if km is None:
        return "sem_km"
    cortes = sorted(cortes)
    anterior = 0
    for corte in cortes:
        if km < corte:
            return f"{anterior // 1000}k-{corte // 1000}k"
        anterior = corte
    return f"{anterior // 1000}k+"


def _preco_justo(
    mediana_preco: float,
    km_anuncio: int | None,
    km_mediana_grupo: float | None,
    params: ScoreParams,
) -> float:
    """Referência ajustada pela km: rodou menos que o grupo → vale mais (e vice-versa)."""
    if km_anuncio is None or km_mediana_grupo is None:
        return mediana_preco
    ajuste = params.alpha_km * (km_mediana_grupo - km_anuncio) / 10_000
    ajuste = max(-params.cap_km, min(params.cap_km, ajuste))
    return mediana_preco * (1 + ajuste)


def calcular_scores(
    anuncios: list[ScoreInput], params: ScoreParams
) -> list[ScoreResult]:
    """Score de cada anúncio dentro do conjunto (a busca filtrada ou o mercado)."""
    por_versao: dict[str, list[ScoreInput]] = {}
    por_modelo: dict[str, list[ScoreInput]] = {}
    for a in anuncios:
        por_versao.setdefault(a.grupo_versao, []).append(a)
        por_modelo.setdefault(a.grupo_modelo, []).append(a)

    resultados: list[ScoreResult] = []
    for a in anuncios:
        if not a.preco:
            resultados.append(ScoreResult(a.id, None, None, None, None))
            continue

        # 1) referência hierárquica: versão (precisa) → modelo (cobre) → FIPE
        ref: float | None = None
        origem: str | None = None
        for nome, grupo in (("VERSAO", por_versao[a.grupo_versao]),
                            ("MODELO", por_modelo[a.grupo_modelo])):
            precos = [x.preco for x in grupo if x.preco]
            if len(precos) >= params.min_grupo:
                kms = [x.km for x in grupo if x.km is not None]
                km_med = median(kms) if kms else None
                ref = _preco_justo(median(precos), a.km, km_med, params)
                origem = f"{nome}:{len(precos)}"
                break
        if ref is None and a.fipe_valor:
            ref = float(a.fipe_valor)
            origem = "FIPE"

        if not ref or ref <= 0:
            resultados.append(ScoreResult(a.id, None, None, None, None))
            continue

        # 2) desconto = % abaixo do preço justo; score = desconto (sem mágica)
        desconto = (ref - a.preco) / ref
        resultados.append(ScoreResult(
            id=a.id,
            preco_ref=round(ref),
            desconto=round(desconto, 4),
            origem_score=origem,
            score=round(desconto, 4),
        ))
    return resultados


def rankear(resultados: list[ScoreResult]) -> list[ScoreResult]:
    """Ordena por score decrescente; anúncios sem score vão para o fim."""
    return sorted(
        resultados,
        key=lambda r: (r.score is not None, r.score if r.score is not None else 0),
        reverse=True,
    )
