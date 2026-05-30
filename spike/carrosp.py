# Spike CarroSP: extrai anuncios reais (titulo, preco, km, ano, cidade, link, foto)
import httpx, re, json
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

def num(s):
    """extrai numero de uma string tipo 'R$ 44.900' ou '85.000 km'"""
    if not s:
        return None
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else None

def parse_card(card):
    a = card.find("a", href=True)
    link = a["href"] if a else None
    if link and link.startswith("/"):
        link = "https://www.carrosp.com.br" + link

    txt = card.get_text(" ", strip=True)

    # titulo: costuma estar em h2/h3 ou no texto do link de info
    title_el = card.select_one("h2, h3, .veiculo-item-info a, [class*='titulo']")
    titulo = title_el.get_text(" ", strip=True) if title_el else None

    # preco
    preco = None
    m = re.search(r"R\$\s*([\d\.]+)", txt)
    if m:
        preco = num(m.group(1))

    # km
    km = None
    m = re.search(r"([\d\.]+)\s*km", txt, re.IGNORECASE)
    if m:
        km = num(m.group(1))

    # ano (formato 2014 ou 2014/2015)
    ano = None
    m = re.search(r"\b(19|20)\d{2}\s*/\s*(19|20)?\d{2}\b|\b(20[0-2]\d|19\d{2})\b", txt)
    if m:
        ano = num(m.group(0)[:4])

    # foto
    img = card.find("img")
    foto = (img.get("src") or img.get("data-src")) if img else None

    return {"titulo": titulo, "preco": preco, "km": km, "ano": ano,
            "cidade_uf": None, "link": link, "foto": foto}

def buscar(url, paginas=1):
    resultados = []
    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
        for p in range(1, paginas + 1):
            page_url = url if p == 1 else f"{url}?pagina={p}"
            r = c.get(page_url)
            soup = BeautifulSoup(r.text, "lxml")
            cards = soup.select("div.veiculo-item")
            for card in cards:
                item = parse_card(card)
                if item["preco"]:  # so conta anuncio com preco
                    resultados.append(item)
            print(f"  pagina {p}: status {r.status_code}, {len(cards)} cards, "
                  f"{sum(1 for c in cards if BeautifulSoup(str(c),'lxml'))} ok")
    return resultados

if __name__ == "__main__":
    URL = "https://www.carrosp.com.br/carros/sao-paulo-sp/todos/"
    print("Buscando em CarroSP:", URL)
    itens = buscar(URL, paginas=1)
    print(f"\nTOTAL com preco: {len(itens)}\n")
    for it in itens[:10]:
        print(f"- {it['titulo']!s:45.45} | R$ {it['preco']!s:>8} | "
              f"{it['km']!s:>7} km | {it['ano']} | {it['link']}")
    # salva amostra
    with open("C:/Users/roger/CAR PRICE/spike/carrosp_amostra.json", "w", encoding="utf-8") as f:
        json.dump(itens, f, ensure_ascii=False, indent=2)
    print(f"\nSalvo {len(itens)} itens em carrosp_amostra.json")
