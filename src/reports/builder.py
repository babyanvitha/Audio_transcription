import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import REPORT_FORMAT, REPORT_TEXT_MODE
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Colour palette
# ──────────────────────────────────────────────────────────────────────────────

class _C:
    HEADER_BG      = (0.11, 0.22, 0.40)   # navy
    HEADER_FG      = (1.00, 1.00, 1.00)   # white
    ROW_ODD        = (1.00, 1.00, 1.00)   # white
    ROW_EVEN       = (0.95, 0.97, 0.99)   # #F2F7FD
    TS_COL_BG      = (0.96, 0.97, 0.98)   # very light grey for timestamp col
    ALERT_FG       = (0.78, 0.05, 0.05)   # deep red
    GRID           = (0.82, 0.87, 0.93)   # steel blue grid lines
    TITLE_FG       = (0.11, 0.22, 0.40)   # navy
    META_FG        = (0.35, 0.35, 0.35)   # mid grey
    SHIFT_DAY_FG   = (0.08, 0.40, 0.08)   # dark green
    SHIFT_NIGHT_FG = (0.18, 0.18, 0.58)   # dark blue
    FOOTER_FG      = (0.50, 0.50, 0.50)   # grey


def _color(triple):
    from reportlab.lib.colors import Color
    return Color(*triple)


# ──────────────────────────────────────────────────────────────────────────────
# Unicode diagnostics
# ──────────────────────────────────────────────────────────────────────────────

def _check_unicode(label: str, text: str) -> None:
    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    logger.debug(
        "[UNICODE] %s — len=%d, non-ASCII=%d, sample=%r",
        label, len(text), non_ascii, text[:60],
    )


# ──────────────────────────────────────────────────────────────────────────────
# Keyword highlighting
# ──────────────────────────────────────────────────────────────────────────────

def highlight_keywords(text: str, alerts, mode: str = "txt") -> str:
    """
    Wrap alert keywords in markup appropriate for *mode*.

    Args:
        text:   Source text.
        alerts: Objects with a ``keywords_found`` iterable.
        mode:   ``'txt'`` → ``***KEYWORD***``
                ``'pdf'`` → ``<font color="#…"><b>KEYWORD</b></font>``
    """
    keywords: set[str] = set()
    for alert in alerts:
        for kw in alert.keywords_found:
            keywords.add(kw)

    if not keywords:
        return text

    r, g, b = _C.ALERT_FG
    alert_hex = "#{:02X}{:02X}{:02X}".format(int(r*255), int(g*255), int(b*255))

    highlighted = text
    for kw in sorted(keywords, key=len, reverse=True):
        if mode == "pdf":
            repl = rf'<font color="{alert_hex}"><b>\1</b></font>'
        else:
            repl = r"***\1***"
        highlighted = re.sub(
            rf"\b({re.escape(kw)})\b",
            repl,
            highlighted,
            flags=re.IGNORECASE,
        )
    return highlighted


# ──────────────────────────────────────────────────────────────────────────────
# Source-text selection
# ──────────────────────────────────────────────────────────────────────────────

def _pick_source_text(result) -> str:
    """
    Return display text for *result* according to ``REPORT_TEXT_MODE``.

    ``'translated'``  → translated_text if present, else text.
    ``'transcribed'`` → always raw text.
    """
    mode = REPORT_TEXT_MODE.lower()
    if mode == "translated":
        return result.translated_text if result.translated_text else result.text
    if mode == "transcribed":
        return result.text
    raise ValueError(
        f"Unsupported REPORT_TEXT_MODE: '{REPORT_TEXT_MODE}'. "
        "Expected 'translated' or 'transcribed'."
    )


# ──────────────────────────────────────────────────────────────────────────────
# TXT layout constants & helpers
# ──────────────────────────────────────────────────────────────────────────────

_TS_W   = 19   # "2026-05-22 14:24:58"
_FN_W   = 28
_SH_W   = 5    # "DAY  " / "NIGHT"
_SEP    = " | "
_MSG_W  = 90


def _txt_rule_width() -> int:
    return _TS_W + len(_SEP) + _FN_W + len(_SEP)+ _SH_W + len(_SEP) + _MSG_W

def _truncate_filename(filename: str, width: int) -> str:                      # NEW FUNCTION
    
    if len(filename) <= width:
        return filename
    if width <= 1:
        return filename[:width]
    return "…" + filename[-(width - 1):]


