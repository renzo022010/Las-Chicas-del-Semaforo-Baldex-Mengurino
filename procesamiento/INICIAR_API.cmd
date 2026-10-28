@echo off
setlocal
cd /d "%~dp0"
echo API local: http://127.0.0.1:8000/docs
echo Espera el mensaje Application startup complete para usarla.
"%~dp0.venv-neural\Scripts\python.exe" -X utf8 -m uvicorn api:app --host 127.0.0.1 --port 8000
pause
