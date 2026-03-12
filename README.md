# Carteiras Temáticas — Dashboard Eleva MFO

Dashboard interativo de acompanhamento das Carteiras Temáticas (Ações e Dividendos), com performance acumulada, rentabilidade por ativo, risco e factsheets em PDF.

---

## Estrutura do projeto

```
Tematica/
├── serve.py                       # Servidor local: busca dados + gera JSON + HTTP
├── dashboard_carteiras_v2.html    # Dashboard (HTML/CSS/JS, sem build)
├── gerar_factsheet.py             # Geração de factsheets em PDF
├── atualizar_railway.sh           # Script para atualizar dados no Railway
├── dashboard_data.json            # Snapshot dos dados (commitado, usado pelo Railway)
├── rebalanceamentos_template.xlsx # Fonte de verdade: pesos históricos por mês
├── comentario.txt                 # Comentário de gestão do mês (para o factsheet)
├── logo_eleva_branco.png          # Logo para o factsheet
├── requirements.txt               # Dependências Python
├── Dockerfile                     # Build para deploy (Docker)
├── railway.toml                   # Config de deploy Railway
├── arquivo/                       # Snapshots e arquivos históricos (não usados)
└── README.md
```

---

## Setup em um novo computador

```bash
# 1. Clonar o repositório
git clone <url-do-repo>
cd Tematica

# 2. Instalar dependências Python (uma vez por máquina)
pip install -r requirements.txt

# 3. Abrir o dashboard com os dados já commitados
python serve.py
```

O repositório já inclui um `dashboard_data.json` atualizado — o dashboard abre imediatamente. Ao rodar `serve.py`, os dados são atualizados automaticamente via yfinance antes de abrir o browser.

> **Fluxo entre PCs (casa ↔ trabalho):**
> 1. Rode `python serve.py` no PC atual (atualiza os dados)
> 2. `git add dashboard_data.json && git commit -m "data: atualiza" && git push`
> 3. No outro PC: `git pull` → `python serve.py`

---

## Atualizar o Railway (dados e código)

O Railway usa o `dashboard_data.json` commitado — **não rebusca dados sozinho**. Isso garante que Railway e PC local mostrem exatamente os mesmos números (retorno total com dividendos).

Para atualizar os dados exibidos no Railway:

```bash
./atualizar_railway.sh
```

O script faz tudo: busca cotações atualizadas, commita o JSON e faz push. O Railway redeploye automaticamente em seguida.

> **Quando rodar:** sempre que quiser que o Railway reflita os dados mais recentes (tipicamente uma vez por mês, após o rebalanceamento).

---

## Atualizar pesos mensais

1. Abra `rebalanceamentos_template.xlsx`
2. Adicione uma coluna com o mês novo (`YYYY-MM`) nas abas `Ações` e/ou `Dividendos`
3. Preencha os pesos (%) de cada ticker
4. Salve e rode `./atualizar_railway.sh` para atualizar local + Railway

O serve.py lê automaticamente todos os meses da planilha. Novos tickers aparecem no dashboard sem necessidade de editar código.

---

## Gerar factsheet

```bash
python gerar_factsheet.py
```

Gera PDFs em `factsheet_acoes.pdf` e `factsheet_dividendos.pdf`. Edite `comentario.txt` com o comentário de gestão do mês antes de gerar.

---

## Flags do serve.py

| Flag | Efeito |
|------|--------|
| `--sem-browser` | Não abre o browser automaticamente |
| `--porta 8080` | Porta customizada (padrão: 8000) |
| `--so-servir` | Só sobe o servidor, sem rebuscar dados (usado pelo Railway) |
| `--sem-yfinance` | Usa somente brapi.dev (price return, sem dividendos) |
| `--sem-fundamentus` | Pula busca de DY do Fundamentus |
| `--inicio 2024-01` | Data inicial customizada (YYYY-MM) |

---

## Token brapi.dev (opcional)

Para evitar rate limiting, adicione o token em `serve.py`:

```python
BRAPI_TOKEN = "seu_token_aqui"  # linha ~82
```

Token gratuito em: https://brapi.dev/dashboard

---

## Tickers com troca de código histórico

| Ticker exibido | Código antigo | Código novo | Cutoff |
|----------------|---------------|-------------|--------|
| EMBJ3          | EMBR3         | EMBJ3       | Out/2025 |
| JBSS32         | JBSS3         | JBSS32      | Jul/2025 |

O serve.py costura automaticamente o histórico dos dois códigos para cada ticker.
