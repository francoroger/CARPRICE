# Debug Napista: por que so 1 card unico? Inspeciona os links de cada card.
import httpx, re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}
with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
    r = c.get("https://napista.com.br/busca")
    soup = BeautifulSoup(r.text, "lxml")
    cards = soup.select(".styles_listingCard__TnL78")
    print("cards:", len(cards))
    for i, card in enumerate(cards[:6]):
        hrefs = [a["href"] for a in card.find_all("a", href=True)]
        anuncio = [h for h in hrefs if "/anuncios/" in h]
        t = card.get_text(" ", strip=True)
        tem_rs = "R$" in t
        print(f"\ncard {i}: tem_R$={tem_rs} | n_links={len(hrefs)} | anuncio_links={anuncio[:2]}")
        print("   texto:", t[:90])
    # talvez o link do anuncio esteja num ANCESTRAL <a> que envolve o card
    print("\n--- testando <a> ancestral ---")
    for i, card in enumerate(cards[:6]):
        anc = card.find_parent("a", href=True)
        print(f"card {i}: ancestral <a> = {anc['href'] if anc else None}")
