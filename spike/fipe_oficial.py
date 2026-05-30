"""Testa a API interna OFICIAL da FIPE (veiculos.fipe.org.br/api/veiculos).

Fluxo: tabela de referência -> marcas -> modelos -> ano-modelo -> valor.
"""
import httpx, json

BASE = "https://veiculos.fipe.org.br/api/veiculos"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://veiculos.fipe.org.br/",
    "Origin": "https://veiculos.fipe.org.br",
    "X-Requested-With": "XMLHttpRequest",
}

def post(path, payload):
    with httpx.Client(headers=HEADERS, timeout=20, http2=True) as c:
        r = c.post(f"{BASE}/{path}", json=payload)
        print(f"  POST {path}: {r.status_code} ({len(r.text)} bytes)")
        r.raise_for_status()
        return r.json()

# 1) tabela de referência (mês atual = primeiro)
tabelas = post("ConsultarTabelaDeReferencia", {})
ref = tabelas[0]
print("tabela ref atual:", ref)
cod_ref = ref["Codigo"]

# 2) marcas (tipo 1 = carro)
marcas = post("ConsultarMarcas", {"codigoTabelaReferencia": cod_ref, "codigoTipoVeiculo": 1})
print(f"marcas: {len(marcas)} | ex:", marcas[:2])
# acha Fiat
fiat = next(m for m in marcas if m["Label"].lower() == "fiat")
print("Fiat:", fiat)

# 3) modelos da Fiat
modelos = post("ConsultarModelos", {
    "codigoTabelaReferencia": cod_ref, "codigoTipoVeiculo": 1,
    "codigoMarca": fiat["Value"],
})
lista = modelos["Modelos"]
print(f"modelos Fiat: {len(lista)} | ex:", lista[:3])
# acha um Argo
argo = next((m for m in lista if "argo" in m["Label"].lower()), lista[0])
print("modelo escolhido:", argo)

# 4) ano-modelo
anos = post("ConsultarAnoModelo", {
    "codigoTabelaReferencia": cod_ref, "codigoTipoVeiculo": 1,
    "codigoMarca": fiat["Value"], "codigoModelo": argo["Value"],
})
print(f"anos: {len(anos)} | ex:", anos[:3])
ano = anos[0]  # ex {"Label":"2021 Gasolina","Value":"2021-1"}
ano_cod, comb = ano["Value"].split("-")

# 5) valor com todos os parâmetros
valor = post("ConsultarValorComTodosParametros", {
    "codigoTabelaReferencia": cod_ref, "codigoTipoVeiculo": 1,
    "codigoMarca": fiat["Value"], "codigoModelo": argo["Value"],
    "anoModelo": ano_cod, "codigoTipoCombustivel": int(comb),
    "tipoVeiculo": "carro", "modeloCodigoExterno": "", "tipoConsulta": "tradicional",
})
print("\n>>> VALOR FIPE:")
print(json.dumps(valor, ensure_ascii=False, indent=2))
