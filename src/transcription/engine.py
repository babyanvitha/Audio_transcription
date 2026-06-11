from dataclasses import dataclass, field
from typing import Optional

from config.settings import (
    WHISPER_MODEL,
    WHISPER_LANGUAGE,
)
from src.ingestion.metadata import AudioFileMeta
from src.utils.logger import get_logger
from src.transcription.translator import translate_text

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Try to read the optional prompt setting; fall back gracefully if not set.
# ---------------------------------------------------------------------------
try:
    from config.settings import WHISPER_INITIAL_PROMPT as _PROMPT_SETTING
except ImportError:
    _PROMPT_SETTING = ""


def _check_unicode(label: str, text: str) -> None:
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    logger.debug(
        "[UNICODE] %s — len=%d, non-ASCII=%d, sample=%r",
        label, len(text), non_ascii, text[:60],
    )

@dataclass
class TranscriptResult:

    meta: AudioFileMeta

    text: str = ""
    translated_text: str = ""
    language_detected: str = ""

    language_confidence: float = 0.0
    segments: list = field(default_factory=list)

    success: bool = False
    error: Optional[str] = None

    # ── Computed properties ──────────────────────────────────────────────────

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text else 0

    @property
    def language_label(self) -> str:
        """Human-readable language name."""
        labels = {
            "en": "English",
            "ar": "Arabic",
            "hi": "Hindi",
            "ta": "Tamil",
            "ml": "Malayalam",
            "und": "Undetermined",
        }
        return labels.get(
            self.language_detected,
            self.language_detected.upper() if self.language_detected else "Unknown",
        )

    @property
    def display_text(self) -> str:
        if self.translated_text and self.translated_text != self.text:
            return self.translated_text
        return self.text


# ──────────────────────────────────────────────────────────────────────────────
# Whisper model loading
# ──────────────────────────────────────────────────────────────────────────────

def _load_model(model_name: str):
    try:
        import whisper
    except ImportError:
        raise ImportError(
            "Whisper is not installed. Run:\n"
            "    pip install openai-whisper"
        )

    logger.info("Loading Whisper model '%s' …", model_name)
    model = whisper.load_model(model_name)
    logger.info("Model '%s' ready.", model_name)
    return model


# ──────────────────────────────────────────────────────────────────────────────
# Single-file transcription
# ──────────────────────────────────────────────────────────────────────────────

def transcribe_file(
    meta: AudioFileMeta,
    model,
    language: Optional[str] = None,
) -> TranscriptResult:
    result = TranscriptResult(meta=meta)

    logger.info("Transcribing: %s", meta.filename)

    try:
        kwargs = dict(
            task="transcribe",
            verbose=False,
            fp16=False,
        )

        if language:
            kwargs["language"] = language

        if _PROMPT_SETTING:
            kwargs["initial_prompt"] = _PROMPT_SETTING

        raw = model.transcribe(str(meta.filepath), **kwargs)

        # ── Raw text ─────────────────────────────────────────────────────────
        result.text = raw.get("text", "").strip()
        _check_unicode(f"Whisper raw text [{meta.filename}]", result.text)

        # ── Language detection ────────────────────────────────────────────────
        result.language_detected = raw.get("language", "und")
        lang_probs: dict = raw.get("language_probs") or {}
        result.language_confidence = lang_probs.get(result.language_detected, 0.0)

        # ── Segments ──────────────────────────────────────────────────────────
        result.segments = raw.get("segments", [])
        result.translated_text = translate_text(
            result.text,
            result.language_detected,
        )
        _check_unicode(
            f"Translated text [{meta.filename}]",
            result.translated_text,
        )

        result.success = True

        logger.info(
            "✓ %s | Lang: %s (%.0f%%) | Words: %d",
            meta.filename,
            result.language_label,
            result.language_confidence * 100,
            result.word_count,
        )

    except Exception as exc:
        result.error = str(exc)
        logger.error(
            "✗ %s — transcription failed: %s",
            meta.filename,
            exc,
        )

    return result

def transcribe_batch(
    metadata_list: list[AudioFileMeta],
    model_name: Optional[str] = None,
    language: Optional[str] = None,
) -> list[TranscriptResult]:
    model_to_use = model_name or WHISPER_MODEL

    raw_lang = language or WHISPER_LANGUAGE
    lang_to_use: Optional[str] = raw_lang if raw_lang else None

    model = _load_model(model_to_use)

    results: list[TranscriptResult] = []
    total = len(metadata_list)

    for idx, meta in enumerate(metadata_list, start=1):
        logger.info("[%d/%d] Processing %s", idx, total, meta.filename)
        result = transcribe_file(meta, model, language=lang_to_use)
        results.append(result)

    successful = sum(1 for r in results if r.success)
    logger.info(
        "Transcription complete: %d/%d files successful.",
        successful,
        total,
    )

    return results
