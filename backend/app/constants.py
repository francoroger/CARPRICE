"""Valores default dos parâmetros do sistema (sobrescrevíveis na tabela settings)."""

DEFAULT_SCORE_PARAMS = {
    "min_grupo": 3,        # nº mínimo de comparáveis p/ referência de mercado
    "alpha_km": 0.005,     # fração do preço por 10.000 km (análise real: ~0,4%)
    "cap_km": 0.10,        # teto do ajuste de km (±10%)
    "threshold_desconto": 0.08,  # desconto mínimo p/ o monitor notificar
    "faixas_km": [30000, 60000, 90000, 120000],  # só exibição (rótulo da faixa)
}

# Chave usada na tabela settings
SCORE_PARAMS_KEY = "score_params"
