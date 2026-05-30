# Recon 2: inspeciona a estrutura interna dos blocos de anuncio do CarroSP
import httpx, re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}
URL = "https://www.carrosp.com.br/carros/sao-paulo-sp/todos/"

with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
    r = c.get(URL)
    print("STATUS:", r.status_code, "| final:", str(r.url))
    soup = BeautifulSoup(r.text, "lxml")

    blocks = soup.select("div[class*='veiculo']")
    print("blocos veiculo:", len(blocks))
    # mostra classes distintas pra achar o container certo
    from collections import Counter
    cls = Counter(" ".join(b.get("class", [])) for b in blocks)
    print("classes:", dict(cls))

    # pega um bloco que tenha preco (R$) dentro
    for b in blocks:
        txt = b.get_text(" ", strip=True)
        if "R$" in txt:
            print("\n=== BLOCO COM PRECO ===")
            print("class:", b.get("class"))
            link = b.find("a", href=True)
            print("link:", link["href"] if link else None)
            print("texto:", txt[:300])
            # tenta achar campos
            print("imgs:", [i.get("src") or i.get("data-src") for i in b.find_all("img")][:2])
            break
