import re
import threading
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

_MODEL_NAME = "facebook/nllb-200-distilled-600M"

_tokenizer = None
_model = None
_load_lock = threading.Lock()


LANG_MAP: dict[str, str] = {
    "ar": "arb_Arab",
    "en": "eng_Latn",
    "hi": "hin_Deva",
    "ta": "tam_Taml",
    "ml": "mal_Mlym",
}

_ENGLISH_LIKE = {"en"}

# Maximum tokens NLLB can handle in one pass.
_MAX_TOKENS = 480   # slightly under 512 to leave room for special tokens


def _check_unicode(label: str, text: str) -> None:
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    logger.debug(
        "[UNICODE] %s — len=%d, non-ASCII=%d, sample=%r",
        label, len(text), non_ascii, text[:60],
    )


def _safe_decode(token_ids, tokenizer) -> str:
    decoded = tokenizer.decode(token_ids, skip_special_tokens=True)

    try:
        round_tripped = decoded.encode("utf-8").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError) as exc:
        logger.warning("[UNICODE] UTF-8 round-trip failed after NLLB decode: %s", exc)
        round_tripped = decoded.encode("utf-8", errors="replace").decode("utf-8")

    if "\ufffd" in round_tripped:
        logger.warning(
            "[UNICODE] Replacement characters (U+FFFD) found in NLLB output — "
            "source script encoding may have been damaged upstream."
        )

    return round_tripped


# ──────────────────────────────────────────────────────────────────────────────
# Model lifecycle
# ──────────────────────────────────────────────────────────────────────────────

def load_translation_model():
    global _tokenizer, _model

    if _tokenizer is not None and _model is not None:
        return _tokenizer, _model

    with _load_lock:
        # Re-check inside the lock (double-checked locking pattern).
        if _tokenizer is None:
            from transformers import AutoTokenizer
            logger.info("Loading translation tokenizer '%s' …", _MODEL_NAME)
            _tokenizer = AutoTokenizer.from_pretrained(
                _MODEL_NAME, local_files_only=True
            )

        if _model is None:
            from transformers import AutoModelForSeq2SeqLM
            logger.info("Loading translation model '%s' …", _MODEL_NAME)
            _model = AutoModelForSeq2SeqLM.from_pretrained(
                _MODEL_NAME, local_files_only=True
            )

    return _tokenizer, _model


def preload_translation_model() -> None:
    try:
        load_translation_model()
        logger.info("Translation model preloaded successfully.")
    except Exception as exc:
        logger.warning(
            "Translation model preload failed: %s. "
            "Non-English files will fall back to raw transcription text.",
            exc,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Language detection for mixed-language handling
# ──────────────────────────────────────────────────────────────────────────────

def _detect_language(text: str) -> str:
    try:
        from langdetect import detect, LangDetectException  # type: ignore
        return detect(text)
    except Exception:
        return "en"


# Simple sentence splitter that preserves Unicode punctuation.
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?।؟])\s+')


def _split_sentences(text: str) -> list[str]:
    """Split *text* into individual sentences."""
    parts = _SENTENCE_SPLIT_RE.split(text.strip())
    return [p for p in parts if p.strip()]


def _translate_chunk(
    chunk: str,
    source_nllb_code: str,
    tokenizer,
    model,
) -> str:
    _check_unicode(f"NLLB input [{source_nllb_code}]", chunk)

    tokenizer.src_lang = source_nllb_code

    encoded = tokenizer(
        chunk,
        return_tensors="pt",
        truncation=True,
        max_length=_MAX_TOKENS,
        padding=False,
    )

    target_id = tokenizer.convert_tokens_to_ids("eng_Latn")

    generated = model.generate(
        **encoded,
        forced_bos_token_id=target_id,
        max_length=_MAX_TOKENS,
        num_beams=4,
        early_stopping=True,
    )

    translated = _safe_decode(generated[0], tokenizer)
    _check_unicode("NLLB output [eng_Latn]", translated)

    return translated


def _translate_segment(
    segment: str,
    declared_source_lang: str,
    tokenizer,
    model,
) -> str:
   
    if not segment.strip():
        return segment

    # Fast path: if the whole file was already English, skip detection.
    if declared_source_lang in _ENGLISH_LIKE:
        return segment

    # Per-segment language detection catches code-switching (e.g. a Malayalam
    # file where every other sentence is in English).
    detected = _detect_language(segment)

    if detected in _ENGLISH_LIKE:
        logger.debug(
            "Segment detected as English — skipping translation: %r", segment[:40]
        )
        return segment

    source_nllb = LANG_MAP.get(detected) or LANG_MAP.get(declared_source_lang)

    if source_nllb is None:
        logger.warning(
            "No NLLB code for detected language '%s' or declared language '%s'. "
            "Returning segment untranslated.",
            detected, declared_source_lang,
        )
        return segment

    return _translate_chunk(segment, source_nllb, tokenizer, model)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def translate_text(
    text: str,
    source_language: str,
) -> str:

    if not text:
        return ""

    if source_language in _ENGLISH_LIKE:
        return text

    try:
        tokenizer, model = load_translation_model()
    except Exception as exc:
        logger.warning(
            "Skipping translation — model could not be loaded: %s", exc
        )
        return text

    sentences = _split_sentences(text)

    if not sentences:
        return text

    translated_parts: list[str] = []

    for sentence in sentences:
        try:
            translated_parts.append(
                _translate_segment(sentence, source_language, tokenizer, model)
            )
        except Exception as exc:
            logger.warning(
                "Segment translation failed (%s) — keeping original: %r",
                exc, sentence[:40],
            )
            translated_parts.append(sentence)

    result = " ".join(translated_parts)
    _check_unicode("translate_text() return value", result)

    return result
