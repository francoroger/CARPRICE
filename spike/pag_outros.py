"""Descobre paginação + filtro por modelo de Napista, iCarros, Comprecar."""
import re, httpx
from bs4 import BeautifulSoup

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
     "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "Accept-Language": "pt-BR"}
c = httpx.Client(headers=H, follow_redirects=True, timeout=30)


def cards_napista(html):
    return [a["href"] for a in BeautifulSoup(html, "lxml").select("a[href*='/anuncios/']")]

def cards_icarros(html):
    return [a.get("href") for a in BeautifulSoup(html, "lxml").select(".offer-card a[href]")]

def cards_comprecar(html):
    return [card.find("a", href=True)["href"] for card in
            BeautifulSoup(html, "lxml").select(".card.vehicle") if card.find("a", href=True)]


def testa(nome, urls, extrai):
    print(f"\n########## {nome} ##########")
    base_ids = None
    for label, u in urls:
        try:
            r = c.get(u)
            ids = extrai(r.text)
            first = ids[0][-30:] if ids else None
            dif = (set(ids) != set(base_ids)) if base_ids is not None else "-"
            # total?
            m = re.search(r'([\d\.]+)\s*(?:ve[ií]culos?|an[uú]ncios?|resultados?)', r.text, re.I)
            print(f"  [{label:16}] {r.status_code} | {len(ids)} cards | dif p/ base: {dif} "
                  f"| total~{m.group(1) if m else '?'} | {str(r.url)[-45:]}")
            if base_ids is None:
                base_ids = ids
        except Exception as e:
            print(f"  [{label:16}] ERRO {type(e).__name__}: {e}")


# Napista: ?pn=N (do print do usuário). Testar filtro marca/modelo tb.
testa("Napista", [
    ("base", "https://napista.com.br/busca/carro"),
    ("pn=2", "https://napista.com.br/busca/carro?pn=2"),
    ("pn=3", "https://napista.com.br/busca/carro?pn=3"),
    ("marca hyundai", "https://napista.com.br/busca/carro?marca=hyundai"),
], cards_napista)

# iCarros: ?pag=N / &pas=N ; filtro fkMarca/fkModelo
testa("iCarros", [
    ("base", "https://www.icarros.com.br/ache/listaanuncios.jsp"),
    ("pag=2", "https://www.icarros.com.br/ache/listaanuncios.jsp?pag=2"),
    ("pas=2", "https://www.icarros.com.br/ache/listaanuncios.jsp?pas=2"),
    ("pagina=2", "https://www.icarros.com.br/ache/listaanuncios.jsp?pagina=2"),
], cards_icarros)

# Comprecar: /carros-usados/{cidade}?pagina=N ou /pagina/N
testa("Comprecar", [
    ("base", "https://www.comprecar.com.br/carros-usados/sao-paulo"),
    ("?pagina=2", "https://www.comprecar.com.br/carros-usados/sao-paulo?pagina=2"),
    ("?page=2", "https://www.comprecar.com.br/carros-usados/sao-paulo?page=2"),
    ("?p=2", "https://www.comprecar.com.br/carros-usados/sao-paulo?p=2"),
], cards_comprecar)

c.close()
