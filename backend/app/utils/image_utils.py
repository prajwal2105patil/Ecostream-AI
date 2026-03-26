import hashlib
import io
import os
import uuid
from pathlib import Path
from typing import Tuple

from PIL import Image


def compute_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def save_upload(file_bytes: bytes, upload_dir: str) -> Tuple[str, str]:
    """Save raw upload; returns (relative_path, sha256_hash)."""
    file_hash = compute_sha256(file_bytes)
    Path(upload_dir).mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(upload_dir, filename)

    img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img.save(filepath, "JPEG", quality=90)
    return filepath, file_hash


def resize_for_yolo(image_path: str, size: int = 640) -> str:
    """Resize image to square for YOLO input; returns path."""
    img = Image.open(image_path).convert("RGB")
    img = img.resize((size, size), Image.LANCZOS)
    resized_path = image_path.replace(".jpg", "_resized.jpg")
    img.save(resized_path, "JPEG", quality=95)
    return resized_path


def annotated_path(original_path: str) -> str:
    """Derive annotated image path from original."""
    base, ext = os.path.splitext(original_path)
    return f"{base}_annotated{ext}"
