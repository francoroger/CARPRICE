"""Wrapper da API interna OFICIAL da FIPE (veiculos.fipe.org.br) com cache (§4.3).

Fluxo oficial: tabela de referência → marcas → modelos → ano-modelo → valor.
Vantagem sobre APIs não-oficiais: lista de modelos EXATA e autoritativa, então o
casamento do anúncio é por sobreposição de tokens contra os labels reais da FIPE
(ex.: anúncio "argo 1.0 6v flex active" → modelo FIPE "ARGO 1.0 6V Flex").

Toda chamada é defensiva: em falha, retorna None e a engine de score segue sem FIPE.
"""
from __future__ import annotations

import json
import logging
import pathlib
import re
import time
import unicodedata
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FipeCache

log = logging.getLogger(__name__)

# Catálogo FIPE estático (marcas + modelos) embutido no repo. Gerado de um IP onde a
# FIPE responde; usado nos dropdowns pois a FIPE oficial bloqueia IP de datacenter
# (ex.: Render). O VALOR (preço) ainda é consultado ao vivo quando disponível.
_CATALOG_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "fipe_modelos.json"
try:
    _CATALOG: dict = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    log.info("catálogo FIPE estático: %d marcas", len(_CATALOG))
except Exception as e:  # noqa: BLE001
    _CATALOG = {}
    log.warning("catálogo FIPE estático não carregado: %s", e)

BASE = "https://veiculos.fipe.org.br/api/veiculos"
TIPO_CARRO = 1
# 2ª palavra que indica um MODELO distinto (não um trim) — ex.: Corolla CROSS, Onix PLUS.
_SUBMODELOS = {"CROSS", "PLUS", "SW", "COUPE", "CABRIO", "CABRIOLET", "COUNTRY", "ADVENTURE"}
# 2ª palavra que é TRIM (colapsa no 1º nome mesmo sendo a única do grupo).
_TRIM_WORDS = {
    "SPORT", "TOURING", "ADVANCE", "ADVANCED", "PREMIER", "PREMIUM", "COMFORT",
    "COMFORTLINE", "HIGHLINE", "HIGH", "ESSENCE", "ATTRACTIVE", "ATTRACTIVE",
    "EXCLUSIVE", "INTENSE", "FEEL", "LIVE", "SHINE", "TREND", "LIMITED", "ELITE",
    "LUXURY", "ACTIVE", "ALLURE", "DYNAMIC", "STYLE", "EDITION", "SPECIAL",
    "SELECT", "EVOLUTION", "GLAMOUR", "COLLECTION", "PERSONAL", "TWIST", "PRECISION",
    "EMOTION", "EXPRESSION", "EXPERIENCE", "VISION", "SENSE", "DRIVE", "TURBO",
    "AUTOMATICO", "FLEX", "LUXE", "LOUNGE", "ELEGANCE", "ULTIMATE", "DESIGN",
}
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://veiculos.fipe.org.br/",
    "Origin": "https://veiculos.fipe.org.br",
    "X-Requested-With": "XMLHttpRequest",
}


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _tokens(s: str | None) -> set[str]:
    return {t for t in _norm(s).split() if t}


