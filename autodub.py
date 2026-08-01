import argparse
import os
import re
import numpy as np
import soundfile as sf
import torch  # Keeps C++ CUDA links active
import onnxruntime as ort
from kokoro_onnx import Kokoro
from misaki import en, espeak

# Initialize Misaki English G2P
# british=False for US English (af_*, am_*), british=True for British English (bf_*, bm_*)
fallback = espeak.EspeakFallback(british=False)
g2p = en.G2P(trf=False, british=False, fallback=fallback)


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
    parser = argparse.ArgumentParser(description="Generate synchronized TTS audio from an SRT file using Kokoro ONNX.")
    parser.add_argument("--srt", default="subtitles.srt", help="Input SRT file path (default: subtitles.srt)")
    parser.add_argument("--out", default="output_audio_synced.wav", help="Output WAV audio path (default: output_audio_synced.wav)")
    parser.add_argument("--voice", default="am_liam", help="Kokoro voice name, e.g. 'am_adam', 'am_michael', 'af_bella' (default: am_liam)")
    parser.add_argument("--speed", type=float, default=1.0, help="Base speech speed multiplier (default: 1.0)")
    parser.add_argument("--lang", default="en-us", help="Language code (default: en-us)")
    parser.add_argument("--model", default="kokoro-v1.0.onnx", help="Path to Kokoro ONNX model weights (default: kokoro-v1.0.onnx)")
    parser.add_argument("--voices-bin", default="voices-v1.0.bin", help="Path to Kokoro voices binary file (default: voices-v1.0.bin)")
    args = parser.parse_args()

    print(f"Loading Kokoro model ('{args.model}')...")
    if not os.path.exists(args.model) or not os.path.exists(args.voices_bin):
        raise FileNotFoundError(
            f"Model files missing. Ensure '{args.model}' and '{args.voices_bin}' exist in your folder."
        )

    # Force CUDA Execution Provider for ONNX Runtime (GPU execution)
    session = ort.InferenceSession(
        args.model,
        providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
    )
    kokoro = Kokoro.from_session(session, args.voices_bin)

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

        # Convert text to phonemes via Misaki
        phonemes, tokens = g2p(sub['text'])
        #Debug
        #print(f"[{i}/{len(subtitles)}] Text: '{sub['text']}' ➔ Phonemes: '{phonemes}'")

        # Generate audio for the line
        samples, sr = kokoro.create(
            text=phonemes,
            voice=args.voice,
            speed=args.speed,
            lang=args.lang,
            is_phonemes=True  # Tells kokoro-onnx to skip internal espeak processing
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
    sf.write(args.out, final_audio, sample_rate)

    total_minutes = len(final_audio) / sample_rate / 60
    print(f"\nSynced audio exported to: {args.out}")
    print(f"Final audio duration: {total_minutes:.2f} minutes")


if __name__ == "__main__":
    main()
