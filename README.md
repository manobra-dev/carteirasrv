# Carteiras Temáticas — Dashboard Eleva MFO

Dashboard interativo de acompanhamento das Carteiras Temáticas (Ações e Dividendos), com performance acumulada, rentabilidade por ativo, risco e factsheets em PDF.

---

## Estrutura do projeto

```
Tematica/
├── serve.py                       # Servidor local: busca dados + gera JSON + HTTP
├── dashboard_carteiras_v2.html    # Dashboard interativo (abre no browser)
├── factsheet.html                 # Factsheet 2 páginas — exportar como PDF pelo browser
├── gerar_factsheet.py             # Alternativa: gera PDF direto via Python/matplotlib
├── carteiras_pipeline.py          # Pipeline de dados: gera CSVs de retorno/performance
├── dashboard_data.json            # Snapshot dos dados (commitado, usado pelo Railway)
├── rebalanceamentos_template.xlsx # Fonte de verdade: pesos históricos por mês
├── comentario.txt                 # Comentário de gestão do mês (para o factsheet)
├── logo_eleva_branco.png          # Logo para o factsheet
├── requirements.txt               # Dependências Python
├── Dockerfile                     # Build para deploy (Docker)
├── railway.toml                   # Config de deploy Railway (fonte de verdade)
├── nixpacks.toml                  # Config de build Railway (nixpacks)
├── Procfile                       # Fallback de start command
├── antes_de_trabalhar.bat         # Script Windows: sincroniza antes de começar
├── salvar_e_enviar.bat            # Script Windows: salva e envia alterações
├── atualizar_railway.sh           # Script Linux/Mac: atualiza dados no Railway
├── atualizar_railway.bat          # Script Windows: atualiza dados no Railway
└── README.md
```

---

## Setup em um novo computador

```bash
# 1. Clonar o repositório
git clone https://github.com/manobra-dev/carteirasrv.git
cd carteirasrv

# 2. Instalar dependências Python (uma vez por máquina)
pip install -r requirements.txt

# 3. Abrir o dashboard com os dados já commitados
python serve.py
```

O repositório já inclui um `dashboard_data.json` atualizado — o dashboard abre imediatamente. Ao rodar `serve.py`, os dados são atualizados automaticamente via yfinance antes de abrir o browser.

---

## Fluxo de trabalho diário (casa ↔ trabalho)

Use os scripts `.bat` para sincronizar entre computadores:

| Quando | Script | O que faz |
|--------|--------|-----------|
| Antes de começar | `antes_de_trabalhar.bat` | Baixa as últimas alterações do GitHub |
| Ao terminar | `salvar_e_enviar.bat` | Salva e envia as alterações para o GitHub |

> O Cowork (Claude) cuida dos commits durante a sessão de trabalho.
> O Railway atualiza automaticamente após cada push.

---

## Gerar o factsheet mensal

**Opção 1 — Via browser (recomendado):**
1. Abra o dashboard e clique em **"Exportar Factsheet PDF"**
2. Isso abre `factsheet.html` em nova aba
3. Clique em **"Salvar como PDF"** e salve como PDF no diálogo de impressão

**Opção 2 — Via Python (gera PDF diretamente):**
```bash
python gerar_factsheet.py
```
Gera `factsheet_acoes.pdf` e `factsheet_dividendos.pdf`. Edite `comentario.txt` com o comentário de gestão do mês antes de gerar.

---

## Atualizar o Railway (dados e código)

O Railway usa o `dashboard_data.json` commitado — **não rebusca dados sozinho**. Isso garante que Railway e PC local mostrem exatamente os mesmos números (retorno total com dividendos).

Para atualizar os dados exibidos no Railway:

- **Windows:** `atualizar_railway.bat`
- **Linux/Mac:** `./atualizar_railway.sh`

O script faz tudo: busca cotações atualizadas, commita o JSON e faz push. O Railway redeploye automaticamente em seguida.

> **Quando rodar:** uma vez por mês, após o fechamento do mês e o rebalanceamento.

---

## Atualizar pesos mensais

1. Abra `rebalanceamentos_template.xlsx`
2. Adicione uma coluna com o mês novo (`YYYY-MM`) nas abas `Ações` e/ou `Dividendos`
3. Preencha os pesos (%) de cada ticker
4. Salve e rode `atualizar_railway.bat` para atualizar local + Railway

O `serve.py` lê automaticamente todos os meses da planilha. Novos tickers aparecem no dashboard sem necessidade de editar código.

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

| Ticker exibido | Código antigo | Motivo |
|----------------|---------------|--------|
| EMBJ3 | EMBR3 | Renomeado Out/2025 |
| JBSS32 | JBSS3 | Renomeado Jul/2025 |
| AXIA3 | ELET3 | Renomeado pós-privatização |
| AXIA6 | ELET6 | Renomeado pós-privatização |

O `serve.py` costura automaticamente o histórico dos dois códigos para cada ticker.

---

## Arquitetura de dados

```
rebalanceamentos_template.xlsx  →  serve.py  →  dashboard_data.json
                                                        ↓
                              dashboard_carteiras_v2.html (local + Railway)
                                                        ↓
                                              factsheet.html (PDF via browser)
```

O `dashboard_data.json` é a única fonte de dados do frontend — tanto local quanto no Railway. Para garantir consistência, ele é gerado com yfinance (retorno total, incluindo dividendos) localmente e commitado no GitHub.