class FipeClient:
    """Resolve valores FIPE reaproveitando 1 conexão e caches por tabela de referência."""

    def __init__(self) -> None:
        self._client = httpx.Client(headers=_HEADERS, timeout=20, http2=True)
        self._ref: int | None = None
        self._ref_mes: str | None = None
        self._marcas: list[dict] | None = None
        self._modelos: dict[int, list[dict]] = {}     # codigoMarca -> modelos
        self._anos: dict[tuple[int, int], list[dict]] = {}
        self._modmap: dict[int, dict[str, str]] = {}  # codigoMarca -> {familia: modelo}
        self._valor_ok: bool | None = None            # circuit-breaker do valor FIPE

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "FipeClient":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def _post(self, path: str, payload: dict):
        time.sleep(0.15)  # respiro p/ não tomar 403 da FIPE oficial (rate limit)
        r = self._client.post(f"{BASE}/{path}", json=payload)
        r.raise_for_status()
        return r.json()

    # --- camadas de resolução, com cache em memória --- #

    def _ref_atual(self) -> int:
        if self._ref is None:
            tabelas = self._post("ConsultarTabelaDeReferencia", {})
            self._ref = tabelas[0]["Codigo"]
            self._ref_mes = tabelas[0]["Mes"].strip()
        return self._ref

    def _get_marcas(self) -> list[dict]:
        if self._marcas is None:
            if _CATALOG:  # catálogo estático (funciona mesmo com FIPE bloqueada)
                self._marcas = [{"Label": v["nome"], "Value": int(c)}
                                for c, v in _CATALOG.items()]
            else:
                self._marcas = self._post(
                    "ConsultarMarcas",
                    {"codigoTabelaReferencia": self._ref_atual(),
                     "codigoTipoVeiculo": TIPO_CARRO},
                )
        return self._marcas

    def _get_modelos(self, cod_marca: int) -> list[dict]:
        if cod_marca not in self._modelos:
            cat = _CATALOG.get(str(cod_marca))
            if cat is not None:  # catálogo estático
                self._modelos[cod_marca] = cat["modelos"]
            else:
                resp = self._post(
                    "ConsultarModelos",
                    {"codigoTabelaReferencia": self._ref_atual(),
                     "codigoTipoVeiculo": TIPO_CARRO, "codigoMarca": cod_marca},
                )
                self._modelos[cod_marca] = resp.get("Modelos", [])
        return self._modelos[cod_marca]

    def _get_anos(self, cod_marca: int, cod_modelo: int) -> list[dict]:
        key = (cod_marca, cod_modelo)
        if key not in self._anos:
            self._anos[key] = self._post(
                "ConsultarAnoModelo",
                {"codigoTabelaReferencia": self._ref_atual(), "codigoTipoVeiculo": TIPO_CARRO,
                 "codigoMarca": cod_marca, "codigoModelo": cod_modelo},
            )
        return self._anos[key]

    # --- matching --- #

    def _match_marca(self, marca: str) -> dict | None:
        alvo = _norm(marca)
        for m in self._get_marcas():
            if _norm(m["Label"]) == alvo:
                return m
        for m in self._get_marcas():
            if alvo and alvo in _norm(m["Label"]):
                return m
        return None

    def _match_modelos_ranked(self, cod_marca: int, texto: str) -> list[dict]:
        """Modelos candidatos ordenados por aderência (melhor primeiro).

        Exige ≥1 palavra-NOME em comum (evita Mobi↔Argo via '1.0'). A FIPE tem
        várias gerações com o mesmo nome → devolvemos vários p/ o resolver depois
        escolher a que tem o ano do carro.
        """
        alvo = _tokens(texto)
        nomes_alvo = {t for t in alvo if t.isalpha() and len(t) >= 3}
        if not alvo:
            return []
        pontuados = []
        for mod in self._get_modelos(cod_marca):
            lt = _tokens(mod["Label"])
            nomes_lt = {t for t in lt if t.isalpha() and len(t) >= 3}
            nomes_comuns = nomes_alvo & nomes_lt
            if not nomes_comuns:
                continue
            inter = len(alvo & lt)
            score = (
                2.0 * len(nomes_comuns) / max(1, len(nomes_lt))
                + inter / max(1, len(lt))
                + 0.2 * inter / max(1, len(alvo))
            )
            if score >= 1.0:
                pontuados.append((score, mod))
        pontuados.sort(key=lambda x: x[0], reverse=True)
        return [m for _s, m in pontuados]

    def _match_modelo(self, cod_marca: int, texto: str) -> dict | None:
        cands = self._match_modelos_ranked(cod_marca, texto)
        return cands[0] if cands else None

    def _match_ano(self, anos: list[dict], ano: int) -> dict | None:
        prefixo = f"{ano}-"
        for a in anos:
            if str(a.get("Value", "")).startswith(prefixo):
                return a
        return None

    def resolver(self, marca: str, modelo: str | None, ano: int, versao: str | None
                 ) -> tuple[int | None, str | None]:
        try:
            mk = self._match_marca(marca)
            if not mk:
                return None, None
            texto_modelo = " ".join(filter(None, [modelo, versao])) or modelo or ""
            # entre os modelos candidatos (várias gerações), usa o que TEM o ano do carro
            for md in self._match_modelos_ranked(int(mk["Value"]), texto_modelo)[:6]:
                anos = self._get_anos(int(mk["Value"]), int(md["Value"]))
                ya = self._match_ano(anos, ano)
                if not ya:
                    continue
                ano_cod, comb = str(ya["Value"]).split("-")
                info = self._post("ConsultarValorComTodosParametros", {
                    "codigoTabelaReferencia": self._ref_atual(), "codigoTipoVeiculo": TIPO_CARRO,
                    "codigoMarca": mk["Value"], "codigoModelo": md["Value"],
                    "anoModelo": ano_cod, "codigoTipoCombustivel": int(comb),
                    "tipoVeiculo": "carro", "modeloCodigoExterno": "", "tipoConsulta": "tradicional",
                })
                return _parse_valor(info.get("Valor")), info.get("CodigoFipe")
            return None, None
        except Exception as e:
            log.warning("FIPE oficial indisponível (%s %s %s): %s", marca, modelo, ano, e)
            return None, None

    @property
    def ref_mes(self) -> str:
        self._ref_atual()
        return self._ref_mes or datetime.now(timezone.utc).strftime("%Y-%m")

    # --- API pública para os filtros em cascata (marca → modelo → versão) --- #

    def valor_disponivel(self) -> bool:
        """True se a FIPE responde p/ consultar VALOR (ConsultarTabelaDeReferencia).

        No Render a FIPE bloqueia o IP → False → o score pula a consulta de preço
        (evita ~12s desperdiçados; usa só MERCADO). Testado uma vez e cacheado.
        """
        if self._valor_ok is None:
            try:
                self._ref_atual()
                self._valor_ok = True
            except Exception:
                self._valor_ok = False
                log.info("FIPE (valor) indisponível — score usará só MERCADO")
        return self._valor_ok

    def marcas(self) -> list[dict]:
        """[{codigo, nome}] de todas as marcas (ordenado)."""
        return [
            {"codigo": str(m["Value"]), "nome": m["Label"]}
            for m in sorted(self._get_marcas(), key=lambda x: x["Label"])
        ]

    def _familia_para_modelo(self, cod_marca: int) -> dict[str, str]:
        """Mapa família→MODELO. Colapsa trims na 1ª palavra (FIT CX/DX → FIT),
        mas preserva modelos compostos reais: mesmo 2º nome em todo o grupo
        (GRAND SIENA) ou 2º nome sub-modelo (Corolla CROSS, Onix PLUS)."""
        if cod_marca in self._modmap:
            return self._modmap[cod_marca]
        fams = {familia_do_label(m["Label"]) for m in self._get_modelos(cod_marca)}
        por_1a: dict[str, set] = {}
        for f in fams:
            por_1a.setdefault(f.split()[0], set()).add(f)

        f2m: dict[str, str] = {}
        for primeira, grupo in por_1a.items():
            segundos = {f.split()[1] for f in grupo if len(f.split()) > 1}
            todos_compostos = all(len(f.split()) > 1 for f in grupo)
            for f in grupo:
                partes = f.split()
                seg = partes[1] if len(partes) > 1 else ""
                if not seg:
                    f2m[f] = primeira
                elif seg in _SUBMODELOS:
                    f2m[f] = f"{primeira} {seg}"            # Corolla Cross, Onix Plus
                elif (len(segundos) == 1 and todos_compostos
                      and len(seg) >= 4 and seg not in _TRIM_WORDS):
                    f2m[f] = f"{primeira} {seg}"            # Grand Siena, PT Cruiser
                else:
                    f2m[f] = primeira                        # trim → colapsa
        self._modmap[cod_marca] = f2m
        return f2m

    def modelos_familias(self, cod_marca: int) -> list[str]:
        """Apenas os MODELOS (ex.: FIT, CIVIC, HR-V, COROLLA, COROLLA CROSS) — sem trims."""
        return sorted(set(self._familia_para_modelo(cod_marca).values()))

    def versoes(self, cod_marca: int, modelo: str) -> list[dict]:
        """[{codigo, nome}] de todas as versões cujo MODELO é o selecionado."""
        f2m = self._familia_para_modelo(cod_marca)
        alvo = _norm(modelo)
        out = []
        for m in self._get_modelos(cod_marca):
            if _norm(f2m.get(familia_do_label(m["Label"]), "")) == alvo:
                out.append({"codigo": str(m["Value"]), "nome": m["Label"]})
        return out


