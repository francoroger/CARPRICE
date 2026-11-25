# CarPrice — Monitoramento de Preços de Carros

**🌐 Site no ar: [pricecar.netlify.app](https://pricecar.netlify.app)** · [Changelog](CHANGELOG.md) (versão atual na aba **Versões** do app e no arquivo [`VERSION`](VERSION)) · [Arquitetura](docs/ARCHITECTURE.md) · [Especificação](PROJETO_v3.md)

Busca ao vivo em vários portais brasileiros (CarroSP, Napista, iCarros, Comprecar,
Localiza, Mobiauto), compara carros iguais pelo **Preço de Mercado** (mesma
versão/modelo + ano, ajustado por km) e avisa quando aparece uma oportunidade.

## O que o app faz

| Recurso | Onde |
|---|---|
| Busca ao vivo nos portais, com filtro por marca → modelo → ano ↔ versão, preço, km, raio | aba **Busca** |
| Avaliação de cada carro: Excelente negócio / Bom preço / Preço justo / Acima / Caro | cards |
| Monitores com frequência própria (30 min a 1 dia) e limite de desconto | aba **Monitores** |
| Alertas no app (badge + notificação do navegador) e **e-mail-resumo** por monitor | aba **Alertas** |
| Conta de usuário: carros salvos ⭐, histórico de buscas, edição de perfil/senha | **Histórico** / Minha conta |
| Parâmetros do score e portais ativos (somente administradores) | **Configurações** |

## Arquitetura de produção

| Parte | Onde | Observação |
|---|---|---|
| Frontend React (Vite + Tailwind) | **Netlify** | chama o backend direto (`VITE_API_URL`) |
| Backend FastAPI | **Render** (free) | scheduler interno: tick de 15 min + limpeza diária |
| Banco Postgres | **Aiven** (`pricecar`) | dados permanentes (contas, monitores, alertas) |
| Keep-warm | **GitHub Actions** | pinga `/api/health` a cada 10 min — mantém o Render e o banco ativos |

### Variáveis de ambiente (Render → carprice-api → Environment)

| Variável | Para quê |
|---|---|
| `DATABASE_URL` | Postgres permanente (Aiven). Sem ela, usa SQLite efêmero. |
| `JWT_SECRET` | assinatura dos logins — texto aleatório longo |
| `ADMIN_EMAILS` | e-mails (vírgula) que podem editar as Configurações. **Recomendado.** Vazio = qualquer usuário logado |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | envio do e-mail-resumo dos alertas (ex.: Gmail com senha de app) |

## Rodar local (dev)

**Backend** (Python 3.12):
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000 (SQLite local; tabelas criadas no boot)
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
python -m pytest                # 41 testes: score, filtros, conectores, FIPE e API
```

`tests/test_api.py` cobre login + rate limit, escopo dos monitores, proteção das
Configurações, frequência da varredura, e-mail-resumo, limpeza e health.

## Segurança e limites

- Login com senha em hash (pbkdf2) e token JWT; rate limit de 10 tentativas de
  login / 10 min e 5 cadastros / hora por IP.
- Busca ao vivo limitada a 30 por IP a cada 10 min (cada busca raspa 6 portais).
- Monitores exigem conta; cada usuário só vê e altera os seus.
- Configurações (score e portais) só para administradores.

## Limitações conhecidas

- Webmotors/OLX/Movida usam anti-bot pesado — exigem acesso via navegador ou
  serviço pago (Fase 2). Mobiauto passou a renderizar no navegador e hoje coleta 0.
- A FIPE oficial bloqueia IP de datacenter; o catálogo (marcas/modelos/anos) é
  estático no repositório e o valor FIPE vira só fallback.
- Render free tem 512 MB de RAM — o mercado é filtrado no SQL para caber.
