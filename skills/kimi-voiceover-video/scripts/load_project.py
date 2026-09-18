#!/usr/bin/env python3
"""Reload a saved project into a work directory.

  load_project.py <project.json> [work-dir]

If work-dir is omitted, uses the one stored in project.json. Restores fixes.json,
shots.json, credits.json, and hook.json so the pipeline can resume.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("work", type=Path, nargs="?")
    args = parser.parse_args()

    if not args.project.is_file():
        print(f"No such project file: {args.project}", file=sys.stderr)
        return 1

    project = json.loads(args.project.read_text(encoding="utf-8"))
    work = Path(args.work).expanduser().resolve() if args.work else Path(project["work"]).expanduser().resolve()
    work.mkdir(parents=True, exist_ok=True)

    for key in ("fixes", "shots", "credits", "hook"):
        data = project.get(key)
        if data is None:
            continue
        if key == "fixes" and not data:
            continue
        if key in ("shots", "credits") and not data:
            continue
        (work / f"{key}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    # Copy source audio/video into work dir if not already there
    source = Path(project["source"]).expanduser().resolve()
    if source.is_file():
        dest = work / source.name
        if not dest.exists():
            shutil.copy2(source, dest)

    print(f"Project loaded into {work}")
    print(f"  source: {project['source']}")
    print(f"  brand: {project['brand']}")
    print(f"  format: {project['format']} · music: {project['music']}")
    print(f"  shots: {len(project.get('shots', []))} · credits: {len(project.get('credits', []))}")
    print("Next: run transcribe.py (or plan_shots.py if transcript exists), then fill_template.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