def familia_do_label(label: str) -> str:
    """Família do modelo = palavras-nome iniciais até a cilindrada/versão.

    Pega as palavras antes do 1º token com dígito, preservando modelos compostos
    que os portais nomeiam por inteiro:
      'GRAND SIENA 1.4 Flex'      → 'GRAND SIENA'   (slug grand-siena)
      'COROLLA CROSS 1.8 Hybrid'  → 'COROLLA CROSS' (slug corolla-cross)
      'T-Cross 1.0 200 TSI'       → 'T-CROSS'
      'ARGO 1.0 6V Flex'          → 'ARGO'
      'HB20 1.0 ...'              → 'HB20' (1º token já tem dígito → fallback)
    """
    toks = label.split()
    nome = [t for t in _ate_digito(toks)][:2]  # no máx 2 palavras (colapsa trims)
    return " ".join(nome).upper() if nome else (toks[0].upper() if toks else label)


def _ate_digito(toks: list[str]):
    for t in toks:
        if any(c.isdigit() for c in t):
            return
        yield t


# Singleton reaproveitado entre requisições da API (mantém os caches de marca/modelo).
_singleton: "FipeClient | None" = None


def get_fipe_client() -> "FipeClient":
    global _singleton
    if _singleton is None:
        _singleton = FipeClient()
    return _singleton


