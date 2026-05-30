# Descoberta: testa varios portais BR de carro e classifica acessibilidade via httpx puro.
# Criterio: status 200 + precos (R$) e km no HTML CRU => SSR scrap-facil (Nivel 1).
# status 200 mas SEM precos no HTML cru => provavel SPA (precisa achar API JSON).
# 403/blok => anti-bot.
import httpx, re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# (nome, lista de URLs candidatas de pagina de listagem)
CANDIDATOS = [
    ("iCarros",            ["https://www.icarros.com.br/ache/carros.jsp",
                            "https://www.icarros.com.br/comprar/carros"]),
    ("Mobiauto",           ["https://www.mobiauto.com.br/comprar/carros"]),
    ("Chaves na Mao",      ["https://www.chavesnamao.com.br/carros/",
                            "https://www.chavesnamao.com.br/veiculos/sp/"]),
    ("Napista",            ["https://napista.com.br/busca"]),
    ("Meu Carro Novo",     ["https://www.meucarronovo.com.br/carros"]),
    ("Usados BR",          ["https://www.usadosbr.com/carros"]),
    ("Carros na Web",      ["https://www.carrosnaweb.com.br/listapaginar.asp"]),
    ("Movida Seminovos",   ["https://seminovos.movida.com.br/carros"]),
    ("Unidas Seminovos",   ["https://seminovos.unidas.com.br/carros",
                            "https://www.unidasseminovos.com.br/carros"]),
    ("OLX Autos",          ["https://www.olx.com.br/autos-e-pecas/carros-vans-e-utilitarios/estado-sp"]),
    ("Autoarremate",       ["https://www.autoarremate.com.br/"]),
    ("Sou Carro",          ["https://www.soucarro.com.br/carros"]),
]

def classificar(precos, km, status, kb):
    if status in (403, 401, 429) or (status == 200 and kb < 5):
        return "ANTI-BOT/bloqueio"
    if status != 200:
        return f"HTTP {status}"
    if precos >= 5 and km >= 3:
        return "SSR FACIL (Nivel 1)"
    if precos >= 5:
        return "SSR parcial (precos sim, km nao)"
    return "SPA? (sem dados no HTML cru -> precisa API)"

with httpx.Client(headers=HEADERS, timeout=25, follow_redirects=True) as c:
    print(f"{'PORTAL':18} {'STATUS':7} {'KB':>5} {'R$':>5} {'km':>5}  VEREDITO")
    print("-" * 78)
    for nome, urls in CANDIDATOS:
        best = None
        for url in urls:
            try:
                r = c.get(url)
                precos = len(re.findall(r"R\$\s*[\d\.]{3,}", r.text))
                kms = len(re.findall(r"\b[\d\.]{2,}\s*km\b", r.text, re.IGNORECASE))
                kb = len(r.text) // 1024
                cand = (r.status_code, kb, precos, kms, str(r.url))
                # escolhe a URL com mais precos
                if best is None or precos > best[2]:
                    best = cand
                if precos >= 5:
                    break
            except Exception as e:
                if best is None:
                    best = (f"ERR:{type(e).__name__}", 0, 0, 0, url)
        status, kb, precos, kms, finalurl = best
        veredito = classificar(precos, kms, status if isinstance(status, int) else -1, kb)
        print(f"{nome:18} {str(status):7} {kb:>5} {precos:>5} {kms:>5}  {veredito}")
