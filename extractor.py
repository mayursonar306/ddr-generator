# extractor.py — extract text and images from PDFs

import io
import os
from PIL import Image
import pdfplumber
from pypdf import PdfReader


def extract_text(pdf_path: str) -> str:
    """Read all text from a PDF. Returns one big string."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
    except Exception as e:
        text = f"[Error reading PDF: {e}]"
    return text


def extract_images(pdf_path: str, output_dir: str, prefix: str) -> list:
    """
    Pull all embedded images from a PDF and save as JPEGs.
    Skips tiny icons and wide banner images.
    Returns list of saved file paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    count = 0

    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            if not hasattr(page, "images"):
                continue
            for img in page.images:
                try:
                    pil = Image.open(io.BytesIO(img.data)).convert("RGB")
                    w, h = pil.size
                    ratio = w / h
                    # Skip icons (too small) and banners (too wide)
                    if w < 300 or h < 200 or ratio > 3.0 or ratio < 0.33:
                        continue
                    path = os.path.join(output_dir, f"{prefix}_{count:04d}.jpg")
                    pil.save(path, "JPEG", quality=88)
                    paths.append(path)
                    count += 1
                except Exception:
                    continue
    except Exception:
        pass

    return paths


def split_thermal_images(thermal_photos: list) -> list:
    """
    Thermal PDFs have image pairs: IR scan + visual photo.
    Return only the IR scans (even-indexed).
    """
    return [p for i, p in enumerate(thermal_photos) if i % 2 == 0]