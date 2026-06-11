from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.ingestion.metadata import scan_folder
from src.transcription.engine import transcribe_batch
from src.transcription.translator import preload_translation_model
from src.alerts.keyword_detector import scan_all_transcripts
from src.reports.builder import build_report, save_report
from src.utils.logger import get_logger

logger = get_logger(__name__)

def _check_unicode(label: str, text: str) -> None:
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    total = len(text)
    sample = text[:60].replace("\n", " ")
    logger.debug(
        "[UNICODE] %s — chars: %d, non-ASCII: %d, sample: %r",
        label, total, non_ascii, sample,
    )

def _dominant_shift(metadata_list) -> str:
    """Return the shift label that appears most often in *metadata_list*."""
    counts = Counter(m.shift_label for m in metadata_list)
    return counts.most_common(1)[0][0]

def run_pipeline(
    folder: Path,
    shift_override: str = "auto",
    model_override: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    run_at = datetime.now()

    # ──────────────────────────────────────────────
    # STEP 1 — Metadata ingestion
    # ──────────────────────────────────────────────
    logger.info("Step 1/4: Extracting metadata")
    metadata_list = scan_folder(folder, shift_override=shift_override)

    if not metadata_list:
        logger.error("No .wav files found in %s. Exiting.", folder)
        return

    # Use the majority shift rather than assuming index-0 is representative.
    shift_label = _dominant_shift(metadata_list)

    if dry_run:
        logger.info("Dry-run mode — stopping after metadata extraction.")
        logger.info("Found %d file(s):", len(metadata_list))
        for m in metadata_list:
            logger.info(
                "  %s | %s | %s",
                m.filename,
                m.modified_at.strftime("%Y-%m-%d %H:%M:%S"),
                m.shift_label,
            )
        return

    # ──────────────────────────────────────────────
    # STEP 2 — Translation model warm-up
    # ──────────────────────────────────────────────
    # Preload once here so transcribe_batch() never blocks waiting for a cold
    # model load in the middle of the loop.
    logger.info("")
    logger.info("Preloading translation model …")
    preload_translation_model()

    # ──────────────────────────────────────────────
    # STEP 3 — Transcription + per-file translation
    # ──────────────────────────────────────────────
    logger.info("")
    logger.info("Step 2/4: Transcribing audio files")
    results = transcribe_batch(
        metadata_list=metadata_list,
        model_name=model_override,
    )

    # Unicode boundary check — after Whisper + translation
    for r in results:
        if r.success:
            _check_unicode(f"Whisper output [{r.meta.filename}]", r.text)
            if r.translated_text:
                _check_unicode(
                    f"Translated text [{r.meta.filename}]",
                    r.translated_text,
                )

    # ──────────────────────────────────────────────
    # STEP 4 — Keyword alert detection
    # ──────────────────────────────────────────────
    logger.info("")
    logger.info("Step 3/4: Scanning for keyword alerts")
    alerts = scan_all_transcripts(results)

    # ──────────────────────────────────────────────
    # STEP 5 — Report generation
    # ──────────────────────────────────────────────
    logger.info("")
    logger.info("Step 4/4: Generating report")
    report_text = build_report(
        results=results,
        alerts=alerts,
        folder=folder,
        shift_label=shift_label,
        run_at=run_at,
    )

    # Unicode boundary check — final report string before disk write
    _check_unicode("Final report text (pre-save)", report_text)

    report_path = save_report(
        report_text,
        folder,
        results=results,
        alerts=alerts,
        folder=folder,
        run_at=run_at,
    )

    # ──────────────────────────────────────────────
    # DONE — summary
    # ──────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("  PIPELINE COMPLETE")
    logger.info("=" * 60)
    logger.info("  Shift        : %s", shift_label)
    logger.info("  Files        : %d", len(results))
    logger.info("  Transcribed  : %d", sum(1 for r in results if r.success))
    logger.info("  Alerts       : %d file(s) flagged", len(alerts))
    logger.info("  Report saved : %s", report_path)
    logger.info("=" * 60)

    if alerts:
        logger.warning("")
        logger.warning(
            "⚠  CRITICAL KEYWORD ALERTS DETECTED — review the report immediately."
        )
        for a in alerts:
            logger.warning(
                "   • %s → %s",
                a.filename,
                ", ".join(k.upper() for k in a.keywords_found),
            )
        logger.warning("")