@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  atualizar_railway.bat — Atualiza os dados do dashboard no Railway (Windows)
REM ─────────────────────────────────────────────────────────────────────────────
REM
REM  O que faz:
REM    1. Busca cotacoes atualizadas via yfinance (retorno total com dividendos)
REM    2. Salva em dashboard_data.json
REM    3. Commita e faz push -> Railway faz redeploy automaticamente
REM
REM  Uso:
REM    atualizar_railway.bat
REM
REM  Pre-requisito: estar na branch main com o repositorio limpo
REM ─────────────────────────────────────────────────────────────────────────────

cd /d "%~dp0"

echo.
echo ═══════════════════════════════════════════════════════
echo   ATUALIZAR DADOS DO RAILWAY
echo ═══════════════════════════════════════════════════════

REM ── Verifica branch ──────────────────────────────────────
for /f "tokens=*" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
if /i not "%BRANCH%"=="main" (
  echo   AVISO: Voce esta na branch '%BRANCH%', nao 'main'.
  set /p RESP="  Continuar mesmo assim? (s/N) "
  if /i not "%RESP%"=="s" (
    echo   Abortado.
    exit /b 1
  )
)

REM ── Busca dados frescos via yfinance ─────────────────────
echo.
echo   Buscando cotacoes atualizadas (yfinance + brapi)...
python serve.py --so-atualizar
if errorlevel 1 (
  echo   ERRO ao rodar serve.py. Verifique o Python e as dependencias.
  exit /b 1
)

echo.
echo   dashboard_data.json atualizado.

REM ── Commita o JSON ────────────────────────────────────────
for /f "tokens=1-3 delims=/" %%a in ('date /t') do set DATA=%%c-%%b-%%a
set MSG=data: atualiza cotacoes %DATA%

git add dashboard_data.json

REM Verifica se ha mudancas para commitar
git diff --cached --quiet
if %errorlevel%==0 (
  echo   Sem mudancas nos dados. Nada a commitar.
  exit /b 0
)

git commit -m "%MSG%"

REM ── Push → dispara redeploy no Railway ───────────────────
echo.
echo   Enviando para o GitHub (Railway vai redeployar)...
git push

echo.
echo ═══════════════════════════════════════════════════════
echo   Concluido! Railway ira redeployar em instantes.
echo   Acompanhe em: https://railway.app
echo ═══════════════════════════════════════════════════════
echo.
