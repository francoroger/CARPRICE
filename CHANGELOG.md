# Changelog

Todas as mudanças relevantes do **CarPrice** são registradas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/) e
versionamento [SemVer](https://semver.org/lang/pt-BR/).

A cada alteração: nova versão + entrada aqui + documentação atualizada + push no GitHub.

## [Não lançado]
- (próximas alterações entram aqui)

## [0.8.0] - 2026-05-30
### Changed
- **Varredura dos monitores reformulada**: agora usa o MESMO pipeline da busca ao
  vivo (`buscar_ao_vivo`) — coleta **paralela** nos 6 portais (antes era sequencial,
  portal a portal), filtros **no servidor do CarroSP** (ano/km/preço/raio), **marca
  canônica**, **cache-first** (monitores com critérios parecidos reaproveitam a
  coleta) e **score focado** com circuit-breaker da FIPE. O código antigo
  (`collect_for_monitor`/`recompute_scores`/`match_and_notify`) foi removido.
- `normalizar_criterios()` centralizado em `buscar_ao_vivo`: qualquer chamador
  (Busca, monitor salvo, scheduler) recebe a mesma normalização.
### Fixed
- **Monitor criado pelo formulário não casava nada**: o `criterios_json` guardava a
  marca no rótulo da FIPE ("VW - VolksWagen") e a varredura antiga não convertia
  para o nome canônico — a URL dos portais e o pós-filtro falhavam. Normalização
  agora é aplicada na varredura (monitores existentes passam a funcionar sem
  precisar recriar).
- Varredura não derruba mais tudo se um monitor falhar (continua nos próximos).

## [0.7.0] - 2026-05-30
### Added
- **Vínculo ano ↔ versão (FIPE)** no filtro de veículos: ao selecionar um modelo
  aparece um seletor de **Ano**; escolher o ano mostra **apenas as versões que
  existem naquele ano**, e escolher a versão restringe os anos àqueles em que ela
  foi fabricada (cruzamento bidirecional, instantâneo no cliente).
- **Anos-modelo embutidos no catálogo FIPE** (`data/fipe_modelos.json`): cada versão
  passa a carregar `"anos": [...]`, gerado por `gen_fipe_anos.py` (ConsultarAnoModelo
  de um IP residencial, pois o Render é bloqueado pela FIPE — mesmo motivo do catálogo).
### Changed
- `FipeClient.versoes()` agora retorna `anos` por versão.
- `FiltroVeiculos.jsx`: a faixa "Ano De/Até" é substituída pelo seletor de Ano quando
  há um modelo com dados de ano; permanece como faixa em buscas amplas (sem modelo).
- O ano específico escolhido restringe a busca àquele ano-modelo (`ano_min=ano_max`).
### Fixed
- **Busca por ano voltava vazia** (ex.: "Gol 2018" num raio de 500 km não trazia nada
  apesar de haver anúncios). Causa: o CarroSP ordena por relevância e o ano específico
  ficava fora das primeiras páginas (teto de paginação) → o pós-filtro descartava tudo.
  Agora o CarroSP filtra **no servidor dele**: `ano1`/`ano2`, `kmIni`/`kmFim`,
  `precoIni`/`precoFim`, `zero`/`usado` vão na URL (junto do `distancia`). "Gol 2018"
  passou de 0 → 12 resultados.
- **Ano lido errado** em alguns anúncios do CarroSP (o ID virava "ano", ex.: 7614715):
  o ano passa a ser o segmento que é realmente um ano (19xx/20xx) na URL.

## [0.6.0] - 2026-05-30
### Added
- **Filtro de veículos compartilhado** (`components/FiltroVeiculos.jsx`): a tela
  **Novo monitor** agora usa os MESMOS filtros ricos da Busca (cascata marca→modelo→
  versão, estado→cidade, ano/preço/km, câmbio, combustível, condição).
- **Raio de distância (km)**: slider a partir da cidade selecionada; reflete na busca
  (CarroSP via `?distancia=N`). Backend: `raio_km` em SearchCriteria/SearchRequest.
- **Filtro de portal** (chips clicáveis) na Busca e no Ranking: clicar mostra só os
  resultados daquele portal; opção "Todos". Filtragem instantânea no cliente.
### Changed
- Componentes de filtro extraídos e reutilizados entre Busca e Monitor (DRY).

## [0.5.8] - 2026-05-30
### Added
- **Cache-first na busca**: se já há resultados recentes (<30min) p/ o critério, devolve
  na hora (~2-3s) em vez de coletar tudo de novo (~30s no Render). A 1ª busca de um
  modelo coleta ao vivo; as seguintes vêm do cache. Botão **↻ Atualizar** força coleta
  ao vivo (param `forcar`).

## [0.5.7] - 2026-05-30
### Changed
- **Mais performance**: timeout da FIPE 20s→8s (fail-rápido quando bloqueada) e a
  indisponibilidade passa a ser cacheada no singleton (não re-sonda a FIPE a cada
  busca). Reduz o tempo da busca no Render.

## [0.5.6] - 2026-05-30
### Changed
- **Performance da busca** (~2min → segundos):
  - GitHub Action `keep-warm` pinga o Render a cada 10min → mata o cold start (~50s).
  - Paginação reduzida (CarroSP 20→8, Napista 8→5 páginas) — busca mais rápida.
  - Circuit-breaker da FIPE: no Render (FIPE bloqueada) o score pula a consulta de
    valor e usa só MERCADO (economiza ~12s).
- **Colapso de modelo universal**: refinado p/ TODAS as marcas — trims curtos
  (GS/GTI/LX) e palavras-trim (SPORT/TOURING/ADVANCE...) colapsam no nome do modelo;
  compostos reais (GRAND SIENA, PT CRUISER) e sub-modelos (CROSS/PLUS) ficam.

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
