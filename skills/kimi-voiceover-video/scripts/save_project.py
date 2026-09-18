#!/usr/bin/env python3
"""Save the current project state so it can be reloaded later.

  save_project.py <work-dir> --source <audio-or-video> --brand <brand.json> \
    [--format vertical] [--music synth] [--approved false]

Writes <work-dir>/project.json with paths, fixes, shots, credits, and settings.
"""

import argparse
import json
import sys
from pathlib import Path


def load_json(work: Path, name: str, default=None):
    path = work / name
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"Warning: {path} is not valid JSON", file=sys.stderr)
    return default


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    parser.add_argument("--source", required=True, help="original audio or video file")
    parser.add_argument("--brand", required=True, help="brand.json file used")
    parser.add_argument("--format", default="vertical", choices=["vertical", "landscape", "square"])
    parser.add_argument("--music", default="synth", help="synth, none, or path to music file")
    parser.add_argument("--approved", action="store_true", help="shot list has user approval")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    brand = Path(args.brand).expanduser().resolve()

    if not source.is_file():
        print(f"Source not found: {source}", file=sys.stderr)
        return 1
    if not brand.is_file():
        print(f"Brand file not found: {brand}", file=sys.stderr)
        return 1

    project = {
        "version": "1.2.0",
        "source": str(source),
        "brand": str(brand),
        "format": args.format,
        "music": args.music,
        "work": str(args.work.expanduser().resolve()),
        "fixes": load_json(args.work, "fixes.json", {}),
        "shots": load_json(args.work, "shots.json", []),
        "credits": load_json(args.work, "credits.json", []),
        "hook": load_json(args.work, "hook.json"),
        "approved": args.approved,
    }

    out = args.work / "project.json"
    out.write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
    print(f"Project saved → {out}")
    print("Next: re-run load_project.py on this file to resume")
    return 0


if __name__ == "__main__":
    sys.exit(main())
