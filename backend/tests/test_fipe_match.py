"""Testes offline do matcher FIPE (sem rede — injeta a lista de modelos)."""
from app.services.fipe import FipeClient, _parse_valor, familia_do_label


def test_familia_do_label():
    # família = palavras-nome até a cilindrada, máx 2 (preserva modelos compostos)
    assert familia_do_label("ARGO 1.0 6V Flex") == "ARGO"
    assert familia_do_label("GRAND SIENA 1.4 Flex") == "GRAND SIENA"
    assert familia_do_label("COROLLA CROSS 1.8 16V Hybrid") == "COROLLA CROSS"
    assert familia_do_label("T-Cross 1.0 200 TSI") == "T-CROSS"
    assert familia_do_label("HB20S 1.0 TGDI Comfort") == "HB20S"  # 1º token tem dígito


def test_parse_valor():
    assert _parse_valor("R$ 87.010,00") == 87010
    assert _parse_valor("R$ 1.234,56") == 1234
    assert _parse_valor(None) is None
    assert _parse_valor("indisponível") is None


def _client_com_modelos(modelos):
    fc = FipeClient()
    fc._ref = 1                 # evita chamada de rede p/ tabela de referência
    fc._modelos[21] = modelos   # injeta cache de modelos da marca 21
    return fc


def test_match_exige_palavra_nome():
    """Regressão: 'Mobi' não pode casar com 'Argo' por causa do '1.0' em comum."""
    fc = _client_com_modelos([
        {"Label": "ARGO 1.0 6V Flex", "Value": 11401},
        {"Label": "MOBI 1.0 Firefly Flex", "Value": 222},
        {"Label": "TORO Freedom 1.8", "Value": 333},
    ])
    try:
        assert fc._match_modelo(21, "Mobi 1.0 Firefly Drive")["Value"] == 222
        assert fc._match_modelo(21, "Argo Drive 1.0 6v Flex")["Value"] == 11401
        # carro de outra marca/modelo sem palavra-nome em comum → None
        assert fc._match_modelo(21, "Onix 1.0 LT") is None
    finally:
        fc.close()


def test_modelos_colapsa_trims_preserva_compostos():
    """Modelo no dropdown = FIT/CIVIC/HR-V; trims (CX/DX/EX) vão p/ versão.
    Sub-modelos (CROSS) e compostos (GRAND SIENA) ficam como modelo próprio."""
    fc = FipeClient()
    fc._ref = 1
    labels = ["FIT CX 1.5", "FIT DX 1.5", "FIT EX 1.5",
              "CIVIC SEDAN 2.0", "CIVIC TYPE-R 2.0",
              "COROLLA GLI 1.8", "COROLLA XEI 2.0", "COROLLA CROSS 1.8",
              "GRAND SIENA 1.4", "GRAND SIENA ESSENCE 1.4"]
    fc._modelos[1] = [{"Label": l, "Value": i} for i, l in enumerate(labels)]
    try:
        mods = set(fc.modelos_familias(1))
        assert "FIT" in mods and "FIT CX" not in mods
        assert "CIVIC" in mods
        assert "COROLLA" in mods and "COROLLA CROSS" in mods   # Cross fica separado
        assert "GRAND SIENA" in mods
        assert len(fc.versoes(1, "FIT")) == 3
        assert len(fc.versoes(1, "COROLLA")) == 2              # GLI, XEI (sem Cross)
        assert len(fc.versoes(1, "COROLLA CROSS")) == 1
    finally:
        fc.close()


def test_match_escolhe_versao_mais_aderente():
    fc = _client_com_modelos([
        {"Label": "HB20S 1.0 Comfort", "Value": 1},
        {"Label": "HB20S 1.0 TGDI Comfort Plus", "Value": 2},
    ])
    try:
        m = fc._match_modelo(21, "Hb20s 1.0 Tgdi Comfort Plus")
        assert m["Value"] == 2
    finally:
        fc.close()
