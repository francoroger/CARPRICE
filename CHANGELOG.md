# Changelog

Todas as mudanças relevantes do **CarPrice** são registradas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/) e
versionamento [SemVer](https://semver.org/lang/pt-BR/).

A cada alteração: nova versão + entrada aqui + documentação atualizada + push no GitHub.

## [Não lançado]
- (próximas alterações entram aqui)

## [0.5.5] - 2026-05-30
### Fixed
- **Dropdown de Modelo ainda trazia trims** (FIT CX/DX/EX, CIVIC SEDAN, HR-V ADVANCE).
  Nova lógica: modelo = 1ª palavra (FIT, CIVIC, HR-V), com exceções que preservam
  modelos compostos reais — mesmo 2º nome em todo o grupo (GRAND SIENA) ou 2º nome
  sub-modelo (Corolla CROSS, Onix PLUS, Corolla SW). Trims vão para o dropdown de Versão.

## [0.5.4] - 2026-05-30
### Added
- **Site no ar**: https://pricecar.netlify.app (frontend Netlify + backend Render).
  Verificado de ponta a ponta com navegador real: dropdowns carregam do backend
  (CORS ok), e **responsivo** em mobile (390px) e desktop (sem scroll horizontal).

## [0.5.3] - 2026-05-30
### Changed
- **Frontend chama o backend DIRETO** (via `VITE_API_URL`) em vez do proxy do Netlify,
  evitando o timeout do proxy (~26s) nas buscas longas (~100s no Render free).
- CORS do backend liberado (`allow_credentials=False`, origens via `CORS_ORIGINS`).
- `netlify.toml`: injeta `VITE_API_URL` no build; removido o redirect `/api`.

## [0.5.2] - 2026-05-30
### Added
- **Catálogo FIPE estático** (`backend/app/data/fipe_modelos.json`, 107 marcas / 7273
  modelos) embutido no backend. Os dropdowns marca→modelo→versão passam a usar esse
  catálogo, então **funcionam mesmo no Render** (a FIPE oficial bloqueia IP de
  datacenter). O valor/preço FIPE continua sendo consultado ao vivo quando disponível.

## [0.5.1] - 2026-05-30
### Fixed
- **Backend no Render não coletava nada** (busca e FIPE retornavam 0/erro): faltava o
  pacote **`h2`** no `requirements.txt` (os fetchers usam `http2=True`). Adicionado
  `httpx[http2]` + `h2`. Confirmado que NÃO era bloqueio de IP do datacenter.
### Changed
- `netlify.toml`: redirect `/api/*` apontado para o backend real
  `https://carprice-api-8xur.onrender.com`.

## [0.5.0] - 2026-05-30
### Added
- **Versionamento + documentação**: `VERSION`, este `CHANGELOG.md` e `docs/ARCHITECTURE.md`.
- **Deploy**: `netlify.toml` (frontend) e `render.yaml` (backend) + guia no README.
- **Ordenação na Busca**: seletor Preço menor→maior (padrão) / maior→menor / Melhor desconto, com re-sort instantâneo no cliente.
### Changed
- **Frontend responsivo**: cabeçalho com quebra de linha no mobile, abas com scroll horizontal, tabela do Ranking rolável, grid de cards 1/2/3 colunas.
- **Busca ao vivo agora é tipo portal** (ordenada por preço); o **Ranking** segue sendo a análise de custo-benefício (score).
### Fixed
- **Naming marca/modelo por portal**: `marca_canonica()` resolve o rótulo da FIPE (`VW - VolksWagen` → `Volkswagen`); `familia_do_label` + colapso por prefixo deixam o dropdown de Modelo só com modelos (T-CROSS, GRAND SIENA), versões no dropdown de Versão.
- CarroSP busca por **marca sem modelo** agora usa `/marca/` (antes caía em `/todos/`).

## [0.4.0] - 2026-05-30
### Added
- **Resultados em cards com foto** (estilo portal), preço em destaque, badges de desconto/origem.
- **Paginação do Napista** (`/busca/{marca}/{modelo}?pn=N`) — centenas de anúncios por modelo.
### Changed
- Filtro de localização por **estado (UF)** em vez de cidade exata (portais devolvem resultados regionais).
- Exibe **todos** os resultados (sem corte em 200) e `min_grupo=2` (mais comparações MERCADO).
### Fixed
- FIPE com referência errada/stale: busca reprocessa FIPE **fresca e conservadora**, escolhendo a geração com o ano do carro.
- Match insensível a espaço (`HB20` casa `HB 20 Hatch`).

## [0.3.0] - 2026-05-29
### Added
- **Busca ao vivo** (`POST /api/search`): entra em todos os portais ativos em paralelo e filtra.
- **Filtros ricos** (estilo CarroSP): cascata marca→modelo→versão (FIPE), ano/preço/km, câmbio, combustível, condição.
- **Localização Estado→Cidade** via API do IBGE.
- **Paginação do CarroSP** (`?page=N`) — traz o catálogo completo do modelo (centenas).
### Fixed
- Engine de score só usava FIPE no cold-start; busca focada por modelo passou a gerar grupos MERCADO.

## [0.2.0] - 2026-05-29
### Added
- **FIPE oficial** (`veiculos.fipe.org.br`) substituindo a API não-oficial; matching por palavra-nome do modelo.
- Conectores **Localiza Seminovos** e **Mobiauto** via `__NEXT_DATA__` (dados estruturados, sem raspar DOM).
### Changed
- `vehicle_listings` virou **mercado global** compartilhado (volume estatístico p/ o score).

## [0.1.0] - 2026-05-29
### Added
- MVP: backend **FastAPI** + **5 conectores** (CarroSP, iCarros, Napista, Localiza, Comprecar) com motor de acesso em camadas.
- **Engine de score** (carros idênticos por versão+ano, faixas de km, mediana, fallback FIPE) com testes.
- **API REST** (monitors, listings, settings, scrape-logs) + **scheduler** (APScheduler) + e-mail.
- **Frontend React + Vite + Tailwind** (Ranking, Monitores, Configurações).
- Spike de viabilidade dos portais (`/spike`) validado ao vivo.

[Não lançado]: https://github.com/francoroger/CARPRICE/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/francoroger/CARPRICE/releases/tag/v0.5.0
[0.4.0]: https://github.com/francoroger/CARPRICE/releases/tag/v0.4.0
[0.3.0]: https://github.com/francoroger/CARPRICE/releases/tag/v0.3.0
[0.2.0]: https://github.com/francoroger/CARPRICE/releases/tag/v0.2.0
[0.1.0]: https://github.com/francoroger/CARPRICE/releases/tag/v0.1.0
