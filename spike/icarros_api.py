"""Captura a API de LISTAGEM do iCarros (array de anúncios) e seu formato."""
import json
from playwright.sync_api import sync_playwright

# página de localização (tem anúncios reais) — capturamos a API que popula a lista
URL = "https://www.icarros.com.br/comprar/usados/carros/sp-sao-paulo"
capturas = []

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(locale="pt-BR", user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"))
    page = ctx.new_page()

    def on_resp(r):
        ct = r.headers.get("content-type", "")
        if "json" not in ct:
            return
        try:
            data = r.json()
        except Exception:
            return
        # procura array de anúncios (lista de dicts com preço/ano/modelo)
        def acha(o, path="root"):
            if isinstance(o, list) and len(o) >= 5 and isinstance(o[0], dict):
                ks = set(o[0].keys())
                if ks & {"preco", "price", "valor", "anoModelo", "ano", "modelo", "model"}:
                    capturas.append((r.url[:120], path, len(o), list(o[0].keys())[:14]))
            elif isinstance(o, dict):
                for k, v in o.items():
                    acha(v, f"{path}.{k}")
        acha(data)

    page.on("response", on_resp)
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)
    # rola a página pra disparar carregamento de mais anúncios
    for _ in range(3):
        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(1500)
    ctx.close(); b.close()

print("=== APIs com array de anúncios ===")
for url, path, n, keys in dict.fromkeys((c[0], c[1], c[2], tuple(c[3])) for c in capturas):
    print(f"\n  {n} itens em {path}")
    print(f"  URL: {url}")
    print(f"  keys: {list(keys)}")
if not capturas:
    print("  (nenhuma — listagem pode vir via outro mecanismo)")
