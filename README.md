# CarPrice — Monitoramento de Preços de Carros

**🌐 Site no ar: [pricecar.netlify.app](https://pricecar.netlify.app)** · **Versão `0.5.4`** · [Changelog](CHANGELOG.md) · [Arquitetura](docs/ARCHITECTURE.md) · [Especificação](PROJETO_v3.md)

> Frontend no **Netlify** (responsivo) chamando o backend FastAPI no **Render**.
> A 1ª busca após inatividade demora ~50s (free tier hiberna); depois fica rápido.

Sistema que monitora anúncios de veículos em múltiplos portais brasileiros,
identifica o **melhor custo-benefício comparando carros idênticos** (versão + ano,
ajustado por km, com FIPE como fallback) e notifica por e-mail quando surge uma
oportunidade. _"Configure uma vez e aguarde os resultados chegarem."_

Especificação completa: [PROJETO_v3.md](PROJETO_v3.md). Provas de coleta: [`/spike`](spike).

## 🚀 Deploy (Netlify + Render)

O app tem **2 partes**: o **frontend** (site estático, vai no Netlify) e o **backend**
Python que faz o scraping ao vivo (vai num host de servidor, ex.: Render). O Netlify
**não roda** o backend Python — ele só serve o site e repassa `/api` pro backend.

**1) Backend no Render** (https://render.com → New → Blueprint → este repo)
- O `render.yaml` cria o serviço FastAPI automaticamente (plano free, só httpx — sem navegador).
- Ao terminar, copie a URL gerada (ex.: `https://carprice-api.onrender.com`).

**2) Aponte o frontend pro backend**
- Edite `netlify.toml` → no redirect `/api/*`, troque a URL pela do seu backend.
- Commit + push (`git add netlify.toml && git commit -m "aponta backend" && git push`).

**3) Frontend no Netlify** (https://app.netlify.com → Add new site → Import → este repo)
- O `netlify.toml` já define: base `frontend`, build `npm run build`, publish `dist`.
- Pronto — o site sobe responsivo e as buscas chamam o backend via proxy `/api`.

> ⚠️ **Aviso honesto:** o scraping a partir de um IP de datacenter (Render) pode
> ser bloqueado/limitado por alguns portais (funciona melhor de IP residencial).
> O free tier do Render hiberna após inatividade (1ª busca após dormir demora ~50s).
> SQLite é efêmero no free — para persistir monitores, crie um Postgres no Render.

## Status — Fase 1 (MVP) entregue

| Componente | Estado |
|---|---|
| Motor de acesso em camadas + **6 conectores** (~170 anúncios/varredura) | ✅ |
| → HTML SSR: Napista, CarroSP, Comprecar, iCarros | ✅ |
| → `__NEXT_DATA__` (Next.js, dados estruturados): Localiza (23), Mobiauto (24) | ✅ |
| Engine de score (idênticos + faixas de km + mediana + fallback FIPE + bônus de km) | ✅ + testes |
| FIPE — API interna **oficial** (veiculos.fipe.org.br) com cache mensal | ✅ matching por palavra-nome do modelo |
| Scheduler (APScheduler) + fluxo automático | ✅ |
| Notificação por e-mail + anti-spam | ✅ |
| API REST (monitors, listings, settings, logs) | ✅ |
| Painel React (ranking, monitores, configurações) | ✅ |

## Rodar com Docker (recomendado)

```bash
docker compose up --build
# frontend: http://localhost:5173
# API:      http://localhost:8000/docs
```

## Rodar local (dev)

**Backend** (Python 3.12):
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env            # SQLite por padrão (sem Postgres)
python -m app.seed              # cria tabelas + seed
uvicorn app.main:app --reload   # http://localhost:8000
```

**Frontend** (Node 20):
```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173 (proxy /api → :8000)
```

## Testes

```bash
cd backend
python -m pytest                # engine de score + parsing dos conectores
```

Atualizar as fixtures de parsing (quando um portal muda de layout):
```bash
python tests/save_fixtures.py
```

## Arquitetura (resumo)

- `app/collectors/` — motor de acesso em **camadas** (`base.py`) + conectores plugáveis.
  Cada conector só faz parsing; o `Fetcher` injetado encapsula o nível de acesso
  (Nível 1 = httpx). Adicionar um portal **não toca no núcleo nem no score**.
- `app/services/scoring.py` — engine de score pura e testável.
- `app/services/scrape.py` — fluxo §6: coleta → dedup → score global → match → notifica.
- `app/models.py` — `vehicle_listings` é o **mercado global** compartilhado (volume p/ a
  estatística); `monitor_matches` é o que se notifica.

## Próximos passos (Fase 2/3)

- Conectores Nível 2 (API JSON de SPAs: Mobiauto, Unidas).
- Webmotors/OLX via API unblocker paga (Nível 5 — PerimeterX).
- WhatsApp, histórico de preços, estimador ML, PWA.

> **FIPE oficial (feito):** integração migrada para a API interna oficial
> `veiculos.fipe.org.br/api/veiculos` (tabela de referência → marcas → modelos →
> ano → valor), com casamento por palavra-nome do modelo. Eliminou os descontos
> espúrios do match por nome. Refinamento aberto: a FIPE oficial aplica rate-limit
> (403 sob carga) — hoje há um respiro de 0,15s/chamada; em escala, paralelizar com
> backoff ou pré-resolver os códigos por modelo.
