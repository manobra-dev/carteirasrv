@echo off
echo.
echo ==========================================
echo   SALVANDO E ENVIANDO ALTERACOES
echo ==========================================
echo.

cd /d "%~dp0"

git status

echo.
set /p MSG="Descricao do que foi alterado (pode deixar vazio): "
if "%MSG%"=="" set MSG=atualizacao

git add -A
git commit -m "%MSG%"
git push

echo.
echo ==========================================
echo   Alteracoes salvas e enviadas!
echo   Railway vai atualizar automaticamente.
echo ==========================================
echo.
pause
