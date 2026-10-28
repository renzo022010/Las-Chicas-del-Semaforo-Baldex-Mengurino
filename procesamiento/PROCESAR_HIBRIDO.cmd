@echo off
setlocal
set "BASE=%~dp0"
if "%~1"=="" (
  set "PHOTO=%BASE%..\Dataset\AGAR_representative\higher-resolution\dark\5271.jpg"
) else (
  set "PHOTO=%~1"
)
"%BASE%.venv-neural\Scripts\python.exe" -X utf8 "%BASE%contador_hibrido.py" "%PHOTO%" --output "%BASE%resultados\hibrido_individual"
if errorlevel 1 (
  echo Error. Revisa el mensaje anterior y README_HIBRIDO.md.
  pause
  exit /b 1
)
explorer "%BASE%resultados\hibrido_individual"
pause
