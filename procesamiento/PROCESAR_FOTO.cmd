@echo off
setlocal
set "BASE=%~dp0"
if not exist "%BASE%.venv\Scripts\python.exe" (
  echo No se encuentra el entorno Python. Consulta README.md.
  pause
  exit /b 1
)
if "%~1"=="" (
  "%BASE%.venv\Scripts\python.exe" -X utf8 "%BASE%contador.py" "%BASE%..\Dataset\AGAR_representative\higher-resolution\dark\5308.jpg" --output "%BASE%resultados\individual"
) else (
  "%BASE%.venv\Scripts\python.exe" -X utf8 "%BASE%contador.py" "%~1" --output "%BASE%resultados\individual"
)
if errorlevel 1 (
  echo No se pudo procesar la imagen. Revisa el mensaje anterior.
  pause
  exit /b 1
)
echo.
echo Resultados guardados en: %BASE%resultados\individual
echo Los circulos son candidatos y requieren revision.
explorer "%BASE%resultados\individual"
pause
