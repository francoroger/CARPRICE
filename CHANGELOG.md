# Changelog

Todas as mudanças relevantes do **CarPrice** são registradas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/) e
versionamento [SemVer](https://semver.org/lang/pt-BR/).

A cada alteração: nova versão + entrada aqui + documentação atualizada + push no GitHub.

## [Não lançado]
- (próximas alterações entram aqui)

## [0.13.2] - 2026-06-16
### Fixed
- **Modelos "letra + número" colapsavam** (Volvo mostrava só "XC" no lugar de
  XC40/XC60/XC90; idem S40/S60/S90, V40/V60). A FIPE escreve esses com espaço
  ("XC 60"), e a extração de família parava no 1º dígito tratando o número como
  cilindrada. Agora junta o número de modelo (2-3 díg.) ao nome: "XC 60" → XC60,
  "S 60" → S60, "C 180" → C180 — preservando cilindrada de 4 díg. ("Gol 1000" → GOL)
  e os modelos compostos (T-Cross, Grand Siena, Corolla Cross).

## [0.13.1] - 2026-06-16
### Added
- **Notificações de alerta**: badge vermelho com a contagem de novos alertas na aba
  "Alertas" + **notificação do navegador** (desktop/celular) quando um monitor acha um
  carro novo — botão "Ativar notificações" pede a permissão. O app verifica a cada
  ~60s e ao concluir uma varredura; abrir a aba zera o badge.
### Fixed
- **`/api/account/alerts` dava 500** (lia `titulo`, campo inexistente em VehicleListing).
  Corrigido — a aba Alertas carrega normalmente.

## [0.13.0] - 2026-06-16
### Added
- **Aba "Alertas"** (logado): mostra os carros que **seus monitores** encontraram
  abaixo do mercado (acima do seu limite de desconto). É onde os alertas aparecem
  dentro do app — sem depender de e-mail. Endpoint `GET /api/account/alerts`.
- **Confirmar senha no cadastro**: campo "Confirmar senha" valida que as duas batem.
- **Página "Minha conta"**: clicar no nome (topo) abre um painel para editar nome e
  e-mail e **trocar a senha** (exige a senha atual). Endpoint `PATCH /api/auth/me`.
### Notes
- O **e-mail de alerta já vai para o e-mail da conta** — falta apenas configurar o
  SMTP no Render para o envio sair de fato (`SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD`).

## [0.12.0] - 2026-05-30
### Added
- **Login real (contas de usuário)**: cadastro/entrada por e-mail+senha com token JWT
  (senha com hash pbkdf2). Botão "Entrar" no topo; ao logar, o nome aparece e há "Sair".
  - **Monitores** passam a ser **por usuário** (cada um vê e roda os seus).
  - **Carros salvos** e **histórico de buscas** ficam guardados **na conta** (servidor),
    sincronizando entre dispositivos. Sem login, seguem no navegador (modo convidado).
  - Backend: tabelas `saved_listings` e `search_history`; endpoints `/api/auth/*`
    (register/login/me) e `/api/account/*` (saved/history); `JWT_SECRET` no Render.
  - Validado contra o Postgres Aiven e no navegador (criar conta → salvar → sair →
    entrar → dados voltam do servidor).

## [0.11.1] - 2026-05-30
### Added
- **Banco permanente (Aiven Postgres)**: backend pronto para usar o Postgres
  `pricecar` da Aiven via `DATABASE_URL` — monitores e dados deixam de resetar a
  cada deploy. `database.py` normaliza `postgres://`→`postgresql://`, força
  `sslmode=require` e usa pool com `pool_recycle` (estável em conexão ociosa).
  `DATABASE_URL` declarado no `render.yaml` como segredo (`sync:false`).
- **Keep-warm (sempre acordado)**: workflow `keep-warm` (GitHub Actions, ping a
  cada 10 min) mantém o backend do Render sem hibernar — fim do cold-start. Como o
  servidor fica on, `SCHEDULER_ENABLED` volta a `true` (varredura agendada roda).

## [0.11.0] - 2026-05-30
### Added
- **Busca não se perde ao atualizar a página**: filtros, resultados, ordenação e
  filtro de portal ficam guardados no navegador (localStorage) e voltam no F5.
- **Aba "Histórico"**: suas buscas recentes (re-executáveis com um clique em
  "Refazer", que restaura os filtros) e os **carros salvos**. Tudo no navegador —
  sobrevive a refresh e a redeploys do backend, sem precisar de login.
- **Salvar carro (⭐)** em cada card da Busca; os salvos aparecem no Histórico.
### Changed
- **Cold-start mais limpo**: enquanto o servidor acorda, o seletor de Marca mostra
  apenas "Carregando…" (sem o aviso alarmante de antes).
### Removed
- **Aba Ranking** e todo o código atrelado (view, `api.listings`, endpoint
  `/api/listings`) — simplifica o app; o custo-benefício já aparece nos cards.
### Known
- Os **monitores** (varredura agendada) seguem no banco do backend, que é efêmero
  no Render free (reseta a cada deploy). Buscas e carros salvos agora persistem no
  navegador; persistência server-side dos monitores entre deploys exige um banco
  permanente (próximo passo).

## [0.10.9] - 2026-05-30
### Fixed
- **Página "Versões" não carregava em produção**: o `CHANGELOG.md`/`VERSION` não
  chegavam ao deploy (o redirect SPA do Netlify devolvia o index.html no lugar).
  Agora os arquivos são **commitados em `public/`** (o Vite os copia p/ o `dist/`) e
  o comando de build do Netlify roda o `copy-meta` explicitamente — dupla garantia.

## [0.10.8] - 2026-05-30
### Added
- **Aba "Versões"**: página de histórico no app que lê o `CHANGELOG.md` e o `VERSION`
  (mesma fonte de verdade do versionamento) e mostra a **versão atual**, a **última
  edição implementada** em destaque e a **linha do tempo de todas as versões** com
  cada alteração rotulada (Novo / Mudou / Corrigido / Limitação). Um passo de build
  (`scripts/copy-meta.mjs` no prebuild) publica os arquivos para o front consumir.

## [0.10.7] - 2026-05-30
### Fixed
- **Filtro por VERSÃO trazia quase nada** (ex.: Commander Limited 2023 → 1 carro,
  sendo que só o CarroSP tem 14): o filtro exigia a string da versão FIPE como
  substring exata da versão do anúncio, mas cada portal escreve a versão em ordem
  e tokens diferentes ("Commander Limited T270 1.3 TB Flex Aut." vs "1.3 16v 4p
  flex t270 limited turbo automatico") → não casava nada. Agora casa por **TRIM +
  cilindrada**: exige as palavras de trim da FIPE (Limited/Longitude/Overland…,
  ignorando ruído de câmbio/combustível/carroceria/marketing) e a cilindrada
  (1.3 ≠ 2.0). Resultado validado: Commander Limited 2023 → **51 carros (CarroSP
  14, igual ao nativo)**, 100% Limited; separa flex 1.3 de diesel 2.0; "LT" não
  casa "LTZ". Testes novos em `tests/test_filters.py`.

## [0.10.6] - 2026-05-30
### Fixed
- **Campo Ano aceitava lixo** (ex.: "-2") quando nenhum modelo estava selecionado e
  a Versão mostrava "Versões de -2…": os campos numéricos (Ano/Preço/Km) agora só
  aceitam dígitos (bloqueiam "-", "e", ".", letras e colar lixo); o Ano livre limita
  a 4 dígitos. Validado no navegador: "-2"→"2", "20188"→"2018", "-500"→"500".
- **Placeholder da Versão** só mostra "Versões de X–Y" quando há um modelo com dados
  de ano selecionado; sem modelo exibe "Todas as versões".
- A lista de versões não é mais esvaziada por engano quando o modelo ainda não tem
  dados de ano carregados.

## [0.10.5] - 2026-05-30
### Fixed
- **CarroSP trazia MUITO menos carros que a busca nativa dele**: quando não havia
  cidade específica, o conector forçava `sao-paulo-sp` (a CAPITAL) na URL e perdia
  todo o interior. O CarroSP não tem filtro por estado na URL — a forma "todas as
  cidades" é `/carros/{marca}/{modelo}/`. Agora usamos essa URL quando não há
  cidade escolhida: **Jeep Commander 2023 foi de 21 → 125 carros** (Campinas,
  Bauru, Piracicaba, Americana, Ribeirão Preto… todo o interior de SP).
- O card do CarroSP passa a trazer a **cidade**; UF assume **SP** (o portal é de São
  Paulo) para o filtro por estado continuar correto. Com cidade específica, mantém
  a URL precisa `/carros/{cidade}-{uf}/…` + raio (`distancia`).

## [0.10.4] - 2026-05-30
### Changed
- **Ano agora é faixa "De/Até" também com modelo selecionado** (pedido p/ monitorar
  vários anos): os dois seletores usam os anos REAIS do modelo na FIPE e mantêm o
  vínculo com a Versão — a lista mostra só as versões que existem dentro da faixa
  (GOL: faixa 2015–2018 → 105 versões viram 36). Faixa invertida se auto-corrige
  e escolher uma versão fora da faixa ajusta a faixa para os anos dela.

## [0.10.3] - 2026-05-30
### Added
- **Botão "Ver resultados" em cada monitor**: a varredura dizia "78 resultados"
  mas não havia onde VER os carros do monitor (o Ranking é o mercado global e os
  alertas só aparecem acima do threshold). Agora cada monitor tem um botão que
  abre os carros encontrados em cards (foto + avaliação, mais barato primeiro) —
  instantâneo, direto do cache da varredura. Se uma varredura terminar com os
  resultados abertos, eles se atualizam sozinhos.

## [0.10.2] - 2026-05-30
### Fixed
- **Dropdowns de Marca/Modelo vazios ao abrir o site**: o backend free (Render)
  hiberna após ~15min parado e a 1ª chamada de marcas falhava — o filtro ficava
  vazio até o usuário dar F5. Agora o componente **tenta de novo sozinho** (a cada
  5s por até 3min), mostra "⏳ acordando o servidor…" enquanto isso e preenche as
  107 marcas automaticamente quando o servidor responde (verificado: recupera sem
  recarregar a página).

## [0.10.1] - 2026-05-30
### Fixed
- **"Varrer agora" parecia travado**: a varredura rodava em segundo plano sem
  nenhum feedback ("os resultados aparecem em instantes" e nada acontecia — no
  Render cada monitor leva ~30-60s). Agora tem **progresso em tempo real**:
  - novo `GET /api/scrape/status` (estado, monitor atual, X/Y concluídos, resumo);
  - o botão mostra "⏳ Varrendo monitor 1/2 (nome) — entrando nos portais…";
  - ao concluir: "✓ Varredura concluída: N monitores, X resultados, Y alertas";
  - o **Ranking recarrega sozinho** quando a varredura termina;
  - sem monitor cadastrado, avisa claramente (a varredura roda os MONITORES);
  - trava de varredura dupla (clicar 2x não dispara duas).

## [0.10.0] - 2026-05-30
### Changed
- **Score REFEITO do zero — "Preço de Mercado"**, calibrado numa análise de 3.887
  anúncios reais (dispersão de preço ±11,5% dentro de modelo+ano; efeito da km
  medido ≈ -0,4% a cada 10.000 km):
  - **Referência hierárquica**: mediana da mesma **versão+ano** (precisa) → mesmo
    **modelo+ano** (cobertura) → FIPE (último recurso). Cobertura: ~50% → **97%**
    dos anúncios avaliados.
  - **Km ajusta a referência** (alpha_km por 10k km, com teto) em vez de fragmentar
    os grupos em faixas — era isso que deixava quase tudo "sem referência".
  - **score = desconto, sem bônus escondido** (antes somava um bônus de km opaco).
  - `origem_score` transparente: "VERSAO:8" = comparado com 8 anúncios da mesma versão.
- **Rótulos intuitivos no lugar de números** (Busca e Ranking):
  🔥 **Excelente negócio** (≥10% abaixo do mercado) · ▼ **Bom preço** (≥5%) ·
  **Preço justo** (±5%) · ▲ **Acima do mercado** · ▲ **Caro** (>12% acima).
  Cada card mostra "X% abaixo/acima do mercado · justo R$Y · comparado com N anúncios".
- Ranking: filtro por **Classificação** (substitui "origem do score"); colunas
  "Preço justo", "Avaliação" e "Comparado com".
- Configurações: parâmetros novos (mín. comparáveis, ajuste por km, teto) no lugar
  de w_km/métrica.

## [0.9.1] - 2026-05-30
### Fixed
- **Fotos do Napista nos cards**: o lazy-load só deixava `<img src>` nos ~8 primeiros
  cards do SSR (40/48 ficavam sem foto). Agora o conector lê a foto de TODOS os
  anúncios do **JSON-LD** da página (`"@id":".../anuncios/{uuid}","image":...`) —
  48/48 com foto.
- **Upsert atualiza a foto**: anúncio já conhecido no banco nunca recebia a foto
  descoberta numa coleta posterior (2.118 anúncios do Napista estavam sem foto no
  banco por isso). O upsert agora atualiza `foto_url` (e cidade/UF se faltavam) —
  as fotos antigas se corrigem conforme as buscas ao vivo rodam.

## [0.9.0] - 2026-05-30
### Added
- **Coleta filtrada por modelo nos portais que só traziam genérico** (motivo de
  Comprecar/Localiza/iCarros nunca aparecerem nos resultados — coletavam ~20
  carros aleatórios da home regional e o pós-filtro descartava tudo):
  - **Comprecar**: `/carros-usados/{marca}/{modelo}` (filtro no servidor).
  - **Localiza**: `/carros/{uf}-{cidade}/{marca}/{modelo}` (SSR no `__NEXT_DATA__`).
  - **iCarros**: `/comprar/usados/{marca}[/{modelo}]` nacional + paginação `?pag=N`
    (até 100 cards); a UF é aplicada no pós-filtro (o link do card traz cidade-uf).
  - Busca "Gol em SP": de 2 portais com resultados → **5 portais**
    (carrosp 87, napista 43, icarros 42, comprecar 12, localiza 3).
### Fixed
- **GOLF não aparece mais na busca de GOL**: modelo alfabético casa por palavra
  inteira; modelo com dígito/hífen (HB20, T-CROSS) segue casando compactado.
  Testes novos em `tests/test_filters.py`.
### Known
- **Mobiauto** passou a renderizar 100% client-side (página placeholder p/ httpx) —
  segue ativo mas sem resultados até o tier navegador (Fase 2).

## [0.8.1] - 2026-05-30
### Added
- **Catálogo FIPE com anos completo**: as 7.273 versões de todas as 107 marcas agora
  têm seus anos-modelo embutidos (`fipe_modelos.json`, ~673 KB). O vínculo
  ano ↔ versão do filtro passa a funcionar para TODAS as marcas no Render
  (ex.: GOL tem 105 versões; escolher 2018 mostra só as 5 que existem em 2018).

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
