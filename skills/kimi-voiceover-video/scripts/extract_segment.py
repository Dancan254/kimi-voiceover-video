#!/usr/bin/env python3
"""Extract the hook audio/video segment for the rest of the pipeline.

  extract_segment.py <audio-or-video> <work-dir>

Reads hook.json and writes <work>/hook.<ext> using ffmpeg. Also shifts words.json
so shot times are relative to the hook start.
"""

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: extract_segment.py <audio-or-video> <work-dir>", file=sys.stderr)
        return 1

    src = Path(sys.argv[1])
    work = Path(sys.argv[2])

    if not src.is_file():
        print(f"No such file: {src}", file=sys.stderr)
        return 1

    hook_path = work / "hook.json"
    if not hook_path.is_file():
        print(f"No hook.json in {work}", file=sys.stderr)
        print("Next: run extract_hook.py first", file=sys.stderr)
        return 1

    hook = json.loads(hook_path.read_text(encoding="utf-8"))
    start = hook["start"]
    end = hook["end"]
    duration = end - start

    out = work / f"hook{src.suffix}"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-i", str(src), "-t", str(duration),
         "-c", "copy", str(out)],
        check=True,
    )

    print(f"Hook segment {start:.1f}s–{end:.1f}s → {out}")
    print("Next: run transcribe.py on the hook segment, then plan_shots.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
