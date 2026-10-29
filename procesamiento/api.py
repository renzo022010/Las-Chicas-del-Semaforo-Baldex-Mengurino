"""Punto de entrada de la API local. Iniciar con INICIAR_API.cmd; documentacion /docs.
El codigo esta en app/: controllers (rutas), services (logica) y schemas (validacion)."""
from app.main import create_app

app=create_app()
