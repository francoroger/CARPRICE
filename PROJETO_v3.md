# PROJETO v3 — Sistema de Monitoramento de Preços de Carros
> Especificação para implementação assistida pelo Claude Code.
> **Esta versão é calibrada por um spike real de coleta** (ver `/spike`), que testou
> os portais ao vivo e definiu quais são viáveis e como acessá-los.

---

## 0. O que mudou da v2 para a v3 (e por quê)

| Tema | v2 (teórico) | v3 (calibrado por teste real) |
|---|---|---|
| Conector piloto | MercadoLivre (API) | **CarroSP** — SSR, `httpx` puro, 31 anúncios extraídos no teste |
| Fonte de dados | MercadoLivre como base | **MercadoLivre descartado** (pouco estoque relevante) |
| Estratégia de acesso | "Playwright onde precisar" | **Motor de acesso em camadas com auto-escalada** (ver §2) |
| Webmotors | conector normal | **PerimeterX confirmado** → fora do MVP; plugin pago opcional |
| Modelo de dados | `listings` por monitor | **Mercado global** separado do que se notifica (ver §5) |
| Engine de score | OK | **Mantida** (é a parte forte) — ver §4.4 |

### Achados do spike (testado ao vivo em 2026, do PC do usuário)
**5 conectores com PARSER PRONTO e validado** (httpx puro, ~128 anúncios reais, zero custo):

| Portal | Acesso | Resultado | Selector / nota de parsing | Decisão |
|---|---|---|---|---|
| **Napista** | `httpx` puro | ✅ 48 anúncios (título/preço/ano/km/cidade) | `a[href*='/anuncios/']`; cards SEM `<a>` interno, link no wrapper | **MVP** |
| **CarroSP** | `httpx` puro | ✅ 31 anúncios (preço/km/ano/versão pela URL) | `div.veiculo-item`; versão limpa na URL | **MVP — piloto** |
| **Comprecar** | `httpx` puro | ✅ 24 anúncios | `.card.vehicle`; km escrito "KM 28.000" (antes do nº) | **MVP** |
| **iCarros** | `httpx` puro | ✅ 20 anúncios (gigante nacional) | `.offer-card`; URL real `/ache/listaanuncios.jsp` | **MVP** |
| **Localiza Seminovos** | `httpx` puro | 🟡 5 via SSR (resto lazy-load) | `/detalhes-carro/` MUI; refinar via API interna na build | **MVP (refinar)** |
| Mobiauto, Unidas, Autoarremate, Usados BR | `httpx` | 200 mas SPA (dados via API JSON interna) | — | Fase 2 |
| **Webmotors** | qualquer nível grátis | ❌ 403 PerimeterX (testado httpx + Chrome real headful) | — | Fase 3 / plugin pago |
| OLX, Movida Seminovos | `httpx` | ❌ 403 anti-bot | — | Fase 3 |

> Parsers de referência no `/spike`: `carrosp.py`, `icarros.py`, `conectores_extra.py`
> (Napista/Comprecar/Localiza). Todos viram conectores `min_tier=HTTP` na Fase 1.

> **Regra de ouro do projeto:** o núcleo coleta dos portais que respondem e **degrada
> graciosamente** — uma fonte que cai é desativada com log, sem derrubar o sistema.

---

## 1. Visão Geral

Sistema que monitora anúncios de veículos em **múltiplos portais SSR brasileiros**,
identifica o **melhor custo-benefício comparando carros idênticos entre si** (mesma
versão + ano-modelo), ajusta o preço pela quilometragem, e notifica o usuário
(e-mail; WhatsApp depois) quando surge uma oportunidade dentro dos critérios.

Filosofia: **"configure uma vez e aguarde os resultados chegarem."**

---

## 2. Motor de Acesso em Camadas (NÚCLEO DA COLETA)

Cada portal é um **conector isolado e plugável**. Além do parsing, cada conector
declara o **nível de acesso** que precisa. O motor tenta do mais barato ao mais caro e
**auto-escala** quando toma bloqueio (403/captcha), registrando o nível que funcionou.

```
Nível 1 — HTTP simples (httpx) + headers de navegador
          → CarroSP, iCarros, Napista, Localiza, Comprecar. 90% do estoque.
Nível 2 — HTTP + "aquecimento de sessão" (pega cookies/token na home) + headers cors
          → para APIs JSON internas de SPAs (Mobiauto, Unidas) [Fase 2].
Nível 3 — Navegador real (Playwright + stealth)
          → fallback quando 1/2 levam captcha [Fase 2/3].
Nível 4 — Proxy residencial rotativo (camada por baixo de qualquer nível)
          → quando o IP é bloqueado [Fase 3].
Nível 5 — API "unblocker" paga (ZenRows/ScraperAPI) para anti-bot pesado
          → Webmotors/OLX/Movida (PerimeterX) [opcional, pago].
```

