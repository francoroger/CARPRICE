import httpx, re, json

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Accept-Language": "pt-BR"}
with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
    r = c.get("https://www.mobiauto.com.br/comprar/carros")
m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
res = json.loads(m.group(1))["props"]["pageProps"]["deals"]["results"]
print("total results:", len(res))
r0 = res[0]
for k, v in r0.items():
    print(f"   {k:24} = {str(v)[:80]}")
