# Arquitetura — CarPrice

Documento técnico de como o sistema funciona. Atualizado a cada alteração relevante
(ver [CHANGELOG.md](../CHANGELOG.md)).

## Visão geral

CarPrice acha o **melhor custo-benefício** em carros usados comparando **anúncios
idênticos** (mesma versão + ano), ajustando por quilometragem, com a **Tabela FIPE
oficial** como referência secundária. Tem duas experiências:

- **Busca** (ao vivo, tipo portal): entra em todos os portais na hora, traz os
  anúncios e ordena por preço. É consulta/navegação.
- **Ranking / Monitores**: análise de custo-benefício (score) e alertas automáticos.

```
┌────────────┐   /api    ┌─────────────────────────────┐   scraping   ┌──────────┐
│  Frontend  │ ────────▶ │  Backend FastAPI            │ ───────────▶ │ Portais  │
│ React+Vite │ ◀──────── │  (coleta, score, FIPE, API) │ ◀─────────── │ BR + FIPE│
│  (Netlify) │           │        (Render)             │              └──────────┘
└────────────┘           └─────────────┬───────────────┘
                                        │ SQLAlchemy
                                  ┌─────▼─────┐
                                  │ SQLite/PG │
                                  └───────────┘
```

## Backend (`/backend`, Python 3.12 / FastAPI)

### Coleta — motor de acesso em camadas (`app/collectors/`)
Cada portal é um **conector plugável** (`PortalConnector`) que só sabe montar a URL de
busca e **parsear** os anúncios. Quem busca é um **Fetcher** injetado, que encapsula o
nível de acesso:

| Nível | Como | Portais |
|---|---|---|
| 1 — HTTP | `httpx` + headers de navegador | CarroSP, Napista, Comprecar, iCarros, Localiza, Mobiauto |
| 2 — Sessão | httpx + cookies/token | (futuro: APIs de SPA) |
| 3 — Browser | Playwright + stealth | (futuro: iCarros filtrado, Webmotors) |
| 5 — Unblocker | API paga (anti-bot) | (futuro: Webmotors/OLX — PerimeterX) |

Os conectores **paginam** quando o portal permite: CarroSP `?page=N`, Napista
`?pn=N`. SSR via HTML (BeautifulSoup) ou via `__NEXT_DATA__` (Localiza, Mobiauto —
JSON estruturado já no HTML do servidor).

**Normalização** (`normalize.py`): `RawListing` → `vehicle_listings`, calculando
`grupo_chave` (versão + ano = "carros idênticos") e `hash_dedup`.

### Naming de marca/modelo (importante)
Cada fonte nomeia diferente. Normalizações:
- **Marca**: FIPE usa prefixo (`VW - VolksWagen`, `GM - Chevrolet`). `marca_canonica()`
  tira o prefixo → `Volkswagen`. Portais usam slug minúsculo (`volkswagen`,
  `mercedes-benz`); filtro compara sem espaço/acento.
- **Modelo**: portais usam o nome completo no slug (`grand-siena`, `t-cross`). A FIPE
  embute trim+versão. `familia_do_label` extrai o nome do modelo e `modelos_familias`
  faz **colapso por prefixo** (se existe "T-CROSS", então "T-CROSS COMFORTLINE" é
  *versão* dele, não modelo). Resultado: dropdown de Modelo só com modelos.

### Engine de score (`app/services/scoring.py`)
1. Agrupa por `grupo_chave` (versão + ano).
2. Segmenta por faixa de km.
3. `preco_ref` = **mediana** da faixa (≥ `min_grupo` anúncios → origem **MERCADO**).
4. Grupo pequeno → **fallback FIPE** (origem FIPE), conservador.
5. `desconto = (preco_ref - preco) / preco_ref`; `score = desconto + bônus de km`.
Parâmetros em `settings` (editáveis no painel).

### FIPE oficial (`app/services/fipe.py`)
Consome a API interna oficial `veiculos.fipe.org.br/api/veiculos`
(tabela de referência → marcas → modelos → ano → valor), com cache. Matching exige a
palavra-nome do modelo e escolhe a geração que tem o ano do carro. Rate-limit tratado.

**Catálogo estático** (`data/fipe_modelos.json`): marcas + modelos + **anos-modelo de
cada versão** embutidos no repo (a FIPE bloqueia IP de datacenter como o Render).
Gerado por `gen_fipe_catalog.py`/`gen_fipe_fill.py` (marcas/modelos) e `gen_fipe_anos.py`
(anos por versão, via `ConsultarAnoModelo`), rodados de um IP residencial. `versoes()`
devolve `{codigo, nome, anos}` → o front cruza **ano ↔ versão** sem chamadas extras:
escolher o ano filtra as versões e escolher a versão restringe os anos.

### Fluxo da busca ao vivo (`app/services/scrape.buscar_ao_vivo`)
Coleta paralela (ThreadPoolExecutor) → upsert no mercado → filtra pelos critérios →
score focado (FIPE fresca p/ grupos pequenos) → ordena (preço/desconto) → devolve.

### API (`app/api/`)
`monitors` (CRUD), `listings` (rankeado), `settings` (score+portais), `ops`
(logs+varredura), `fipe` (cascata marca→modelo→versão), `localidades` (IBGE),
`search` (busca ao vivo).

### Modelo de dados (`app/models.py`)
`vehicle_listings` é o **mercado global** compartilhado; `monitor_matches` é o que se
notifica; `listing_scores`, `fipe_cache`, `scrape_logs`, `settings`, `portals`,
`monitors`, `notifications`.

## Frontend (`/frontend`, React + Vite + Tailwind)
Abas: **Busca** (cards com foto, filtros estilo portal, ordenação), **Ranking**
(tabela por score), **Monitores** (CRUD), **Configurações** (parâmetros + portais +
logs). Usa `/api` relativo (proxy do Vite em dev; redirect do Netlify em produção).
Responsivo (mobile-first).

## Deploy
Frontend → **Netlify** (estático + proxy `/api`). Backend → **Render** (FastAPI,
`render.yaml`). Detalhes e caveats no [README](../README.md#-deploy-netlify--render).

## Testes
`backend/tests/`: engine de score, parsing dos conectores (fixtures reais), matcher
FIPE. Rodar: `cd backend && python -m pytest`.

## Limitações conhecidas
- iCarros/Comprecar/Mobiauto/Webmotors paginados/filtrados exigem tier navegador ou
  unblocker pago (anti-bot / IDs internos / render JS).
- Scraping de IP datacenter pode ser bloqueado por portais.
- Sem raio de distância ainda (cidade é ponto de coleta, filtro é por UF).
- Modelos sem label-base na FIPE (ex.: Corolla puro) mantêm clutter residual de trims.
