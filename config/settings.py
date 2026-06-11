from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

OUTPUT_DIR       = PROJECT_ROOT / "output"
TRANSCRIPTS_DIR  = OUTPUT_DIR / "transcripts"
REPORTS_DIR      = OUTPUT_DIR / "reports"
LOGS_DIR         = PROJECT_ROOT / "logs" 

# Options: "tiny" | "base" | "small" | "medium" | "large"

WHISPER_MODEL = "small"
WHISPER_LANGUAGE = "en"

SHIFT_DAY_START   = 6   # 06:00
SHIFT_DAY_END     = 18  # 18:00
SHIFT_NIGHT_START = 18  # 18:00
SHIFT_NIGHT_END   = 6   # 06:00

# ─────────────────────────────────────────────────────────────────────────────
# KEYWORD ALERTS
# ─────────────────────────────────────────────────────────────────────────────
# Case-insensitive. 

CRITICAL_KEYWORDS = [
    # ── English ──────────────────────────────────────────────
    "fire",
    "explosion",
    "spill",
    "oil spill",
    "chemical spill",
    "leak",
    "gas leak",
    "emergency",
    "evacuate",
    "evacuation",
    "mayday",
    "help",
    "injured",
    "injury",
    "accident",
    "hazmat",
    "toxic",
    "smoke",
    "flood",
]


# GPS Chemoil filename format: CH{channel}_{radioID}_{suffix}.wav
FILENAME_REGEX = r"^(?P<channel>CH\d+)_(?P<radio_id>[0-9a-fA-F]+)_(?P<suffix>.+)\.wav$"

# ─────────────────────────────────────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────────────────────────────────────

COMPANY_NAME   = "GPS Chemoil"
SITE_NAME      = "Port of Fujairah Terminal"
REPORT_TITLE   = "Shift Radio Communication Transcript Report"

REPORT_FORMAT = "both"       #txt, pdf, or both
REPORT_TEXT_MODE = "translated"  # "transcribed" (Whisper output) or "translated" (auto-translated to English)

