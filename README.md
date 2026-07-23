# Audio Classifier & Profanity Filter

## Overview

This application analyzes audio input — either an uploaded file or a live
microphone feed — to determine its content type (Speech, Music, or Noise),
detect the spoken language, and identify profane content. It is built with
Flet for the UI layer and Python for the audio-processing backend.

The project consists of two functional tracks:

1. **File-upload pipeline** — accepts an audio file, classifies it, detects
   language, and (on request) checks it for profanity.
2. **Live filter** — processes a microphone feed in real time and plays it
   back through the speaker with profane words bleeped out, using a short
   broadcast delay. This module is designed for eventual deployment as an
   Auracast BIS sink on Samsung devices, and its input/output layer is
   isolated accordingly to support that transition.

---

## Project Structure

```
audio_app/
├── main.py            Application entry point and UI (Flet)
├── audio_pipeline.py  File-upload pipeline
├── models/            Trained model files (not included)
├── stage1/             SVM training artifacts
├── profanity/          Profanity detection (wordlist + ML classifier)
├── speech/            Standalone language-detection test utility
├── realtime/          Live microphone-to-speaker filtering engine
└── requirements.txt
```

---

## File Reference

### main.py

The application's entry point and the entirety of its UI, built with Flet.
The file is organized into three parts:

- **Design system** — a `Palette` class defining the light and dark color
  schemes, and a set of reusable component builders (`card()`, `chip()`,
  `pill_button()`, `ring()`, `status_pill()`, etc.) used consistently across
  every screen.
- **Screen builders** — one function per screen: `build_home`,
  `build_result`, `build_history`, `build_live`, `build_analytics`,
  `build_settings`, `build_about`. Each returns the Flet component tree for
  that screen.
- **`main(page)`** — initializes the page theme and file picker, and defines
  a `navigate(screen_name)` router that switches the active screen and
  updates the bottom navigation bar. The module-level `ft.run(main)` call is
  the application's actual entry point.

**Screens:**

- **Home** — File picker (`wav`, `mp3`, `ogg`, `flac`, `m4a`, `aac`); a
  profanity-detection toggle set before a file is selected; a shortcut to the
  Live Filter screen; a "Recent" list from analysis history. File selection
  runs `analyze_audio()` on a background thread and navigates to Result.
- **Result** — Displays detected type, language, duration, and timestamp,
  with an in-app audio player. If profanity detection is enabled and the
  clip is classified as Speech, automatically runs translation and
  profanity checking in the background and displays a category-by-category
  score breakdown.
- **History** — Chronological list of past analyses (type, language,
  timestamp).
- **Live Filter** — Start/stop control for the real-time engine, a live
  status indicator, and a stats panel: detected language, seconds
  played/beeped, buffer depth, analysis pass count, unverified-segment
  count, input overflows, output underruns, active backend, delay, cushion,
  and active speaker/monitor.
- **Analytics** — Aggregate scan count, per-type distribution
  (Speech/Music/Noise), and a language-frequency breakdown of past speech
  clips.
- **Settings** — Theme toggle, history export (to `.txt`), and history
  clearing (with confirmation).
- **About** — Version information and specification summaries for the SVM
  classifier and the Whisper model.

### audio_pipeline.py

The file-upload analysis pipeline invoked from the Home screen. Loads three
models once at import time: the SVM classifier and its feature scaler (from
`models/`), and Whisper (`small`).

- **`extract_features(audio, sr)`** — Extracts the 57 features consumed by
  the SVM classifier: 20 MFCC means, 20 MFCC standard deviations, 12 chroma
  means, and one value each for spectral centroid, spectral bandwidth,
  spectral rolloff, zero-crossing rate, and RMS. This is the exact feature
  set `stage1/Features.csv` was built from.
- **`classify_audio(path)`** — Loads up to 10 seconds of audio at 16 kHz,
  extracts the 57 features, scales them, and returns `"Speech"`, `"Music"`,
  or `"Noise"`.
- **`detect_language(path)`** — Runs Whisper's language detection on the
  initial audio window and maps the result to one of 11 supported
  languages.
