#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════
  CARTEIRAS TEMÁTICAS — PIPELINE PROFISSIONAL DE DADOS
  Escritório de Investimentos
═══════════════════════════════════════════════════════════

Uso:
    python3 carteiras_pipeline.py
    python3 carteiras_pipeline.py --inicio 2024-06-01 --fim 2026-01-31
    python3 carteiras_pipeline.py --carteira acoes --inicio 2024-01-01

Saída (pasta outputs/):
    cotacoes_mensais.csv      — preços de fechamento ajustado por ativo
    retornos_mensais.csv      — retorno % mensal por ativo
    performance_acumulada.csv — retorno % acumulado desde a data inicial
    resumo_carteiras.csv      — métricas consolidadas por carteira
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

# ──────────────────────────────────────────────────────────
#  CONFIGURAÇÃO
# ──────────────────────────────────────────────────────────

OUTPUT_DIR = Path(__file__).parent / "pipeline_outputs"
CACHE_DIR  = OUTPUT_DIR / ".cache"
API_BASE   = "https://brapi.dev/api"

# ┌──────────────────────────────────────────────────────────┐
# │  TABELA DE ALIASES                                        │
# │  Chave  = ticker no portfólio (novo nome)                 │
# │  Valor  = ticker na base de dados (nome histórico)        │
# │                                                           │
# │  Por que isso é necessário?                               │
# │  Quando uma empresa renomeia seu ticker na B3, as bases   │
# │  de dados históricas como brapi.dev, Yahoo Finance e      │
# │  Bloomberg continuam armazenando os dados pelo ticker     │
# │  antigo. Para obter série histórica completa, consultamos │
# │  pelo ticker original e mapeamos de volta ao novo nome.   │
# └──────────────────────────────────────────────────────────┘
TICKER_ALIAS: dict[str, str] = {
    "EMBJ3": "EMBR3",   # Embraer S.A. — renomeado (dados ainda em EMBR3)
    "AXIA3": "ELET3",   # Eletrobras PN — renomeado pós-privatização
    "AXIA6": "ELET6",   # Eletrobras PNB — renomeado pós-privatização
}


def resolve_ticker(portfolio_ticker: str) -> str:
    """Retorna o ticker correto para consulta na API."""
    return TICKER_ALIAS.get(portfolio_ticker, portfolio_ticker)


# ──────────────────────────────────────────────────────────
#  PORTFOLIOS
# ──────────────────────────────────────────────────────────

PORTFOLIOS = {
    "acoes": {
        "name": "Carteira de Ações",
        "montante": 300_000,
        "ativos": {
            "BPAC11": {"peso": 0.05, "setor": "Financeiro"},
            "BBAS3":  {"peso": 0.05, "setor": "Financeiro"},
            "ITUB4":  {"peso": 0.12, "setor": "Financeiro"},
            "JPMC34": {"peso": 0.05, "setor": "Financeiro"},
            "CPLE3":  {"peso": 0.08, "setor": "Energia"},
            "EMBJ3":  {"peso": 0.10, "setor": "Aviação"},
            "WEGE3":  {"peso": 0.05, "setor": "Indústria"},
            "GGBR4":  {"peso": 0.05, "setor": "Siderurgia"},
            "VALE3":  {"peso": 0.10, "setor": "Commodities"},
            "AURA33": {"peso": 0.10, "setor": "Mineração"},
            "AXIA3":  {"peso": 0.05, "setor": "Energia Elétrica"},  # ELET3
            "TTEN3":  {"peso": 0.06, "setor": "Agroindústria"},
            "CSMG3":  {"peso": 0.04, "setor": "Saneamento"},
            "IVVB11": {"peso": 0.10, "setor": "Índices"},
        },
    },
    "dividendos": {
        "name": "Carteira de Dividendos",
        "montante": 300_000,
        "ativos": {
            "BBDC4":  {"peso": 0.10, "setor": "Financeiro"},
            "CXSE3":  {"peso": 0.08, "setor": "Seguros"},
            "ITUB4":  {"peso": 0.15, "setor": "Financeiro"},
            "B3SA3":  {"peso": 0.05, "setor": "Financeiro"},
            "SANB11": {"peso": 0.05, "setor": "Financeiro"},
            "NDIV11": {"peso": 0.10, "setor": "Índice"},
            "PETR4":  {"peso": 0.12, "setor": "Petroquímica"},
            "VALE3":  {"peso": 0.10, "setor": "Commodities"},
            "CSMG3":  {"peso": 0.15, "setor": "Saneamento"},
            "AXIA6":  {"peso": 0.10, "setor": "Energia Elétrica"},  # ELET6
        },
    },
}

