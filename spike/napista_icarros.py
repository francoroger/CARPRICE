import re, httpx
from bs4 import BeautifulSoup
from collections import Counter

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Accept-Language": "pt-BR"}
c = httpx.Client(headers=H, follow_redirects=True, timeout=30)

print("===== Napista /busca/hyundai/hb20 paginado =====")
prev = None
for pn in [1, 2, 3, 8]:
    u = f"https://napista.com.br/busca/hyundai/hb20" + (f"?pn={pn}" if pn > 1 else "")
    r = c.get(u)
    cards = BeautifulSoup(r.text, "lxml").select("a[href*='/anuncios/']")
    ids = [a["href"] for a in cards]
    hb = sum(1 for a in cards if "hb20" in a.get_text(" ", strip=True).lower())
    print(f"  pn={pn}: {len(cards)} cards, {hb} hb20, dif={set(ids)!=set(prev) if prev else '-'}")
    prev = ids

print("\n===== iCarros filtrado: achar container real dos HB20 =====")
u = "https://www.icarros.com.br/comprar/usados/carros/hyundai/hb20/sp-sao-paulo"
r = c.get(u)
soup = BeautifulSoup(r.text, "lxml")
# acha elementos cujo texto tenha 'hb20' E preço
cont = Counter()
for el in soup.find_all(["article", "li", "div", "a"]):
    t = el.get_text(" ", strip=True).lower()
    if "hb20" in t and "r$" in t and 20 < len(t) < 400:
        cont[" ".join(el.get("class", [])) or el.name] += 1
for cls, n in cont.most_common(6):
    print(f"  {n:>3}x  .{cls[:55]}")
# pagina ?pag=2 muda?
ids1 = [a.get("href") for a in soup.select("a[href*='/comprar/']")][:5]
r2 = c.get(u + "?pag=2")
ids2 = [a.get("href") for a in BeautifulSoup(r2.text, "lxml").select("a[href*='/comprar/']")][:5]
print("  ?pag=2 muda?", ids1 != ids2)
c.close()
