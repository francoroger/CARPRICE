# Acha a URL de listagem real do iCarros e inspeciona a estrutura dos cards.
import httpx, re
from bs4 import BeautifulSoup
from collections import Counter

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

CANDIDATOS = [
    "https://www.icarros.com.br/ache/listaanuncios.jsp",
    "https://www.icarros.com.br/ache/listaanuncios.jsp?fkMarca=&fkModelo=&pas=0",
    "https://www.icarros.com.br/comprar/carros/sao-paulo-sp",
    "https://www.icarros.com.br/ache/carros.jsp?lkid=20&sop-340=true",
    "https://www.icarros.com.br/comprar/usados/carros/sp-sao-paulo",
]

def probe(c, url):
    r = c.get(url)
    soup = BeautifulSoup(r.text, "lxml")
    precos = len(re.findall(r"R\$\s*[\d\.]{4,}", r.text))
    kms = len(re.findall(r"\b[\d\.]{2,}\s*km\b", r.text, re.I))
    # acha containers que tenham R$ E km juntos (cards de anuncio)
    cont = Counter()
    for el in soup.find_all(["article", "li", "div", "a"]):
        t = el.get_text(" ", strip=True)
        if "R$" in t and re.search(r"\d[\d\.]*\s*km", t, re.I) and 30 < len(t) < 350:
            cont[" ".join(el.get("class", [])) or el.name] += 1
    return r.status_code, str(r.url), len(r.text)//1024, precos, kms, cont

with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
    for url in CANDIDATOS:
        try:
            st, final, kb, p, k, cont = probe(c, url)
            redir = "->REDIR" if final.rstrip("/") != url.split("?")[0].rstrip("/") and "index" in final else ""
            print(f"\n{url}")
            print(f"  status {st} | {kb}KB | {p} R$ | {k} km | final: {final[:70]} {redir}")
            for cls, n in cont.most_common(4):
                print(f"     card? {n:>3}x  .{cls[:55]}")
        except Exception as e:
            print(f"\n{url}\n  ERRO: {type(e).__name__}: {e}")