def _wrap_txt(text: str, width: int) -> list[str]:
    """Word-wrap to *width* code-points; correct for Indic + Latin scripts."""
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        proposed = f"{current} {word}" if current else word
        if len(proposed) <= width:
            current = proposed
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _format_txt_record(dt: datetime, filename: str,  shift_code: str, message: str) -> str:
    ts  = dt.strftime("%Y-%m-%d %H:%M:%S")
    fn  = _truncate_filename(filename, _FN_W).ljust(_FN_W)[:_FN_W] 
    sh  = shift_code.ljust(_SH_W)[:_SH_W]
    wr  = _wrap_txt(message, _MSG_W)
    ind = " " * _TS_W + _SEP + " " * _FN_W + _SEP + " " * _SH_W + _SEP
    return "\n".join([ts + _SEP + fn + _SEP+ sh + _SEP + wr[0]] + [ind + l for l in wr[1:]])


# ──────────────────────────────────────────────────────────────────────────────
# TXT report builder
# ──────────────────────────────────────────────────────────────────────────────

def build_report(
    results,
    alerts,
    folder: Path,
    shift_label: str,
    run_at: Optional[datetime] = None,
) -> str:
    if run_at is None:
        run_at = datetime.now()

    W    = _txt_rule_width()
    rule = "=" * W
    thin = "-" * W

    successful = sorted(
        (r for r in results if r.success),
        key=lambda r: r.meta.modified_at,
    )

    records: list[str] = []
    for result in successful:
        file_alerts  = [a for a in alerts if a.filename == result.meta.filename]
        source_text  = _pick_source_text(result)
        _check_unicode(f"TXT source [{result.meta.filename}]", source_text)
        display      = highlight_keywords(source_text.strip(), file_alerts, mode="txt")
        display      = " ".join(display.split())
        shift_code   = "DAY" if result.meta.shift_label == "Day Shift" else "NIGHT"
        records.append(_format_txt_record(result.meta.modified_at, result.meta.filename, shift_code, display))

    col_hdr = (
        f"{'TIMESTAMP':<{_TS_W}}{_SEP}"
        f"{'FILENAME':<{_FN_W}}{_SEP}"  
        f"{'SHIFT':<{_SH_W}}{_SEP}"
        f"MESSAGE"
    )

    lines: list[str] = [
        rule,
        "GPS CHEMOIL RADIO COMMUNICATION LOG".center(W),
        rule,
        "",
        f"Generated  : {run_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Source dir : {folder}",
        f"Records    : {len(successful)}",
        "",
        thin, col_hdr, thin, "",
    ]
    for rec in records:
        lines.append(rec)
        lines.append("")
    lines += [rule, "END OF LOG".center(W), rule]

    report = "\n".join(lines)
    _check_unicode("build_report() return", report)
    return report


# ──────────────────────────────────────────────────────────────────────────────
# Save dispatcher
# ──────────────────────────────────────────────────────────────────────────────

def save_report(
    report_text: str,
    output_folder: Path,
    results=None,
    alerts=None,
    folder: Optional[Path] = None,
    run_at: Optional[datetime] = None,
) -> Path:
    _check_unicode("save_report() input", report_text)

    fmt = REPORT_FORMAT.lower()

    if fmt == "txt":
        return _save_txt(report_text, output_folder)

    if fmt == "pdf":
        return _save_pdf(output_folder, results or [], alerts or [], folder, run_at)

    if fmt == "both":
        txt_path = _save_txt(report_text, output_folder)
        _save_pdf(output_folder, results or [], alerts or [], folder, run_at)
        return txt_path

    raise ValueError(
        f"Unsupported REPORT_FORMAT: '{REPORT_FORMAT}'. "
        "Expected 'txt', 'pdf', or 'both'."
    )


def _save_txt(report_text: str, output_folder: Path) -> Path:
    out = output_folder / "overall_summary_report.txt"
    out.write_text(report_text, encoding="utf-8")
    logger.info("TXT report saved: %s", out)
    return out


def _save_pdf(
    output_folder: Path,
    results,
    alerts,
    folder: Optional[Path],
    run_at: Optional[datetime],
) -> Path:
    out = output_folder / "overall_summary_report.pdf"
    _build_pdf(out, results, alerts, folder, run_at)
    logger.info("PDF report saved: %s", out)
    return out


# ──────────────────────────────────────────────────────────────────────────────
# Unicode font resolution
# ──────────────────────────────────────────────────────────────────────────────

_FONT_CANDIDATES: list[str] = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans[wdth,wght].ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _find_unicode_font() -> Optional[str]:
    """Return the first existing font path from the candidate list."""
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            logger.debug("Unicode font selected: %s", path)
            return path
    logger.warning(
        "No Unicode-capable TTF font found on this system. "
        "PDF will use built-in Helvetica — non-Latin glyphs (Indic, Arabic) "
        "will not render correctly. "
        "Fix: install 'fonts-noto' on Linux, or verify "
        "Arial Unicode.ttf on macOS."
    )
    return None


