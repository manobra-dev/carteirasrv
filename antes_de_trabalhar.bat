@echo off
echo.
echo ==========================================
echo   SINCRONIZANDO COM A VERSAO MAIS RECENTE
echo ==========================================
echo.

cd /d "%~dp0"
git pull

echo.
echo ==========================================
echo   Pronto! Pode abrir o Cowork agora.
echo ==========================================
echo.
pause
