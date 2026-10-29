"""Rutas y limites de la API local."""
from pathlib import Path
import os
ROOT=Path(__file__).resolve().parent.parent
OUTPUT=ROOT/'resultados/api'
SAMPLES_DB=ROOT/'resultados/muestras.db'
MAX_BYTES=20*1024*1024
MAX_PIXELS=60_000_000
RESULT_FILES=('foto_conteo.jpg','foto_original.jpg','foto_resultado.json','foto_segments.png','foto_instances.png','foto_roi.png','revision.json')
WEB_DIR=ROOT/'web'  # PWA compilada (npm run build en pwa/)

def hybrid_requested():
    """MOTOR=clasico evita cargar el modelo neuronal."""
    return not os.environ.get('MOTOR','hibrido').lower().startswith('clas')

def access_key():
    """CLAVE_ACCESO protege la API cuando se abre a la red; sin ella la API queda libre (uso local)."""
    return os.environ.get('CLAVE_ACCESO') or None
