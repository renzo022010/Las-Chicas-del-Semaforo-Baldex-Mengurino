"""Punto de entrada de la API local. Iniciar con INICIAR_API.cmd o INICIAR.bat (raiz); documentacion /docs.
El codigo esta en app/: controllers (rutas), services (logica) y schemas (validacion).
Si existe web/ (PWA compilada) se sirve en el mismo puerto; CLAVE_ACCESO protege la API al abrirla a la red."""
from app.config import WEB_DIR,access_key
from app.main import create_app

app=create_app(web_dir=WEB_DIR,access_key=access_key())
