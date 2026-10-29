"""Rutas y limites de la API local."""
from pathlib import Path
import os
ROOT=Path(__file__).resolve().parent.parent
OUTPUT=ROOT/'resultados/api'
SAMPLES_DB=ROOT/'resultados/muestras.db'
MAX_BYTES=20*1024*1024
MAX_PIXELS=60_000_000
RESULT_FILES=('foto_conteo.jpg','foto_original.jpg','foto_resultado.json','foto_segments.png','foto_instances.png','foto_roi.png','revision.json')

def hybrid_requested():
    """MOTOR=clasico evita cargar el modelo neuronal."""
    return not os.environ.get('MOTOR','hibrido').lower().startswith('clas')
