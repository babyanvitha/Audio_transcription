"""
src/transcription/engine.py
============================
Step 2 of the pipeline: run Whisper speech-to-text on each audio file.
"""

from dataclasses import dataclass
from typing import Optional

from config.settings import WHISPER_MODEL, WHISPER_LANGUAGE
from src.ingestion.metadata import AudioFileMeta
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TranscriptResult:
    """Transcription output for a single audio file."""

    meta: AudioFileMeta

    text: str = ""
    language_detected: str = ""
    language_confidence: float = 0.0

    segments: list = None

    success: bool = False
    error: Optional[str] = None

    def __post_init__(self):
        if self.segments is None:
            self.segments = []

    @property
    def word_count(self) -> int:
        return len(self.text.split()) if self.text else 0

    @property
    def language_label(self) -> str:
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
            self.language_detected.upper(),
        )


def _load_model(model_name: str):
    """
    Load Whisper model.

    First run downloads the model.
    Subsequent runs use the cached copy.
    """

    try:
        import whisper

    except ImportError:
        raise ImportError(
            "Whisper is not installed. Run:\n"
            "pip install openai-whisper"
        )

    logger.info(f"Loading Whisper model '{model_name}' ...")

    model = whisper.load_model(model_name)

    logger.info(f"Model '{model_name}' ready.")

    return model


def transcribe_file(
    meta: AudioFileMeta,
    model,
    language: Optional[str] = None,
) -> TranscriptResult:
    """
    Transcribe a single audio file.
    """

    result = TranscriptResult(meta=meta)

    logger.info(f"Transcribing: {meta.filename}")

    try:

        raw = model.transcribe(
            str(meta.filepath),
            language=language,
            task="transcribe",      # non-English -> English
            verbose=False,
            fp16=False,
        )

        result.text = raw.get("text", "").strip()

        result.language_detected = raw.get(
            "language",
            "und",
        )

        result.segments = raw.get(
            "segments",
            [],
        )

        result.success = True

        logger.info(
            f"✓ {meta.filename} | "
            f"Lang: {result.language_label} | "
            f"Words: {result.word_count}"
        )

    except Exception as exc:

        result.error = str(exc)

        logger.error(
            f"✗ {meta.filename} — "
            f"transcription failed: {exc}"
        )

    return result


def transcribe_batch(
    metadata_list: list[AudioFileMeta],
    model_name: Optional[str] = None,
    language: Optional[str] = None,
) -> list[TranscriptResult]:
    """
    Transcribe all files using a single loaded model.
    """

    model_to_use = model_name or WHISPER_MODEL

    lang_to_use = language or WHISPER_LANGUAGE

    model = _load_model(model_to_use)

    results = []

    total = len(metadata_list)

    for idx, meta in enumerate(metadata_list, start=1):

        logger.info(
            f"[{idx}/{total}] Processing {meta.filename}"
        )

        result = transcribe_file(
            meta,
            model,
            language=lang_to_use,
        )

        results.append(result)

    successful = sum(
        1 for r in results
        if r.success
    )

    logger.info(
        f"Transcription complete: "
        f"{successful}/{total} files successful."
    )

    return results