BENCHMARK = "BOVA11"  # ETF do Ibovespa como referência


# ──────────────────────────────────────────────────────────
#  API CLIENT
# ──────────────────────────────────────────────────────────

class BrapiClient:
    """
    Cliente para a API brapi.dev (B3 / dados brasileiros).
    Implementa:
      - Batch requests (até 5 tickers por chamada)
      - Retry com backoff exponencial
      - Cache em disco (JSON) para evitar re-fetching
      - Resolução automática de aliases de ticker
    """

    BATCH_SIZE = 5
    MAX_RETRIES = 3

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "CarteirasAnalytics/2.0 (internal)",
            "Accept": "application/json",
        })
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, ticker: str, interval: str, range_: str) -> Path:
        return self.cache_dir / f"{ticker}_{interval}_{range_}.json"

    def _load_cache(self, path: Path) -> dict | None:
        if path.exists():
            age = time.time() - path.stat().st_mtime
            if age < 3600 * 6:  # Cache válido por 6h
                with open(path) as f:
                    return json.load(f)
        return None

    def _save_cache(self, path: Path, data: dict):
        with open(path, "w") as f:
            json.dump(data, f)

    def _get_quote(self, ticker_api: str, interval: str = "1mo", range_: str = "2y",
                   fundamental: bool = False) -> dict | None:
        """Busca cotação de um único ticker."""
        cache_path = self._cache_key(ticker_api, interval, range_)
        cached = self._load_cache(cache_path)
        if cached:
            return cached

        params = {"range": range_, "interval": interval}
        if fundamental:
            params["fundamental"] = "true"

        for attempt in range(self.MAX_RETRIES):
            try:
                resp = self.session.get(
                    f"{API_BASE}/quote/{ticker_api}",
                    params=params,
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("results"):
                    self._save_cache(cache_path, data)
                    return data
            except requests.RequestException as e:
                wait = 2 ** attempt
                print(f"  ⚠ Tentativa {attempt+1}/{self.MAX_RETRIES} falhou para {ticker_api}: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(wait)
        return None

    def fetch_monthly_prices(
        self,
        portfolio_tickers: list[str],
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, pd.Series]:
        """
        Busca preços mensais de fechamento para uma lista de tickers.
        Aplica aliases automaticamente.

        Returns:
            dict[display_ticker → pd.Series(index=DatetimeIndex, values=close_price)]
        """
        results: dict[str, pd.Series] = {}
        start_ts = int(start_date.timestamp())

        # Include benchmark
        all_tickers = portfolio_tickers + [BENCHMARK]

        print(f"\n📥 Buscando cotações mensais: {len(all_tickers)} ativos")
        print(f"   Período: {start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')}")

        for display_ticker in all_tickers:
            api_ticker = resolve_ticker(display_ticker)
            if api_ticker != display_ticker:
                print(f"   🔁 Alias: {display_ticker} → {api_ticker}")

            data = self._get_quote(api_ticker, interval="1mo", range_="2y")
            if not data or not data.get("results"):
                print(f"   ❌ Sem dados para {display_ticker} ({api_ticker})")
                continue

            item = data["results"][0]
            hist = item.get("historicalDataPrice", [])

            if not hist:
                print(f"   ⚠ Histórico vazio: {display_ticker}")
                continue

            # Filter by date range and build Series
            filtered = [
                (datetime.fromtimestamp(d["date"]), d["close"])
                for d in hist
                if d.get("close") is not None and d["date"] >= start_ts
            ]

            if not filtered:
                print(f"   ⚠ Sem dados no período para {display_ticker}")
                continue

            dates, closes = zip(*sorted(filtered))
            series = pd.Series(closes, index=pd.DatetimeIndex(dates), name=display_ticker)
            results[display_ticker] = series
            print(f"   ✅ {display_ticker}: {len(series)} meses ({series.index[0].strftime('%m/%y')} → {series.index[-1].strftime('%m/%y')})")

            time.sleep(0.15)  # Rate limiting cortesia

        return results

    def fetch_dividend_yield(self, tickers: list[str]) -> dict[str, float | None]:
        """Busca Dividend Yield (trailing 12m) via fundamentals."""
        dy_map: dict[str, float | None] = {}
        print(f"\n📊 Buscando Dividend Yield ({len(tickers)} ativos)…")

        for display_ticker in tickers:
            api_ticker = resolve_ticker(display_ticker)
            data = self._get_quote(api_ticker, interval="1mo", range_="1y", fundamental=True)
            if data and data.get("results"):
                dy = data["results"][0].get("dividendYield")
                if dy is not None:
                    # Normalizar: brapi retorna decimal ou percentual
                    dy_pct = dy if dy > 1 else dy * 100
                    dy_map[display_ticker] = round(dy_pct, 2)
                    print(f"   ✅ {display_ticker}: DY = {dy_map[display_ticker]:.1f}%")
                else:
                    dy_map[display_ticker] = None
                    print(f"   ⚠ {display_ticker}: DY não disponível")
            else:
                dy_map[display_ticker] = None
            time.sleep(0.1)

        return dy_map


# ──────────────────────────────────────────────────────────
#  CÁLCULOS DE PERFORMANCE
# ──────────────────────────────────────────────────────────

def calculate_monthly_returns(prices: dict[str, pd.Series]) -> pd.DataFrame:
    """Calcula retorno % mensal para cada ativo."""
    returns = {}
    for ticker, series in prices.items():
        if len(series) >= 2:
            returns[ticker] = series.pct_change().mul(100).round(4)
    return pd.DataFrame(returns).sort_index()


def calculate_cumulative_returns(prices: dict[str, pd.Series]) -> pd.DataFrame:
    """Calcula retorno % acumulado desde o início do período."""
    cumulative = {}
    for ticker, series in prices.items():
        if len(series) >= 2:
            base = series.iloc[0]
            cumulative[ticker] = ((series / base) - 1).mul(100).round(4)
    return pd.DataFrame(cumulative).sort_index()


def calculate_portfolio_weighted_return(
    monthly_returns: pd.DataFrame,
    portfolio_key: str,
) -> pd.Series:
    """
    Calcula o retorno mensal ponderado da carteira.

    Fórmula: R_carteira(t) = Σ [peso_i × R_i(t)]
    onde peso_i é a alocação % do ativo i.
    """
    p = PORTFOLIOS[portfolio_key]
    weighted = pd.Series(0.0, index=monthly_returns.index)

    for ticker, info in p["ativos"].items():
        if ticker in monthly_returns.columns:
            weighted += info["peso"] * monthly_returns[ticker].fillna(0)

    return weighted.round(4)


def calculate_summary_metrics(
    monthly_returns: pd.DataFrame,
    portfolio_key: str,
) -> dict:
    """Calcula métricas consolidadas da carteira."""
    p = PORTFOLIOS[portfolio_key]
    portfolio_returns = calculate_portfolio_weighted_return(monthly_returns, portfolio_key)
    portfolio_returns_clean = portfolio_returns.dropna()

    if len(portfolio_returns_clean) == 0:
        return {}

    total_return = ((1 + portfolio_returns_clean / 100).prod() - 1) * 100
    ann_return   = ((1 + total_return / 100) ** (12 / len(portfolio_returns_clean)) - 1) * 100
    volatility   = portfolio_returns_clean.std()
    max_drawdown = (portfolio_returns_clean.cumsum() - portfolio_returns_clean.cumsum().cummax()).min()
    sharpe       = (portfolio_returns_clean.mean() / volatility * (12 ** 0.5)) if volatility > 0 else None

    return {
        "carteira": p["name"],
        "periodo_meses": len(portfolio_returns_clean),
        "retorno_total_pct": round(total_return, 2),
        "retorno_anualizado_pct": round(ann_return, 2),
        "volatilidade_mensal_pct": round(volatility, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "sharpe_ratio": round(sharpe, 3) if sharpe else None,
        "meses_positivos": int((portfolio_returns_clean > 0).sum()),
        "meses_negativos": int((portfolio_returns_clean < 0).sum()),
    }


# ──────────────────────────────────────────────────────────
#  MAIN PIPELINE
# ──────────────────────────────────────────────────────────

def run_pipeline(
    carteiras: list[str],
    start_date: datetime,
    end_date: datetime,
):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = BrapiClient()

    all_prices:  dict[str, pd.Series] = {}
    all_summary: list[dict] = []

    print("═" * 60)
    print("  CARTEIRAS TEMÁTICAS — PIPELINE DE DADOS")
    print("═" * 60)

    for carteira_key in carteiras:
        p = PORTFOLIOS[carteira_key]
        tickers = list(p["ativos"].keys())
        print(f"\n{'─'*60}")
        print(f"  Processando: {p['name']}")
        print(f"{'─'*60}")

        # 1. Fetch prices
        prices = client.fetch_monthly_prices(tickers, start_date, end_date)
        all_prices.update(prices)

        # 2. Calculate returns
        monthly   = calculate_monthly_returns(prices)
        cumulative = calculate_cumulative_returns(prices)
        port_weighted = calculate_portfolio_weighted_return(monthly, carteira_key)

        # 3. Summary metrics
        metrics = calculate_summary_metrics(monthly, carteira_key)
        all_summary.append(metrics)
        print(f"\n  📈 Retorno Total:         {metrics.get('retorno_total_pct', 'N/D')}%")
        print(f"  📈 Retorno Anualizado:    {metrics.get('retorno_anualizado_pct', 'N/D')}%")
        print(f"  📊 Volatilidade Mensal:   {metrics.get('volatilidade_mensal_pct', 'N/D')}%")
        print(f"  📉 Máx. Drawdown:         {metrics.get('max_drawdown_pct', 'N/D')}%")
        print(f"  ⚡ Sharpe Ratio:          {metrics.get('sharpe_ratio', 'N/D')}")

        # 4. Save per-portfolio CSVs
        tag = carteira_key
        monthly_out = monthly.copy()
        monthly_out[f"CARTEIRA_{tag.upper()}"] = port_weighted
        if BENCHMARK in monthly_out.columns:
            monthly_out[f"BOVA11_REF"] = monthly_out[BENCHMARK]

        monthly_out.index = monthly_out.index.strftime("%Y-%m")
        cumulative.index  = cumulative.index.strftime("%Y-%m")

        monthly_out.to_csv(OUTPUT_DIR / f"retornos_mensais_{tag}.csv", float_format="%.4f")
        cumulative.to_csv(OUTPUT_DIR / f"performance_acumulada_{tag}.csv", float_format="%.4f")
        print(f"\n  💾 Salvo: retornos_mensais_{tag}.csv")
        print(f"  💾 Salvo: performance_acumulada_{tag}.csv")

        # 5. Fetch DY (optional)
        dy = client.fetch_dividend_yield(tickers)
        dy_rows = [
            {"ticker": t, "dy_12m_pct": v, "setor": p["ativos"][t]["setor"], "peso": p["ativos"][t]["peso"]}
            for t, v in dy.items()
        ]
        pd.DataFrame(dy_rows).to_csv(OUTPUT_DIR / f"dividend_yield_{tag}.csv", index=False)
        print(f"  💾 Salvo: dividend_yield_{tag}.csv")

    # 6. Save global prices
    if all_prices:
        price_df = pd.DataFrame(all_prices).sort_index()
        price_df.index = price_df.index.strftime("%Y-%m")
        price_df.to_csv(OUTPUT_DIR / "cotacoes_mensais.csv", float_format="%.2f")
        print(f"\n  💾 Salvo: cotacoes_mensais.csv ({price_df.shape[0]} meses × {price_df.shape[1]} ativos)")

    # 7. Summary
    if all_summary:
        pd.DataFrame(all_summary).to_csv(OUTPUT_DIR / "resumo_carteiras.csv", index=False)
        print(f"  💾 Salvo: resumo_carteiras.csv")

    print(f"\n{'═'*60}")
    print(f"  ✅ Pipeline concluído! Arquivos em: {OUTPUT_DIR.resolve()}")
    print(f"{'═'*60}\n")


# ──────────────────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Pipeline de dados para Carteiras Temáticas",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Exemplos:
  python3 carteiras_pipeline.py
  python3 carteiras_pipeline.py --inicio 2024-06-01 --fim 2026-01-31
  python3 carteiras_pipeline.py --carteira acoes --inicio 2023-01-01
        """,
    )
    parser.add_argument("--inicio",   default="2024-06-01", help="Data inicial (YYYY-MM-DD)")
    parser.add_argument("--fim",      default="2026-01-31", help="Data final (YYYY-MM-DD)")
    parser.add_argument("--carteira", default="todas",
                        choices=["todas", "acoes", "dividendos"],
                        help="Carteira a processar (default: todas)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    try:
        start = datetime.strptime(args.inicio, "%Y-%m-%d")
        end   = datetime.strptime(args.fim,    "%Y-%m-%d")
    except ValueError as e:
        print(f"❌ Formato de data inválido: {e}")
        sys.exit(1)

    carteiras = list(PORTFOLIOS.keys()) if args.carteira == "todas" else [args.carteira]
    run_pipeline(carteiras, start, end)
