"""Filtro de anúncios: casamento de modelo (palavra inteira vs compacto)."""
from app.models import VehicleListing
from app.services.filters import passa_filtros


def _l(**kw) -> VehicleListing:
    return VehicleListing(url="x", **kw)


def test_modelo_alfabetico_nao_casa_prefixo():
    # 'GOL' não pode trazer GOLF (substring) — palavra inteira
    assert passa_filtros(_l(marca="Volkswagen", modelo="Gol", versao="1.6 MSI"),
                         {"modelo": "GOL"})
    assert not passa_filtros(_l(marca="Volkswagen", versao="GOLF 1.0 TSI"),
                             {"modelo": "GOL"})


def test_modelo_com_digito_casa_compactado():
    # 'HB20' precisa casar 'HB 20 Hatch' (portais variam o espaço)
    assert passa_filtros(_l(marca="Hyundai", versao="HB 20 Hatch Comfort"),
                         {"modelo": "HB20"})


def test_modelo_composto_e_hifen():
    assert passa_filtros(_l(marca="Volkswagen", versao="T Cross 200 TSI"),
                         {"modelo": "T-CROSS"})
    assert passa_filtros(_l(marca="Toyota", modelo="Corolla Cross", versao="XRE"),
                         {"modelo": "COROLLA CROSS"})
    # Corolla simples NÃO entra na busca de Corolla Cross
    assert not passa_filtros(_l(marca="Toyota", modelo="Corolla", versao="XEI"),
                             {"modelo": "COROLLA CROSS"})
