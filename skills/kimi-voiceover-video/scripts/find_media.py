#!/usr/bin/env python3
"""Source images for a shot list and record credits.

  find_media.py <work-dir> [--max-per-query 3]

Reads shots.json, searches Wikimedia Commons and Simple Icons for each image_query,
downloads up to N candidates per query into <work>/assets/, and writes credits.json
with source, author, and licence for every file.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "kimi-voiceover-video-skill/1.0"
SIMPLE_ICONS_VERSION = "13"


def commons_search(query, limit=5):
    """Return list of file titles from Wikimedia Commons search."""
    url = (
        "https://commons.wikimedia.org/w/api.php"
        f"?action=query&list=search&srnamespace=6&srlimit={limit}&format=json"
        f"&srsearch={urllib.parse.quote(query)}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as e:
        print(f"  Commons search failed for '{query}': {e}", file=sys.stderr)
        return []

    return [item["title"] for item in data.get("query", {}).get("search", [])]


def commons_file_info(title):
    """Return (image_url, author, licence) for a Commons file title, or None."""
    url = (
        "https://commons.wikimedia.org/w/api.php"
        f"?action=query&titles={urllib.parse.quote(title)}"
        "&prop=imageinfo&iiprop=url|extmetadata&iiurlwidth=800&format=json"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError):
        return None

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        info = page.get("imageinfo", [None])[0]
        if not info:
            continue
        meta = info.get("extmetadata", {})
        artist = meta.get("Artist", {}).get("value", "")
        licence = meta.get("LicenseShortName", {}).get("value", "")
        if not licence:
            licence = meta.get("License", {}).get("value", "")
        # Strip HTML from artist
        artist = re.sub(r"<[^>]+>", "", artist).strip() or "Unknown"
        # Prefer a scaled thumb to avoid multi-megabyte originals
        image_url = info.get("thumburl") or info.get("url")
        return image_url, artist, licence or "Unknown"
    return None


def download(url, dest: Path):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            dest.write_bytes(resp.read())
        return True
    except urllib.error.URLError as e:
        print(f"  Download failed: {e}", file=sys.stderr)
        return False


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


def find_media_for_query(query: str, assets_dir: Path, prefix: str, max_candidates: int):
    results = []

    # Try Simple Icons first for short logo-like queries
    slug = simple_icon_slug(query)
    if slug and max_candidates > 0:
        icon_url = f"https://cdn.jsdelivr.net/npm/simple-icons@{SIMPLE_ICONS_VERSION}/icons/{slug}.svg"
        dest = assets_dir / f"{prefix}_icon.svg"
        if download(icon_url, dest):
            results.append({
                "file": str(dest.name),
                "source": icon_url,
                "author": "Simple Icons",
                "licence": "CC0 1.0",
                "type": "logo",
                "verified": False,
            })
            if len(results) >= max_candidates:
                return results

    # Wikimedia Commons
    titles = commons_search(query, limit=max(5, max_candidates * 2))
    for i, title in enumerate(titles):
        if len(results) >= max_candidates:
            break
        info = commons_file_info(title)
        if not info or not info[0]:
            continue
        url, artist, licence = info
        clean_url = url.split("?")[0]
        ext = Path(clean_url).suffix or ".jpg"
        dest = assets_dir / f"{prefix}_{i+1}{ext}"
        if download(url, dest):
            results.append({
                "file": str(dest.name),
                "source": url,
                "author": artist,
                "licence": licence,
                "type": "photo",
                "verified": False,
            })

    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    parser.add_argument("--max-per-query", type=int, default=3, help="candidates per image query")
    args = parser.parse_args()

    shots_path = args.work / "shots.json"
    if not shots_path.is_file():
        print(f"No shots.json in {args.work}", file=sys.stderr)
        print("Next: run plan_shots.py first", file=sys.stderr)
        return 1

    shots = json.loads(shots_path.read_text(encoding="utf-8"))
    queries = {s.get("image_query", "").strip() for s in shots if s.get("image_query", "").strip()}
    if not queries:
        print("No image queries in shots.json; nothing to source.")
        return 0

    assets_dir = args.work / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    credits = []
    for query in sorted(queries):
        print(f"Searching: {query}")
        prefix = re.sub(r"[^a-z0-9]", "_", query.lower())[:30]
        found = find_media_for_query(query, assets_dir, prefix, args.max_per_query)
        if not found:
            print(f"  no results for '{query}'")
        for item in found:
            print(f"  → {item['file']} ({item['licence']})")
        credits.extend(found)

    credits_path = args.work / "credits.json"
    credits_path.write_text(json.dumps(credits, indent=2) + "\n", encoding="utf-8")

    print(f"Sourced {len(credits)} media files → {credits_path}")
    print("Next: review every candidate image before using it in the composition")
    return 0


if __name__ == "__main__":
    sys.exit(main())
