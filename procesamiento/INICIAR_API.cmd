@echo off
setlocal
cd /d "%~dp0"
rem Usa el entorno neuronal si existe; si no, la API arranca solo con el motor clasico.
set "PY=%~dp0.venv-neural\Scripts\python.exe"
if not exist "%PY%" (
  set "PY=%~dp0.venv\Scripts\python.exe"
  set "MOTOR=clasico"
)
echo API local: http://127.0.0.1:8000/docs
echo Espera el mensaje Application startup complete para usarla.
"%PY%" -X utf8 -m uvicorn api:app --host 127.0.0.1 --port 8000
pause
