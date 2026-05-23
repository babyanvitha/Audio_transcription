from datetime import datetime
from pathlib import Path
import re


def highlight_keywords(text: str, alerts) -> str:
    """
    Highlight alert keywords inside transcript text.

    Example:
        fire -> ***FIRE***
    """
    keywords = set()

    for alert in alerts:
        for kw in alert.keywords_found:
            keywords.add(kw)

    highlighted = text

    for kw in sorted(keywords, key=len, reverse=True):
        highlighted = re.sub(
            rf"\b({re.escape(kw)})\b",
            r"***\1***",
            highlighted,
            flags=re.IGNORECASE,
        )

    return highlighted


def build_report(results, alerts, folder: Path, shift_label: str, run_at=None) -> str:

    successful = [r for r in results if r.success]

    successful.sort(
        key=lambda r: r.meta.modified_at
    )

    day_shift_blocks = []
    night_shift_blocks = []

    for result in successful:

        file_alerts = [
            a for a in alerts
            if a.filename == result.meta.filename
        ]

        transcript_text = highlight_keywords(
            result.text.strip(),
            file_alerts,
        )

        dt = result.meta.modified_at

        block_lines = [
            f"Filename : {result.meta.filename}",
            f"Date     : {dt.strftime('%Y-%m-%d')}",
            f"Time     : {dt.strftime('%H:%M:%S')}",
            f"Shift    : {result.meta.shift_label}",
            "",
        ]

        if file_alerts:

            keywords = sorted({
                kw
                for alert in file_alerts
                for kw in alert.keywords_found
            })

            block_lines.extend([
                "ALERTS DETECTED",
                "-" * 40,
            ])

            for kw in keywords:
                block_lines.append(f"- {kw.upper()}")

            block_lines.append("")

        block_lines.extend([
            "TRANSCRIPT",
            "-" * 40,
            transcript_text,
        ])

        block = "\n".join(block_lines)

        if result.meta.shift_label == "Day Shift":
            day_shift_blocks.append(block)
        else:
            night_shift_blocks.append(block)

    report_lines = [
        "=" * 70,
        "GPS CHEMOIL RADIO COMMUNICATION TRANSCRIPT REPORT",
        "=" * 70,
        "",
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    if day_shift_blocks:

        report_lines.extend([
            "",
            "=" * 70,
            "DAY SHIFT",
            "=" * 70,
            "",
        ])

        for block in day_shift_blocks:

            report_lines.extend([
                block,
                "",
                "-" * 70,
                "",
            ])

    if night_shift_blocks:

        report_lines.extend([
            "",
            "=" * 70,
            "NIGHT SHIFT",
            "=" * 70,
            "",
        ])

        for block in night_shift_blocks:

            report_lines.extend([
                block,
                "",
                "-" * 70,
                "",
            ])

    return "\n".join(report_lines)


def save_report(report_text: str, output_folder: Path, run_at=None) -> Path:
    out_path = output_folder / "overall_summary_report.txt"
    out_path.write_text(report_text, encoding="utf-8")
    return out_path


def save_individual_transcripts(results, output_folder: Path, alerts=None):
    alerts = alerts or []

    saved = []

    for r in results:
        if not r.success:
            continue

        dt = r.meta.modified_at

        transcript_text = highlight_keywords(
            r.text,
            [a for a in alerts if a.filename == r.meta.filename],
        )

        content = f"""Date  : {dt.strftime('%Y-%m-%d')}
Time  : {dt.strftime('%H:%M:%S')}
Shift : {r.meta.shift_label}

TRANSCRIPT

{transcript_text}
"""

        out = output_folder / f"{Path(r.meta.filename).stem}_transcript.txt"

        out.write_text(content, encoding="utf-8")

        saved.append(out)

    return saved