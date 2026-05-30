# Spike Webmotors: tenta a API JSON interna com "aquecimento de sessao" (Nivel 2)
import httpx, json

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

API = "https://www.webmotors.com.br/api/search/car"
PARAMS = {
    "url": "https://www.webmotors.com.br/carros/estoque?marca1=TOYOTA&modelo1=COROLLA",
    "actualPage": 1,
    "displayPerPage": 24,
    "order": 1,
    "showMenu": "true",
    "showCount": "true",
    "showBreadCrumb": "true",
    "testAB": "false",
    "returnUrl": "false",
}

def try_level(name, headers, prime=False):
    print(f"\n=== {name} ===")
    with httpx.Client(headers=headers, timeout=30, follow_redirects=True,
                      http2=True) as c:
        if prime:
            h = c.get("https://www.webmotors.com.br/carros/estoque")
            print(f"  priming home: {h.status_code} (cookies: {len(c.cookies)})")
        try:
            r = c.get(API, params=PARAMS)
            print(f"  API status: {r.status_code} | content-type: {r.headers.get('content-type','?')[:40]}")
            if r.status_code == 200 and "json" in r.headers.get("content-type", ""):
                data = r.json()
                results = data.get("SearchResults") or data.get("searchResults") or []
                print(f"  >>> SUCESSO: {len(results)} resultados no JSON")
                if results:
                    s = results[0]
                    # campos variam; mostra chaves de topo
                    print("  chaves do 1o resultado:", list(s.keys())[:12])
                    print("  amostra:", json.dumps(s, ensure_ascii=False)[:400])
                return True
            else:
                print(f"  corpo (inicio): {r.text[:160]!r}")
        except Exception as e:
            print(f"  ERRO: {type(e).__name__}: {e}")
    return False

# Nivel 1: header minimo (esperado 403)
try_level("NIVEL 1 - httpx cru", {"User-Agent": UA})

# Nivel 2: headers de navegador + aquecimento de sessao + Accept json + Referer
h2 = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Referer": "https://www.webmotors.com.br/carros/estoque",
    "Origin": "https://www.webmotors.com.br",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}
try_level("NIVEL 2 - headers completos + sessao aquecida", h2, prime=True)