```python
class AccessTier(IntEnum):
    HTTP = 1
    SESSION = 2
    BROWSER = 3
    PROXY = 4
    UNBLOCKER = 5

class PortalConnector(ABC):
    name: str
    enabled: bool
    min_tier: AccessTier          # nível mínimo declarado pelo conector
    rate_limit_s: float           # intervalo mínimo entre requisições

    @abstractmethod
    async def search(self, criteria: SearchCriteria, fetch: Fetcher) -> list[RawListing]:
        """Recebe um 'fetch' já no tier certo. Só faz parsing — não sabe de proxy/browser."""
```

- **Separação de responsabilidades:** o conector **só sabe parsear**. Quem busca é um
  `Fetcher` injetado, que encapsula o nível de acesso. Trocar de nível **não altera o
  conector**. Adicionar portal novo na Fase 2 **não toca no núcleo nem no score**.
- **Testes de parsing isolados:** cada conector tem fixtures de HTML salvo + teste que
  valida a extração, para detectar quando o portal muda de layout.
- **Auto-escalada:** se um `Fetcher` nível 1 retorna 403/captcha, o motor reexecuta no
  nível seguinte (se habilitado) e memoriza o nível efetivo do portal.

> O `/spike` já contém implementações funcionais de referência:
> `spike/carrosp.py` (Nível 1 completo), `spike/webmotors_browser.py` (Nível 3),
> `spike/descobrir_portais.py` (varredura de viabilidade). Use como ponto de partida.

---

## 3. Stack Técnica

| Camada | Tecnologia |
|---|---|
| Backend/API | Python 3.12 / FastAPI |
| Coleta | httpx (Nível 1-2) + Playwright (Nível 3) — conectores modulares |
| Parsing | BeautifulSoup + lxml |
| Banco | PostgreSQL 15+ |
| Agendador | APScheduler (MVP) → Celery + Redis (escala) |
| Frontend | React + Vite + TailwindCSS |
| E-mail | SMTP / SendGrid |
| WhatsApp | (Fase 2) Cloud API oficial ou Evolution API |
| ORM/Migrations | SQLAlchemy + Alembic |
| Container | Docker + Docker Compose |

---

## 4. Módulos

### 4.1 Cadastro de Monitoramento (Busca Salva)
Filtros: marca, modelo, **versão**, ano fab/modelo (faixa), faixa de preço, km máx,
câmbio, combustível, UF/cidade/raio, opcionais.
Cada monitor: frequência de varredura + status (ativo/pausado) + canais de notificação +
`threshold_desconto`.

### 4.2 Conectores (ver §2)
Roster do MVP: **CarroSP, iCarros, Napista, Localiza Seminovos, Comprecar.**
Normalização: `RawListing` → `Listing` padrão. Deduplicação entre portais por hash
(versão+ano+km+preço+localização).

### 4.3 Integração FIPE
- Resolve código FIPE por marca/modelo/ano (wrapper da API pública FIPE — não-oficial,
  tolerar indisponibilidade). Cache mensal em `fipe_cache`.
- **Papel:** referência exibida + **fallback do score** (ver 4.4).

### 4.4 Engine de Score — Custo-Benefício (NÚCLEO — mantido da v2)
**Objetivo:** dentro de um conjunto de carros idênticos, eleger o **mais barato
considerando a quilometragem**.

1. **Agrupamento de idênticos** — chave `versão + ano-modelo` (combustível/câmbio entram
   na chave se divergirem). No CarroSP a versão já vem limpa da URL do anúncio.
2. **Preço esperado por faixa de km** — segmenta o grupo em faixas (`0–30k | 30–60k |
   60–90k | 90–120k | 120k+`, configurável); `preco_ref` = **mediana** da faixa.
3. **Desconto relativo** — `desconto = (preco_ref - preco_anuncio) / preco_ref`.
4. **Fallback FIPE** — se o grupo/faixa tiver `< min_grupo` anúncios (default 3),
   usa `desconto = (fipe_valor - preco_anuncio) / fipe_valor`; marca `origem_score=FIPE`.
