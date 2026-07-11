"""PDF extraction with PyMuPDF, plus OCR for scanned pages.

Digital pages are read directly. A page with little or no extractable text but
an embedded image (a scan) is rasterised and OCR'd — Gemini vision first (needs
only an API key, no local binary), then Tesseract as a fallback that also yields
a real confidence score. Every page is tagged with a ``[Page N]`` marker so
downstream tools can cite pages, and a page that genuinely can't be read is
labelled explicitly rather than dropped silently.
"""

from __future__ import annotations

import asyncio
import io
import time

from ..gemini_client import GeminiClient, LLMUnavailable
from ..schemas import ExtractedDoc
from .base import ExtractionOutcome, InputFile

# Below this many characters a page is treated as scanned and sent to OCR.
_MIN_PAGE_CHARS = 15
_UNREADABLE = "[unreadable page — OCR unavailable; install Tesseract or set GEMINI_API_KEY]"
_OCR_PROMPT = (
    "Transcribe ALL text in this page image exactly, preserving reading order, "
    "line breaks, tables, and code indentation. Output only the transcribed "
    "text, with no commentary."
)


def _has_image(page) -> bool:
    try:
        return bool(page.get_images(full=True))
    except Exception:
        return True  # can't tell — err toward attempting OCR


def _read_pages(data: bytes) -> tuple[int, list[tuple[str, bytes | None]]]:
    """Open the PDF and return ``(page_count, [(text, png_or_None), ...])``.

    A PNG is rendered only for pages that look scanned (little text but an
    embedded image), so digital pages incur no rasterisation cost. All PyMuPDF
    work is confined to this function because ``fitz`` objects are not async-safe.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        pages: list[tuple[str, bytes | None]] = []
        for page in doc:
            text = (page.get_text() or "").strip()
            png = None
            if len(text) < _MIN_PAGE_CHARS and _has_image(page):
                try:
                    png = page.get_pixmap(dpi=200).tobytes("png")
                except Exception:
                    png = None
            pages.append((text, png))
        return doc.page_count, pages
    finally:
        doc.close()


def _tesseract(png: bytes) -> tuple[str, float | None]:
    """OCR a rendered page with Tesseract → (text, mean_confidence) or ("", None)."""
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except Exception:
        return "", None
    try:
        img = Image.open(io.BytesIO(png))
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


async def _ocr_page(png: bytes, gemini: GeminiClient) -> tuple[str, float | None, str]:
    """OCR one page image: Gemini vision first, then Tesseract.

    Returns ``(text, confidence_or_None, engine)``; ``engine`` is "" if neither
    path produced text.
    """
    try:
        res = await gemini.generate(
            _OCR_PROMPT,
            parts=[GeminiClient.image_part(png, "image/png")],
            temperature=0.0,
        )
        if res.text.strip():
            return res.text.strip(), 0.95, "gemini-vision"
    except LLMUnavailable:
        pass
    except Exception:
        pass
    text, conf = await asyncio.to_thread(_tesseract, png)
    if text:
        return text, conf, "tesseract"
    return "", None, ""


async def extract_pdf(file: InputFile, gemini: GeminiClient) -> ExtractionOutcome:
    started = time.time()
    try:
        n_pages, pages = await asyncio.to_thread(_read_pages, file.data)
    except Exception as exc:
        return ExtractionOutcome(
            doc=None,
            tool="pdf_extract",
            duration_ms=int((time.time() - started) * 1000),
            ok=False,
            error=f"PDF parse failed: {exc}",
        )

    parts: list[str] = []
    ocr_confs: list[float] = []
    ocr_pages: list[int] = []
    failed_pages: list[int] = []
    engines: set[str] = set()
    produced_any = False

    for i, (text, png) in enumerate(pages):
        if png is not None:  # scanned page — OCR it
            ocr_text, conf, engine = await _ocr_page(png, gemini)
            if ocr_text:
                text = ocr_text
                ocr_pages.append(i + 1)
                engines.add(engine)
                if conf is not None:
                    ocr_confs.append(conf)
            else:
                failed_pages.append(i + 1)
                text = _UNREADABLE
        if text and text != _UNREADABLE:
            produced_any = True
        parts.append(f"[Page {i + 1}]\n{text}".rstrip())

    duration_ms = int((time.time() - started) * 1000)
    if not produced_any:
        return ExtractionOutcome(
            doc=None,
            tool="pdf_extract",
            duration_ms=duration_ms,
            ok=False,
            error="No extractable text found in PDF (scanned pages need Tesseract or a Gemini API key).",
        )

    confidence = (sum(ocr_confs) / len(ocr_confs)) if ocr_confs else None
    doc = ExtractedDoc(
        source=file.filename,
        kind="pdf",
        content="\n\n".join(parts).strip(),
        ocr_confidence=round(confidence, 3) if confidence is not None else None,
    )
    metadata = {"pages": n_pages}
    if ocr_pages:
        metadata["ocr_pages"] = ocr_pages
        metadata["ocr_engine"] = ",".join(sorted(engines))
    if failed_pages:
        metadata["failed_pages"] = failed_pages
    return ExtractionOutcome(
        doc=doc, tool="pdf_extract", duration_ms=duration_ms, metadata=metadata
    )
