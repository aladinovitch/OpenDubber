# Open-Dubber — Lightweight Local Video Dubbing Pipeline
A fast, zero-cloud-cost workflow to translate and dub videos locally using **Kokoro ONNX** for speech synthesis and **FFmpeg** for audio-video merging.

## 🛠️ Quick Installation (Windows)

Open **PowerShell** (or Command Prompt) and run the following commands:
### 1. System Dependencies
Install Python and FFmpeg automatically via Windows Package Manager:
```powershell
winget install Python.Python.3 FFmpeg
```
Note: After running this, close and reopen your terminal so Windows recognizes `python` and `ffmpeg` in your system PATH.

### 2. Python Packages
Install the required TTS and audio processing libraries:

```python
pip install kokoro-onnx soundfile
```

### 3. Download Model Weights
Download these two required files and place them directly inside your project folder:
- 🎡 Model architecture [kokoro-v1.0.onnx](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx)
- 🔉 Voice embeddings [voices-v1.0.bin](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin)

## 🍽️Preparations
1. Download your source video (`.mp4` or `.mkv`) using a local downloader like [Any Video Converter](https://www.any-video-converter.com/en8/for_video_free/) or similar local downloader.
2. Copy the original YouTube video transcript text.
3. Pass the transcript to an LLM (e.g., Gemini / ChatGPT) with a domain-aware prompt:
    > Translate this transcript from [Source Language] to [Target Language] for a [Recipe/Game/Topic Context] video. Format directly as a downloadable synchronized `.srt` file.
4. Create a working folder structure:
    ```text
    dubbing_project/
    ├── input_video.mkv
    ├── subtitles.srt
    ├── auto_dub.py
    ├── kokoro-v1.0.onnx
    └── voices-v1.0.bin
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
          "-v", "--voice", default="af_bella",
          help="Kokoro voice name, e.g. 'af_bella', 'am_adam', 'am_michael' (default: af_bella)"
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

## 🎬 Running the Pipeline
1. Generate Synchronized Audio
    Run `auto_dub.py` with default settings (looks for `subtitles.srt`) or pass custom flags:
    ```powershell
    # Default run (subtitles.srt -> output_audio_synced.wav using af_bella)
    python auto_dub.py
    
    # Custom run with specific files & voice
    python auto_dub.py -i video_subtitle_translated.srt -o english_dub.wav -v am_adam
    
    # View all supported CLI options
    python auto_dub.py --help
    ``` 
 1. Merge Audio & Video
    Merge the newly synthesized audio track with your original video while applying loudness normalization:
    ```powershell
    ffmpeg -i "input_video.mkv" -i "output_audio_synced.wav" -c:v copy -c:a aac -af "loudnorm" -map 0:v:0 -map 1:a:0 "final_dubbed_video.mp4"
    ```
## 🧹 Optional Cleanup & Teardown
Once your dubbed video is saved to your preferred storage (Drive, Dropbox, Mega, etc.), you can clean up your system environment:
1. Remove the dubbing_project folder
2. Remove Python Packages
   ```python
    pip uninstall kokoro-onnx soundfile misaki -y 
    ```
3. Uninstall Runtimes via WinGet
   ```powershell
   winget uninstall Python.Python.3 FFmpeg
   ```
4. Clear Remaining System Cache
   ```powershell
   # Delete local pip cache and installed site-packages
   Remove-Item -Recurse -Force "$env:LOCALAPPDATA\pip" -ErrorAction SilentlyContinue
   Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Programs\Python" -ErrorAction SilentlyContinue
   Remove-Item -Recurse -Force "$env:APPDATA\Python" -ErrorAction SilentlyContinue
    ```