- **`transcribe_audio(path)`** — Transcribes audio in its original (source)
  language.
- **`translate_to_english(path)`** / **`translate_array_to_english(array, sr)`**
  — Translates audio to English using Whisper's translate task. The array
  variant operates on in-memory audio (used by the real-time pipeline) and
  expects 16 kHz input.
- **`check_profanity(text)`** — Passes English text to the `profanity`
  package's ML detector and returns its verdict, with a safe fallback if the
  model failed to load.
- **`analyze_audio(path)`** — The primary entry point called by `main.py` on
  every file upload. Runs classification, and language detection only when
  the type is Speech or Music. Transcription, translation, and profanity
  checking are intentionally deferred and triggered on demand from the
  Result screen, keeping the initial upload response fast.

**Note:** `audio_pipeline.py` performs an unconditional `import whisper` at
module load, with no fallback. Without `openai-whisper` installed, this
import fails — and since `main.py` imports `audio_pipeline` at startup, the
application fails to launch as a result.

### models/

Not source code — the expected location for two pre-trained artifacts:

```
models/svm_model.pkl
models/scaler.pkl
```

These must be supplied; they are not included in this repository. If
retraining is required, see **Training Data: MUSAN** below.

### stage1/

Reference artifacts documenting how the SVM classifier was trained. Not
loaded by the application at runtime.

- **`Features.csv`** — The MUSAN dataset after feature extraction: one row
  per clip, 57 feature columns (MFCC mean/standard deviation, chroma,
  spectral centroid/bandwidth/rolloff, zero-crossing rate, RMS) plus class
  label. This is the exact table `svm_model.pkl` and `scaler.pkl` were fit
  on.
- **`Model_results.csv`** — Training and evaluation results for the
  Speech/Music/Noise classifier.
- **Confusion matrix** — Classification results on the held-out test set,
  showing where the trained model confused one class for another.

Together, these three artifacts document classifier performance and provide
a baseline for any future retraining or feature-set changes.

### profanity/

Two complementary detection mechanisms:

- **`profanity_wordlist.py`** — `Wordlist` class providing fast, exact
  word/phrase matching with leetspeak normalization (`sh1t` → `shit`) and
  repeated-character collapsing (`fuuuck` → `fuuck`). Matching is
  whole-token by default to avoid false positives on innocuous words
  containing a flagged substring; a small set of unambiguous terms is also
  matched as a substring. Ships with a compact built-in English list;
  production deployments can supply additional per-language `.txt` files
  via `--wordlist-dir` (compatible with the community LDNOOBW list format).
  Because Whisper provides word-level timestamps, a wordlist match
  identifies the exact time range to bleep.
- **`profanity_detector.py`** — ML-based detection using
  `unitary/multilingual-toxic-xlm-roberta` via `transformers.pipeline()`,
  loaded at import time. `detect_profanity(text)` scores text against six
  categories (toxic, obscene, insult, threat, identity_attack,
  sexual_explicit) and flags content as profane above a 70% confidence
  threshold, returning the top category, its score, and the full label
  breakdown. `score_texts(list)` is a batched variant used by the real-time
  filter to localize a sentence-level flag down to the specific word
  responsible.
- **`__init__.py`** — Lazily imports `detect_profanity` / `score_texts` so
  that importing the package alone does not load the transformer model
  unless it is actually invoked.
- **`test_profanity.py`** — Manual test utility. Run without arguments for
  interactive text-mode testing, or supply an audio file path to run the
  complete pipeline (classification, transcription, translation, profanity
  check).

### speech/speech_language_detection.py

A standalone diagnostic script, independent of `main.py`. Loads Whisper
`small` and prompts for an audio file path in a loop, printing the detected
language for each. Intended for isolated testing of language detection.

### realtime/

The live microphone-to-speaker filtering engine. This directory includes its
own detailed `realtime/README.md`, covering CLI arguments, latency tuning,
and the Auracast integration path in full; consult it before modifying this
code. Contents:

