import httpx, re

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
t = httpx.get("https://www.mobiauto.com.br/comprar/carros", headers=HEADERS,
              follow_redirects=True, timeout=30).text

por_id = re.findall(r'href="(/comprar/[^"]*29122015[^"]*)"', t)
print("links com o id 29122015:", por_id[:3])

amostra = re.findall(r'href="(/comprar/carro/[^"]+)"', t)
print("amostra /comprar/carro/:")
for x in amostra[:5]:
    print("  ", x)
