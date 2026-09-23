#!/usr/bin/env python3
"""Source media for a shot list and record credits.

  find_media.py <work-dir> [--max-per-query 3] [--gif QUERY] [--clip QUERY] [--local FILE]

Reads shots.json: image_query (photos/logos), gif_query, clip_query and local_media entries per
shot, plus any --gif/--clip/--local given on the command line. Searches Wikimedia Commons and
Simple Icons, downloads candidates into <work>/assets/, and writes credits.json with source,
author, and licence for every file.

Animated gifs and videos are converted to webm (VP9/VP8) so the renderer can seek them
frame-exactly — a .gif embedded directly plays on wall-clock time and breaks determinism.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "kimi-voiceover-video-skill/1.0"
SIMPLE_ICONS_VERSION = "13"
MAX_GIF_BYTES = 15_000_000
CONVERT_EXTS = {".gif", ".mp4", ".mov", ".m4v", ".avi", ".mkv"}


def commons_api(params):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"  Commons API failed: {e}", file=sys.stderr)
        return {}


def commons_search(query, limit=5, filter=None):
    """Return list of file titles from Wikimedia Commons search.

    filter is a raw CirrusSearch file filter, e.g. "filetype:video" or "filemime:image/gif"
    (gif is a bitmap, so filetype:gif matches nothing).
    """
    if filter:
        query = f"{query} {filter}"
    data = commons_api({
        "action": "query", "list": "search", "srnamespace": 6,
        "srlimit": limit, "format": "json", "srsearch": query,
    })
    return [item["title"] for item in data.get("query", {}).get("search", [])]


def strip_html(value):
    return re.sub(r"<[^>]+>", "", value or "").strip()


def commons_file_info(title):
    """Return {url, author, licence, mime, size} for a Commons file title, or None."""
    data = commons_api({
        "action": "query", "titles": title, "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 800, "format": "json",
    })
    for page in data.get("query", {}).get("pages", {}).values():
        info = page.get("imageinfo", [None])[0]
        if not info:
            continue
        meta = info.get("extmetadata", {})
        licence = strip_html(meta.get("LicenseShortName", {}).get("value", "")) or \
            strip_html(meta.get("License", {}).get("value", "")) or "Unknown"
        return {
            # Prefer a scaled thumb to avoid multi-megabyte originals
            "url": info.get("thumburl") or info.get("url"),
            "original": info.get("url"),
            "author": strip_html(meta.get("Artist", {}).get("value", "")) or "Unknown",
            "licence": licence,
            "mime": info.get("mime", ""),
            "size": info.get("size", 0),
        }
    return None


def find_clips_for_query(query, assets_dir, prefix, max_candidates):
    results = []
    for i, title in enumerate(commons_search(query, limit=max(5, max_candidates * 2), filter="filetype:video")):
        if len(results) >= max_candidates:
            break
        info = commons_file_info(title)
        # imageinfo's thumburl is a jpg poster for videos; the original file is the playable one
        if not info or not info.get("original"):
            continue
        url = info["original"]
        if info["size"] > MAX_GIF_BYTES * 3:
            print(f"  skipping {title} ({info['size']//1_000_000} MB video)")
            continue
        ext = Path(url.split("?")[0]).suffix or ".webm"
        if ext == ".webm":
            dest = assets_dir / f"{prefix}_clip{i+1}.webm"
            ok = download(url, dest)
        else:
            raw = assets_dir / f"{prefix}_clip{i+1}{ext}"
            dest = assets_dir / f"{prefix}_clip{i+1}.webm"
            ok = download(url, raw) and to_webm(raw, dest)
            if ok:
                raw.unlink()
        if ok:
            results.append({
                "file": str(dest.name), "source": url, "author": info["author"],
                "licence": info["licence"], "type": "clip", "verified": False,
            })
    return results


def download(url, dest: Path):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.write_bytes(resp.read())
        return True
    except urllib.error.URLError as e:
        print(f"  Download failed: {e}", file=sys.stderr)
        return False


def webm_encoder():
    out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                         capture_output=True, text=True).stdout
    if "libvpx-vp9" in out:
        return ["-c:v", "libvpx-vp9", "-crf", "34", "-b:v", "0"]
    if "libvpx" in out:
        return ["-c:v", "libvpx", "-b:v", "1.2M"]
    return None


def to_webm(src: Path, dest: Path):
    """Convert gif/video to a muted, <=640px webm. Returns True on success."""
    enc = webm_encoder()
    if not enc:
        print("  No VP8/VP9 encoder in ffmpeg; cannot convert " + src.name, file=sys.stderr)
        return False
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-an",
           "-vf", "scale='min(640,iw)':-2", *enc, str(dest)]
    if subprocess.run(cmd, capture_output=True).returncode != 0 or not dest.is_file():
        print(f"  Conversion to webm failed: {src.name}", file=sys.stderr)
        return False
    return True


def simple_icon_slug(query):
    """Return a Simple Icons slug if the query looks like a brand/logo name."""
    # Simple icons are lower-case, no spaces
    slug = re.sub(r"[^a-z0-9]", "", query.lower())
    # Some common renames
    aliases = {
        "javascript": "javascript",
        "typescript": "typescript",
        "python": "python",
        "java": "openjdk",
        "docker": "docker",
        "kubernetes": "kubernetes",
        "github": "github",
        "git": "git",
        "nodejs": "nodedotjs",
        "node": "nodedotjs",
        "react": "react",
        "spring": "spring",
        "springboot": "springboot",
        "kafka": "apachekafka",
        "postgres": "postgresql",
        "mongodb": "mongodb",
        "redis": "redis",
        "aws": "amazonaws",
        "gcp": "googlecloud",
        "azure": "microsoftazure",
    }
    return aliases.get(slug, slug) if slug else None


def find_images_for_query(query, assets_dir, prefix, max_candidates):
    results = []

    # Try Simple Icons first for short logo-like queries
    slug = simple_icon_slug(query)
    if slug and max_candidates > 0:
        icon_url = f"https://cdn.jsdelivr.net/npm/simple-icons@{SIMPLE_ICONS_VERSION}/icons/{slug}.svg"
        dest = assets_dir / f"{prefix}_icon.svg"
        if download(icon_url, dest):
            results.append({
                "file": str(dest.name), "source": icon_url, "author": "Simple Icons",
                "licence": "CC0 1.0", "type": "logo", "verified": False,
            })
            if len(results) >= max_candidates:
                return results

    # Wikimedia Commons
    for i, title in enumerate(commons_search(query, limit=max(5, max_candidates * 2))):
        if len(results) >= max_candidates:
            break
        info = commons_file_info(title)
        if not info or not info["url"]:
            continue
        ext = Path(info["url"].split("?")[0]).suffix or ".jpg"
        dest = assets_dir / f"{prefix}_{i+1}{ext}"
        if download(info["url"], dest):
            results.append({
                "file": str(dest.name), "source": info["url"], "author": info["author"],
                "licence": info["licence"], "type": "photo", "verified": False,
            })

    return results


def find_gifs_for_query(query, assets_dir, prefix, max_candidates):
    results = []
    for i, title in enumerate(commons_search(query, limit=max(5, max_candidates * 2), filter="filemime:image/gif")):
        if len(results) >= max_candidates:
            break
        info = commons_file_info(title)
        if not info or not info["url"]:
            continue
        if info["size"] > MAX_GIF_BYTES:
            print(f"  skipping {title} ({info['size']//1_000_000} MB gif)")
            continue
        raw = assets_dir / f"{prefix}_gif{i+1}.gif"
        dest = assets_dir / f"{prefix}_gif{i+1}.webm"
        if download(info["url"], raw) and to_webm(raw, dest):
            raw.unlink()
            results.append({
                "file": str(dest.name), "source": info["url"], "author": info["author"],
                "licence": info["licence"], "type": "gif", "verified": False,
            })
    return results


def add_local(path_str, assets_dir, prefix, index):
    src = Path(path_str).expanduser()
    if not src.is_file():
        print(f"  Local file not found: {src}", file=sys.stderr)
        return None
    ext = src.suffix.lower()
    if ext == ".webm":
        dest = assets_dir / f"{prefix}_local{index}.webm"
        shutil.copyfile(src, dest)
    elif ext in CONVERT_EXTS:
        dest = assets_dir / f"{prefix}_local{index}.webm"
        if not to_webm(src, dest):
            return None
    else:
        dest = assets_dir / f"{prefix}_local{index}{ext}"
        shutil.copyfile(src, dest)
    return {
        "file": str(dest.name), "source": str(src), "author": "user-provided file",
        "licence": "user's own", "type": "local", "verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    parser.add_argument("--max-per-query", type=int, default=3, help="candidates per query")
    parser.add_argument("--gif", action="append", default=[], help="extra gif query (repeatable)")
    parser.add_argument("--clip", action="append", default=[], help="extra video clip query (repeatable)")
    parser.add_argument("--local", action="append", default=[], help="local media file (repeatable)")
    args = parser.parse_args()

    shots_path = args.work / "shots.json"
    shots = json.loads(shots_path.read_text(encoding="utf-8")) if shots_path.is_file() else []
    if not shots_path.is_file() and not (args.gif or args.clip or args.local):
        print(f"No shots.json in {args.work}", file=sys.stderr)
        print("Next: run plan_shots.py first, or pass --gif/--clip/--local", file=sys.stderr)
        return 1

    image_queries = {s.get("image_query", "").strip() for s in shots if s.get("image_query", "").strip()}
    gif_queries = {s.get("gif_query", "").strip() for s in shots if s.get("gif_query", "").strip()} | set(args.gif)
    clip_queries = {s.get("clip_query", "").strip() for s in shots if s.get("clip_query", "").strip()} | set(args.clip)
    local_paths = list(args.local)
    for s in shots:
        local = s.get("local_media")
        if isinstance(local, str):
            local_paths.append(local)
        elif isinstance(local, list):
            local_paths.extend(str(p) for p in local)

    if not (image_queries or gif_queries or clip_queries or local_paths):
        print("No media queries in shots.json; nothing to source.")
        return 0

    assets_dir = args.work / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    credits = []
    for query in sorted(image_queries):
        print(f"Searching images: {query}")
        prefix = re.sub(r"[^a-z0-9]", "_", query.lower())[:30]
        found = find_images_for_query(query, assets_dir, prefix, args.max_per_query)
        if not found:
            print(f"  no results for '{query}'")
        for item in found:
            print(f"  → {item['file']} ({item['licence']})")
        credits.extend(found)

    for query in sorted(gif_queries):
        print(f"Searching gifs: {query}")
        prefix = re.sub(r"[^a-z0-9]", "_", query.lower())[:30]
        found = find_gifs_for_query(query, assets_dir, prefix, args.max_per_query)
        if not found:
            print(f"  no gif results for '{query}'")
        for item in found:
            print(f"  → {item['file']} ({item['licence']})")
        credits.extend(found)

    for query in sorted(clip_queries):
        print(f"Searching clips: {query}")
        prefix = re.sub(r"[^a-z0-9]", "_", query.lower())[:30]
        found = find_clips_for_query(query, assets_dir, prefix, args.max_per_query)
        if not found:
            print(f"  no clip results for '{query}'")
        for item in found:
            print(f"  → {item['file']} ({item['licence']})")
        credits.extend(found)

    for i, path_str in enumerate(local_paths):
        item = add_local(path_str, assets_dir, "local", i + 1)
        if item:
            print(f"  → {item['file']} (user's own)")
            credits.append(item)

    credits_path = args.work / "credits.json"
    if credits_path.is_file():
        try:
            existing = json.loads(credits_path.read_text(encoding="utf-8"))
            kept = [c for c in existing if c.get("file") not in {n["file"] for n in credits}]
            credits = kept + credits
        except json.JSONDecodeError:
            pass
    credits_path.write_text(json.dumps(credits, indent=2) + "\n", encoding="utf-8")

    print(f"Sourced {len(credits)} media files → {credits_path}")
    print("Next: review every candidate before using it; gifs and clips are webm, seek them with clip()")
    return 0


if __name__ == "__main__":
    sys.exit(main())
