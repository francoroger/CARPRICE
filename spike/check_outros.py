# Confirma Nivel 1 (httpx puro) em Comprecar e Localiza Seminovos
import httpx, re
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

ALVOS = {
    "Comprecar (SP)": "https://www.comprecar.com.br/carros-usados/sao-paulo-sp",
    "Localiza Seminovos": "https://seminovos.localiza.com/carros/sp-sao-paulo",
}

with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as c:
    for nome, url in ALVOS.items():
        try:
            r = c.get(url)
            soup = BeautifulSoup(r.text, "lxml")
            precos = len(re.findall(r"R\$\s*[\d\.]{3,}", r.text))
            kms = len(re.findall(r"[\d\.]+\s*km", r.text, re.IGNORECASE))
            print(f"{nome:22} | status {r.status_code} | {len(r.text)//1024:>4} KB | "
                  f"~{precos} precos | ~{kms} km | url final: {str(r.url)[:55]}")
        except Exception as e:
            print(f"{nome:22} | ERRO: {type(e).__name__}: {e}")
