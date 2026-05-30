"""Testes da engine de score (§4.4). Cobre os 3 casos exigidos pelo projeto."""
from app.services.scoring import (
    ScoreInput,
    ScoreParams,
    calcular_scores,
    faixa_de_km,
    rankear,
)


def _by_id(resultados):
    return {r.id: r for r in resultados}


def test_faixa_de_km():
    cortes = [30000, 60000, 90000, 120000]
    assert faixa_de_km(0, cortes) == "0k-30k"
    assert faixa_de_km(29999, cortes) == "0k-30k"
    assert faixa_de_km(30000, cortes) == "30k-60k"
    assert faixa_de_km(150000, cortes) == "120k+"
    assert faixa_de_km(None, cortes) == "sem_km"


def test_grupo_grande_usa_mercado():
    """Grupo com >= min_grupo anúncios na faixa → origem MERCADO, mediana como ref."""
    params = ScoreParams(min_grupo=3, w_km=0.0)  # zera bônus p/ isolar o desconto
    # mesmo carro, mesma faixa de km (todos 0-30k), preços: 50k,52k,54k,40k
    anuncios = [
        ScoreInput(id=1, grupo_chave="onix-2020", preco=50000, km=10000),
        ScoreInput(id=2, grupo_chave="onix-2020", preco=52000, km=15000),
        ScoreInput(id=3, grupo_chave="onix-2020", preco=54000, km=20000),
        ScoreInput(id=4, grupo_chave="onix-2020", preco=40000, km=25000),  # barato
    ]
    res = _by_id(calcular_scores(anuncios, params))

    # mediana de [50,52,54,40] = 51000
    assert res[4].origem_score == "MERCADO"
    assert res[4].preco_ref == 51000
    # anúncio de 40k está ~21,6% abaixo da referência → desconto positivo alto
    assert res[4].desconto > 0.2
    # anúncio de 54k está acima da referência → desconto negativo
    assert res[3].desconto < 0


def test_grupo_pequeno_cai_para_fipe():
    """Faixa com < min_grupo anúncios → fallback FIPE."""
    params = ScoreParams(min_grupo=3, w_km=0.0)
    anuncios = [
        ScoreInput(id=1, grupo_chave="raro-2018", preco=80000, km=10000, fipe_valor=100000),
        ScoreInput(id=2, grupo_chave="raro-2018", preco=95000, km=12000, fipe_valor=100000),
    ]
    res = _by_id(calcular_scores(anuncios, params))

    # só 2 anúncios (< 3) → não há base de mercado → usa FIPE
    assert res[1].origem_score == "FIPE"
    assert res[1].preco_ref == 100000
    # 80k vs FIPE 100k → 20% abaixo
    assert abs(res[1].desconto - 0.20) < 1e-6


def test_grupo_pequeno_sem_fipe_fica_indefinido():
    params = ScoreParams(min_grupo=3)
    anuncios = [
        ScoreInput(id=1, grupo_chave="x", preco=50000, km=10000, fipe_valor=None),
    ]
    res = _by_id(calcular_scores(anuncios, params))
    assert res[1].origem_score is None
    assert res[1].score is None


def test_desempate_por_km():
    """Mesmo preço (mesmo desconto), mesma faixa de km → o de menor km pontua mais."""
    params = ScoreParams(min_grupo=3, w_km=0.05)
    # os 3 caem na MESMA faixa (0-30k) → mesma referência de mercado
    anuncios = [
        ScoreInput(id=1, grupo_chave="hb20-2021", preco=60000, km=5000),   # menos km
        ScoreInput(id=2, grupo_chave="hb20-2021", preco=60000, km=15000),
        ScoreInput(id=3, grupo_chave="hb20-2021", preco=60000, km=25000),  # mais km
    ]
    res = _by_id(calcular_scores(anuncios, params))

    # mesmo preço e mesma referência → mesmo desconto; o bônus de km desempata
    assert res[1].desconto == res[2].desconto == res[3].desconto
    assert res[1].score > res[2].score > res[3].score  # menor km → maior score

    ranking = rankear(calcular_scores(anuncios, params))
    assert ranking[0].id == 1  # o de menor km lidera


def test_ranking_ordena_por_score():
    params = ScoreParams(min_grupo=3, w_km=0.0)
    anuncios = [
        ScoreInput(id=1, grupo_chave="g", preco=50000, km=10000),
        ScoreInput(id=2, grupo_chave="g", preco=52000, km=10000),
        ScoreInput(id=3, grupo_chave="g", preco=30000, km=10000),  # melhor negócio
    ]
    ranking = rankear(calcular_scores(anuncios, params))
    assert ranking[0].id == 3
    assert ranking[0].desconto > 0
