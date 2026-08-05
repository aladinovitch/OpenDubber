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
