"""Espia a rede do iCarros filtrado: acha a API JSON dos anúncios (ou o seletor renderizado)."""
from playwright.sync_api import sync_playwright

URL = "https://www.icarros.com.br/comprar/usados/carros/hyundai/hb20/sp-sao-paulo"
apis = []

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(locale="pt-BR", user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"))
    page = ctx.new_page()

    def on_resp(r):
        ct = r.headers.get("content-type", "")
        if "json" in ct and any(k in r.url.lower() for k in
                                ("anuncio", "oferta", "veiculo", "search", "busca", "listagem", "api", "result")):
            apis.append((r.status, r.url[:130]))

    page.on("response", on_resp)
    page.goto(URL, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(2500)

    print("status pagina:", page.title()[:60])
    # conta cards renderizados + acha seletor
    for sel in [".offer-card", "[class*='ResultCard']", "[data-testid*='card']",
                "article", "[class*='anuncio']", "a[href*='/comprar/']"]:
        n = page.eval_on_selector_all(sel, "els=>els.length")
        if n:
            print(f"  render sel {sel}: {n}")
    # texto do 1º card que tenha HB20
    txt = page.eval_on_selector_all("*", """els => {
      for (const e of els) { const t=e.innerText||''; if (t.toLowerCase().includes('hb20') && t.includes('R$') && t.length<300) return {cls:e.className, tag:e.tagName, txt:t.slice(0,120)}; }
      return null; }""")
    print("  card HB20 exemplo:", txt)

    ctx.close(); b.close()

print("\n=== APIs JSON capturadas ===")
for st, u in dict.fromkeys(apis):
    print(f"  {st}  {u}")
if not apis:
    print("  (nenhuma API JSON óbvia — provável render via JS sem endpoint isolado)")
