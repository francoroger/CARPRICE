# Recon dos 3 portais restantes: acha container de card e dumpa amostra de 1 card.
import httpx, re
from bs4 import BeautifulSoup
from collections import Counter

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

ALVOS = {
    "Napista":   ["https://napista.com.br/busca",
                  "https://napista.com.br/carros"],
    "Localiza":  ["https://seminovos.localiza.com/carros/sp-sao-paulo",
                  "https://seminovos.localiza.com/carros"],
    "Comprecar": ["https://www.comprecar.com.br/carros-usados/sao-paulo",
                  "https://www.comprecar.com.br/carros-usados",
                  "https://www.comprecar.com.br/busca"],
}

def achar_cards(soup):
    cont = Counter()
    exemplos = {}
    for el in soup.find_all(["article", "li", "div", "a"]):
        t = el.get_text(" ", strip=True)
        if "R$" in t and re.search(r"\d[\d\.]*\s*km", t, re.I) and 25 < len(t) < 400:
            key = " ".join(el.get("class", [])) or el.name
            cont[key] += 1
            exemplos.setdefault(key, el)
    return cont, exemplos

with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
    for nome, urls in ALVOS.items():
        print(f"\n########## {nome} ##########")
        for url in urls:
            try:
                r = c.get(url)
                soup = BeautifulSoup(r.text, "lxml")
                cont, ex = achar_cards(soup)
                print(f"  {url}\n    status {r.status_code} | {len(r.text)//1024}KB | final {str(r.url)[:60]}")
                if cont:
                    for cls, n in cont.most_common(3):
                        print(f"      {n:>3}x  .{cls[:55]}")
                    # dumpa o melhor exemplo
                    best = cont.most_common(1)[0][0]
                    el = ex[best]
                    a = el.find("a", href=True)
                    print(f"      EXEMPLO ({best[:40]}):")
                    print(f"        link: {(a['href'] if a else None)!s:.70}")
                    print(f"        texto: {el.get_text(' ', strip=True)[:160]}")
                    break
                else:
                    print("      (sem cards R$+km no HTML cru)")
            except Exception as e:
                print(f"  {url}\n    ERRO: {type(e).__name__}: {e}")
