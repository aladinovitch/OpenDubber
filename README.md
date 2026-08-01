# 🎙️ OpenDubber (Auto-Dub Pipeline)
An automated video translation and neural TTS sync pipeline using Whisper, Kokoro ONNX, and FFmpeg.

## ⚡ Quickstart: Kaggle (Recommended)
> **No local installation required.** Uses Kaggle's free T4 GPUs (30 hours/week).

1. Open the [OpenDubber Kaggle Notebook](https://www.kaggle.com/aladinetk/opendubber).
2. Click **"Copy & Edit"** in the top right.
3. Ensure **GPU T4 x2** is enabled under `Settings -> Accelerator`.
4. Make sure Kaggle can access the internet under `Settings -> Turn on internet`.
5. Run Cells 1 & 2 to initialize dependencies and `auto_dub.py`.
6. Update your asset link and names in Cell 3 and run!

*Note: A free [Kaggle Account](https://www.kaggle.com) is required to run cells and access GPU acceleration.*

## 📝 Optional: Generate Subtitles
If the YouTube video does not have an existing transcript/subtitle file, generate foreign language `.srt` subtitles directly in Kaggle:
- `pytubefix`: Downloads the raw audio stream from YouTube (fallback: `yt-dlp` if blocked).
- `whisper`: Transcribes audio to `.srt`.

---

## 🛠️ Local Installation (Windows)
If you prefer running offline on your local machine we need few steps:

### 1. Preparations
1. Download your source video (`.mp4` or `.mkv`) using a local downloader like [Any Video Converter](https://www.any-video-converter.com/en8/for_video_free/) or similar local downloader.
2. Copy the original YouTube video transcript text.
3. Pass the transcript to an LLM (e.g., Gemini / ChatGPT) with a domain-aware prompt:
    > Translate this transcript from [Source Language] to [Target Language] for a [Recipe/Game/Topic Context] video. Format directly as a downloadable synchronized `.srt` file.
4. Create a working folder structure:
    ```text
    dubbing_project/
    ├── input_video.mkv
    ├── subtitles.srt
    ├── kokoro-v1.0.onnx
    ├── voices-v1.0.bin
    └── auto_dub.py (not required on Collab)
    ```
5. Make a python file: `auto_dub.py`

  <details>
    <summary>Click to expand auto_dub.py </summary>
    
  ```python
  import argparse
  import os
  import re
  import numpy as np
  import soundfile as sf
  from kokoro_onnx import Kokoro
  
  
  def timestamp_to_seconds(ts_str):
      """Converts SRT timestamp HH:MM:SS,mmm to float seconds."""
      hours, minutes, seconds = ts_str.replace(',', '.').split(':')
      return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
  
  
  def parse_srt_with_timestamps(filename):
      """Parses an SRT file and extracts clean text with start/end timestamps."""
      if not os.path.exists(filename):
          raise FileNotFoundError(f"Subtitles file not found: '{filename}'")
  
      with open(filename, 'r', encoding='utf-8') as f:
          content = f.read()
  
      # Match subtitle index, timestamps, and text
      pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n([\s\S]*?)(?=\n\n|\Z)'
      matches = re.findall(pattern, content)
  
      subtitles = []
      for match in matches:
          start_time = timestamp_to_seconds(match[1])
          end_time = timestamp_to_seconds(match[2])
          # Clean text lines and strip HTML tags
          raw_text = match[3].replace('\n', ' ').strip()
          text = re.sub(r'<[^>]+>', '', raw_text)
  
          if text:
              subtitles.append({
                  'start': start_time,
                  'end': end_time,
                  'text': text
              })
      return subtitles
  
  
  def main():
      parser = argparse.ArgumentParser(
          description="Generate synchronized TTS audio from an SRT file using Kokoro ONNX."
      )
      parser.add_argument(
          "-i", "--srt", default="subtitles.srt",
          help="Input SRT file path (default: subtitles.srt)"
      )
      parser.add_argument(
          "-o", "--output", default="output_audio_synced.wav",
          help="Output WAV audio path (default: output_audio_synced.wav)"
      )
      parser.add_argument(
        "-v", "--voice", default="am_adam",
        help="Kokoro voice name, e.g. 'af_bella', 'am_adam', 'am_michael' (default: am_adam)"
      )
      parser.add_argument(
          "-s", "--speed", type=float, default=1.0,
          help="Base speech speed multiplier (default: 1.0)"
      )
      parser.add_argument(
          "-l", "--lang", default="en-us",
          help="Language code (default: en-us)"
      )
      parser.add_argument(
          "--model", default="kokoro-v1.0.onnx",
          help="Path to Kokoro ONNX model weights (default: kokoro-v1.0.onnx)"
      )
      parser.add_argument(
          "--voices-bin", default="voices-v1.0.bin",
          help="Path to Kokoro voices binary file (default: voices-v1.0.bin)"
      )
  
      args = parser.parse_args()
  
      print(f"Loading Kokoro model ('{args.model}')...")
      if not os.path.exists(args.model) or not os.path.exists(args.voices_bin):
          raise FileNotFoundError(
              f"Model files missing. Ensure '{args.model}' and '{args.voices_bin}' exist in your folder."
          )
  
      kokoro = Kokoro(args.model, args.voices_bin)
  
      subtitles = parse_srt_with_timestamps(args.srt)
      print(f"Found {len(subtitles)} subtitle lines in '{args.srt}'.")
  
      audio_chunks = []
      current_sample_position = 0
      sample_rate = 24000  # Default Kokoro sample rate (24 kHz)
  
      for i, sub in enumerate(subtitles, 1):
          target_start_sample = int(sub['start'] * sample_rate)
  
          # Calculate silent samples needed before this subtitle line
          silence_needed = target_start_sample - current_sample_position
          if silence_needed > 0:
              audio_chunks.append(np.zeros(silence_needed, dtype=np.float32))
              current_sample_position += silence_needed
  
          # Generate audio for the line
          samples, sr = kokoro.create(
              sub['text'],
              voice=args.voice,
              speed=args.speed,
              lang=args.lang
          )
          sample_rate = sr  # Update sample rate dynamically
  
          audio_chunks.append(samples)
          current_sample_position += len(samples)
  
          if i % 10 == 0 or i == len(subtitles):
              print(f"Processed line {i}/{len(subtitles)} ({sub['start']:.1f}s)")
  
      # Concatenate all silence pads and speech chunks
      print("Assembling final audio track...")
      final_audio = np.concatenate(audio_chunks)
  
      # Save output WAV file
      sf.write(args.output, final_audio, sample_rate)
  
      total_minutes = len(final_audio) / sample_rate / 60
      print(f"\nDone! Saved: {args.output}")
      print(f"Final audio duration: {total_minutes:.2f} minutes")
  
  
  if __name__ == "__main__":
      main()
  ```
  </details>

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
Download these two required files and place them directly inside your project folder:
- 🎡 Model architecture [kokoro-v1.0.onnx](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx)
- 🔉 Voice embeddings [voices-v1.0.bin](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin)

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
