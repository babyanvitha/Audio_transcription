"""
src/pipeline.py

  Step 1 — Metadata ingestion  (src/ingestion/metadata.py)
  Step 2 — Transcription       (src/transcription/engine.py)
  Step 3 — Keyword detection   (src/alerts/keyword_detector.py)
  Step 4 — Report generation   (src/reports/builder.py)

"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from src.ingestion.metadata import scan_folder
from src.transcription.engine import transcribe_batch
from src.alerts.keyword_detector import scan_all_transcripts
from src.reports.builder import build_report, save_report, save_individual_transcripts
from src.utils.logger import get_logger

logger = get_logger(__name__)


def run_pipeline(
    folder: Path,
    shift_override: str = "auto",
    model_override: Optional[str] = None,
    dry_run: bool = False,
) -> None:
    """
    Run the full transcription pipeline for a folder of .wav files.

    Args:
        folder:         Directory containing .wav radio recordings.
        shift_override: 'day', 'night', or 'auto'.
        model_override: Whisper model name, or None to use config default.
        dry_run:        If True, only scan for files and show metadata.
    """
    run_at = datetime.now()

    # ─────────────────────────────────────────────
    # STEP 1 — Metadata ingestion
    # ─────────────────────────────────────────────
    logger.info("")
    logger.info("Step 1/4 completed: Metadata extracted")
    metadata_list = scan_folder(folder, shift_override=shift_override)

    if not metadata_list:
        logger.error("No .wav files found. Exiting.")
        return

    shift_label = metadata_list[0].shift_label   # all files share the same shift

    if dry_run:
        logger.info("Dry-run mode — stopping after metadata extraction.")
        logger.info(f"Found {len(metadata_list)} file(s):")
        for m in metadata_list:
            logger.info(
                f"  {m.filename} | "
                f"{m.modified_at.strftime('%Y-%m-%d %H:%M:%S')} | "
                f"{m.shift_label}"
            )
        return

    # ─────────────────────────────────────────────
    # STEP 2 — Transcription
    # ─────────────────────────────────────────────
    logger.info("")
    logger.info("Step 2/4: Transcribing audio files")
    results = transcribe_batch(
        metadata_list=metadata_list,
        model_name=model_override,
    )

    # ─────────────────────────────────────────────
    # STEP 3 — Keyword alert detection
    # ─────────────────────────────────────────────
    logger.info("")
    logger.info("Step 3/4: Scanning keywords")
    alerts = scan_all_transcripts(results)

    # ─────────────────────────────────────────────
    # STEP 4 — Report generation
    # ─────────────────────────────────────────────
    logger.info("")
    logger.info("Step 4/4: Generating outputs")
    report_text = build_report(
        results=results,
        alerts=alerts,
        folder=folder,
        shift_label=shift_label,
        run_at=run_at,
    )

    report_path = save_report(report_text, folder, run_at=run_at)
    save_individual_transcripts(results, folder, alerts,)

    # ─────────────────────────────────────────────
    # DONE — print summary
    # ─────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("  PIPELINE COMPLETE")
    logger.info("=" * 60)
    logger.info(f"  Shift        : {shift_label}")
    logger.info(f"  Files        : {len(results)}")
    logger.info(f"  Transcribed  : {sum(1 for r in results if r.success)}")
    logger.info(f"  Alerts       : {len(alerts)} file(s) flagged")
    logger.info(f"  Report saved : {report_path}")
    logger.info("=" * 60)

    if alerts:
        logger.warning("")
        logger.warning("⚠  CRITICAL KEYWORD ALERTS DETECTED — review the report immediately.")
        for a in alerts:
            logger.warning(f"   • {a.filename} → {', '.join(k.upper() for k in a.keywords_found)}")
        logger.warning("")
