"""Testes do engine de Preço de Mercado (v0.10)."""
from app.services.scoring import (
    ScoreInput,
    ScoreParams,
    calcular_scores,
    faixa_de_km,
    rankear,
)


def _by_id(resultados):
    return {r.id: r for r in resultados}


def test_faixa_de_km_exibicao():
    cortes = [30000, 60000, 90000, 120000]
    assert faixa_de_km(0, cortes) == "0k-30k"
    assert faixa_de_km(30000, cortes) == "30k-60k"
    assert faixa_de_km(150000, cortes) == "120k+"
    assert faixa_de_km(None, cortes) == "sem_km"


def _a(id, preco, km=None, versao="gol 1.0|2018", modelo="vw|gol|2018", fipe=None):
    return ScoreInput(id=id, grupo_versao=versao, grupo_modelo=modelo,
                      preco=preco, km=km, fipe_valor=fipe)


def test_referencia_por_versao():
    """4 anúncios da mesma versão → referência = mediana da versão (VERSAO:4)."""
    params = ScoreParams(min_grupo=3, alpha_km=0.0)  # sem ajuste de km p/ isolar
    r = _by_id(calcular_scores(
        [_a(1, 50000), _a(2, 52000), _a(3, 54000), _a(4, 40000)], params))
    # mediana = 51000; anúncio 4 (40k) está ~21,6% abaixo
    assert r[4].origem_score == "VERSAO:4"
    assert r[4].preco_ref == 51000
    assert abs(r[4].desconto - (51000 - 40000) / 51000) < 1e-3
    assert r[4].score == r[4].desconto  # score = desconto, sem mágica


def test_fallback_para_modelo():
    """Versões diferentes (sem volume) mas mesmo modelo → referência MODELO:n."""
    params = ScoreParams(min_grupo=3, alpha_km=0.0)
    r = _by_id(calcular_scores([
        _a(1, 50000, versao="gol 1.0|2018"),
        _a(2, 52000, versao="gol 1.6 msi|2018"),
        _a(3, 54000, versao="gol trendline|2018"),
    ], params))
    assert r[1].origem_score == "MODELO:3"
    assert r[1].preco_ref == 52000  # mediana do modelo


def test_fallback_para_fipe():
    """Sem comparáveis em nível nenhum → FIPE quando existir, senão sem score."""
    params = ScoreParams(min_grupo=3)
    r = _by_id(calcular_scores([
        _a(1, 45000, modelo="vw|gol|2018", fipe=50000),
        _a(2, 60000, versao="argo drive|2022", modelo="fiat|argo|2022"),
    ], params))
    assert r[1].origem_score == "FIPE"
    assert abs(r[1].desconto - 0.10) < 1e-3
    assert r[2].origem_score is None and r[2].score is None


def test_ajuste_de_km_na_referencia():
    """Carro com km abaixo da mediana do grupo tem preço justo MAIOR (e vice-versa)."""
    params = ScoreParams(min_grupo=3, alpha_km=0.01, cap_km=0.10)
    # grupo com km mediana 60k; anúncios de mesmo preço
    r = _by_id(calcular_scores([
        _a(1, 50000, km=20000),   # 40k km abaixo da mediana → ref +4%
        _a(2, 50000, km=60000),   # na mediana → ref neutra
        _a(3, 50000, km=100000),  # 40k acima → ref -4%
    ], params))
    assert r[1].preco_ref > r[2].preco_ref > r[3].preco_ref
    assert r[1].desconto > 0 > r[3].desconto  # rodou pouco = mais barato que o justo
    assert abs(r[1].preco_ref - round(50000 * 1.04)) <= 1
    assert abs(r[3].preco_ref - round(50000 * 0.96)) <= 1


def test_cap_do_ajuste_km():
    """Diferença absurda de km não distorce a referência além do teto."""
    params = ScoreParams(min_grupo=3, alpha_km=0.01, cap_km=0.05)
    r = _by_id(calcular_scores([
        _a(1, 50000, km=0),
        _a(2, 50000, km=100000),
        _a(3, 50000, km=300000),  # 200k acima da mediana → capado em -5%
    ], params))
    assert r[3].preco_ref == round(50000 * 0.95)


def test_rankear_sem_score_no_fim():
    params = ScoreParams(min_grupo=3, alpha_km=0.0)
    rs = calcular_scores([
        _a(1, 40000), _a(2, 52000), _a(3, 54000),
        _a(9, 99000, versao="x|?", modelo="y|?"),  # sem comparável nem FIPE
    ], params)
    ordenado = rankear(rs)
    assert ordenado[0].id == 1          # maior desconto primeiro
    assert ordenado[-1].id == 9         # sem score no fim
