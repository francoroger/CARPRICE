import httpx, re, json

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Accept-Language": "pt-BR"}

def next_data(url):
    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
        r = c.get(url)
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    return json.loads(m.group(1))

# ---- Localiza: campos completos de um product ----
print("########## LOCALIZA products[0] ##########")
d = next_data("https://seminovos.localiza.com/carros/sp-sao-paulo")
prods = d["props"]["pageProps"]["products"]
print("total:", len(prods))
p0 = prods[0]
for k, v in p0.items():
    sv = str(v)
    print(f"   {k:28} = {sv[:60]}")

# ---- Mobiauto: estrutura de deals ----
print("\n########## MOBIAUTO deals ##########")
d = next_data("https://www.mobiauto.com.br/comprar/carros")
deals = d["props"]["pageProps"]["deals"]
print("deals keys:", list(deals.keys()))
for k, v in deals.items():
    if isinstance(v, list):
        print(f"   deals.{k}: lista de {len(v)}")
        if v and isinstance(v[0], dict):
            print("      keys[0]:", list(v[0].keys())[:18])
