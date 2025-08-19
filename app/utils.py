from __future__ import annotations

from typing import Iterable
from PIL import Image
from io import BytesIO


def allowed_file(filename: str, allowed: Iterable[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in set(allowed)


def validate_image_file(file_storage) -> bool:
    """Valida integridade básica com Pillow e checa mimetype image/*.

    Compatível com Python 3.13 (sem imghdr)."""
    try:
                                     
        if not (getattr(file_storage, 'mimetype', '') or '').startswith('image/'):
                                                          
            pass
                             
        data = file_storage.read()
        file_storage.seek(0)
        img = Image.open(BytesIO(data))
        img.verify()
        file_storage.seek(0)
        return True
    except Exception:
        file_storage.seek(0)
        return False





