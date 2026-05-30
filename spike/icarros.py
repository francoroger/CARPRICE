# Conector iCarros (Nivel 1, httpx puro). Cards .offer-card.
import httpx, re, json
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def num(s):
    d = re.sub(r"[^\d]", "", s or "")
    return int(d) if d else None

def parse_card(card):
    t = card.get_text(" ", strip=True)
    a = card.find("a", href=True)
    link = a["href"] if a else None
    if link and link.startswith("/"):
        link = "https://www.icarros.com.br" + link

    titulo_el = card.select_one("[class*='title'], [class*='titulo'], h2, h3")
    titulo = titulo_el.get_text(" ", strip=True) if titulo_el else None

    preco = re.search(r"R\$\s*([\d\.]+)", t)
    km = re.search(r"([\d\.]+)\s*km", t, re.I)
    # ano-modelo formato 2019/2020 ou 2019
    ano = re.search(r"\b(20[0-2]\d|19\d{2})\s*/\s*(20[0-2]\d)\b|\b(20[0-2]\d|19\d{2})\b", t)
    img = card.find("img")
    foto = (img.get("src") or img.get("data-src")) if img else None

    return {
        "titulo": titulo,
        "preco": num(preco.group(1)) if preco else None,
        "km": num(km.group(1)) if km else None,
        "ano": num((ano.group(2) or ano.group(0))[:4]) if ano else None,
        "link": link,
        "foto": foto,
    }

def buscar(url):
    out = []
    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
        r = c.get(url)
        soup = BeautifulSoup(r.text, "lxml")
        cards = soup.select(".offer-card")
        # filtra os "small-offer-card" (recomendados) se quiser; aqui pega todos com preco
        for card in cards:
            item = parse_card(card)
            if item["preco"]:
                out.append(item)
        print(f"status {r.status_code} | {len(cards)} cards | {len(out)} com preco")
    return out

if __name__ == "__main__":
    URL = "https://www.icarros.com.br/comprar/usados/carros/sp-sao-paulo"
    print("iCarros:", URL)
    itens = buscar(URL)
    for it in itens[:10]:
        print(f"- {it['titulo']!s:42.42} | R$ {it['preco']!s:>8} | "
              f"{it['km']!s:>7} km | {it['ano']} | {str(it['link'])[:55]}")
    with open("C:/Users/roger/CAR PRICE/spike/icarros_amostra.json", "w", encoding="utf-8") as f:
        json.dump(itens, f, ensure_ascii=False, indent=2)
    print(f"\nSalvo {len(itens)} itens em icarros_amostra.json")
