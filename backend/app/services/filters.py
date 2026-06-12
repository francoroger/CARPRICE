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


def passa_filtros(l: VehicleListing, crit: dict) -> bool:
    """True se o anúncio satisfaz todos os filtros informados no critério."""
    alvo = _texto(l)  # compactado (sem espaços) p/ tolerar 'HB20' vs 'HB 20'
    alvo_esp = _norm_txt(" ".join(filter(None, [l.marca, l.modelo, l.versao, l.cidade])))

    if crit.get("marca") and _compact(crit["marca"]) not in alvo:
        return False
    if crit.get("modelo") and not _casa_modelo(crit["modelo"], alvo, alvo_esp):
        return False
    if crit.get("versao") and _compact(crit["versao"]) not in _compact(l.versao or ""):
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
