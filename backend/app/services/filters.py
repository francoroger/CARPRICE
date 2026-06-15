"""Filtro de anúncios — modelado nos filtros do CarroSP (§ busca/monitor).

Uma única função aplica todos os pós-filtros, usada tanto pelo monitor agendado
quanto pela busca ao vivo. Campos ausentes no critério são ignorados (não filtram).
"""
from __future__ import annotations

import re

from app.collectors.normalize import _norm_txt
from app.models import VehicleListing


def _compact(s: str | None) -> str:
    """Normaliza e remove espaços — casa 'HB20' com 'HB 20 Hatch', 'hr-v' com 'hr v'."""
    return _norm_txt(s).replace(" ", "")


def _texto(l: VehicleListing) -> str:
    return _compact(" ".join(filter(None, [l.marca, l.modelo, l.versao, l.cidade])))


def _casa_modelo(modelo: str, alvo_compacto: str, alvo_espacado: str) -> bool:
    """Modelo alfabético casa por PALAVRA INTEIRA ('gol' NÃO casa 'golf');
    modelo com dígito/hífen casa compactado ('hb20' casa 'HB 20 Hatch')."""
    mn = _norm_txt(modelo)
    if mn.replace(" ", "").isalpha():
        return re.search(rf"\b{re.escape(mn)}\b", alvo_espacado) is not None
    return _compact(modelo) in alvo_compacto


# Palavras NÃO-distintivas de versão (transmissão, combustível, carroceria, fillers).
# Cada portal escreve a versão diferente; o que diferencia é o TRIM + a cilindrada.
_VERSAO_NOISE = {
    # transmissão
    "aut", "auto", "automatico", "automatica", "automatizado", "autom", "mec",
    "manual", "mt", "at", "cvt", "dct", "tiptronic", "at6", "at9",
    # combustível / indução
    "flex", "flexpower", "power", "fpower", "gasolina", "gas", "alcool", "etanol",
    "diesel", "die", "dies", "turbo", "tb", "td", "tdi", "tsi", "gdi", "vhc",
    "vvt", "mpi", "msi",
    # carroceria
    "hatch", "sedan", "sed", "suv", "coupe", "perua", "conversivel", "cabriolet",
    # marketing / genéricos
    "novo", "nova", "new", "total", "mi",
    # portas / lugares / tração
    "portas", "port", "lugares", "lugar", "passageiros", "pas", "awd", "4wd", "fwd",
}


def _tok_versao(palavra: str, tokens_anuncio: set[str]) -> bool:
    """Trim casa por igualdade OU prefixo (≥3 letras): 'Overl.'↔'Overland',
    'Comfort'↔'Comfortline'. 'LT' NÃO casa 'LTZ' (prefixo só ≥3 → trims curtos
    exigem igualdade exata, separando LT/LTZ/LS)."""
    if palavra in tokens_anuncio:
        return True
    for t in tokens_anuncio:
        curto, longo = (palavra, t) if len(palavra) <= len(t) else (t, palavra)
        if len(curto) >= 3 and longo.startswith(curto):
            return True
    return False


def _casa_versao(versao_fipe: str, versao_anuncio: str | None, modelo: str | None) -> bool:
    """Casa a versão FIPE com a do anúncio por TRIM + cilindrada (não substring).

    A versão FIPE ('Commander Limited T270 1.3 TB Flex Aut.') e a do anúncio
    ('1.3 16v 4p flex t270 limited turbo automatico') usam ordem/tokens diferentes
    → substring nunca casava. Exigimos: (1) toda palavra-TRIM da FIPE (alfabética,
    fora do ruído e do nome do modelo) presente no anúncio; (2) a cilindrada
    (1.3/2.0), se a FIPE tiver, igual. Assim 'Limited' ≠ 'Longitude' e a flex 1.3
    se separa da diesel 2.0.
    """
    alvo = _norm_txt(versao_fipe)
    cand = _norm_txt(versao_anuncio or "")
    if not cand:
        return False
    tokens = set(cand.split())
    modelo_toks = set(_norm_txt(modelo or "").split())
    trim = [t for t in alvo.split()
            if t.isalpha() and len(t) >= 2
            and t not in _VERSAO_NOISE and t not in modelo_toks]
    for palavra in trim:
        if not _tok_versao(palavra, tokens):
            return False
    m = re.search(r"\d[.,]\d", versao_fipe or "")
    if m:
        disp = m.group(0).replace(",", ".")
        if disp not in (versao_anuncio or "") and disp.replace(".", " ") not in cand:
            return False
    return True


def passa_filtros(l: VehicleListing, crit: dict) -> bool:
    """True se o anúncio satisfaz todos os filtros informados no critério."""
    alvo = _texto(l)  # compactado (sem espaços) p/ tolerar 'HB20' vs 'HB 20'
    alvo_esp = _norm_txt(" ".join(filter(None, [l.marca, l.modelo, l.versao, l.cidade])))

    if crit.get("marca") and _compact(crit["marca"]) not in alvo:
        return False
    if crit.get("modelo") and not _casa_modelo(crit["modelo"], alvo, alvo_esp):
        return False
    if crit.get("versao") and not _casa_versao(crit["versao"], l.versao, crit.get("modelo")):
        return False
    # Localização: o ESTADO (UF) é o filtro real; a cidade é só um ponto de coleta
    # (os portais devolvem resultados REGIONAIS — filtrar por cidade exata cortaria
    # os vizinhos, ex.: HB20 de Limeira numa busca de SP). Não filtramos por cidade.
    if crit.get("uf") and l.uf and crit["uf"].upper() != (l.uf or "").upper():
        return False

    # ano (faixa)
    if crit.get("ano_min") and (l.ano_modelo or 0) < crit["ano_min"]:
        return False
    if crit.get("ano_max") and l.ano_modelo and l.ano_modelo > crit["ano_max"]:
        return False

    # preço (faixa)
    if crit.get("preco_min") and (l.preco or 0) < crit["preco_min"]:
        return False
    if crit.get("preco_max") and (l.preco or 0) > crit["preco_max"]:
        return False

    # km (faixa)
    if crit.get("km_min") and (l.km or 0) < crit["km_min"]:
        return False
    if crit.get("km_max") and l.km and l.km > crit["km_max"]:
        return False

    # câmbio / combustível (texto nos campos próprios ou na versão)
    if crit.get("cambio"):
        campo = _norm_txt((l.cambio or "") + " " + (l.versao or ""))
        if _norm_txt(crit["cambio"]) not in campo:
            return False
    if crit.get("combustivel"):
        campo = _norm_txt((l.combustivel or "") + " " + (l.versao or ""))
        if _norm_txt(crit["combustivel"]) not in campo:
            return False

    # cor (best-effort: poucos portais trazem cor → casa no texto se houver)
    if crit.get("cor"):
        if _norm_txt(crit["cor"]) not in _norm_txt((l.versao or "") + " " + (l.modelo or "")):
            return False

    # condição: 0km (km<=100) ou usado. Km desconhecido (None) NÃO é filtrado.
    cond = crit.get("condicao")
    if l.km is not None:
        if cond == "0km" and l.km > 100:
            return False
        if cond == "usado" and l.km <= 100:
            return False

    return True
