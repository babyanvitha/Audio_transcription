"""
src/alerts/keyword_detector.py
================================
Step 3 of the pipeline: scan every transcript for critical safety keywords
and build structured alert records that appear highlighted in the report.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from config.settings import CRITICAL_KEYWORDS
from src.transcription.engine import TranscriptResult
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Number of characters to show either side of a keyword hit (context window)
CONTEXT_WINDOW = 150


@dataclass
class KeywordHit:
    """A single keyword match within a transcript."""
    keyword: str
    position: int           # character index in the full text
    context_excerpt: str    # surrounding text for the report


@dataclass
class AlertRecord:
    """All keyword hits for a single file."""
    filename: str
    hits: list[KeywordHit] = field(default_factory=list)

    @property
    def keywords_found(self) -> list[str]:
        return sorted({h.keyword for h in self.hits})

    @property
    def hit_count(self) -> int:
        return len(self.hits)

    @property
    def has_alerts(self) -> bool:
        return bool(self.hits)


def _extract_context(text: str, position: int, keyword: str) -> str:
    """Return a short excerpt centred on the keyword match position."""
    start = max(0, position - CONTEXT_WINDOW)
    end = min(len(text), position + len(keyword) + CONTEXT_WINDOW)
    excerpt = text[start:end].strip().replace("\n", " ")
    if start > 0:
        excerpt = "…" + excerpt
    if end < len(text):
        excerpt = excerpt + "…"
    return excerpt


def scan_transcript(result: TranscriptResult) -> Optional[AlertRecord]:
    """
    Scan a single TranscriptResult for all critical keywords.

    Returns an AlertRecord if any keywords are found, None otherwise.
    """
    if not result.success or not result.text:
        return None

    text_lower = result.text.lower()
    alert = AlertRecord(
        filename=result.meta.filename,
    )

    for keyword in CRITICAL_KEYWORDS:
        pattern = re.compile(re.escape(keyword.lower()))
        for match in pattern.finditer(text_lower):
            hit = KeywordHit(
                keyword=keyword,
                position=match.start(),
                context_excerpt=_extract_context(result.text, match.start(), keyword),
            )
            alert.hits.append(hit)

    if alert.has_alerts:
        logger.warning(
            f"  ⚠ KEYWORD ALERT: {result.meta.filename} → "
            f"{', '.join(alert.keywords_found).upper()} "
            f"({alert.hit_count} hit(s))"
        )

    return alert if alert.has_alerts else None


def scan_all_transcripts(results: list[TranscriptResult]) -> list[AlertRecord]:
    """
    Scan all transcript results and return only the records with keyword hits.

    Returns:
        List of AlertRecord (one per file that triggered at least one keyword).
    """
    alerts = []
    for result in results:
        alert = scan_transcript(result)
        if alert:
            alerts.append(alert)

    if alerts:
        total_hits = sum(a.hit_count for a in alerts)
        logger.warning(
            f"Keyword scan complete: {len(alerts)} file(s) flagged, "
            f"{total_hits} total hit(s)."
        )
    else:
        logger.info("Keyword scan complete: No critical keywords detected.")

    return alerts
