# Recon: baixa uma pagina de busca do CarroSP e mostra a estrutura
import httpx
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

URL = "https://www.carrosp.com.br/carros/sao-paulo-sp/"

with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
    r = c.get(URL)
    print("STATUS:", r.status_code, "| len:", len(r.text), "| final url:", str(r.url))
    soup = BeautifulSoup(r.text, "lxml")

    # heuristica: procurar blocos de anuncio. tentamos varios seletores comuns.
    print("\n--- procurando containers de anuncio ---")
    for sel in ["div.box-veiculo", "div.veiculo", "article", "div.card", "li.veiculo",
                "div.anuncio", "a[href*='/carros/']", "div[class*='veiculo']",
                "div[class*='card']", "div[class*='produto']", "div[class*='item']"]:
        found = soup.select(sel)
        if found:
            print(f"{sel}: {len(found)} elementos")

    # mostra os primeiros links que parecem ficha de carro
    print("\n--- amostra de links de carro ---")
    seen = 0
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "/carros/" in href and any(ch.isdigit() for ch in href):
            print(repr(href[:90]), "|", a.get_text(strip=True)[:60])
            seen += 1
            if seen >= 8:
                break
