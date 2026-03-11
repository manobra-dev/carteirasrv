# Carteiras Temáticas — Dashboard Eleva MFO

Dashboard interativo de acompanhamento das Carteiras Temáticas (Ações e Dividendos), com performance acumulada, rentabilidade por ativo, risco e factsheets em PDF.

---

## Estrutura do projeto

```
Tematica/
├── serve.py                      # Servidor local: busca dados + gera JSON + HTTP
├── dashboard_carteiras_v2.html   # Dashboard (HTML/CSS/JS, sem build)
├── gerar_factsheet.py            # Geração de factsheets em PDF
├── dashboard_data.json           # JSON gerado pelo serve.py (snapshot commitado)
├── carteiras_jan2026_v2.xlsx     # Planilha de pesos históricos (fonte de verdade)
├── rebalanceamentos_template.xlsx# Template para novos rebalanceamentos
├── logo_eleva_branco.png         # Logo para o factsheet
├── requirements.txt              # Dependências Python
├── Dockerfile                    # Build para deploy
├── railway.toml                  # Config de deploy Railway
└── README.md
```

---

## Uso local

**Pré-requisitos:** Python 3.11+, dependências em `requirements.txt`

```bash
pip install -r requirements.txt
python serve.py
```

O serve.py irá:
1. Buscar cotações mensais ajustadas (yfinance → fallback brapi.dev)
2. Buscar Dividend Yield (Fundamentus → brapi → estático)
3. Buscar CDI mensal (BCB)
4. Salvar `dashboard_data.json`
5. Abrir o dashboard em `http://localhost:8000`

**Flags úteis:**

| Flag | Efeito |
|------|--------|
| `--sem-browser` | Não abre o browser automaticamente |
| `--porta 8080` | Porta customizada (padrão: 8000) |
| `--sem-yfinance` | Usa somente brapi.dev (sem retorno total por dividendos) |
| `--sem-fundamentus` | Pula busca de DY do Fundamentus |
| `--inicio 2024-01` | Data inicial customizada (YYYY-MM) |

---

## Atualizar pesos mensais

1. Abra `carteiras_jan2026_v2.xlsx`
2. Adicione uma coluna com o mês novo (`YYYY-MM`) na aba `Ações` e/ou `Dividendos`
3. Preencha os pesos (%) de cada ticker
4. Salve o arquivo e rode `python serve.py` novamente

O serve.py lê automaticamente todos os meses da planilha. Novos tickers aparecem no dashboard sem necessidade de editar código.

---

## Gerar factsheet

```bash
python gerar_factsheet.py
```

Gera PDFs em `factsheet_acoes.pdf` e `factsheet_dividendos.pdf`. Edite o arquivo `comentario.txt` com o comentário de gestão do mês antes de gerar.

---

## Deploy (Railway)

O deploy é automático via `railway.toml`. O serve.py sobe com `--sem-browser` e regenera o JSON na inicialização. O healthcheck aponta para o HTML principal.

Para deploys onde yfinance não estiver disponível (bloqueio de rede), use a flag `--sem-yfinance` no `startCommand` do `railway.toml`.

---

## Token brapi.dev (opcional)

Para evitar rate limiting, adicione o token em `serve.py`:

```python
BRAPI_TOKEN = "seu_token_aqui"  # linha ~82
```

Token gratuito em: https://brapi.dev/dashboard

---

## Tickers com troca de código (stitch)

| Ticker exibido | Código antigo | Código novo | Cutoff |
|----------------|---------------|-------------|--------|
| EMBJ3          | EMBR3         | EMBJ3       | Out/2025 |
| JBSS32         | JBSS3         | JBSS32      | Jul/2025 |

O serve.py costura automaticamente o histórico dos dois códigos para cada ticker.
