#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  atualizar_railway.sh — Atualiza os dados do dashboard no Railway
# ─────────────────────────────────────────────────────────────────────────────
#
#  O que faz:
#    1. Busca cotações atualizadas via yfinance (retorno total com dividendos)
#    2. Salva em dashboard_data.json
#    3. Commita e faz push → Railway faz redeploy automaticamente
#
#  Uso:
#    ./atualizar_railway.sh
#    ./atualizar_railway.sh "comentário customizado"   (opcional)
#
#  Pré-requisito: estar na branch main com o repositório limpo
# ─────────────────────────────────────────────────────────────────────────────

set -e  # para em caso de erro

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ATUALIZAR DADOS DO RAILWAY"
echo "═══════════════════════════════════════════════════════"

# ── Verifica se está na branch main ──────────────────────
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" != "main" ]; then
  echo "  ⚠  Você está na branch '$BRANCH', não 'main'."
  read -rp "     Continuar mesmo assim? (s/N) " resp
  [[ "$resp" =~ ^[sS]$ ]] || { echo "  Abortado."; exit 1; }
fi

# ── Busca dados frescos via yfinance ─────────────────────
echo ""
echo "  📥  Buscando cotações atualizadas (yfinance + brapi)…"
python3 serve.py --sem-browser

echo ""
echo "  ✅  dashboard_data.json atualizado."

# ── Commita o JSON ────────────────────────────────────────
DATA=$(date +"%Y-%m-%d")
MSG="${1:-"data: atualiza cotações $DATA"}"

git add dashboard_data.json
if git diff --cached --quiet; then
  echo "  ℹ   Sem mudanças nos dados. Nada a commitar."
  exit 0
fi

git commit -m "$MSG"

# ── Push → dispara redeploy no Railway ───────────────────
echo ""
echo "  🚀  Enviando para o GitHub (Railway vai redeployar)…"
git push

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Concluído! Railway irá redeployar em instantes."
echo "  Acompanhe em: https://railway.app"
echo "═══════════════════════════════════════════════════════"
echo ""
