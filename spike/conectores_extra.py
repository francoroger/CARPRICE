# Parsers Napista, Comprecar e Localiza (Nivel 1, httpx puro).
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

def precos_todos(t):
    """retorna lista de precos em R$ no texto (em reais inteiros)"""
    out = []
    for m in re.finditer(r"R\$\s*([\d\.]+)(?:,\d{2})?", t):
        v = num(m.group(1))
        if v and v > 1000:
            out.append(v)
    return out

def extrai_km(t):
    # pega numeros adjacentes a "km" (antes OU depois) e escolhe o maior plausivel
    cands = []
    for m in re.finditer(r"([\d\.]+)\s*km\b", t, re.I):
        cands.append(num(m.group(1)))
    for m in re.finditer(r"\bkm\s*:?\s*([\d\.]+)", t, re.I):
        cands.append(num(m.group(1)))
    cands = [k for k in cands if k is not None]
    return max(cands) if cands else None

def campos(t):
    precos = precos_todos(t)
    ano = re.search(r"\b(20[0-2]\d|19\d{2})\s*/\s*(20[0-2]\d)\b|\b(20[0-2]\d|19\d{2})\b", t)
    return {
        "preco": precos[-1] if precos else None,      # ultimo R$ = preco final ("por")
        "km": extrai_km(t),
        "ano": num((ano.group(2) or ano.group(0))[:4]) if ano else None,
    }

def base(host):
    return lambda h: (host + h) if h and h.startswith("/") else h

# fragmentos que identificam o link do ANUNCIO (nao logo/botao)
LINK_HINTS = ("/anuncios/", "/detalhes-carro/", "/comprar/", "/carros-usados/", "/veiculo")

def melhor_link(card):
    # o proprio elemento e um <a>?
    if card.name == "a" and card.get("href"):
        return card["href"]
    for a in card.find_all("a", href=True):
        if any(h in a["href"] for h in LINK_HINTS):
            return a["href"]
    a = card.find("a", href=True)
    if a:
        return a["href"]
    # link num ancestral <a> que envolve o card
    anc = card.find_parent("a", href=True)
    return anc["href"] if anc else None

def parse(url, selector, host, titulo_corte=70, sobe_para_card=False):
    abs_link = base(host)
    out, seen = [], set()
    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
        r = c.get(url)
        soup = BeautifulSoup(r.text, "lxml")
        elems = soup.select(selector)
        for el in elems:
            # Localiza: el e o <a>; sobe ate um ancestral que tenha R$
            card = el
            if sobe_para_card:
                anc = el
                for _ in range(5):
                    if anc.parent is None:
                        break
                    anc = anc.parent
                    if "R$" in anc.get_text():
                        card = anc
                        break
            t = card.get_text(" ", strip=True)
            if "R$" not in t:
                continue
            href = melhor_link(card)
            link = abs_link(href)
            if link in seen:
                continue
            seen.add(link)
            f = campos(t)
            if not f["preco"]:
                continue
            out.append({"titulo": t[:titulo_corte], "link": link, **f})
        print(f"  status {r.status_code} | {len(elems)} elems | {len(out)} unicos com preco")
    return out

CONFIG = {
    "Napista":   ("https://napista.com.br/busca",
                  "a[href*='/anuncios/']", "https://napista.com.br", False),
    "Comprecar": ("https://www.comprecar.com.br/carros-usados/sao-paulo",
                  ".card.vehicle", "https://www.comprecar.com.br", False),
    "Localiza":  ("https://seminovos.localiza.com/carros/sp-sao-paulo",
                  "a[href*='/detalhes-carro/']", "https://seminovos.localiza.com", True),
}

if __name__ == "__main__":
    todos = {}
    for nome, (url, sel, host, sobe) in CONFIG.items():
        print(f"\n### {nome} ### {url}")
        try:
            itens = parse(url, sel, host, sobe_para_card=sobe)
            todos[nome] = itens
            for it in itens[:6]:
                print(f"  - R$ {it['preco']!s:>8} | {it['km']!s:>7} km | {it['ano']} | {it['titulo'][:55]}")
        except Exception as e:
            print(f"  ERRO: {type(e).__name__}: {e}")
    with open("C:/Users/roger/CAR PRICE/spike/extra_amostra.json", "w", encoding="utf-8") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)
    print("\nresumo:", {k: len(v) for k, v in todos.items()})
