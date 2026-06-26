"""Image OCR: Tesseract for a real confidence score + Gemini vision for a
clean transcript. Either path degrades gracefully if its dependency is missing.
"""

from __future__ import annotations

import io
import time

from ..gemini_client import GeminiClient, LLMUnavailable
from ..schemas import ExtractedDoc
from .base import ExtractionOutcome, InputFile


def _tesseract_ocr(data: bytes) -> tuple[str, float | None]:
    """Run Tesseract, returning (text, mean_confidence in 0..1) or ("", None)."""
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except Exception:
        return "", None
    try:
        img = Image.open(io.BytesIO(data))
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


async def extract_image(file: InputFile, gemini: GeminiClient) -> ExtractionOutcome:
    started = time.time()
    import asyncio

    tess_text, confidence = await asyncio.to_thread(_tesseract_ocr, file.data)

    transcript = tess_text
    note = "tesseract"
    # Prefer Gemini vision for a cleaned, layout-aware transcript when available.
    try:
        result = await gemini.generate(
            "Transcribe ALL text in this image exactly, preserving line breaks and "
            "code indentation. Output only the transcribed text, no commentary.",
            parts=[GeminiClient.image_part(file.data, file.content_type or "image/png")],
            temperature=0.0,
        )
        if result.text.strip():
            transcript = result.text.strip()
            note = "gemini-vision"
            if confidence is None:
                confidence = 0.95  # high heuristic when only the LLM transcribed
    except LLMUnavailable:
        pass
    except Exception:
        pass

    duration_ms = int((time.time() - started) * 1000)
    if not transcript:
        return ExtractionOutcome(
            doc=None,
            tool="image_ocr",
            duration_ms=duration_ms,
            ok=False,
            error="OCR produced no text (Tesseract and Gemini both unavailable or empty).",
        )
    doc = ExtractedDoc(
        source=file.filename,
        kind="image",
        content=transcript,
        ocr_confidence=round(confidence, 3) if confidence is not None else None,
    )
    return ExtractionOutcome(
        doc=doc, tool="image_ocr", duration_ms=duration_ms, metadata={"engine": note}
    )
