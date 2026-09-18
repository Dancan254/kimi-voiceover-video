#!/usr/bin/env python3
"""Write a brand file from answers collected by the agent.

  init_brand.py --handle @theirhandle [--preset kimi-violet] [--accent '#8b5cf6'] …

Flags, not prompts: the skill runs this after asking the user, and an interactive
prompt would hang there. Surface colours are derived from the background so a user
only has to name two colours.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_PATH = Path.home() / ".config" / "kimi-voiceover-video" / "brand.json"
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

PRESETS = {
    "kimi-violet": {"bg": "#0f0f1a", "accent": "#8b5cf6", "textBody": "#E8E6F2", "textMuted": "#8079A3"},
    "midnight-pink": {"bg": "#12121f", "accent": "#f0196a", "textBody": "#E6E6E6", "textMuted": "#6B7A99"},
    "carbon-cyan": {"bg": "#0d1117", "accent": "#21d4c2", "textBody": "#E4EAF2", "textMuted": "#7D8DA5"},
    "ink-amber": {"bg": "#14110d", "accent": "#f5a524", "textBody": "#EDE6DA", "textMuted": "#9A8C76"},
    "violet-signal": {"bg": "#100e1b", "accent": "#8b5cf6", "textBody": "#E8E6F2", "textMuted": "#8079A3"},
    "tiktok-neon": {"bg": "#050505", "accent": "#ff0050", "textBody": "#ffffff", "textMuted": "#00f2ea"},
    "youtube-dark": {"bg": "#0f0f0f", "accent": "#ff0000", "textBody": "#f1f1f1", "textMuted": "#aaaaaa"},
    "minimal-light": {"bg": "#f5f5f7", "accent": "#0071e3", "textBody": "#1d1d1f", "textMuted": "#86868b"},
    "sports-energy": {"bg": "#0a0a0a", "accent": "#ff6b00", "textBody": "#ffffff", "textMuted": "#00d4aa"},
}

FONT_URLS = {
    ("Archivo", "Geist Mono"): "https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&family=Geist+Mono:wght@400..700&display=swap",
}


def mix(color: str, other: str, amount: float) -> str:
    a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02x}" for x, y in zip(a, b))


def font_url(heading: str, mono: str) -> str:
    known = FONT_URLS.get((heading, mono))
    if known:
        return known
    families = "&".join(f"family={name.replace(' ', '+')}:wght@400;700" for name in (heading, mono))
    return f"https://fonts.googleapis.com/css2?{families}&display=swap"


def font_url_works(url: str, families: tuple[str, ...]) -> tuple[bool, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120 Safari/537.36"})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return False, f"Google Fonts returned {error.code}"
    except OSError as error:
        return False, f"could not reach Google Fonts ({error})"
    # A family Google doesn't know is dropped from a 200 response, so check each one by name
    missing = [name for name in families if f"font-family: '{name}'" not in body]
    if missing:
        return False, "Google Fonts has no family called " + " or ".join(repr(name) for name in missing)
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a Kimi voiceover-video brand file.")
    parser.add_argument("--handle", required=True, help="social handle shown in the corner, e.g. @kimi")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="kimi-violet")
    parser.add_argument("--accent", help="accent colour as #rrggbb (overrides the preset)")
    parser.add_argument("--bg", help="background colour as #rrggbb (overrides the preset)")
    parser.add_argument("--heading", default="Archivo", help="display font, any Google font (default: Archivo)")
    parser.add_argument("--mono", default="Geist Mono", help="code font, any Google font (default: Geist Mono)")
    parser.add_argument("--output-dir", default="~/kimi-voiceover-videos", help="where finished videos go")
    parser.add_argument("--out", type=Path, default=DEFAULT_PATH, help=f"brand file to write (default: {DEFAULT_PATH})")
    parser.add_argument("--force", action="store_true", help="overwrite an existing brand file")
    parser.add_argument("--skip-font-check", action="store_true", help="don't verify the fonts against Google Fonts")
    args = parser.parse_args()

    if args.out.exists() and not args.force:
        print(f"{args.out} already exists", file=sys.stderr)
        print("Next: edit it by hand, or re-run with --force to replace it", file=sys.stderr)
        return 1

    colors = dict(PRESETS[args.preset])
    for name in ("accent", "bg"):
        value = getattr(args, name)
        if value:
            colors[name] = value
    for name in ("accent", "bg"):
        if not HEX.match(colors[name]):
            print(f"{name} must look like #rrggbb, got {colors[name]}", file=sys.stderr)
            print("Next: pass a six-digit hex colour", file=sys.stderr)
            return 1

    url = font_url(args.heading, args.mono)
    if not args.skip_font_check:
        ok, reason = font_url_works(url, (args.heading, args.mono))
        if not ok:
            print(reason, file=sys.stderr)
            print("Next: check the exact family names on fonts.google.com, or pass --skip-font-check", file=sys.stderr)
            return 1

    # Expand ~ so scripts that read brand["output"]["dir"] later don't create a literal
    # "~" directory in the current working directory.
    output_dir = Path(args.output_dir).expanduser().resolve()

    brand = {
        "handle": args.handle if args.handle.startswith("@") else "@" + args.handle,
        "colors": {
            "bg": colors["bg"],
            # Surfaces lift off the background and carry a trace of the accent, so cards read as
            # part of the palette instead of flat grey; the user only ever names two colours
            "surface1": mix(mix(colors["bg"], "#ffffff", 0.035), colors["accent"], 0.03),
            "surface2": mix(mix(colors["bg"], "#ffffff", 0.065), colors["accent"], 0.04),
            "border": mix(mix(colors["bg"], "#ffffff", 0.11), colors["accent"], 0.06),
            "accent": colors["accent"],
            "textBody": colors["textBody"],
            "textMuted": colors["textMuted"],
        },
        "fonts": {"heading": args.heading, "mono": args.mono, "googleFontsUrl": url},
        "output": {"dir": str(output_dir)},
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(brand, indent=2) + "\n", encoding="utf-8")
    print(f"{args.out} · {brand['handle']} · {brand['colors']['bg']} bg · {brand['colors']['accent']} accent · {args.heading} / {args.mono}")
    print("Next: run setup.sh to download those fonts, then make a video")
    return 0


if __name__ == "__main__":
    sys.exit(main())
