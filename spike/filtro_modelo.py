"""Descobre como filtrar por modelo (Hyundai HB20) em iCarros, Napista, Comprecar
e a paginação do Comprecar."""
import re, httpx
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Accept-Language": "pt-BR"}
c = httpx.Client(headers=H, follow_redirects=True, timeout=30)

def conta_modelo(html, termo, sel):
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(sel)
    n_termo = sum(1 for card in cards if termo in card.get_text(" ", strip=True).lower())
    return len(cards), n_termo

print("===== iCarros: URLs de modelo HB20 =====")
for u in [
    "https://www.icarros.com.br/comprar/usados/carros/hyundai/hb20/sp-sao-paulo",
    "https://www.icarros.com.br/comprar/usados/carros/sp-sao-paulo/hyundai/hb20",
    "https://www.icarros.com.br/ache/carrosusados.jsp?fkMarca=24&fkModelo=181",
]:
    try:
        r = c.get(u)
        tot, nh = conta_modelo(r.text, "hb20", ".offer-card")
        m = re.search(r'([\d\.]+)\s*(?:ve[ií]culos?|an[uú]ncios?|ofertas?|resultados?)', r.text, re.I)
        print(f"  {tot} cards, {nh} c/ hb20 | total~{m.group(1) if m else '?'} | {str(r.url)[-55:]}")
    except Exception as e:
        print(f"  ERRO {e} | {u[-40:]}")

print("\n===== Napista: filtro de modelo =====")
for u in [
    "https://napista.com.br/busca/carro/hyundai/hb20",
    "https://napista.com.br/busca/carro?marca=hyundai&modelo=hb20",
    "https://napista.com.br/hyundai/hb20",
]:
    try:
        r = c.get(u)
        tot, nh = conta_modelo(r.text, "hb20", "a[href*='/anuncios/']")
        print(f"  {tot} cards, {nh} c/ hb20 | {str(r.url)[-50:]}")
    except Exception as e:
        print(f"  ERRO {e} | {u[-40:]}")

print("\n===== Comprecar: modelo + paginação =====")
for u in [
    "https://www.comprecar.com.br/carros-usados/sao-paulo/hyundai/hb20",
    "https://www.comprecar.com.br/carros-usados/sao-paulo?marca=hyundai&modelo=hb20",
    "https://www.comprecar.com.br/carros-usados/sao-paulo/2",
    "https://www.comprecar.com.br/carros-usados/sao-paulo/pagina/2",
]:
    try:
        r = c.get(u)
        tot, nh = conta_modelo(r.text, "hb20", ".card.vehicle")
        ids = [card.find("a", href=True)["href"][-25:] for card in
               BeautifulSoup(r.text, "lxml").select(".card.vehicle")[:2] if card.find("a", href=True)]
        print(f"  {tot} cards, {nh} c/ hb20 | 1os ids {ids} | {str(r.url)[-48:]}")
    except Exception as e:
        print(f"  ERRO {e} | {u[-40:]}")
c.close()
