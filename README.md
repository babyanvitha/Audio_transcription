# Project Overview

The system uses OpenAI Whisper for speech recognition and translation, allowing multilingual radio communications to be converted into readable English text. It is designed for processing folders containing multiple walkie-talkie or radio recordings and automatically generates:

- Individual transcript files for each audio recording
- Highlighted alert keywords within transcripts
- An overall chronological communication report grouped by shift

---

## Features

### Audio Transcription
- Processes `.wav` audio files
- Supports batch processing of entire folders
- Uses OpenAI Whisper speech-to-text models
- Supports automatic language detection
- Can translate non-English speech into English

### Alert Detection
Detects critical operational keywords such as:

- Fire
- Explosion
- Spill
- Chemical Spill
- Oil Spill
- Gas Leak
- Emergency
- Evacuation
- Injury
- Accident
- Toxic
- Smoke
- Flood

Detected keywords are highlighted within transcript outputs.

### Shift Classification
Automatically categorizes recordings into:

- Day Shift (06:00–18:00)
- Night Shift (18:00–06:00)

using the audio file's modification timestamp.

### Reporting
Generates:
- Individual Transcript Files
- Overall Summary Report


---

## Python Version

Recommended:

```text
Python 3.11+
```

Verify:

```bash
python --version
```

---

## FFmpeg

Required by Whisper for audio processing.

Verify installation:

```bash
ffmpeg -version
```

```bash
ffprobe -version
```

---

# Installation

## Step 1: Extract Project

## Step 2: Create Virtual Environment

### Windows

```cmd
python -m venv .venv
```

### macOS/Linux

```bash
python3 -m venv .venv
```

---

## Step 3: Activate Virtual Environment

### Windows Command Prompt

```cmd
.venv\Scripts\activate
```

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
source .venv/bin/activate
```

Expected:

```text
(.venv)
```

---

## Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 5: Install FFmpeg

### Simplest Method (Windows)

Open Command Prompt:

```cmd
winget install Gyan.FFmpeg
```

Verify:

```cmd
ffmpeg -version
```

```cmd
ffprobe -version
```

---

### Alternative (No Admin Rights)

Download:

https://www.gyan.dev/ffmpeg/builds/

Extract to:

```text
C:\Users\<username>\Tools\ffmpeg
```

Add:

```text
C:\Users\<username>\Tools\ffmpeg\bin
```

to your User PATH.

---

# Running the Application

## Basic Usage

```bash
python main.py "<audio_folder_path>"
```

Example:

```bash
python main.py "/Users/username/RadioBackup/2026-05-16"
```

---
## Manual Shift Override

Force Day Shift:

```bash
python main.py "<audio_folder_path>" --shift day
```

Force Night Shift:

```bash
python main.py "<audio_folder_path>" --shift night
```

## Manual Whisper Model Selection

Override model for a run:

```bash
python main.py "<audio_folder_path>" --model small
```

Available models:

```text
tiny
base
small
medium
large
```

---

# Output Files

Outputs are generated directly inside the audio folder supplied to the application.

Example:

```text
audio_files/
│
├── CH2_01000485_54.wav
├── CH2_01000486_54.wav
│
├── CH2_01000485_54_transcript.txt
├── CH2_01000486_54_transcript.txt
│
└── overall_summary_report.txt
```

---

# Configuration

All configurable settings are located in:

```text
config/settings.py
```

---

## Changing Whisper Model

File:

```text
config/settings.py
```

Current:

```python
WHISPER_MODEL = "medium"
```

Available values:

```python
WHISPER_MODEL = "tiny"
WHISPER_MODEL = "base"
WHISPER_MODEL = "small"
WHISPER_MODEL = "medium"
WHISPER_MODEL = "large"
```

### Model Comparison

| Model | Speed | Accuracy |
|---------|---------|---------|
| tiny | Fastest | Lowest |
| base | Fast | Good |
| small | Recommended | Very Good |
| medium | Slower | Higher |
| large | Slowest | Highest |

Recommended for radio recordings:

```python
WHISPER_MODEL = "small"
```

---

## Changing Language Detection Behaviour

File:

```text
config/settings.py
```

Current:

```python
WHISPER_LANGUAGE = None
```

Meaning:

```text
Automatic language detection
```

---

Force English:

```python
WHISPER_LANGUAGE = "en"
```

Useful when all recordings are expected to be English.

---

Examples:

```python
WHISPER_LANGUAGE = "en"
WHISPER_LANGUAGE = "ar"
WHISPER_LANGUAGE = "ta"
WHISPER_LANGUAGE = "hi"
WHISPER_LANGUAGE = None
```

---

## Changing Translation Behaviour

File:

```text
src/transcription/engine.py
```

Locate:

```python
raw = model.transcribe(
    ...
    task="translate",
)
```

### Translate to English

```python
task="translate"
```

Behavior:

```text
Malayalam → English
Arabic → English
Tamil → English
```

---

### Preserve Original Language

```python
task="transcribe"
```

Behavior:

```text
Malayalam → Malayalam transcript
Arabic → Arabic transcript
Tamil → Tamil transcript
```

---

# Changing Alert Keywords

File:

```text
config/settings.py
```

Variable:

```python
CRITICAL_KEYWORDS
```

Example:

```python
CRITICAL_KEYWORDS = [
    "fire",
    "explosion",
    "spill",
    "gas leak",
    "emergency",
]
```

Keywords are matched case-insensitively.

---

# Project Structure

```text
audio_transcription/
│
├── main.py
│
├── config/
│   └── settings.py
│
├── src/
│   │
│   ├── ingestion/
│   │   └── metadata.py
│   │
│   ├── transcription/
│   │   └── engine.py
│   │
│   ├── alerts/
│   │   └── keyword_detector.py
│   │
│   ├── reports/
│   │   └── builder.py
│   │
│   └── pipeline.py
│
├── requirements.txt
│
└── README.md
```

---

# Pipeline Flow

```text
Audio Folder
      │
      ▼
Metadata Extraction
      │
      ▼
Whisper Transcription
      │
      ▼
Keyword Detection
      │
      ▼
Individual Transcript Generation
      │
      ▼
Overall Summary Report Generation
```

---

# First Run Notes

The first execution downloads the selected Whisper model from the internet.

Example:

```python
WHISPER_MODEL = "small"
```

The model is cached locally.

Subsequent runs:

- Do not require internet
- Reuse the cached model automatically

---

# Troubleshooting

## ffmpeg not found

Verify:

```bash
ffmpeg -version
```

```bash
ffprobe -version
```

Install FFmpeg and ensure it is available in PATH.

---

## Whisper model download failure

Check:

- Internet connection
- Python installation
- SSL certificates

---

## No transcript generated

Possible causes:

- Audio contains only noise/static
- Extremely short transmission
- Incorrect language detection
- Unsupported/corrupted audio file

Try:

```python
WHISPER_MODEL = "small"
```

or

```python
WHISPER_LANGUAGE = "en"
```

if communications are primarily in English.

---