- **`realtime_filter.py`** — Orchestrator. Builds the analyzer and runs the
  threaded live engine (capture → voice activity detection → transcription
  → profanity check → delayed, beeped playback); also provides an offline
  mode for file-in/file-out processing.
- **`config.py`** — `RealtimeConfig` dataclass defining all tunable
  parameters (timing, delay, VAD mode, beep settings, profanity thresholds,
  backpressure limits), plus the CLI argument parser that constructs one.
- **`transcription.py`** — A single `TranscriptionEngine` interface over
  three interchangeable backends: `faster-whisper` (recommended;
  approximately 4x faster on CPU), `openai-whisper` (fallback), and a
  dependency-free mock backend used for testing. All backends return an
  identical `Word(text, start, end)` structure.
- **`vad.py`** — Voice activity detection, used to avoid running
  transcription on non-speech audio. `EnergyVAD` (default) is a
  dependency-free adaptive noise-floor gate; `SileroVAD` is an optional
  neural alternative for noisy or music-bed audio.
- **`audio_io.py`** — Input sources (`MicSource`, `WavFileSource`,
  `StdinPCMSource`), the `SpeakerSink` output, beep-tone generation and
  overlay, WAV read/write, streaming resampling, and buffer management.
- **`selftest.py`** — Logic-level tests (resampling, chunk assembly,
  wordlist matching, beep placement, VAD) using the mock backend; requires
  no Whisper/torch installation.
- **`livetest.py`** — End-to-end test of the threaded live engine using a
  simulated clock, verifying zero sample loss and correct beep placement.

The Auracast integration point is isolated to `audio_io.py`: adding a new
input source class alongside `MicSource` and registering it in
`make_source()` is sufficient to integrate a new transport without modifying
the rest of the pipeline.

---

## Setup

**Python version:** 3.10–3.12 is recommended, matching the versions
`faster-whisper` and `torch` provide prebuilt wheels for.

**System dependencies (not installable via pip):**

```bash
sudo apt install libportaudio2   # Required for microphone/speaker I/O (sounddevice)
sudo apt install ffmpeg          # Required by Whisper to decode audio files
```

On macOS: `brew install portaudio ffmpeg`. On Windows, ensure `ffmpeg` is on
the system `PATH`; PortAudio ships bundled with the `sounddevice` wheel.

**Python dependencies:**

```bash
pip install -r requirements.txt
```

This installs the UI framework, the classification and Whisper stack, the
profanity detection models, and the live audio I/O dependencies. See
`requirements.txt` for the complete list.

**Model files:**

`audio_pipeline.py` requires two pre-trained files not included in this
repository:

```
models/svm_model.pkl
models/scaler.pkl
```

Place existing trained files in this location, or retrain following the
instructions below.

Once configured:

```bash
python main.py
```

---

## Training Data: MUSAN

The SVM classifier (Speech/Music/Noise; 57 features — MFCC, chroma, and
spectral features; RBF kernel) was trained on **MUSAN**, a public corpus of
music, speech, and noise recordings distributed by OpenSLR under a Creative
Commons / public-domain license.

**Download:**

```bash
wget https://www.openslr.org/resources/17/musan.tar.gz
tar -xvzf musan.tar.gz
```

This produces a `musan/` directory containing three subfolders — `music/`,
`speech/`, `noise/` — each holding 16 kHz WAV files organized by source. This
is the raw input expected by `extract_features()` in `audio_pipeline.py` for
retraining `svm_model.pkl` and `scaler.pkl`. To reuse the already-extracted
feature set instead of repeating extraction, refer to `stage1/Features.csv`.

This dataset is only required for retraining the classifier; it is not
needed if `svm_model.pkl` and `scaler.pkl` are already available.

---

## Usage

```bash
python main.py                             # Launch the application
python realtime/realtime_filter.py         # Live filter, standalone (microphone to speaker)
python realtime/selftest.py                # Real-time engine logic tests (no heavy dependencies)
python realtime/livetest.py                # End-to-end live-engine test with a simulated clock
python profanity/test_profanity.py         # Profanity detector — text or audio-file mode
python speech/speech_language_detection.py # Standalone Whisper language-detection utility
```
