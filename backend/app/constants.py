"""Valores default dos parâmetros do sistema (sobrescrevíveis na tabela settings)."""

DEFAULT_SCORE_PARAMS = {
    "faixas_km": [30000, 60000, 90000, 120000],  # cortes das faixas de km
    "min_grupo": 2,        # mínimo de anúncios na faixa p/ usar MERCADO; abaixo → FIPE
    "w_km": 0.05,          # peso do bônus de km no desempate
    "threshold_desconto": 0.08,  # desconto mínimo p/ notificar
    "metrica_ref": "mediana",    # "mediana" ou "media"
}

# Chave usada na tabela settings
SCORE_PARAMS_KEY = "score_params"
