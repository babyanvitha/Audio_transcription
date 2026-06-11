# GPS Chemoil -- AI Radio Transcription & Alert Suite

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#license)
[![Status](https://img.shields.io/badge/status-production-brightgreen.svg)](#)

A production-ready batch audio transcription system designed for multilingual radio communications. Automatically converts `.wav` recordings into English transcripts, detects critical safety keywords, and generates professional shift-based reports in TXT and PDF formats.

**Built for:** GPS Chemoil Port Operations | **Use case:** Radio communication archival & compliance reporting

---

## Features

### Core Capabilities
- **Batch Audio Processing**: Convert entire folders of `.wav` files in a single run
- **Multilingual Transcription**: Automatic language detection for 100+ languages via OpenAI Whisper
- **Auto-Translation**: Convert non-English speech to English using Meta's NLLB-200 model
- **Critical Keyword Detection**: Scan transcripts for safety-critical terms (fire, explosion, emergency, etc.)
- **Shift Classification**: Automatically categorize recordings by Day/Night shifts based on file timestamps
- **Professional Reporting**: Generate chronological TXT and PDF reports with keyword highlighting

### Output Formats

| Format | Purpose | Features |
|--------|---------|----------|
| **TXT** | Archival & grep-friendly | Pipe-delimited, UTF-8, monospace | 
| **PDF** | Professional distribution | A4 layout, colour-coded shifts, vector text |

### Supported Languages
- **Auto-detection**: Whisper detects language automatically from speech
- **Translation**: Malayalam, Arabic, Tamil, Hindi, English -> English (NLLB-200)
- **Fallback**: Preserved original language if translation unavailable

### Safety & Compliance
- **Keywords monitored**: Fire, Explosion, Spill, Gas Leak, Emergency, Evacuation, Injury, Toxic, Flood, Mayday, etc.
- **Context preservation**: Keyword hits include surrounding 300-character excerpt in reports
- **UTF-8 integrity**: Full Unicode support (Indic scripts, Arabic, emoji) with diagnostics at every boundary

---

## Architecture

### System Overview

```
[INPUT: Folder of .wav files (radio recordings)]
          |
          v
[1. METADATA EXTRACTION]
   - Scan .wav files
   - Extract modification timestamp
   - Classify Day/Night shift
          |
          v
[2. TRANSCRIPTION (Whisper)]
   - Speech -> Text
   - Auto language detection
   - Confidence scoring
          |
          v
[3. TRANSLATION (NLLB-200)]
   - Optional: Non-English -> English
   - Per-sentence language detect
   - Mixed-language handling
          |
          v
[4. KEYWORD ALERTS]
   - Regex matching (case-insensitive)
   - Context extraction
   - Hit counting
          |
          v
[5. REPORT GENERATION]
   - Chronological sort
   - Keyword highlighting
   - Shift grouping (TXT) / coloring (PDF)
          |
          v
[OUTPUT: TXT & PDF reports in audio folder]
```

### Processing Pipeline Stages

#### **Stage 1: Metadata Extraction**
- Locates all `.wav` files in the input folder
- Reads file modification timestamp
- Auto-detects shift: **Day Shift** (06:00-18:00) or **Night Shift** (18:00-06:00)
- Handles shift override flag (`--shift day|night`)

#### **Stage 2: Transcription**
- Loads OpenAI Whisper model (tiny/base/small/medium/large)
- Processes audio with settings:
  - `fp16=False` (CPU-optimized)
  - Optional domain vocabulary prompt (via `WHISPER_INITIAL_PROMPT`)
  - Language: auto-detect or override via config
- Extracts: text, language code, language confidence score, segments

#### **Stage 3: Translation (Optional)**
- Detects if transcribed text is non-English
- Per-sentence language detection using `langdetect`
- Tokenizes with NLLB tokenizer (max 512 tokens per chunk)
- Translates each chunk independently, stitches results
- **Handles mixed-language input**: Splits Malayalam + English sentence -> translates only Malayalam
- Preserves original in `translated_text` field

#### **Stage 4: Keyword Detection**
- Scans both original and translated text (configurable via `REPORT_TEXT_MODE`)
- Case-insensitive regex matching against `CRITICAL_KEYWORDS` list
- Extracts 300-character context window around each hit
- Returns: filename, keywords found, total hits

#### **Stage 5: Report Generation**
- **TXT Report**:
  - Fixed-width pipe-delimited format
  - Chronologically sorted records
  - DAY/NIGHT section headers
  - Keywords wrapped in `***markers***`
  
- **PDF Report**:
  - Professional A4 layout (1.8 cm margins)
  - Single chronological table (no section breaks)
  - Colour-coded shift labels (green=DAY, blue=NIGHT)
  - Keywords rendered as **bold red** text
  - Automatic page breaks; headers repeat on every page
  - Unicode font fallback (Noto Sans -> Helvetica)

---

## Folder Structure

```
audio_transcription/

+-- main.py                          # Entry point (CLI)
+-- requirements.txt                 # Python dependencies
+-- README.md                        # This file
|
+-- config/
|   +-- __init__.py
|   +-- settings.py                  # All configurable parameters
|
+-- src/
|   +-- __init__.py
|   |
|   +-- pipeline.py                  # Orchestrates pipeline stages
|   |
|   +-- ingestion/
|   |   +-- __init__.py
|   |   +-- metadata.py              # Metadata extraction, shift detection
|   |
|   +-- transcription/
|   |   +-- __init__.py
|   |   +-- engine.py                # Whisper transcription engine
|   |   +-- translator.py            # NLLB translation + language detection
|   |
|   +-- alerts/
|   |   +-- __init__.py
|   |   +-- keyword_detector.py      # Regex-based keyword scanning
|   |
|   +-- reports/
|   |   +-- __init__.py
|   |   +-- builder.py               # TXT & PDF report generation (ReportLab)
|   |
|   +-- utils/
|       +-- __init__.py
|       +-- logger.py                # Rotating file + console logging
|
+-- audio_files/                     # Sample input folder (optional)
+-- logs/                            # Application logs (auto-created)
+-- output/                          # Generated reports (auto-created)
    +-- transcripts/
    +-- reports/
```

---

## Installation

### Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.9 | 3.11+ |
| FFmpeg | 4.2 | 5.0+ |
| RAM | 4 GB | 8 GB+ |
| Disk | 2 GB | 10 GB (for model cache) |

#### FFmpeg Setup

**macOS** (Homebrew):
```bash
brew install ffmpeg
```

**Linux** (Ubuntu/Debian):
```bash
sudo apt-get install ffmpeg
```

**Windows** (via winget):
```cmd
winget install Gyan.FFmpeg
```

Verify:
```bash
ffmpeg -version
ffprobe -version
```

### Step-by-Step Installation

**1. Clone / Extract Repository**
```bash
cd /path/to/audio_transcription
```

**2. Create Virtual Environment**
```bash
# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (Command Prompt)
python -m venv .venv
.venv\Scripts\activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

**3. Install Python Dependencies**
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- `openai-whisper` — Speech recognition
- `torch` — PyTorch (CPU, no CUDA)
- `transformers` — Hugging Face models (NLLB, AutoTokenizer)
- `langdetect` — Language detection
- `reportlab` — PDF generation
- `sentencepiece` — Tokenization for NLLB
- `numpy` — Numerical computing

**4. Pre-download Models (Optional but Recommended)**

On first run, models are downloaded automatically (~2-3 GB). To pre-download:

```bash
# Whisper (e.g., 'small' model)
python -c "import whisper; whisper.load_model('small')"

# NLLB Translation
python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM; \
  AutoTokenizer.from_pretrained('facebook/nllb-200-distilled-600M'); \
  AutoModelForSeq2SeqLM.from_pretrained('facebook/nllb-200-distilled-600M')"
```

Models are cached in `~/.cache/whisper/` and `~/.cache/huggingface/`.

---

## Configuration

All settings are in `config/settings.py`.

### Transcription Settings

```python
WHISPER_MODEL = "small"              # tiny|base|small|medium|large
WHISPER_LANGUAGE = None              # None (auto), "en", "ml", "ar", "ta", "hi"
WHISPER_INITIAL_PROMPT = ""          # Optional domain vocabulary for Whisper
```

### Shift Detection

```python
SHIFT_DAY_START = 6                  # 06:00 (24-hour format)
SHIFT_DAY_END = 18                   # 18:00
SHIFT_NIGHT_START = 18               # 18:00
SHIFT_NIGHT_END = 6                  # 06:00 (wraps midnight)
```

### Critical Keywords

```python
CRITICAL_KEYWORDS = [
    "fire", "explosion", "spill", "oil spill", "chemical spill",
    "leak", "gas leak", "emergency", "evacuate", "evacuation",
    "mayday", "help", "injured", "injury", "accident",
    "hazmat", "toxic", "smoke", "flood",
]
```
All matches are **case-insensitive**.

### Report Generation

```python
REPORT_FORMAT = "both"               # "txt" | "pdf" | "both"
REPORT_TEXT_MODE = "transcribed"     # "transcribed" (raw) | "translated" (English)
```

**Explanation of `REPORT_TEXT_MODE`:**
- `"transcribed"`: Show original language text in reports
- `"translated"`: Show auto-translated English text (if available)

### File Paths

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TRANSCRIPTS_DIR = OUTPUT_DIR / "transcripts"
REPORTS_DIR = OUTPUT_DIR / "reports"
LOGS_DIR = PROJECT_ROOT / "logs"
```

### Metadata Extraction

```python
FILENAME_REGEX = r"^(?P<channel>CH\d+)_(?P<radio_id>[0-9a-fA-F]+)_(?P<suffix>.+)\.wav$"
# GPS Chemoil radio filenames: CH2_01000485_54.wav
```

### Company / Report Metadata

```python
COMPANY_NAME = "GPS Chemoil"
SITE_NAME = "Port of Fujairah Terminal"
REPORT_TITLE = "Shift Radio Communication Transcript Report"
```

---

## Usage

### Basic Command

```bash
python main.py "/path/to/audio/folder"
```

### With Options

```bash
# Force Day shift (ignore timestamps)
python main.py "/path/to/audio" --shift day

# Force Night shift
python main.py "/path/to/audio" --shift night

# Override Whisper model
python main.py "/path/to/audio" --model medium

# Dry-run: scan files only, no transcription
python main.py "/path/to/audio" --dry-run

# Combined
python main.py "/path/to/audio" --shift night --model small --dry-run
```

### Argument Reference

| Argument | Short | Values | Default | Purpose |
|----------|-------|--------|---------|---------|
| `folder` | — | path | *required* | Input folder with .wav files |
| `--shift` | `-s` | day/night/auto | auto | Override shift detection |
| `--model` | `-m` | tiny/base/small/medium/large | config | Override Whisper model |
| `--dry-run` | — | flag | off | Scan metadata only |

### Output

Reports are generated inside the input folder:

```
audio_folder/
├── audio_file_1.wav
├── audio_file_2.wav
│
├── overall_summary_report.txt      # Pipe-delimited transcript log
└── overall_summary_report.pdf      # Professional A4 report
```

---

## Sample Output

### TXT Report Format

```
================================================================
   GPS CHEMOIL RADIO COMMUNICATION LOG
================================================================

Generated  : 2026-06-11 14:35:22
Source dir : /path/to/audio_files
Records    : 3 (day: 2, night: 1)

------------------------------------------------------------
TIMESTAMP            | SHIFT | MESSAGE
------------------------------------------------------------

DAY SHIFT
----

2026-06-11 07:30:15  | DAY   | Manifest received for berth 3, ***CHEMICAL SPILL*** 
                     |       | kit dispatched
                     |       | 
2026-06-11 14:22:00  | DAY   | All clear, systems nominal


NIGHT SHIFT
================================================================
                 NIGHT SHIFT
================================================================

2026-06-11 22:15:44  | NIGHT | Container check complete, no issues

================================================================
                     END OF LOG
================================================================
```

### PDF Report Features

- **Professional A4 layout** with header and footer
- **Colour-coded shifts**: Green (DAY), Dark Blue (NIGHT)
- **Chronological table** with alternating row backgrounds
- **Bold red keywords**: Safety-critical terms highlighted
- **Auto-wrapping**: Message text breaks intelligently across pages
- **Repeating headers** on every page for readability
- **Unicode fonts**: Supports Indic scripts, Arabic, emoji (where fonts available)

---

## Language Support

### Supported Input Languages (Whisper)

Whisper detects from audio automatically. Common examples:

| Language | Code | Region | Encoding |
|----------|------|--------|----------|
| English | en | — | ASCII/UTF-8 |
| Arabic | ar | Middle East | UTF-8 |
| Malayalam | ml | India | UTF-8 (Indic) |
| Tamil | ta | India | UTF-8 (Indic) |
| Hindi | hi | India | UTF-8 (Devanagari) |

### Translation Pipeline (NLLB-200)

**Current Support:**
- Malayalam -> English
- Arabic -> English
- Tamil -> English
- Hindi -> English
- English -> English (pass-through)

**Mixed-Language Handling:**
If input contains Malayalam + English in one sentence:
```
Input:  "Manifest received for berth 3, എന്നാൽ കണ്ടെയ്നർ കാത്തിരിപ്പിലുണ്ട്"
```

NLLB segments by language and translates only non-English parts:
```
Output: "Manifest received for berth 3, but container is waiting"
```

### Language Fallback
- If language detection fails -> defaults to `"en"` (English)
- If translation fails -> uses original transcribed text
- All errors logged with severity level

---

## Technical Details

### Models & Libraries

| Component | Library | Version | Notes |
|-----------|---------|---------|-------|
| **Speech Recognition** | `openai-whisper` | ≥20231117 | Medium model: ~1.5 GB |
| **Translation** | `transformers` + NLLB | ≥4.40.0 | facebook/nllb-200-distilled-600M: ~2 GB |
| **Language Detection** | `langdetect` | ≥1.0.9 | Per-sentence detection |
| **PDF Generation** | `reportlab` | ≥4.0.0 | Pure Python, no Ghostscript needed |
| **Tokenization** | `sentencepiece` | ≥0.1.98 | NLLB tokenizer |
| **Numerical Compute** | `torch` | ≥2.0.0 | CPU-optimized (no CUDA) |
| **Logging** | Python stdlib | 3.11+ | Rotating file handler |

### Key Design Decisions

1. **CPU-only processing** (`fp16=False`): Ensures compatibility across environments without NVIDIA GPUs
2. **Distilled NLLB model**: ~600M parameters vs. 3.5B full; trades minor accuracy for 6× speed
3. **Per-sentence translation**: Handles mixed-language input (radio operators code-switch)
4. **Unicode boundary diagnostics**: DEBUG logs at every I/O step to trace text corruption
5. **Lazy-format logging**: Uses `%s` placeholders instead of f-strings for production safety
6. **Streaming architecture**: Processes one file at a time, not all in memory
7. **ReportLab PDF**: Pure Python (no external processes), integrates Unicode font fallback

### Token Limits & Chunking

| Stage | Limit | Strategy |
|-------|-------|----------|
| Whisper | ~480K tokens | Streams audio; handles arbitrary length |
| NLLB | 512 tokens | Splits on sentence boundaries; re-joins |
| Keyword scan | Unlimited | Line-by-line regex; memory-efficient |

---

## Performance Considerations

### Model Sizes & Memory

| Model | Size | VRAM | Speed | Accuracy |
|-------|------|------|-------|----------|
| tiny | 40 MB | 100 MB | ~1 min/4 min | Low |
| base | 140 MB | 200 MB | ~2 min/4 min | Good |
| **small** | 500 MB | 800 MB | ~4 min/4 min | **Very Good** (RECOMMENDED) |
| medium | 1.5 GB | 2 GB | ~8 min/4 min | Higher |
| large | 3.0 GB | 4 GB | ~15 min/4 min | Highest |

*Processing time listed as: CPU / 4-min audio clip*

### Per-Stage Latency

| Stage | Latency | Bottleneck |
|-------|---------|-----------|
| Metadata scan | <100ms | I/O |
| Transcription | **3-60 sec/file** | Model inference (CPU) |
| Translation | 1-10 sec/file | NLLB forward passes |
| Keyword detection | 10-100ms/file | Regex matching |
| Report generation | 200-500ms | PDF rendering |

### Optimization Tips

- **Pre-download models**: Avoid first-run 2-3 GB download over network
- **Use `--model small`**: Sweet spot for accuracy vs. speed
- **Batch runs**: Process multiple audio folders sequentially; no parallelization overhead
- **Use TXT-only**: Skip PDF rendering (`REPORT_FORMAT = "txt"`) for speed (5-10% faster)

### Memory Profile

| Component | Peak RAM |
|-----------|----------|
| Base Python + logger | ~50 MB |
| Whisper (small model) | ~800 MB |
| NLLB (distilled) | ~1.2 GB |
| ReportLab PDF builder | ~100 MB |
| **Total** | **~2.2 GB** |

Typical run on 8 GB RAM: **Safe** [OK] | On 4 GB RAM: **Possible but tight** [CAUTION]

---

## Error Handling & Troubleshooting

### Common Issues

#### **"ffmpeg not found"**
```
Error: ffmpeg is required
```
**Solution:**
```bash
# Verify installation
ffmpeg -version
ffprobe -version

# macOS: Install Homebrew, then
brew install ffmpeg

# Linux: Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows: Install from https://ffmpeg.org/download.html or use winget
```

#### **"No .wav files found"**
```
Warning: No .wav files found in /path/to/folder
```
**Cause:** Folder contains non-.wav files or is empty
**Solution:**
- Verify folder path with `--dry-run`: `python main.py /path --dry-run`
- Check file extensions (must be `.wav`, not `.mp3`, `.m4a`, etc.)
- Use absolute paths: `/Users/username/radio/` not `~/radio/`

#### **"Whisper model download failure"**
```
Error: Failed to download model 'small'
```
**Cause:** Network timeout, SSL certificate, or permission issues
**Solution:**
```bash
# Test internet
ping huggingface.co

# Manual model download
python -c "import whisper; whisper.load_model('small')"

# Or pre-download via cache
export TRANSFORMERS_CACHE=~/.cache/huggingface
```

#### **"CUDA out of memory"**
**Cause:** Running GPU version on insufficient VRAM
**Solution:** This distribution is CPU-only; if you compiled with CUDA, revert to `fp16=False`:
```python
# config/settings.py or engine.py
fp16 = False
```

#### **"UTF-8 replacement characters (U+FFFD) in output"**
```
[UNICODE] Replacement characters (U+FFFD) found in NLLB output
```
**Cause:** NLLB tokenizer clipped UTF-8 multi-byte sequence
**Solution:** Enable debug logging to trace point of corruption
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### **"PDF font rendering poor quality"**
**Cause:** No Unicode-capable TTF found on system
**Solution:**
```bash
# Linux: Install Noto Sans
sudo apt-get install fonts-noto fonts-noto-cjk

# macOS: Verify Arial Unicode.ttf exists
ls "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
```

### Diagnostic Tools

**Enable debug logging:**
```bash
export LOGLEVEL=DEBUG
python main.py /path/to/audio
```

**Check audio quality:**
```bash
ffprobe -v error -select_streams a:0 -show_entries stream=codec_name,sample_rate,channels -of default=noprint_wrappers=1 file.wav
```

**Validate UTF-8 output:**
```bash
file -i overall_summary_report.txt  # Should show "charset=utf-8"
```

---

## Future Improvements

### Short-term (Planned)
- [ ] **Stereo audio support**: Process left/right channels independently
- [ ] **Diarization**: Identify speaker changes ("Speaker 1: …", "Speaker 2: …")
- [ ] **Real-time streaming**: Accept RTMP/UDP audio feeds instead of .wav files only
- [ ] **Custom keyword per-shift**: Different alert lists for day vs. night operations
- [ ] **Confidence filtering**: Skip transcripts below language confidence threshold

### Medium-term (Proposed)
- [ ] **Multi-language translation**: Support French, Spanish, German, Chinese, etc.
- [ ] **Audio preprocessing**: Noise reduction, echo cancellation (torchaudio)
- [ ] **Excel export**: Alternative to TXT/PDF for data analysis
- [ ] **Web UI**: Simple Flask dashboard for monitoring batch runs
- [ ] **Slack/Teams alerts**: Post critical keyword hits to chat in real-time

### Long-term (Vision)
- [ ] **Custom fine-tuning**: Domain-specific model for radio jargon
- [ ] **Parallel processing**: Multi-GPU or multi-process batch transcription
- [ ] **Audio archive management**: S3/GCS storage backend integration
- [ ] **Compliance reporting**: GDPR-compliant PII redaction, audit logs
- [ ] **ML anomaly detection**: Detect unusual speech patterns or urgent tones

---

## Dependencies

### Production Requirements

```
openai-whisper>=20231117     # Speech recognition
torch>=2.0.0                 # Deep learning framework (CPU)
numpy>=1.24.0                # Numerical computing
transformers>=4.40.0         # Hugging Face models (NLLB)
langdetect>=1.0.9            # Language detection
reportlab>=4.0.0             # PDF generation
sentencepiece>=0.1.98        # Tokenization (NLLB)
```

### System Requirements

- **Python**: 3.11+
- **FFmpeg**: 4.2+ (for audio decoding)
- **FFprobe**: (ships with FFmpeg)
- **OS**: macOS 11+, Linux (Ubuntu 20.04+), Windows 10+

### Optional Enhancements

- **Noto Sans fonts** (Linux): `sudo apt-get install fonts-noto` for Unicode PDF rendering
- **CUDA** (GPU acceleration): Not included; CPU-only distribution for portability

---

## License

This project is provided as-is for operational use by GPS Chemoil.

```
MIT License

Copyright (c) 2026 GPS Chemoil

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## Support & Contribution

### Reporting Issues

When reporting bugs, include:
1. Python version: `python --version`
2. OS: macOS, Linux, Windows + version
3. FFmpeg version: `ffmpeg -version`
4. Exact command run
5. Error message + last 20 lines of logs (in `logs/transcription.log`)

### Contributing

This is a production system for GPS Chemoil operations. External contributions welcome via:
- Bug reports (with reproduction steps)
- Performance optimizations
- Language/model additions (with testing)

Ensure PRs include tests and updated documentation.

---

## Additional Resources

- [Whisper Model Card](https://github.com/openai/whisper)
- [NLLB Model Hub](https://huggingface.co/facebook/nllb-200-distilled-600M)
- [ReportLab Documentation](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [FFmpeg Formats & Codecs](https://ffmpeg.org/ffmpeg-formats.html)

---

**Last Updated:** June 2026 | **Status:** Production Ready [OK]