# ──────────────────────────────────────────────────────────────────────────────
# PDF builder — professional A4 table layout
# ──────────────────────────────────────────────────────────────────────────────

# Column widths as fractions of the usable page width.
_COL_TS_FRAC    = 0.155   # "2026-05-22 14:24:58" at 7.5 pt
_COL_FN_FRAC    = 0.190   # filename — wraps onto 2 lines if long 
_COL_SHIFT_FRAC = 0.090   # "NIGHT" fits at 7.5 pt
# Message = remainder (~77.5 % of usable width)


def _xml_safe(text: str) -> str:
    escaped = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    # Restore intentional markup
    escaped = re.sub(r"&lt;(/?b)&gt;",         r"<\1>",  escaped)
    escaped = re.sub(r"&lt;(font [^&<>]*)&gt;", r"<\1>",  escaped)
    escaped = re.sub(r"&lt;(/font)&gt;",        r"<\1>",  escaped)
    escaped = re.sub(r"&amp;(#\d+;)",           r"&\1",   escaped)
    return escaped


def _build_pdf(
    out_path: Path,
    results,
    alerts,
    folder: Optional[Path],
    run_at: Optional[datetime],
) -> None:
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer,
        Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    if run_at is None:
        run_at = datetime.now()

    # ── Font setup ───────────────────────────────────────────────────────────
    font_path = _find_unicode_font()
    body_font = "Helvetica"

    if font_path:
        try:
            pdfmetrics.registerFont(TTFont("ReportFont", font_path))
            body_font = "ReportFont"
            logger.debug("PDF font registered from %s", font_path)
        except Exception as exc:
            logger.warning(
                "Font registration failed (%s); falling back to Helvetica.", exc
            )

    # ── Page geometry ────────────────────────────────────────────────────────
    PAGE_W, PAGE_H = A4
    ML = MR = MT = 1.8 * cm
    MB = 2.2 * cm                          # extra bottom for footer
    usable_w = PAGE_W - ML - MR

    cw_ts    = usable_w * _COL_TS_FRAC
    cw_fn    = usable_w * _COL_FN_FRAC 
    cw_shift = usable_w * _COL_SHIFT_FRAC
    cw_msg   = usable_w - cw_ts - cw_fn- cw_shift

    # ── Paragraph styles ─────────────────────────────────────────────────────
    title_sty = ParagraphStyle(
        "PdfTitle",
        fontName=body_font,
        fontSize=16,
        leading=20,
        textColor=_color(_C.TITLE_FG),
        alignment=TA_LEFT,
        spaceAfter=2,
    )

    meta_sty = ParagraphStyle(
        "PdfMeta",
        fontName=body_font,
        fontSize=8,
        leading=12,
        textColor=_color(_C.META_FG),
        alignment=TA_LEFT,
    )

    col_hdr_sty = ParagraphStyle(
        "ColHdr",
        fontName=body_font,
        fontSize=8,
        leading=11,
        textColor=_color(_C.HEADER_FG),
        alignment=TA_LEFT,
    )

    ts_sty = ParagraphStyle(
        "TsCell",
        fontName=body_font,
        fontSize=7,
        leading=10,
        textColor=_color((0.20, 0.20, 0.20)),
        alignment=TA_LEFT,
    )
    fn_sty = ParagraphStyle(
        "FnCell",
        fontName=body_font,
        fontSize=6.5,
        leading=9,
        textColor=_color((0.30, 0.30, 0.30)),
        alignment=TA_LEFT,
        wordWrap="CJK",
    )

    # wordWrap='CJK' allows intra-word breaks — critical for Indic/Arabic text
    # that may not have conventional word-boundary spaces after NLLB translation.
    msg_sty = ParagraphStyle(
        "MsgCell",
        fontName=body_font,
        fontSize=8,
        leading=11,
        textColor=_color((0.08, 0.08, 0.08)),
        alignment=TA_LEFT,
        wordWrap="CJK",
    )

    shift_day_sty = ParagraphStyle(
        "ShiftDay",
        fontName=body_font,
        fontSize=7,
        leading=10,
        textColor=_color(_C.SHIFT_DAY_FG),
        alignment=TA_CENTER,
    )

    shift_night_sty = ParagraphStyle(
        "ShiftNight",
        fontName=body_font,
        fontSize=7,
        leading=10,
        textColor=_color(_C.SHIFT_NIGHT_FG),
        alignment=TA_CENTER,
    )

    # ── Data preparation ─────────────────────────────────────────────────────
    successful = sorted(
        (r for r in results if r.success),
        key=lambda r: r.meta.modified_at,
    )

    # Header row
    table_data = [[
        Paragraph("TIMESTAMP", col_hdr_sty),
        Paragraph("FILENAME",  col_hdr_sty),
        Paragraph("SHIFT",     col_hdr_sty),
        Paragraph("MESSAGE",   col_hdr_sty),
    ]]

    # Per-row background commands accumulated here
    row_bg_cmds: list[tuple] = []

    for row_idx, result in enumerate(successful, start=1):
        file_alerts  = [a for a in alerts if a.filename == result.meta.filename]
        source_text  = _pick_source_text(result)
        _check_unicode(f"PDF source [{result.meta.filename}]", source_text)

        raw_msg = highlight_keywords(source_text.strip(), file_alerts, mode="pdf")
        raw_msg = " ".join(raw_msg.split())
        safe_msg = _xml_safe(raw_msg)
        _check_unicode(f"PDF safe_msg [{result.meta.filename}]", safe_msg)

        # Timestamp: two-line format keeps column narrow
        ts_str = result.meta.modified_at.strftime("%Y-%m-%d\n%H:%M:%S")

        is_day = result.meta.shift_label == "Day Shift"
        shift_str = "DAY" if is_day else "NIGHT"

        table_data.append([
            Paragraph(ts_str,    ts_sty),
            Paragraph(_xml_safe(result.meta.filename), fn_sty),
            Paragraph(shift_str, shift_day_sty if is_day else shift_night_sty),
            Paragraph(safe_msg,  msg_sty),
        ])

        bg = _color(_C.ROW_ODD if row_idx % 2 == 1 else _C.ROW_EVEN)
        row_bg_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg))

    # ── Table style ──────────────────────────────────────────────────────────
    header_bg = _color(_C.HEADER_BG)
    ts_col_bg = _color(_C.TS_COL_BG)
    grid_c    = _color(_C.GRID)

    tbl_style = TableStyle([
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0),  header_bg),
        ("FONTNAME",      (0, 0), (-1, 0),  body_font),
        ("FONTSIZE",      (0, 0), (-1, 0),  8),
        ("TOPPADDING",    (0, 0), (-1, 0),  6),
        ("BOTTOMPADDING", (0, 0), (-1, 0),  6),
        ("LEFTPADDING",   (0, 0), (-1, 0),  6),

        # Data rows
        ("TOPPADDING",    (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),

        # Top-align so tall message cells don't push short timestamp cells down
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),

        # Timestamp column — subtle distinct background
        ("BACKGROUND",    (0, 1), (0, -1),  ts_col_bg),

        # Grid
        ("LINEBELOW",     (0, 0), (-1, 0),  1.0, grid_c),
        ("INNERGRID",     (0, 1), (-1, -1), 0.3, grid_c),
        ("BOX",           (0, 0), (-1, -1), 0.6, grid_c),
    ] + row_bg_cmds)

    table = Table(
        table_data,
        colWidths=[cw_ts, cw_fn,cw_shift, cw_msg],
        repeatRows=1,
        splitByRow=True,
        hAlign="LEFT",
    )
    table.setStyle(tbl_style)

    # ── Footer callback ──────────────────────────────────────────────────────
    footer_font  = body_font
    footer_label = "GPS CHEMOIL RADIO COMMUNICATION LOG"

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(footer_font, 6.5)
        canvas.setFillColor(_color(_C.FOOTER_FG))
        y = MB * 0.40
        canvas.drawString(ML, y, footer_label)
        canvas.drawRightString(PAGE_W - MR, y, f"Page {doc.page}")
        # Thin rule above footer
        canvas.setStrokeColor(_color(_C.GRID))
        canvas.setLineWidth(0.4)
        canvas.line(ML, MB * 0.70, PAGE_W - MR, MB * 0.70)
        canvas.restoreState()

    # ── Story assembly ───────────────────────────────────────────────────────
    folder_str = str(folder) if folder else "—"
    n_records  = len(successful)

    story = [
        # Title
        Paragraph("GPS CHEMOIL", title_sty),
        Paragraph("RADIO COMMUNICATION LOG", title_sty),
        Spacer(1, 2 * mm),
        HRFlowable(
            width="100%",
            thickness=1.2,
            color=_color(_C.TITLE_FG),
            spaceAfter=3 * mm,
        ),
        # Metadata
        Paragraph(f"<b>Generated :</b>  {run_at.strftime('%Y-%m-%d  %H:%M:%S')}", meta_sty),
        Paragraph(f"<b>Source dir :</b>  {folder_str}", meta_sty),
        Paragraph(f"<b>Records    :</b>  {n_records}", meta_sty),
        Spacer(1, 4 * mm),
        # Data table
        table,
    ]

    # ── Document build ───────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        leftMargin=ML,
        rightMargin=MR,
        topMargin=MT,
        bottomMargin=MB,
        title="GPS Chemoil Radio Communication Log",
        author="Automated Pipeline",
    )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)