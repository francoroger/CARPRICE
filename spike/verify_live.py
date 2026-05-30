"""Verifica o site no ar (pricecar.netlify.app): responsivo + integração com o backend."""
from playwright.sync_api import sync_playwright

URL = "https://pricecar.netlify.app/"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    for nome, w, h in [("mobile", 390, 844), ("desktop", 1280, 800)]:
        ctx = b.new_context(viewport={"width": w, "height": h}, locale="pt-BR")
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3500)  # deixa as marcas carregarem do backend
        # marca dropdown populou? (prova que /api/fipe/marcas funcionou do browser)
        sel = page.query_selector("form select")
        nopt = page.eval_on_selector_all("form select option", "els=>els.length") if sel else 0
        # sem scroll horizontal? (responsivo)
        overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 2")
        print(f"[{nome} {w}x{h}] marcas_no_dropdown~{nopt} | scroll_horizontal={overflow}")
        page.screenshot(path=f"C:/Users/roger/CAR PRICE/spike/live_{nome}.png", full_page=False)
        ctx.close()
    b.close()
print("screenshots: spike/live_mobile.png, spike/live_desktop.png")
