from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from config.settings import SHIFT_DAY_START, SHIFT_DAY_END
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AudioFileMeta:
    filename: str
    filepath: Path

    modified_at: datetime
    shift_label: str

    processed_at: datetime = field(default_factory=datetime.now)


def _detect_shift(dt: datetime) -> str:
    if SHIFT_DAY_START <= dt.hour < SHIFT_DAY_END:
        return "Day Shift"

    return "Night Shift"


def extract_metadata(
    filepath: Path,
    shift_override: str = "auto",
) -> AudioFileMeta:

    stat = filepath.stat()

    modified_at = datetime.fromtimestamp(stat.st_mtime)

    if shift_override == "day":
        shift_label = "Day Shift"

    elif shift_override == "night":
        shift_label = "Night Shift"

    else:
        shift_label = _detect_shift(modified_at)

    return AudioFileMeta(
        filename=filepath.name,
        filepath=filepath,
        modified_at=modified_at,
        shift_label=shift_label,
    )


def scan_folder(
    folder: Path,
    shift_override: str = "auto",
):

    wav_files = sorted(folder.glob("*.wav"))

    if not wav_files:
        logger.warning("No .wav files found")
        return []

    logger.info(f"Found {len(wav_files)} audio file(s)")

    results = []

    for wf in wav_files:
        results.append(
            extract_metadata(
                wf,
                shift_override=shift_override,
            )
        )

    return results