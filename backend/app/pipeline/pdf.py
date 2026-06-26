"""PDF extraction with PyMuPDF, falling back to OCR for scanned pages.

Text is tagged with page markers so downstream tools can cite pages.
"""

from __future__ import annotations

import io
import time

from ..schemas import ExtractedDoc
from .base import ExtractionOutcome, InputFile


def _ocr_pixmap(png_bytes: bytes) -> tuple[str, float | None]:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except Exception:
        return "", None
    try:
        img = Image.open(io.BytesIO(png_bytes))
        data_dict = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        words, confs = [], []
        for word, conf in zip(data_dict.get("text", []), data_dict.get("conf", []), strict=False):
            try:
                c = float(conf)
            except (TypeError, ValueError):
                c = -1.0
            if word.strip() and c >= 0:
                words.append(word)
                confs.append(c)
        text = " ".join(words).strip()
        confidence = (sum(confs) / len(confs) / 100.0) if confs else None
        return text, confidence
    except Exception:
        return "", None


def _extract_sync(data: bytes) -> tuple[str, float | None, int]:
    """Return (text, ocr_confidence_or_None, n_pages)."""
    import fitz  # type: ignore  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    parts: list[str] = []
    ocr_confs: list[float] = []
    used_ocr = False
    for i, page in enumerate(doc):
        page_text = (page.get_text() or "").strip()
        if len(page_text) < 15:  # likely scanned — OCR fallback
            try:
                pix = page.get_pixmap(dpi=200)
                ocr_text, conf = _ocr_pixmap(pix.tobytes("png"))
                if ocr_text:
                    used_ocr = True
                    page_text = ocr_text
                    if conf is not None:
                        ocr_confs.append(conf)
            except Exception:
                pass
        parts.append(f"[Page {i + 1}]\n{page_text}".rstrip())
    n_pages = doc.page_count
    doc.close()
    text = "\n\n".join(parts).strip()
    confidence = (sum(ocr_confs) / len(ocr_confs)) if (used_ocr and ocr_confs) else None
    return text, confidence, n_pages


async def extract_pdf(file: InputFile) -> ExtractionOutcome:
    import asyncio

    started = time.time()
    try:
        text, confidence, n_pages = await asyncio.to_thread(_extract_sync, file.data)
    except Exception as exc:
        return ExtractionOutcome(
            doc=None,
            tool="pdf_extract",
            duration_ms=int((time.time() - started) * 1000),
            ok=False,
            error=f"PDF parse failed: {exc}",
        )
    duration_ms = int((time.time() - started) * 1000)
    if not text:
        return ExtractionOutcome(
            doc=None,
            tool="pdf_extract",
            duration_ms=duration_ms,
            ok=False,
            error="No extractable text found in PDF.",
        )
    doc = ExtractedDoc(
        source=file.filename,
        kind="pdf",
        content=text,
        ocr_confidence=round(confidence, 3) if confidence is not None else None,
    )
    return ExtractionOutcome(
        doc=doc, tool="pdf_extract", duration_ms=duration_ms, metadata={"pages": n_pages}
    )
