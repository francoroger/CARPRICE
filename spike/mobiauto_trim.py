import httpx, re, json

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Accept-Language": "pt-BR"}
with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
    r = c.get("https://www.mobiauto.com.br/comprar/carros")
m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
res = json.loads(m.group(1))["props"]["pageProps"]["deals"]["results"]
r0 = res[0]
print("=== trim ===")
print(json.dumps(r0["trim"], ensure_ascii=False, indent=1)[:900])
print("\n=== dealer ===")
print(json.dumps(r0["dealer"], ensure_ascii=False, indent=1)[:500])
print("\n=== campos url-like no result ===")
for k, v in r0.items():
    if isinstance(v, str) and ("/" in v or "url" in k.lower() or "slug" in k.lower()):
        print(f"   {k} = {v[:90]}")
