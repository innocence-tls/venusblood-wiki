"""Размыть обложки игр для публикации.

Оригиналы лежат в originals/ (папка не попадает в git), размытые копии — в static/art/
под тем же именем. Новую обложку: положить в originals/cover-<slug>.webp и запустить

    python tools/blur_covers.py
"""
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
RADIUS = 0.05  # доля ширины картинки

for source in sorted((ROOT / "originals").glob("cover-*.webp")):
    image = Image.open(source).convert("RGB")
    blurred = image.filter(ImageFilter.GaussianBlur(image.width * RADIUS))
    blurred.save(ROOT / "static/art" / source.name, quality=80)
    print(source.name)
