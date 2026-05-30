"""Inspeciona __NEXT_DATA__ de Localiza e Mobiauto procurando o array de anúncios."""
import httpx, re, json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
ALVOS = {
    "Localiza": "https://seminovos.localiza.com/carros/sp-sao-paulo",
    "Mobiauto": "https://www.mobiauto.com.br/comprar/carros",
}

def achar_listas(obj, caminho="props"):
    """Caminha no JSON e reporta arrays grandes de dicts (candidatos a anúncios)."""
    achados = []
    def walk(o, path):
        if isinstance(o, list):
            if len(o) >= 5 and isinstance(o[0], dict):
                achados.append((path, len(o), list(o[0].keys())[:12]))
            for i, v in enumerate(o[:1]):
                walk(v, f"{path}[0]")
        elif isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{path}.{k}")
    walk(obj, caminho)
    return achados

with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
    for nome, url in ALVOS.items():
        print(f"\n########## {nome} ##########")
        r = c.get(url)
        m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
        if not m:
            print("  sem __NEXT_DATA__"); continue
        data = json.loads(m.group(1))
        props = data.get("props", {})
        listas = achar_listas(props)
        # ordena por tamanho
        listas.sort(key=lambda x: -x[1])
        for path, n, keys in listas[:6]:
            print(f"  [{n:>3} itens] {path}")
            print(f"        keys: {keys}")