def _parse_valor(valor: str | None) -> int | None:
    """'R$ 87.010,00' -> 87010 (reais inteiros)."""
    if not valor:
        return None
    inteiro = valor.split(",")[0]
    digits = re.sub(r"[^\d]", "", inteiro)
    return int(digits) if digits else None


def valor_fipe(
    db: Session,
    marca: str | None,
    modelo: str | None,
    ano: int | None,
    versao: str | None = None,
    client: FipeClient | None = None,
) -> int | None:
    """Valor FIPE (reais inteiros) com cache mensal. None se não resolver.

    Reaproveita um FipeClient se fornecido (1 conexão p/ toda a varredura).
    """
    if not (marca and ano):
        return None

    ref = datetime.now(timezone.utc).strftime("%Y-%m")
    modelo_key = modelo or ""  # chave consistente (evita == NULL no SQL)
    cache = db.scalar(
        select(FipeCache).where(
            FipeCache.marca == marca, FipeCache.modelo == modelo_key,
            FipeCache.ano == ano, FipeCache.ref_mes == ref,
        )
    )
    if cache:
        return cache.valor

    own = client is None
    fc = client or FipeClient()
    try:
        valor, codigo = fc.resolver(marca, modelo, ano, versao)
    finally:
        if own:
            fc.close()

    db.add(FipeCache(codigo_fipe=codigo, marca=marca, modelo=modelo_key, ano=ano,
                     valor=valor, ref_mes=ref, atualizado_em=datetime.now(timezone.utc)))
    db.commit()
    return valor
