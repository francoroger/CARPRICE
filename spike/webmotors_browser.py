# Spike Webmotors NIVEL 3: navegador real (Playwright) capturando a API JSON interna.
# Deixa o Chromium fazer o handshake do PerimeterX e intercepta a resposta de /api/search/car.
import json
from playwright.sync_api import sync_playwright

ALVO = "https://www.webmotors.com.br/carros/estoque/toyota/corolla?tipoveiculo=carros&marca1=TOYOTA&modelo1=COROLLA"

capturado = {"listings": None, "status_api": None, "status_pagina": None}

def run():
    with sync_playwright() as p:
        launch_kwargs = dict(
            headless=False,
            args=["--disable-blink-features=AutomationControlled",
                  "--no-sandbox", "--start-maximized"],
        )
        try:
            browser = p.chromium.launch(channel="chrome", **launch_kwargs)
            print("usando Chrome real instalado")
        except Exception:
            browser = p.chromium.launch(**launch_kwargs)
            print("usando Chromium do Playwright")
        ctx = browser.new_context(
            locale="pt-BR",
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"),
            viewport={"width": 1366, "height": 768},
        )
        # mascara o navigator.webdriver (sinal classico de bot)
        ctx.add_init_script("""
            Object.defineProperty(navigator,'webdriver',{get:()=>undefined});
            Object.defineProperty(navigator,'languages',{get:()=>['pt-BR','pt','en']});
            Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
            window.chrome = {runtime:{}};
        """)
        page = ctx.new_page()

        def on_response(resp):
            if "/api/search/car" in resp.url:
                capturado["status_api"] = resp.status
                if resp.status == 200:
                    try:
                        data = resp.json()
                        res = data.get("SearchResults") or data.get("searchResults") or []
                        capturado["listings"] = res
                    except Exception as e:
                        capturado["listings"] = f"erro json: {e}"

        page.on("response", on_response)

        print("Navegando ...")
        r = page.goto(ALVO, wait_until="domcontentloaded", timeout=60000)
        capturado["status_pagina"] = r.status if r else None
        print("status da pagina:", capturado["status_pagina"])

        # espera a SPA disparar a chamada da API e renderizar os cards
        try:
            page.wait_for_selector("[class*='card'], [data-qa*='card'], a[href*='/comprar/']",
                                   timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(4000)

        # fallback: conta cards renderizados no DOM
        cards_dom = page.eval_on_selector_all(
            "a[href*='/comprar/'], [class*='card']", "els => els.length")
        print("cards no DOM:", cards_dom)
        print("titulo da pagina:", page.title()[:80])

        ctx.close()
        browser.close()

run()

print("\n=== RESULTADO ===")
print("status API /api/search/car:", capturado["status_api"])
lst = capturado["listings"]
if isinstance(lst, list):
    print(f">>> SUCESSO: {len(lst)} carros capturados via API interna (navegador real)")
    for s in lst[:5]:
        esp = s.get("Specification", {})
        seller = s.get("Seller", {})
        prices = s.get("Prices", {})
        print(f"  - {esp.get('Make',{}).get('value','?')} "
              f"{esp.get('Model',{}).get('value','?')} "
              f"{esp.get('Version',{}).get('value','?')[:30]} | "
              f"ano {esp.get('YearModel','?')} | "
              f"{esp.get('Odometer','?')} km | "
              f"R$ {prices.get('Price','?')} | {seller.get('City','?')}")
    with open("C:/Users/roger/CAR PRICE/spike/webmotors_amostra.json", "w", encoding="utf-8") as f:
        json.dump(lst, f, ensure_ascii=False, indent=2)
    print("  (amostra salva em webmotors_amostra.json)")
else:
    print("listings:", lst)
