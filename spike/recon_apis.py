"""Caça endpoints de API interna nos portais SPA (Localiza, Mobiauto, Unidas).

Procura no HTML: __NEXT_DATA__ (Next.js), URLs com /api|/v1|graphql|search|gateway,
e os bundles JS (pra inspecionar depois).
"""
import httpx, re, json
from collections import Counter

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

ALVOS = {
    "Localiza": "https://seminovos.localiza.com/carros/sp-sao-paulo",
    "Mobiauto": "https://www.mobiauto.com.br/comprar/carros",
    "Unidas":   "https://seminovos.unidas.com.br/carros",
}

API_PAT = re.compile(r'https?://[a-z0-9.\-]+(?:/[a-zA-Z0-9._\-/]*)?'
                     r'(?:api|/v\d|graphql|gateway|search|busca|estoque|veiculos|catalog)'
                     r'[a-zA-Z0-9._\-/]*', re.I)

with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
    for nome, url in ALVOS.items():
        print(f"\n########## {nome} ##########  {url}")
        try:
            r = c.get(url)
        except Exception as e:
            print("  ERRO:", e); continue
        html = r.text
        print(f"  status {r.status_code} | {len(html)//1024} KB")

        # Next.js?
        nxt = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if nxt:
            try:
                data = json.loads(nxt.group(1))
                print("  __NEXT_DATA__: sim | buildId:", data.get("buildId"))
                # procura apiUrl/baseUrl em runtimeConfig
                rc = json.dumps(data.get("runtimeConfig", {}) or data.get("props", {}))
                for m in set(re.findall(r'https?://[a-z0-9.\-]+', rc, re.I)):
                    if any(k in m for k in ("api", "gateway", "service")):
                        print("     host:", m)
            except Exception as e:
                print("  __NEXT_DATA__ parse falhou:", e)

        # URLs candidatas a API no HTML
        achados = Counter(m.lower() for m in API_PAT.findall(html))
        hosts = Counter(re.match(r'https?://[a-z0-9.\-]+', u).group(0) for u in achados)
        print("  hosts de API candidatos:")
        for h, n in hosts.most_common(6):
            print(f"     {n:>3}x  {h}")
        print("  amostra de URLs:")
        for u, _ in achados.most_common(6):
            print("     ", u[:100])

        # bundles JS (next/static/chunks) p/ inspecao posterior
        scripts = re.findall(r'<script[^>]+src="([^"]+\.js[^"]*)"', html)
        print(f"  scripts JS: {len(scripts)} | ex:", scripts[:2])