5. **Score final** — `score = desconto + bonus_km` (bônus leve `w_km` para desempate por
   menor km). Ranking por `score` desc. **Notifica** se `desconto ≥ threshold_desconto`.

| Parâmetro | Default | Função |
|---|---|---|
| `faixas_km` | [30k,60k,90k,120k] | Cortes das faixas |
| `min_grupo` | 3 | Mínimo p/ usar mercado; abaixo → FIPE |
| `w_km` | 0.05 | Peso do bônus de km no desempate |
| `threshold_desconto` | 0.08 | Mínimo p/ notificar |
| `metrica_ref` | mediana | mediana ou média |

> **Calibrar com dados reais** depois de acumular amostra. Comece conservador.

### 4.5 Notificações
Dispara quando anúncio **novo** cruza `threshold_desconto` e está dentro dos filtros.
MVP: e-mail (SMTP). Anti-spam: só anúncio inédito (`hash_dedup`).
Payload: foto, preço, km, ano, **desconto vs idênticos**, origem (MERCADO/FIPE),
posição no ranking, link.

### 4.6 Painel Administrativo
- Globais: frequência, **portais ativos + nível de acesso**, credenciais, parâmetros do score.
- Monitores: CRUD, ativar/pausar, ver ranking com desconto e origem.
- Observabilidade: `scrape_logs`, saúde por portal, nível efetivo usado, última execução,
  taxa de sucesso.

---

## 5. Modelo de Dados (REFORMULADO — mercado global)

> Mudança-chave: o **mercado** (todos os anúncios coletados) é **global e compartilhado**,
> para a estatística do score ter volume. A relação **monitor↔anúncio** só decide o que
> notificar. Sem isso, cada monitor isolado cairia sempre no fallback FIPE por falta de amostra.

```
users            (id, email, nome, senha_hash, criado_em)

monitors         (id, user_id, nome, criterios_json, frequencia_min,
                  threshold_desconto, canais_notif, status, criado_em)

portals          (id, nome, slug, min_tier, rate_limit_s, config_json, ativo)

vehicle_listings (id, portal_id, url, marca, modelo, versao, ano_fab, ano_modelo,
                  preco, km, faixa_km, cambio, combustivel, cidade, uf, foto_url,
                  grupo_chave, hash_dedup, fipe_codigo, fipe_valor,
                  primeiro_visto_em, ultimo_visto_em, ativo)
                  -- MERCADO GLOBAL: alimenta a estatística do score

listing_scores   (id, listing_id, preco_ref, desconto, origem_score, score, calculado_em)
                  -- score recalculado a cada varredura

monitor_matches  (id, monitor_id, listing_id, desconto, posicao_ranking, criado_em)
                  -- o que casa com cada monitor (base da notificação)

fipe_cache       (id, codigo_fipe, marca, modelo, ano, valor, ref_mes, atualizado_em)

notifications    (id, monitor_id, listing_id, canal, status, enviado_em)

settings         (id, chave, valor_json)

scrape_logs      (id, portal_id, monitor_id, tier_usado, status, qtd_resultados,
                  erro, duracao_ms, executado_em)
```

---

## 6. Fluxo Automático

```
Scheduler (a cada X min, por monitor ativo)
  └─ Para cada portal ATIVO: Fetcher(min_tier) → connector.search() → normaliza
        └─ se 403/captcha e tier+1 habilitado → auto-escala e tenta de novo
  └─ Upsert em vehicle_listings (mercado global; atualiza ultimo_visto_em)
  └─ Deduplica entre portais (hash_dedup)
  └─ Agrupa por (versao + ano_modelo) + atribui faixa_km
  └─ Por grupo+faixa: preco_ref (mediana)
        ├─ grupo/faixa >= min_grupo → origem MERCADO
        └─ senão → consulta FIPE → origem FIPE
  └─ Calcula desconto + score → grava listing_scores
  └─ Para cada monitor: filtra listings que casam + desconto >= threshold → monitor_matches
  └─ Notifica anúncios NOVOS (e-mail) — anti-spam por hash_dedup
  └─ Registra scrape_log (com tier_usado)
```

---

## 7. Roadmap Evolutivo
1. Conectores Nível 2 (API JSON de SPAs): Mobiauto, Unidas, Autoarremate.
2. WhatsApp (Cloud API/Evolution).
3. Conector Nível 5 pago opcional p/ Webmotors/OLX (PerimeterX) via unblocker.
4. Histórico de preço por anúncio (detectar quedas) + alerta "anúncio sumiu" (vendido).
5. Estimador de preço justo via ML (regressão km/ano/versão/região) substituindo faixas fixas.
6. Detecção de anúncio suspeito (desconto absurdo = possível fraude).
7. PWA + push; comparador lado a lado; análise de revenda; multiusuário/SaaS.

