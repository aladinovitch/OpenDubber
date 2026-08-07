import os
import re
import subprocess
import ipywidgets as widgets
from IPython.display import display, clear_output
from pathlib import Path
from batchdub import batchdub

try:
    from kaggle_secrets import UserSecretsClient
    user_secrets = UserSecretsClient()
    default_mega_url = user_secrets.get_secret("MEGA_URL")
except Exception:
    default_mega_url = ""

# Define available Kokoro voices
KOKORO_VOICES = [
    "am_liam", "am_michael", "am_echo", "am_santa", "am_adam", 
    "af_sarah", "af_heart", "af_aoede", "af_jessica"
]

def launch_dashboard():
    """Renders the OpenDubber interactive notebook dashboard."""
    style = {'description_width': '140px'}
    layout = widgets.Layout(width='450px')
    
    mega_url_input = widgets.Text(
        value=default_mega_url,
        placeholder='https://mega.nz/folder/...',
        description='Mega URL:',
        style=style,
        layout=layout
    )
    
    subfolder_input = widgets.Text(
        value='dubdir',
        description='Dubbing dir:',
        style=style,
        layout=layout
    )
    
    voice_select = widgets.Dropdown(
        options=KOKORO_VOICES,
        value='am_liam',
        description='Kokoro Voice:',
        style=style,
        layout=layout
    )
    
    speed_slider = widgets.FloatSlider(
        value=1.0,
        min=0.8,
        max=1.5,
        step=0.05,
        description='Speech Speed:',
        style=style,
        layout=layout
    )

    keep_audio_checkbox = widgets.Checkbox(
        value=False,
        description='Keep raw synced WAV file after remuxing',
        disabled=False,
        indent=False
    )
    
    queue_rows_container = widgets.VBox()
    
    def create_queue_row(video_val="", srt_val=""):
        """Creates a single (Video, Subtitle) input row with a delete button."""
        video_box = widgets.Text(value=video_val, placeholder='video.mkv', layout=widgets.Layout(width='600px'))
        srt_box = widgets.Text(value=srt_val, placeholder='subtitle.srt', layout=widgets.Layout(width='600px'))
        remove_btn = widgets.Button(icon='trash', button_style='danger', layout=widgets.Layout(width='32px', height='24px', margin='4px 0 0 5px', padding='0'))
        
        row = widgets.HBox([video_box, srt_box, remove_btn], layout=widgets.Layout(margin='2px 2px', overflow='auto'))
        
        def on_remove(_):
            queue_rows_container.children = [r for r in queue_rows_container.children if r != row]
            
        remove_btn.on_click(on_remove)
        return row

    def add_queue_row(b=None, video="", srt=""):
        current_children = list(queue_rows_container.children)
        current_children.append(create_queue_row(video, srt))
        queue_rows_container.children = current_children
    
    def auto_discover_queue(b=None):
        """Scans the target work_dir and auto-fills matching video/srt pairs."""
        subfolder = subfolder_input.value.strip()
        work_dir = Path("/kaggle/working") / subfolder
        
        if not work_dir.exists():
            with output_area:
                clear_output()
                print(f"⚠️ Directory '{work_dir}' does not exist yet. Run 'Mega Download' first.")
            return

        video_extensions = {".mp4", ".mkv", ".webm", ".avi", ".mov"}
        discovered = []

        # Look for video files that have matching .srt sidecars
        for vid in sorted(work_dir.glob("*")):
            if vid.suffix.lower() in video_extensions:
                srt_candidate = work_dir / f"{vid.stem}.srt"
                if srt_candidate.exists():
                    discovered.append((vid.name, srt_candidate.name))

        if discovered:
            # Clear existing rows and replace with auto-detected pairs
            queue_rows_container.children = []
            for v_file, s_file in discovered:
                add_queue_row(video=v_file, srt=s_file)
            
            with output_area:
                clear_output()
                print(f"✨ Auto-discovered {len(discovered)} video/subtitle pair(s) in '{subfolder}'!")
        else:
            with output_area:
                clear_output()
                print(f"🔍 No matching (Video + .srt) pairs found in '{work_dir}'.")
    
    add_row_btn = widgets.Button(
        description='Add Video/Subtitle Pair',
        button_style='info',
        icon='plus',
        layout=widgets.Layout(width='250px', height='20px',margin='5px 0 20px 0')
    )
    add_row_btn.on_click(add_queue_row)

    # Auto-discovery button
    auto_detect_btn = widgets.Button(
        description='Auto Pairs',
        button_style='warning',
        icon='search',
        layout=widgets.Layout(width='140px', height='20px', margin='5px 0 15px 5px')
    )
    auto_detect_btn.on_click(auto_discover_queue)
    queue_controls = widgets.HBox([add_row_btn, auto_detect_btn])

    # --- Buttons Setup ---
    download_button = widgets.Button(
        description='Mega Download',
        button_style='primary',
        icon='download',
        layout=widgets.Layout(width='250px', height='30px', margin='10px 0 0 0')
    )
    
    run_button = widgets.Button(
        description='Dubbing Machine',
        button_style='success',
        icon='play',
        layout=widgets.Layout(width='250px', height='30px', margin='10px 0 0 0')
    )
    
    output_area = widgets.Output()
    # --- Click Action: Download ---
    def on_download_click(b):
        with output_area:
            clear_output()
            mega_url = mega_url_input.value.strip()
            subfolder = subfolder_input.value.strip()
            work_dir = Path("/kaggle/working") / subfolder
            work_dir.mkdir(parents=True, exist_ok=True)

            if not mega_url:
                print("❌ Error: Mega URL is empty! Please enter a valid URL.")
                return
            
            print(f"📥 Starting Mega download to: {work_dir}")
            print(f"🔗 URL: {mega_url}\n")
            cmd = ["megadl", "--path", str(work_dir), mega_url]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Regex to capture percentage progress lines (e.g. "15.57%")
            pct_pattern = re.compile(r"(\d+\.\d+)%")
            last_reported_step = -1
    
            for line in process.stdout:
                clean_line = line.strip()
                if not clean_line:
                    continue
    
                # 1. Capture file initialization line (e.g., "F /path/to/file")
                if clean_line.startswith("F "):
                    filename = Path(clean_line.split(" ", 1)[1]).name
                    print(f"📦 Downloading: {filename}", flush=True)
                    last_reported_step = -1  # Reset milestone tracker for new file
                    continue
    
                # 2. Check if the line is a progress update
                match = pct_pattern.search(clean_line)
                if match:
                    percentage = float(match.group(1))
                    # Report only at 25%, 50%, 75%, and 100% milestones
                    current_step = int(percentage // 25)
                    if current_step > last_reported_step and current_step > 0:
                        print(f"   ⏳ Progress: {current_step * 25}%", flush=True)
                        last_reported_step = current_step
                    continue
    
                # 3. Print any non-progress structural logs (errors, warnings, existing file skips)
                print(clean_line, flush=True)
            process.wait()
            # megadl returns 0 on success, or non-zero if files already exist/skipped
            existing_files = list(work_dir.glob("*"))
            if process.returncode == 0 or len(existing_files) > 0:
                print(f"\n✅ Assets ready in '{subfolder}'! ({len(existing_files)} file(s) present)", flush=True)
            else:
                print(f"\n⚠️ Download finished with code {process.returncode}. Verify files in {work_dir}", flush=True)
            auto_discover_queue()
    
    def on_run_click(b):
        with output_area:
            clear_output()
            
            # 1. Parse Directory & Secrets
            mega_url = mega_url_input.value.strip()
            subfolder = subfolder_input.value.strip()
            work_dir = Path("/kaggle/working") / subfolder
            work_dir.mkdir(parents=True, exist_ok=True)
            
            selected_voice = voice_select.value
            selected_speed = speed_slider.value
            keep_audio = keep_audio_checkbox.value
    
            # 2. Extract Dubbing Queue dynamically from UI rows
            dub_queue = []
            for row in queue_rows_container.children:
                v_val = row.children[0].value.strip()
                s_val = row.children[1].value.strip()
                if v_val and s_val:
                    dub_queue.append((v_val, s_val))
            print(f"🎯 Preparing Dubbing Queue...", flush=True)
            print(f" 🗣️ Voice: {selected_voice} | Speed: {selected_speed}x", flush=True)
            print(f" 📋 Queue Items ({len(dub_queue)}):", flush=True)
            for idx, (vid, srt) in enumerate(dub_queue, 1):
                print(f"    {idx}. Video: {vid} | Sub: {srt}", flush=True)
            print("-" * 50)
    
            if not dub_queue:
                print("⚠️ Warning: Your dubbing queue is empty!", flush=True)
                return
    
            # 3. File Verification & Pre-flight Check
            missing_files = []
            for video_file_name, srt_file_name in dub_queue:
                video_path = work_dir / video_file_name
                srt_path = work_dir / srt_file_name
    
                if not video_path.exists():
                    missing_files.append(f"📹 Video missing: {video_file_name}")
    
                if not srt_path.exists():
                    missing_files.append(f"📄 Subtitle missing: {srt_file_name}")
    
            # If any file is missing, print issues and abort execution
            if missing_files:
                print("❌ Execution Aborted! The following required files were not found in the directory:")
                for issue in missing_files:
                    print(f"   • {issue}")
                print(f"\n💡 Expected Directory: {work_dir}")
                print("👉 Click '📥 Download from MEGA' first if you haven't pulled your assets yet.")
                return
            print("⚡ All queue files verified on disk. Launching batch dubbing...\n", flush=True)
            batchdub(dub_queue, work_dir, voice=selected_voice, speed=selected_speed, keep_audio=keep_audio)
    
    download_button.on_click(on_download_click)
    run_button.on_click(on_run_click)
    
    # Render Dashboard Layout
    ui_box = widgets.VBox([
        widgets.HTML("<h3>🎙️ OpenDubber Execution Panel</h3>"),
        mega_url_input,
        subfolder_input,
        voice_select,
        speed_slider,
        keep_audio_checkbox,
        widgets.HTML("<hr style='margin: 10px 0;'/><h4>🎬 Dubbing Queue (Video, Subtitle)</h4>"),
        queue_rows_container,
        queue_controls,
        download_button,
        run_button,
        output_area
    ])
    
    display(ui_box)
