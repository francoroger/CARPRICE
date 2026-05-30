"""Cataloga TODOS os filtros do CarroSP: parâmetros de URL, selects, checkboxes e facetas."""
import httpx, re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
# página de busca com filtros (Honda HR-V em Limeira, como no print)
URL = ("https://www.carrosp.com.br/carros/limeira-sp/honda/hr-v"
       "?tipo_id=1&marca_id=32&modelo_id=3649&ano1=2024")

with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
    r = c.get(URL)
print("status:", r.status_code, "| url:", str(r.url)[:90])
soup = BeautifulSoup(r.text, "lxml")

# 1) Formulário(s) de filtro
print("\n===== FORMULÁRIOS =====")
for f in soup.find_all("form"):
    fid = f.get("id") or f.get("name")
    if fid and "busca" in (fid or "").lower():
        print("form:", fid, "| action:", f.get("action"))

# 2) SELECTS (dropdowns) — name + algumas opções
print("\n===== SELECTS (dropdowns) =====")
for s in soup.find_all("select"):
    name = s.get("name") or s.get("id")
    if not name:
        continue
    opts = [o.get_text(strip=True) for o in s.find_all("option")][:6]
    print(f"  {name:22} -> {opts}")

# 3) INPUTS (texto, hidden, checkbox, radio, range)
print("\n===== INPUTS =====")
vistos = set()
for i in soup.find_all("input"):
    name = i.get("name") or i.get("id")
    tipo = i.get("type", "text")
    if not name or name in vistos:
        continue
    vistos.add(name)
    print(f"  [{tipo:8}] {name}")

# 4) Facetas com contagem (Câmbio, Motorização, Cor...) — links com (n)
print("\n===== FACETAS (label + contagem) =====")
facetas = re.findall(r'([A-Za-zÀ-ú0-9\.\s]{2,30}?)\s*<\w+[^>]*>\s*(\d+)\s*</', r.text)
for label, n in facetas[:40]:
    lab = label.strip()
    if lab and not lab.isdigit() and len(lab) > 1:
        print(f"  {lab[:30]:30} ({n})")

# 5) Todos os parâmetros de URL conhecidos (extrai de hrefs de filtro)
print("\n===== PARÂMETROS DE URL nos links de filtro =====")
params = set()
for a in soup.find_all("a", href=True):
    for m in re.findall(r'[?&]([a-zA-Z_]+)=', a["href"]):
        params.add(m)
print(" ", sorted(params))
