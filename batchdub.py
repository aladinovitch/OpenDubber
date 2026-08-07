import os
import subprocess
import sys
from pathlib import Path
from IPython.display import display, Javascript
from tqdm.notebook import tqdm

def stream_process(cmd, prefix=""):
    """
    Executes a process and streams output inside a single tqdm notebook widget line.
    Turns blue while running, green on completion, or red on unhandled errors.
    """
    env = os.environ.copy()
    env["ONNXRUNTIME_LOGGING_LEVEL"] = "3"
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )

    # bar_format="{desc}: {postfix}" creates a clean widget bar without empty square blocks
    with tqdm(total=None, desc=prefix, bar_format="{desc} {postfix}") as pbar:
        buffer = ""
        while True:
            char = process.stdout.read(1)
            if not char and process.poll() is not None:
                break

            if char in ('\r', '\n'):
                clean_line = buffer.strip()
                buffer = ""

                if not clean_line:
                    continue

                if "provider_bridge_ort.cc" in clean_line or "Failed to create CUDAExecutionProvider" in clean_line:
                    continue

                if '\r' in clean_line:
                    clean_line = clean_line.split('\r')[-1].strip()

                if clean_line:
                    pbar.set_postfix_str(clean_line[:90])
                    pbar.update()
            else:
                buffer += char

    process.wait()
    return process.returncode

def batchdub(track_list, work_dir, voice="am_liam", speed=1.0, keep_audio=False):
    total = len(track_list)

    for idx, (video_filename, srt_filename) in enumerate(tqdm(track_list, desc="Overall Batch"), start=1):
        print(f"[{idx}/{total}] 🎙️ Dubbing {video_filename}", flush=True)

        # Paths setup
        input_video = work_dir / video_filename
        input_srt = work_dir / srt_filename
        video_stem = Path(video_filename).stem
        output_audio = work_dir / f"{video_stem}_synced.wav"
        output_video = work_dir / f"[En dub] {video_stem}.mp4"

        # STEP 1: Run autodub.py (TTS)
        dub_cmd = [
        sys.executable, "-u", "autodub.py",
        "--srt", str(input_srt),
        "--out", str(output_audio),
        "--voice", str(voice),
        "--speed", str(speed)
        ]
        print("  ⏳ [TTS] Generating dubbed audio...", flush=True)
        result_code = stream_process(dub_cmd, prefix="    [autodub] ")
        if result_code != 0:
            print(f"⚠️ Error during autodub execution for {video_filename}. Skipping to next step.")
            continue

        # STEP 2: Run FFmpeg video/audio remuxing (Optional)
        if not output_audio.exists():
            print(f"❌ Cannot run FFmpeg: Audio file '{output_audio.name}' was not found!")
            continue

        ffmpeg_cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "info", "-stats", "-y",
            "-i", str(input_video),
            "-i", str(output_audio),
            "-c:v", "copy",
            "-c:a", "aac",
            "-af", "loudnorm",
            "-map", "0:v:0",
            "-map", "1:a:0",
            str(output_video)
        ]
        print("  🎬 [FFmpeg] Remuxing video & audio...", flush=True)
        ffmpeg_code = stream_process(ffmpeg_cmd, prefix="    [ffmpeg] ")

        if ffmpeg_code == 0:
            print(f"✅ Successfully created MP4: {output_video.name}\n", flush=True)
            if not keep_audio and output_audio.exists():
                output_audio.unlink()
        else:
            print(f"❌ FFmpeg remuxing failed for {video_filename}\n", flush=True)

    # --- 3. BROWSER NOTIFICATION GUI ---
    print("🎉 All tracks processed")
    display(Javascript('alert("🎉 Kaggle Batch Processing Complete!");'))
