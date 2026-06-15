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


# --- casamento de VERSÃO por trim + cilindrada (não substring) --- #

def test_versao_trim_separa_limited_de_longitude():
    crit = {"modelo": "COMMANDER", "versao": "Commander Limited T270 1.3 TB Flex Aut."}
    # anúncio escreve a versão noutra ordem — tem que casar mesmo assim
    assert passa_filtros(
        _l(marca="Jeep", modelo="Commander",
           versao="1.3 16v 4p flex t270 limited turbo automatico at6"), crit)
    # Longitude/Overland NÃO entram na busca de Limited
    assert not passa_filtros(
        _l(marca="Jeep", modelo="Commander",
           versao="1.3 16v 4p flex t270 longitude turbo automatico at6"), crit)
    assert not passa_filtros(
        _l(marca="Jeep", modelo="Commander",
           versao="1.3 16v 4p flex t270 overland turbo automatico at6"), crit)


def test_versao_cilindrada_separa_flex_de_diesel():
    crit_diesel = {"modelo": "COMMANDER", "versao": "Commander Limited TD380 2.0 4x4 Die.Aut."}
    # Limited FLEX 1.3 não entra na busca de Limited DIESEL 2.0 (cilindrada difere)
    assert not passa_filtros(
        _l(marca="Jeep", modelo="Commander",
           versao="1.3 16v 4p flex t270 limited turbo automatico"), crit_diesel)
    assert passa_filtros(
        _l(marca="Jeep", modelo="Commander",
           versao="2.0 td 4x4 limited diesel automatico"), crit_diesel)


def test_versao_ignora_carroceria_e_marketing():
    # FIPE prefixa 'ONIX HATCH LT'; anúncio diz só '1.0 12v lt flex' (sem 'hatch')
    crit = {"modelo": "ONIX", "versao": "ONIX HATCH LT 1.0 12V Flex 5p Mec."}
    assert passa_filtros(_l(marca="Chevrolet", modelo="Onix", versao="1.0 12v 4p flex lt"), crit)
    # LTZ não casa busca de LT (trim curto exige igualdade — não casa por prefixo)
    assert not passa_filtros(_l(marca="Chevrolet", modelo="Onix", versao="1.4 4p ltz flex"), crit)


def test_versao_trim_abreviado_por_prefixo():
    # FIPE abrevia 'Overl.'; anúncio escreve 'Overland' (prefixo ≥3 casa)
    crit = {"modelo": "COMMANDER", "versao": "Commander Overl. TD380 2.0 4x4 Die. Aut."}
    assert passa_filtros(
        _l(marca="Jeep", modelo="Commander", versao="2.0 overland 4x4 diesel"), crit)
