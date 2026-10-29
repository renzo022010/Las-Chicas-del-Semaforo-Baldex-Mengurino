@echo off
setlocal
rem Inicia todo: Python portable en runtime\, servidor (PWA + API) y abre la app en el navegador.
rem Uso: INICIAR.cmd [compartir] [--instalar-ia] [--puerto N] [--nueva-clave] [--sin-navegador]
chcp 65001 >nul
cd /d "%~dp0"
set "RT=%~dp0runtime"
set "UV_EXE=%RT%\uv.exe"
set "UV_PYTHON_INSTALL_DIR=%RT%\python"
set "UV_CACHE_DIR=%RT%\cache"
if not exist "%RT%" mkdir "%RT%"

if not exist "%UV_EXE%" (
  echo Descargando uv, el instalador de Python portable ^(solo la primera vez^)...
  curl -L --fail --silent --show-error -o "%RT%\uv.zip" https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip || goto :error
  tar -xf "%RT%\uv.zip" -C "%RT%" || goto :error
  del "%RT%\uv.zip"
)
if not exist "%RT%\venv\Scripts\python.exe" (
  echo Preparando Python 3.12 portable en runtime\ ^(solo la primera vez^)...
  "%UV_EXE%" venv --python 3.12 --python-preference only-managed "%RT%\venv" || goto :error
)
"%RT%\venv\Scripts\python.exe" -X utf8 "%~dp0procesamiento\lanzador.py" %*
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo No se pudo iniciar. Revisa el mensaje anterior.
pause
exit /b 1
