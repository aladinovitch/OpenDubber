import os
import subprocess
from IPython.display import display, Javascript

def batchdub(track_list):
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
        result = subprocess.run(dub_cmd)
        
        if result.returncode != 0:
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
        
        ffmpeg_result = subprocess.run(ffmpeg_cmd)
        
        if ffmpeg_result.returncode == 0:
            print(f"✅ Successfully created MP4: {output_video.name}\n")
            if output_audio.exists():
                output_audio.unlink()
        else:
            print(f"❌ FFmpeg remuxing failed for {video_filename}\n")
            
        print() # Line break between tracks

    # --- 3. BROWSER NOTIFICATION GUI ---
    print("🎉 All tracks processed")
    display(Javascript('alert("🎉 Kaggle Batch Processing Complete!");'))
