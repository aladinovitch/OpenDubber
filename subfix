import argparse
import re
from pathlib import Path
from datetime import timedelta

def srt_time_to_td(time_str: str) -> timedelta:
    """Converts HH:MM:SS,mmm to Python timedelta."""
    time_str = time_str.replace('.', ',')
    hours, minutes, seconds_ms = time_str.split(':')
    seconds, milliseconds = seconds_ms.split(',')
    return timedelta(
        hours=int(hours),
        minutes=int(minutes),
        seconds=int(seconds),
        milliseconds=int(milliseconds)
    )

def td_to_srt_time(td: timedelta) -> str:
    """Converts Python timedelta back to HH:MM:SS,mmm string."""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    milliseconds = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def repair_srt_timestamps(
    input_srt_path: str, 
    output_srt_path: str = None, 
    min_gap_ms: int = 50, 
    verbose: bool = True
) -> str:
    """
    Cleans and repairs SRT files:
    - Resolves timestamp overlaps between adjacent subtitles.
    - Enforces a minimum gap (default 50ms) between segments.
    - Ensures valid line formatting and chronological sequence.
    - Accurately inspects speech pacing (CPS) without bleeding across blocks.
    """
    srt_path = Path(input_srt_path)
    if not srt_path.exists():
        print(f"⚠️ SRT file not found: {input_srt_path}")
        return input_srt_path

    if output_srt_path is None:
        output_srt_path = str(srt_path.with_name(f"{srt_path.stem}_cleaned.srt"))

    content = srt_path.read_text(encoding="utf-8", errors="replace").strip()
    
    # Normalize line endings to standard Unix \n
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split raw file by double newlines to isolate blocks reliably
    raw_blocks = [b.strip() for b in re.split(r'\n\s*\n', content) if b.strip()]

    parsed_entries = []
    time_pattern = re.compile(r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})')

    for block in raw_blocks:
        lines = block.split('\n')
        if len(lines) < 2:
            continue
            
        # Line 0 is index, Line 1 is timestamp, Line 2+ is actual text
        idx_str = lines[0].strip()
        time_match = time_pattern.search(lines[1])
        
        if not time_match or not idx_str.isdigit():
            # In case an SRT index is missing or malformed
            continue
            
        start_str, end_str = time_match.groups()
        text_clean = " ".join([l.strip() for l in lines[2:]]).strip()

        start_td = srt_time_to_td(start_str)
        end_td = srt_time_to_td(end_str)

        # Fix zero or negative duration lines
        if end_td <= start_td:
            old_end = td_to_srt_time(end_td)
            end_td = start_td + timedelta(milliseconds=500)
            if verbose:
                print(f" 🛠️ [Block {idx_str}] Fixed zero/negative duration: expanded to {td_to_srt_time(end_td)}")

        parsed_entries.append({
            'orig_idx': idx_str,
            'start': start_td, 
            'end': end_td, 
            'text': text_clean
        })

    if not parsed_entries:
        print(f"⚠️ Warning: Could not parse SRT blocks in {srt_path.name}. Returning original.")
        return input_srt_path

    parsed_entries.sort(key=lambda x: x['start'])
    gap = timedelta(milliseconds=min_gap_ms)

    if verbose:
        print(f"\n🔍 --- Inspecting & Cleaning: {srt_path.name} ---")

    # 1. Overlap Adjustments
    repaired_count = 0
    for i in range(len(parsed_entries) - 1):
        curr_entry = parsed_entries[i]
        next_entry = parsed_entries[i + 1]

        if curr_entry['end'] > next_entry['start']:
            repaired_count += 1
            old_curr_end = td_to_srt_time(curr_entry['end'])
            old_next_start = td_to_srt_time(next_entry['start'])
            
            new_end = next_entry['start'] - gap
            if new_end > curr_entry['start']:
                curr_entry['end'] = new_end
                if verbose:
                    print(
                        f" ✂️ [Overlap Fix #{repaired_count}] Truncated Block #{curr_entry['orig_idx']} end time "
                        f"from {old_curr_end} -> {td_to_srt_time(curr_entry['end'])}"
                    )
            else:
                next_entry['start'] = curr_entry['end'] + gap
                if verbose:
                    print(
                        f" ⏩ [Overlap Fix #{repaired_count}] Shifted Block #{next_entry['orig_idx']} start time "
                        f"from {old_next_start} -> {td_to_srt_time(next_entry['start'])}"
                    )

    # 2. Precise Pacing Check (Cleaned Text Only)
    if verbose:
        pacing_issues = 0
        for entry in parsed_entries:
            duration_sec = (entry['end'] - entry['start']).total_seconds()
            if duration_sec > 0:
                cps = len(entry['text']) / duration_sec
                if cps > 24:
                    pacing_issues += 1
                    print(f" ⚠️ [Fast Speech] Block #{entry['orig_idx']} ({cps:.1f} CPS): \"{entry['text'][:40]}...\" (Audio will be sped up)")
                elif cps < 4 and len(entry['text']) > 5:
                    pacing_issues += 1
                    print(f" 💤 [Long Silence Gap] Block #{entry['orig_idx']} ({cps:.1f} CPS): {duration_sec:.1f}s window for short text.")
        
        if pacing_issues == 0:
            print(" 🎯 Speech pacing looks balanced across all blocks.")

    # Reconstruct cleaned SRT string
    repaired_blocks = []
    for idx, entry in enumerate(parsed_entries, 1):
        start_fmt = td_to_srt_time(entry['start'])
        end_fmt = td_to_srt_time(entry['end'])
        repaired_blocks.append(f"{idx}\n{start_fmt} --> {end_fmt}\n{entry['text']}\n")

    output_path = Path(output_srt_path)
    output_path.write_text("\n".join(repaired_blocks), encoding="utf-8")

    if verbose:
        if repaired_count > 0:
            print(f"✅ Finished! Fixed {repaired_count} overlap(s). Saved to: {output_path.name}\n")
        else:
            print(f"✅ Finished! No overlaps found. Saved to: {output_path.name}\n")

    return str(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect and clean SRT files for video dubbing.")
    
    parser.add_argument(
        "--srt", 
        required=True, 
        help="Path to the input SRT file."
    )
    parser.add_argument(
        "--out", 
        default=None, 
        help="Path to save the output SRT file (default: input_cleaned.srt)."
    )
    parser.add_argument(
        "--min-gap", 
        type=int, 
        default=50, 
        help="Minimum gap in milliseconds between subtitles (default: 50)."
    )
    parser.add_argument(
        "--quiet", 
        action="store_true", 
        help="Suppress detailed console log outputs."
    )

    args = parser.parse_args()

    repair_srt_timestamps(
        input_srt_path=args.srt,
        output_srt_path=args.out,
        min_gap_ms=args.min_gap,
        verbose=not args.quiet
    )
