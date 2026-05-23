
import argparse
import sys
from pathlib import Path

from src.pipeline import run_pipeline
from src.utils.logger import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gps-transcribe",
        description="GPS Chemoil — Batch Radio Audio Transcription & Report Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "D:/RadioBackup/2026-05-16"
  python main.py "D:/RadioBackup" --shift night --model medium
  python main.py "." --dry-run
        """,
    )
    parser.add_argument(
        "folder",
        help="Path to the folder containing .wav audio files",
    )
    parser.add_argument(
        "--shift", "-s",
        choices=["day", "night", "auto"],
        default="auto",
        help="Shift label: day (06:00-18:00), night (18:00-06:00), or auto-detect (default)",
    )
    parser.add_argument(
        "--model", "-m",
        choices=["tiny", "base", "small", "medium", "large"],
        default=None,
        help="Whisper model override (default: from config/settings.py)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan for .wav files and show metadata only — no transcription",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    folder = Path(args.folder).resolve()
    if not folder.exists():
        logger.error(f"Folder not found: {folder}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("  GPS Chemoil — AI Radio Transcription Suite")
    logger.info("=" * 60)
    logger.info(f"  Folder : {folder}")
    logger.info(f"  Shift  : {args.shift}")
    logger.info(f"  Dry run: {args.dry_run}")
    logger.info("=" * 60)

    run_pipeline(
        folder=folder,
        shift_override=args.shift,
        model_override=args.model,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
