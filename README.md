# 🎙️ OpenDubber (Auto-Dub Pipeline)
An automated, GPU-accelerated video dubbing and audio pipeline designed to generate natural-sounding voiceovers from subtitles using **Kokoro TTS** and **FFmpeg**.

## ⚡ Quick Start Pipeline
> 💡 **Why Kaggle?**  
> I strongly recommend the [Kaggle](https://www.kaggle.com) notebook over local setup, as it provides
> * **free T4 GPU** (30 hrs/week), pre-configured CUDA environment, and high-bandwidth asset processing.
> * **Enhanced Phonetics:** Pre-configured with `misaki` G2P for fluid, natural pronunciation.
> * **Advanced Audio Processing:** Integrated `pytubefix` audio extraction + `whisper` speech-to-text.

Run the [OpenDubber Kaggle Notebook](https://www.kaggle.com/aladinetk/opendubber).

The notebook is divided into three streamlined phases:
1. **`Engine Warming`**  
   Installs system dependencies (`espeak-ng`, `ffmpeg`, `megatools`), sets up CUDA-accelerated `onnxruntime-gpu` for Kaggle T4 GPUs, fetches Kokoro v1.0 model weights, and pulls execution scripts.
2. **`Dubbing Machine`**  
   Launches the interactive IPyWidgets UI dashboard. Allows downloading video assets via Mega, managing batch video/SRT queues, selecting Kokoro voice profiles/speech speeds, and running the dubbing engine.
3. **`Inspection Bay` (Optional)**  
   Generates fast HTML5 video clip samples directly inside the notebook to preview audio sync and voice quality before downloading full outputs.

## 🛠️ Transcript & Subtitle Utilities
### 🎙️ YouTube & Whisper Auto-Transcription
Generate `.srt` subtitles from any video link when transcripts aren't available:
* **Audio Extraction:** Fetches streams via `pytubefix`.
* **Speech-to-Text:** Generates timestamped `.srt` files locally using OpenAI's `whisper` (`--model turbo` or `large-v3`).

### 🧹 Subtitle Cleaning
`subfix.py` the CLI utility to validate, re-index, clean formatting errors, and strip problematic tags from subtitles:

```bash
# Clean in-place
!python subfix.py --srt "/path/to/subtitles.srt"

# Output to new file
!python subfix.py --srt "/path/to/subtitles.srt" --out "/path/to/cleaned.srt"
```
## 📂 Repository Structure
* **`opendubber.ipynb`**: Master Kaggle/Jupyter notebook containing the full 3-step pipeline setup and UI.
* **`dashboard.py`**: Interactive IPyWidgets UI panel for queue & asset management inside the notebook.
* **`batchdub.py`**: Batch processing runner that loops through video/SRT queues.
* **`autodub.py`**: Core audio synthesis engine, time-stretching, and FFmpeg remuxing logic (GPU/Kaggle optimized).
* **`autodub_local.py`**: Lightweight standalone CPU script for running dubs locally on Windows/Linux.
* **`subfix.py`**: Standalone CLI utility for validating, cleaning, and repairing `.srt` subtitle files.

## 🛠️ Local Installation (Windows)
If you prefer running offline on your local machine instead of Kaggle, here are the setup steps:
> ℹ️ **Note:** The local workflow is kept intentionally lightweight and uses standard CPU execution. It does **not** include integrated YouTube audio downloading, Whisper transcription, or advanced G2P engines (`misaki`). You will need to provide ready-made `.mkv` and `.srt` files.

### 1. Preparations
1. Download your source video (`.mp4` or `.mkv`) using a local downloader like [Any Video Converter](https://www.any-video-converter.com/en8/for_video_free/) or similar local downloader.
2. Copy the original YouTube video transcript text.
3. Pass the transcript to an LLM (e.g., Gemini / ChatGPT) with a domain-aware prompt:
    > Translate this transcript from [Source Language] to [Target Language] for a [Recipe/Game/Topic Context] video. Format directly as a downloadable synchronized `.srt` file.
4. Download the Python file [`autodub_local.py`](./autodub_local.py)

### 2. System Dependencies
Open **PowerShell** (or Command Prompt) and run the following commands:
Install Python and FFmpeg automatically via Windows Package Manager:
```powershell
winget install Python3 FFmpeg
```
Note: After running this, close and reopen your terminal so Windows recognizes `python` and `ffmpeg` in your system PATH. Or just shift-click on the terminal taskbar to open a new one.

### 3. Python Packages
Install the required TTS and audio processing libraries:

```powershell
pip install kokoro-onnx soundfile
```

### 4. Download Model Weights
Download these two required files:
- 🎡 Model architecture [kokoro-v1.0.onnx](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx)
- 🔉 Voice embeddings [voices-v1.0.bin](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin)

### Folder structure
Finally you need to create a folder and have it structured like this
```text
dubbing_project/
├── input_video.mkv
├── subtitles.srt
├── kokoro-v1.0.onnx
├── voices-v1.0.bin
└── 
```

## 🎬 Running the Pipeline
1. On your terminal navigate to the dubbing_project
2. Generate Synchronized Audio

   Run `auto_dub_local.py` with default settings (looks for `subtitles.srt`) or pass custom flags:
    ```powershell
    # Default run (subtitles.srt -> output_audio_synced.wav using am_liam)
    python autodub_local.py
    
    # Custom run with specific files & voice
    python autodub_local.py --srt video_subtitle_translated.srt -out english_dub.wav -v am_adam
    
    # View all supported CLI options
    python autodub_local --help
    ```
    Explore voice samples on the [hexgrad/Kokoro-TTS](https://huggingface.co/spaces/hexgrad/Kokoro-TTS)
   
 3. Merge Audio & Video

    Merge the newly synthesized audio track with your original video while applying loudness normalization:
    ```powershell
    ffmpeg -i "input_video.mkv" -i "output_audio_synced.wav" -c:v copy -c:a aac -af "loudnorm" -map 0:v:0 -map 1:a:0 "final_dubbed_video.mp4"
    ```
## 🧹 Teardown (Optional)
When finished dubbing, save your videos onto your preferred storage (Drive, Dropbox, Mega, etc.), you can clean up your system environment.
1. Remove the dubbing_project folder
2. Remove Python Packages and the runtimes
   ```powershell
    pip uninstall kokoro-onnx soundfile -y
    winget uninstall Python3 FFmpeg
    # Delete pip cache AND leftover user-installed Python packages/environments
    Remove-Item -Recurse -Force "$env:LOCALAPPDATA\pip" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Programs\Python" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$env:APPDATA\Python" -ErrorAction SilentlyContinue
    ```
## 📜 License & Acknowledgments
This project relies on several remarkable open-source tools:
* **Neural TTS Engine:** Powered by [Kokoro ONNX](https://github.com/hexgrad/kokoro).
* **Audio & Video Processing:** Handled via [FFmpeg](https://ffmpeg.org/).
* **Transcription:** Driven by [OpenAI Whisper](https://github.com/openai/whisper).
* **Media Extraction:** Audio streams fetched using [PyTubefix](https://github.com/JuanBindez/pytubefix) and [yt-dlp](https://github.com/yt-dlp/yt-dlp).
* **G2P Processing:** Enhanced phonetics powered by [Misaki](https://github.com/hexgrad/misaki).

## ☕ Support the Project

Enjoying videos in your language thanks to OpenDubber? Consider supporting the project!

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Donate-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/aladinetk)
[![Liberapay](https://img.shields.io/badge/Liberapay-Donate-F6C915?style=for-the-badge&logo=liberapay&logoColor=black)](https://liberapay.com/AladineTK/)



