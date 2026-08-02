# 🎙️ OpenDubber (Auto-Dub Pipeline)
An automated video translation and neural TTS sync pipeline using **Kokoro ONNX**, **FFmpeg**, and **Whisper**.
OpenDubber automatically takes video/subtitle pairs, processes speech timing, generates localized neural voiceovers using Kokoro, and remuxes the audio back onto the video track with volume normalization.

## ⚡ Quickstart: Kaggle
> 💡 **Why Kaggle?**  
> I strongly recommend the [Kaggle](https://www.kaggle.com) notebook over local setup, as it provides
> * **free T4 GPU** (30 hrs/week), pre-configured CUDA environment, and high-bandwidth asset processing.
> * **Enhanced Phonetics:** Pre-configured with `misaki` G2P for fluid, natural pronunciation.
> * **Advanced Audio Processing:** Integrated `pytubefix` audio extraction + `whisper` speech-to-text.

### Setup Instructions
1. Open the [OpenDubber Kaggle Notebook](https://www.kaggle.com/aladinetk/opendubber).
2. Click **"Copy & Edit"** in the top right.
3. Ensure **GPU T4 x2** is enabled under `Settings -> Accelerator`.
4. Make sure Kaggle can access the internet under `Settings -> Turn on internet`.
5. *(Optional)* Add your secure queue/credentials in **Add-ons -> Secrets**.
6. Run the notebook sequentially!

### 📝 Subtitle Generation & Dubbing Workflow
#### 1. Automatic Transcription (Whisper)
If your source media lacks an `.srt` file, the pipeline automatically extracts audio via `pytubefix` (with `yt-dlp` fallback) and runs OpenAI Whisper to generate timestamped subtitles:
* **Pytubefix:** Streamlines audio extraction directly from web sources.
* **Whisper:** Transcribes audio to synchronized `.srt` tracks in target languages.
#### 2. Speech Synthesis & Remuxing (`autodub.py`)
Once `.srt` files are present, `autodub.py` executes speech synthesis and final assembly:

```bash
python autodub.py --srt "/path/to/subtitles.srt" --out "/path/to/output_synced.wav"
```
---

## 🛠️ Local Installation (Windows)
If you prefer running offline on your local machine we need few steps:
> ℹ️ **Note:** The local script is kept intentionally lightweight and uses standard CPU execution. It does **not** include integrated YouTube audio downloaders, Whisper transcription, or advanced G2P engines (`misaki`). You will need to provide ready-made `.mkv` and `.srt` files.

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
└── autodub_local.py
```

## 🎬 Running the Pipeline
1. On your terminal navigate to the dubbing_project
2. Generate Synchronized Audio

   Run `auto_dub.py` with default settings (looks for `subtitles.srt`) or pass custom flags:
    ```powershell
    # Default run (subtitles.srt -> output_audio_synced.wav using am_adam)
    python auto_dub.py
    
    # Custom run with specific files & voice
    python auto_dub.py -i video_subtitle_translated.srt -o english_dub.wav -v am_adam
    
    # View all supported CLI options
    python auto_dub.py --help
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
    pip uninstall kokoro-onnx soundfile misaki -y
    winget uninstall Python3 FFmpeg
    # Delete pip cache AND leftover user-installed Python packages/environments
    Remove-Item -Recurse -Force "$env:LOCALAPPDATA\pip" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Programs\Python" -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force "$env:APPDATA\Python" -ErrorAction SilentlyContinue
    ```

[![Ko-fi](https://img.shields.io/badge/Ko--fi-Donate-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/aladinetk)
[![Liberapay](https://img.shields.io/badge/Liberapay-Donate-F6C915?style=for-the-badge&logo=liberapay&logoColor=black)](https://liberapay.com/AladineTK/)