---

## 8. Entrega em Fases

**Fase 1 (MVP):** monorepo + Docker Compose; modelo de dados §5; **motor de acesso em
camadas (Nível 1)** + interface de conectores; **CarroSP** completo (a partir de
`spike/carrosp.py`) + testes de parsing; FIPE com cache; **engine de score §4.4 completa
com testes** (grupo grande=MERCADO, grupo pequeno=FIPE, desempate por km); APScheduler;
e-mail com anti-spam; API REST; painel React básico.

**Fase 2:** demais conectores Nível 1 (iCarros, Napista, Localiza, Comprecar) + Nível 2
(Mobiauto/Unidas); deduplicação entre portais; WhatsApp; Celery+Redis; observabilidade.

**Fase 3:** Webmotors/OLX via unblocker pago; histórico de preços; estimador ML; PWA.

---

## PROMPT INICIAL — FASE 1 (colar no Claude Code)

```
Implemente a FASE 1 (MVP) do sistema descrito em PROJETO_v3.md.
Stack: Python 3.12 / FastAPI, PostgreSQL, SQLAlchemy + Alembic, APScheduler, httpx +
BeautifulSoup/lxml, React + Vite + Tailwind, Docker Compose.

Já existe uma pasta /spike com coleta REAL funcionando — use como base, não comece do zero:
- spike/carrosp.py  → conector CarroSP Nível 1 já extrai 31 anúncios (preço/km/ano/versão pela URL)
- spike/descobrir_portais.py → varredura de viabilidade dos portais
- spike/webmotors_browser.py → referência de Nível 3 (NÃO usar no MVP; Webmotors fica fora)

Entregue nesta ordem, com commits incrementais, mostrando o plano antes de cada módulo:

1. Estrutura monorepo (/backend, /frontend) + docker-compose (Postgres, backend, frontend).
2. Modelo de dados completo (SQLAlchemy) da seção 5 — IMPORTANTE: vehicle_listings é o
   MERCADO GLOBAL compartilhado; monitor_matches é o que se notifica. + migrations Alembic.
3. MOTOR DE ACESSO EM CAMADAS (seção 2): interface PortalConnector com min_tier + um
   Fetcher injetável que encapsula o nível de acesso (Nível 1 = httpx com headers de
   navegador). O conector só faz parsing; trocar de nível não altera o conector.
4. Conector CarroSP completo a partir de spike/carrosp.py, com RawListing→Listing
   normalizado e TESTES DE PARSING isolados (fixture de HTML salvo).
5. Integração FIPE com cache mensal (wrapper da API pública FIPE, tolerando indisponibilidade).
6. ENGINE DE SCORE (seção 4.4): agrupa por versão+ano-modelo sobre o MERCADO GLOBAL,
   faixas de km, preço de referência por mediana, desconto relativo, fallback FIPE quando
   grupo < min_grupo, bônus de km para desempate. Parâmetros lidos da tabela settings.
   ESCREVA TESTES cobrindo: grupo grande (origem MERCADO), grupo pequeno (fallback FIPE),
   e desempate por km.
7. Scheduler (APScheduler) executando o fluxo da seção 6 por monitor ativo, com degradação
   graciosa (portal que falha é logado e pulado) e registro de tier_usado em scrape_logs.
8. Notificação por e-mail (SMTP configurável) com anti-spam (só anúncio inédito por hash_dedup).
9. API REST: CRUD monitors, settings, listagem de listings rankeados (desconto + origem_score),
   status de scrape_logs.
10. Painel React: criar/editar/pausar monitor; ver ranking com desconto/origem/km;
    editar settings (faixas_km, min_grupo, w_km, threshold_desconto, frequência, portais ativos).

Regras de arquitetura:
- Use variáveis de ambiente para todas as credenciais.
- Conectores plugáveis: adicionar um portal novo (Fase 2) NÃO pode exigir mudar o núcleo
  nem a engine de score.
- Cada conector com testes de parsing isolados (detectar quebra por mudança de layout).
- Degradação graciosa: fonte que cai é desativada com log, sem derrubar o sistema.

Comece pela estrutura do projeto e o docker-compose, depois o modelo de dados.
```
