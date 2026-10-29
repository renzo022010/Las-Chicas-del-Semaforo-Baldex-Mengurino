"""Lectura y validacion de fotos subidas."""
import io
import cv2,numpy as np
from PIL import Image,ImageOps,UnidentifiedImageError
from app.config import MAX_PIXELS

class InvalidPhoto(ValueError):pass

def decode_photo(raw:bytes):
    """Devuelve la foto en BGR. Aplica la rotacion EXIF de los celulares para que foto y coordenadas coincidan con lo que vio el usuario."""
    try:
        with Image.open(io.BytesIO(raw)) as image:
            w,h=image.size
            if min(w,h)<64 or w*h>MAX_PIXELS:raise InvalidPhoto('Dimensiones no permitidas')
            rgb=np.asarray(ImageOps.exif_transpose(image).convert('RGB'))
    except InvalidPhoto:raise
    except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError) as exc:
        raise InvalidPhoto(str(exc)) from exc
    return cv2.cvtColor(rgb,cv2.COLOR_RGB2BGR)
