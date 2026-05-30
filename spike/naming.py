"""Mapeia como CADA portal nomeia marca/modelo (texto do anúncio + slug da URL).

Casos difíceis: VW/Volkswagen, GM/Chevrolet, Citroën (acento), Mercedes-Benz (hífen),
e modelos compostos (Grand Siena, Corolla Cross, T-Cross).
"""
import re, json, httpx
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Accept-Language": "pt-BR"}
c = httpx.Client(headers=H, follow_redirects=True, timeout=30)

# (marca_canonica, modelo) — variando dificuldade
CASOS = [
    ("Volkswagen", "T-Cross"),
    ("Chevrolet", "Onix"),
    ("Citroen", "C3"),
    ("Mercedes-Benz", "Classe A"),
    ("Fiat", "Grand Siena"),
    ("Toyota", "Corolla Cross"),
]

def sl(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def carrosp(marca, modelo):
    u = f"https://www.carrosp.com.br/carros/sao-paulo-sp/{sl(marca)}/{sl(modelo)}/"
    r = c.get(u)
    soup = BeautifulSoup(r.text, "lxml")
    cards = soup.select("div.veiculo-item")
    # marca/modelo vêm do path do link do anúncio
    ex = None
    for card in cards[:1]:
        a = card.find("a", href=True)
        if a:
            parts = [p for p in a["href"].split("/") if p]
            ex = "/".join(parts[parts.index("comprar")+1:parts.index("comprar")+4]) if "comprar" in parts else a["href"][:50]
    m = re.search(r'([\d\.]+)\s*ve[ií]culos', r.text, re.I)
    return f"url={sl(marca)}/{sl(modelo)} status={r.status_code} cards={len(cards)} total={m.group(1) if m else '?'} ex_path={ex}"

def napista(marca, modelo):
    u = f"https://napista.com.br/busca/{sl(marca)}/{sl(modelo)}"
    r = c.get(u)
    cards = BeautifulSoup(r.text, "lxml").select("a[href*='/anuncios/']")
    ex = cards[0].get_text(" ", strip=True)[:45] if cards else None
    return f"url={sl(marca)}/{sl(modelo)} cards={len(cards)} ex='{ex}'"

def nextdata(url, marca, modelo, path):
    r = c.get(url)
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        return "sem next_data"
    d = json.loads(m.group(1))
    arr = d.get("props", {}).get("pageProps", {})
    for k in path.split("."):
        arr = arr.get(k, {}) if isinstance(arr, dict) else {}
    arr = arr if isinstance(arr, list) else []
    return f"{len(arr)} itens"

for marca, modelo in CASOS:
    print(f"\n===== {marca} / {modelo} =====")
    try: print("  CarroSP :", carrosp(marca, modelo))
    except Exception as e: print("  CarroSP ERRO", e)
    try: print("  Napista :", napista(marca, modelo))
    except Exception as e: print("  Napista ERRO", e)

# Localiza/Mobiauto: como nomeiam a marca nos campos estruturados (genérico)
print("\n===== nomes de marca estruturados (Localiza / Mobiauto) =====")
r = c.get("https://seminovos.localiza.com/carros/sp-sao-paulo")
m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
prods = json.loads(m.group(1))["props"]["pageProps"].get("products", [])
print("  Localiza marcas:", sorted({p.get("marcaDescricao") for p in prods}))
print("  Localiza modelos(familia):", sorted({p.get("modeloFamiliaDescricao") for p in prods})[:8])
r = c.get("https://www.mobiauto.com.br/comprar/carros")
m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
res = json.loads(m.group(1))["props"]["pageProps"]["deals"]["results"]
print("  Mobiauto marcas:", sorted({d["trim"]["make"]["name"] for d in res if d.get("trim")}))
c.close()
