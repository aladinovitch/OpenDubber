import os
import subprocess
import sys
from pathlib import Path
from IPython.display import display, Javascript

def stream_process(cmd, prefix=""):
    """Helper function to execute a command and stream its output in real-time."""
    # Mute noisy ONNX runtime loggers in child processes
    env = os.environ.copy()
    env["ONNXRUNTIME_LOGGING_LEVEL"] = "3"
    env["PYTHONUNBUFFERED"] = "1"  # Force unbuffered stdout/stderr across Python scripts

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Combine stderr into stdout for continuous streaming
        text=True,
        bufsize=1,
        env=env
    )

    # Stream line by line in real-time
    for line in process.stdout:
        clean_line = line.strip()
        if not clean_line:
            continue

        # Filter out noisy ONNX C++ Provider fallback errors
        if "provider_bridge_ort.cc" in clean_line or "Failed to create CUDAExecutionProvider" in clean_line:
            continue

        # Handle carriage returns (\r) often used by progress bars (FFmpeg / tqdm)
        if '\r' in clean_line:
            clean_line = clean_line.split('\r')[-1].strip()
            
        if clean_line:
            print(f"{prefix}{clean_line}", flush=True)

    process.wait()
    return process.returncode

def batchdub(track_list, work_dir):
    total = len(track_list)
    
    for idx, (video_filename, srt_filename) in enumerate(track_list, start=1):
        print(f"[{idx}/{total}] 🎙️ Dubbing {video_filename}")
        
        # Paths setup
        input_video = work_dir / video_filename
        input_srt = work_dir / srt_filename
        video_stem = Path(video_filename).stem
        output_audio = work_dir / f"{video_stem}_synced.wav"
        output_video = work_dir / f"[En dub] {video_stem}.mp4"
        
        # STEP 1: Run autodub.py (TTS)
        
        dub_cmd = ["python", "autodub.py", "--srt", str(input_srt), "--out", str(output_audio)]
        result_code = stream_process(dub_cmd, prefix="    [autodub] ")
        
        if result_code.returncode != 0:
            print(f"⚠️ Error during autodub execution for {video_filename}. Skipping to next step.")
            continue

        # STEP 2: Run FFmpeg video/audio remuxing (Optional)
        if not output_audio.exists():
            print(f"❌ Cannot run FFmpeg: Audio file '{output_audio.name}' was not found!")
            continue
        
        ffmpeg_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(input_video),
            "-i", str(output_audio),
            "-c:v", "copy",
            "-c:a", "aac",
            "-af", "loudnorm",
            "-map", "0:v:0",
            "-map", "1:a:0",
            str(output_video)
        ]
        
        ffmpeg_code = stream_process(ffmpeg_cmd, prefix="    [ffmpeg] ")
        
        if ffmpeg_code.returncode == 0:
            print(f"✅ Successfully created MP4: {output_video.name}\n")
            if output_audio.exists():
                output_audio.unlink()
        else:
            print(f"❌ FFmpeg remuxing failed for {video_filename}\n")
            
        print() # Line break between tracks

    # --- 3. BROWSER NOTIFICATION GUI ---
    print("🎉 All tracks processed")
    display(Javascript('alert("🎉 Kaggle Batch Processing Complete!");'))
