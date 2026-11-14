#!/usr/bin/env python3
"""
Render Moeen Uddin's profile README as a stack of animated SVG cards.

The cards use only things that survive GitHub's <img> sandbox:
  * an inline <style> block with CSS keyframes
  * fonts subset with pyftsubset and embedded as base64 WOFF data URIs
  * no scripts, no external requests

Usage
-----
    python render_cards.py             # animated cards + preview.html + README.md
    STATIC=1 python render_cards.py    # final frame only, for screenshots

Contribution data lives in data/contributions.json and is refreshed by
scripts/fetch_contributions.py (run daily from .github/workflows/profile.yml).
"""

from __future__ import annotations

import base64
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CARDS = ROOT / "cards"
DATA = ROOT / "data" / "contributions.json"
ASSETS = ROOT / "assets"
FONT_DIR = ASSETS / "fonts"
PORTRAIT = ASSETS / "portrait.jpg"

# ── Brand: sampled from rag-diagnostic-agent.vercel.app ──────────────────────
INK = "#1a3a2a"
INK_SOFT = "#1b2e24"
BODY = "#4a6355"
MUTED = "#7a9e8a"
PRIMARY = "#2d6a4f"
MID = "#40916c"
ACCENT = "#52b788"
LIGHT = "#74c69d"
PALE = "#d8f3dc"
BG = "#f0f7f1"
BORDER = "#c7e8d0"
WHITE = "#ffffff"
DARK_CELL = "#24473a"

PROFILE = {
    "name": "Moeen Uddin",
    "login": "MoeenUddin01",
    "github": "https://github.com/MoeenUddin01",
    "site": "https://rag-diagnostic-agent.vercel.app",
    "tagline": [
        "I build applied AI systems — retrieval, agents,",
        "and the products that make them useful.",
    ],
}

FEATURED = [
    {
        "slug": "specrag",
        "name": "SpecRAG",
        "desc": "A modular, spec-driven RAG architecture for document retrieval and LLM context engineering.",
        "chips": ["Python", "RAG"],
        "url": "https://github.com/MoeenUddin01/SpecRAG",
        "colour": PRIMARY,
    },
    {
        "slug": "finora",
        "name": "Finora",
        "desc": "Accounting and invoicing for customers, suppliers, products, sales, purchases, taxes and reports.",
        "chips": ["FastAPI", "React", "Tailwind"],
        "url": "https://github.com/MoeenUddin01/Finora",
        "colour": MID,
    },
    {
        "slug": "aegisarm",
        "name": "AegisArm",
        "desc": "Closed-loop robotic predictive maintenance with PyTorch LSTMs and PyBullet physics.",
        "chips": ["PyTorch", "PyBullet"],
        "url": "https://github.com/MoeenUddin01/AegisArm",
        "colour": ACCENT,
    },
    {
        "slug": "plantdoc",
        "name": "PlantDoc",
        "desc": "Upload a leaf, get an instant diagnosis — EfficientNet-B2 paired with retrieval-augmented generation.",
        "chips": ["LIVE", "EfficientNet", "RAG"],
        "url": PROFILE["site"],
        "colour": MID,
    },
    {
        "slug": "football",
        "name": "Football prediction",
        "desc": "Elo ratings, leak-free time-series features and XGBoost/Poisson tournament simulation.",
        "chips": ["Python", "XGBoost"],
        "url": "https://github.com/MoeenUddin01/-Football-Match-Outcome-And-Score-Prediction",
        "colour": PRIMARY,
    },
]

TILES = [
    {
        "file": "tile-ai.svg",
        "eyebrow": "01 · APPLIED AI",
        "title": "Retrieval & agents",
        "sub": "SpecRAG, evaluation, tool use",
        "cta": "VIEW PROJECT",
        "url": "https://github.com/MoeenUddin01/SpecRAG",
        "colour": PRIMARY,
        "alt": "Applied AI — retrieval, agents and evaluation",
    },
    {
        "file": "tile-build.svg",
        "eyebrow": "02 · PRODUCT",
        "title": "Full-stack systems",
        "sub": "FastAPI · React · Frappe",
        "cta": "VIEW PROJECT",
        "url": "https://github.com/MoeenUddin01/Finora",
        "colour": MID,
        "alt": "Product engineering — FastAPI, React and Frappe",
    },
    {
        "file": "tile-live.svg",
        "eyebrow": "03 · LIVE",
        "title": "PlantDoc",
        "sub": "Try the diagnosis demo",
        "cta": "LIVE DEMO",
        "url": PROFILE["site"],
        "colour": ACCENT,
        "alt": "PlantDoc live demo — AI plant disease diagnostics",
    },
]

STATIC = os.environ.get("STATIC", "").strip().lower() in {"1", "true", "yes", "on"}

# ── Small helpers ────────────────────────────────────────────────────────────


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def integer(value: int) -> str:
    return f"{value:,}"


def num(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def make_defs(extra: str = "") -> str:
    return f"""
<defs>
  <filter id="shadow" x="-4%" y="-8%" width="108%" height="122%">
    <feDropShadow dx="0" dy="8" stdDeviation="9" flood-color="{INK}" flood-opacity="0.10"/>
  </filter>
  <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
    <feDropShadow dx="0" dy="3" stdDeviation="5" flood-color="{INK}" flood-opacity="0.12"/>
  </filter>
  <linearGradient id="heroBg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#f6fbf7"/>
    <stop offset="0.55" stop-color="{BG}"/>
    <stop offset="1" stop-color="#e2f1e7"/>
  </linearGradient>
  <linearGradient id="blob" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{LIGHT}"/>
    <stop offset="1" stop-color="{MID}"/>
  </linearGradient>
  <linearGradient id="bar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#a7dcc0"/>
    <stop offset="1" stop-color="{ACCENT}"/>
  </linearGradient>
  <linearGradient id="barPeak" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{MID}"/>
    <stop offset="1" stop-color="{INK}"/>
  </linearGradient>
  <linearGradient id="barNow" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{LIGHT}"/>
    <stop offset="1" stop-color="{PRIMARY}"/>
  </linearGradient>
  {extra}
</defs>"""


def card_rect(w: int, h: int, rx: int = 30, fill: str = WHITE, stroke: str = BORDER) -> str:
    return (
        f'<rect x="10" y="10" width="{w - 20}" height="{h - 20}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1" filter="url(#shadow)"/>'
    )


def text(
    x: float,
    y: float,
    value: str,
    *,
    size: float = 16,
    fill: str = BODY,
    weight: int | str = 400,
    anchor: str = "start",
    cls: str = "",
    letter_spacing: float | None = None,
    style: str = "",
    opacity: float | None = None,
) -> str:
    bits = [
        f'x="{num(x)}"',
        f'y="{num(y)}"',
        f'font-size="{num(size)}"',
        f'fill="{fill}"',
        f'font-weight="{weight}"',
        f'text-anchor="{anchor}"',
    ]
    if cls:
        bits.append(f'class="{cls}"')
    if letter_spacing is not None:
        bits.append(f'letter-spacing="{num(letter_spacing)}"')
    if style:
        bits.append(f'style="{style}"')
    if opacity is not None:
        bits.append(f'opacity="{num(opacity)}"')
    return f"<text {' '.join(bits)}>{esc(value)}</text>"


def pill(x: float, y: float, w: float, h: float, fill: str, stroke: str | None = BORDER, rx: float | None = None) -> str:
    stroke_attr = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
    return f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" rx="{num(rx if rx is not None else h / 2)}" fill="{fill}"{stroke_attr}/>'


def arrow_path(cx: float, cy: float, size: float, colour: str, width: float = 2.0) -> str:
    s = size
    return (
        f'<path d="M {num(cx - s * 0.45)} {num(cy)} H {num(cx + s * 0.45)} '
        f'M {num(cx + s * 0.06)} {num(cy - s * 0.39)} L {num(cx + s * 0.45)} {num(cy)} '
        f'L {num(cx + s * 0.06)} {num(cy + s * 0.39)}" fill="none" '
        f'stroke="{colour}" stroke-width="{num(width)}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def external_arrow(cx: float, cy: float, size: float, colour: str, width: float = 2.0) -> str:
    s = size
    return (
        f'<path d="M {num(cx - s * 0.42)} {num(cy + s * 0.42)} L {num(cx + s * 0.42)} {num(cy - s * 0.42)} '
        f'M {num(cx - s * 0.05)} {num(cy - s * 0.42)} H {num(cx + s * 0.42)} V {num(cy + s * 0.05)}" '
        f'fill="none" stroke="{colour}" stroke-width="{num(width)}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def leaf_mark(x: float, y: float, size: float) -> str:
    """The PlantDoc-ish mark: a dark rounded square with two leaves."""
    s = size
    return f"""
<g transform="translate({num(x)} {num(y)})">
  <rect width="{num(s)}" height="{num(s)}" rx="{num(s * 0.28)}" fill="{INK}"/>
  <path d="M {num(s * 0.29)} {num(s * 0.66)} C {num(s * 0.28)} {num(s * 0.36)} {num(s * 0.50)} {num(s * 0.20)} {num(s * 0.75)} {num(s * 0.22)} C {num(s * 0.76)} {num(s * 0.52)} {num(s * 0.56)} {num(s * 0.69)} {num(s * 0.29)} {num(s * 0.66)} Z" fill="{LIGHT}"/>
  <path d="M {num(s * 0.34)} {num(s * 0.77)} C {num(s * 0.42)} {num(s * 0.53)} {num(s * 0.61)} {num(s * 0.44)} {num(s * 0.79)} {num(s * 0.49)} C {num(s * 0.75)} {num(s * 0.70)} {num(s * 0.57)} {num(s * 0.80)} {num(s * 0.34)} {num(s * 0.77)} Z" fill="{PALE}" opacity="0.9"/>
  <path d="M {num(s * 0.35)} {num(s * 0.70)} C {num(s * 0.49)} {num(s * 0.56)} {num(s * 0.60)} {num(s * 0.45)} {num(s * 0.69)} {num(s * 0.34)}" fill="none" stroke="{INK}" stroke-width="{num(s * 0.035)}" stroke-linecap="round"/>
</g>"""


# ── Motion ───────────────────────────────────────────────────────────────────

BASE_CSS = f"""
text {{ font-family: 'DM Sans', Arial, Helvetica, sans-serif; }}
.serif {{ font-family: 'Fraunces', Georgia, 'Times New Roman', serif; }}
.eyebrow {{ font-size: 10.5px; font-weight: 600; letter-spacing: 2.1px; fill: {PRIMARY}; }}
.mono {{ font-family: 'DM Sans', Arial, sans-serif; letter-spacing: 1.4px; }}
"""

# Deliberately no SMIL: inside an <img>, SMIL ignores prefers-reduced-motion,
# so it could not satisfy "every animation off". CSS keyframes can be switched
# off by the media query below and by STATIC=1.
MOTION_CSS = """
.a-rise,.a-fade,.a-slide,.a-grow,.a-pop { animation-fill-mode: both; }
.a-rise {
  animation-name: rise; animation-duration: .85s;
  animation-timing-function: cubic-bezier(.20,.80,.24,1);
  animation-delay: calc(var(--base) + var(--d, 0s));
}
.a-fade {
  animation-name: fade; animation-duration: .9s;
  animation-timing-function: ease-out;
  animation-delay: calc(var(--base) + var(--d, 0s));
}
.a-slide {
  animation-name: slide; animation-duration: .85s;
  animation-timing-function: cubic-bezier(.20,.80,.24,1);
  animation-delay: calc(var(--base) + var(--d, 0s));
}
.a-grow {
  animation-name: grow; animation-duration: .95s;
  animation-timing-function: cubic-bezier(.16,.84,.28,1);
  animation-delay: calc(var(--base) + var(--d, 0s));
  transform-box: fill-box; transform-origin: bottom center;
}
.a-pop {
  animation-name: pop; animation-duration: .45s;
  animation-timing-function: cubic-bezier(.20,.90,.30,1.2);
  animation-delay: calc(var(--base) + var(--d, 0s));
  transform-box: fill-box; transform-origin: center;
}
.a-blob {
  animation: breathe 16s ease-in-out infinite;
  animation-delay: calc(var(--base) + .4s);
  transform-box: fill-box; transform-origin: center;
}
.a-halo {
  animation: halo 3.4s ease-in-out infinite;
  animation-delay: calc(var(--base) + 1.6s);
}
.a-nudge {
  animation: nudge 2.8s ease-in-out infinite;
  animation-delay: calc(var(--base) + 1.1s);
}
@keyframes rise { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes slide { from { opacity: 0; transform: translateX(-16px); } to { opacity: 1; transform: translateX(0); } }
@keyframes grow { from { opacity: .25; transform: scaleY(.03); } to { opacity: 1; transform: scaleY(1); } }
@keyframes pop { from { opacity: 0; transform: scale(.15); } to { opacity: 1; transform: scale(1); } }
@keyframes breathe { 0%,100% { transform: scale(1) rotate(0deg); } 50% { transform: scale(1.035) rotate(2deg); } }
@keyframes halo { 0%,100% { opacity: .25; } 50% { opacity: .9; } }
@keyframes nudge { 0%,100% { transform: translateX(0); } 50% { transform: translateX(4px); } }
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
"""


def motion_css() -> str:
    if STATIC:
        return "* { animation: none !important; transition: none !important; }"
    return MOTION_CSS


# ── Fonts ────────────────────────────────────────────────────────────────────

FONT_FACES = [
    {
        "family": "Fraunces",
        "filename": "Fraunces.ttf",
        "style": "normal",
        "weight": 600,
        "axes": {"wght": 600, "opsz": 48, "SOFT": 0, "WONK": 0},
    },
    {
        "family": "Fraunces",
        "filename": "Fraunces-Italic.ttf",
        "style": "italic",
        "weight": 600,
        "axes": {"wght": 600, "opsz": 48, "SOFT": 0, "WONK": 0},
    },
    {
        "family": "DM Sans",
        "filename": "DMSans.ttf",
        "style": "normal",
        "weight": 400,
        "axes": {"wght": 400, "opsz": 14},
    },
    {
        "family": "DM Sans",
        "filename": "DMSans.ttf",
        "style": "normal",
        "weight": 500,
        "axes": {"wght": 500, "opsz": 14},
    },
    {
        "family": "DM Sans",
        "filename": "DMSans.ttf",
        "style": "normal",
        "weight": 600,
        "axes": {"wght": 600, "opsz": 14},
    },
]


@dataclass
class Card:
    filename: str
    width: int
    height: int
    title: str
    desc: str
    base_delay: float
    body: str


def visible_text(body: str) -> str:
    chunks = re.findall(r">([^<>]+)<", body)
    return "".join(html.unescape(chunk) for chunk in chunks)


def build_font_faces(cards: list[Card]) -> dict[tuple[str, str, int], str]:
    """Instance the variable fonts, subset them with pyftsubset, return CSS faces."""
    text = "".join(visible_text(card.body) for card in cards)
    # Always keep the full printable ASCII range so counts/dates never break.
    text += "".join(chr(c) for c in range(32, 127))
    text += "—–·’‘“”…↗↓→"
    unique = "".join(sorted(set(text)))

    tmpdir = Path(tempfile.mkdtemp(prefix="profile-fonts-"))
    css: dict[tuple[str, str, int], str] = {}
    try:
        text_file = tmpdir / "chars.txt"
        text_file.write_text(unique, encoding="utf-8")
        for face in FONT_FACES:
            family = face["family"]
            filename = face["filename"]
            style = face["style"]
            weight = face["weight"]
            source = FONT_DIR / filename
            if not source.exists():
                raise SystemExit(
                    f"Missing font source: {source}\n"
                    "Put the Fraunces/DM Sans variable TTFs in assets/fonts/."
                )

            # Pin the variable axes first: a static instance subsets to a
            # fraction of the size of a variable WOFF.
            instance = tmpdir / f"{Path(filename).stem}-{weight}-{style}.ttf"
            axes = [f"{tag}={value}" for tag, value in face["axes"].items()]
            cmd = [
                sys.executable,
                "-m",
                "fontTools.varLib.instancer",
                str(source),
                *axes,
                "--no-recalc-timestamp",
                f"--output={instance}",
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError as exc:
                raise SystemExit(
                    "fontTools.varLib.instancer failed:\n"
                    + exc.stderr.decode("utf-8", "replace")
                ) from exc

            out = tmpdir / f"{Path(filename).stem}-{weight}-{style}.woff"
            cmd = [
                sys.executable,
                "-m",
                "fontTools.subset",
                str(instance),
                f"--text-file={text_file}",
                f"--output-file={out}",
                "--flavor=woff",
                "--layout-features=kern,liga",
                "--no-hinting",
                "--desubroutinize",
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError as exc:
                raise SystemExit(
                    "pyftsubset failed:\n" + exc.stderr.decode("utf-8", "replace")
                ) from exc
            payload = base64.b64encode(out.read_bytes()).decode("ascii")
            css[(family, style, weight)] = (
                "@font-face{"
                f"font-family:'{family}';"
                f"src:url(data:font/woff;base64,{payload}) format('woff');"
                f"font-weight:{weight};font-style:{style};font-display:block;"
                "}"
            )
            print(
                f"  font  {family:9} {style:6} {weight} "
                f"{len(payload) / 1024:5.1f} kB (base64)"
            )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return css


def font_css_for(card: Card, faces: dict[tuple[str, str, int], str]) -> str:
    weights = {int(value) for value in re.findall(r'font-weight="(\d+)"', card.body)}
    weights.add(400)
    italic = 'font-style="italic"' in card.body
    selected = []
    for (family, style, weight), css in faces.items():
        if family == "Fraunces":
            if style == "italic" and italic:
                selected.append(css)
            elif style == "normal" and 600 in weights:
                selected.append(css)
        elif weight in weights:
            selected.append(css)
    return "".join(selected)


def assemble(card: Card, faces: dict[tuple[str, str, int], str]) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{card.width}" height="{card.height}" viewBox="0 0 {card.width} {card.height}" role="img" aria-labelledby="title desc" style="--base:{num(card.base_delay, 2)}s">
<title id="title">{esc(card.title)}</title>
<desc id="desc">{esc(card.desc)}</desc>
<style>{font_css_for(card, faces)}{BASE_CSS}{motion_css()}</style>
{card.body}
</svg>
"""


# ── Data ─────────────────────────────────────────────────────────────────────


def load_data() -> dict:
    if not DATA.exists():
        raise SystemExit(f"Missing {DATA}. Run scripts/fetch_contributions.py first.")
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    days = []
    for item in raw.get("days", []):
        days.append(
            {
                "date": date.fromisoformat(item["date"]),
                "count": int(item.get("count", 0)),
                "level": int(item.get("level", 0)),
            }
        )
    days.sort(key=lambda d: d["date"])
    if not days:
        raise SystemExit(f"{DATA} contains no days.")
    return {"days": days, "generated_at": raw.get("generated_at")}


def compute_stats(days: list[dict]) -> dict:
    total = sum(d["count"] for d in days)
    active_days = sum(1 for d in days if d["count"] > 0)

    longest = current = 0
    best_range = None
    run_start = None
    for day in days:
        if day["count"] > 0:
            if run_start is None:
                run_start = day["date"]
            current += 1
            if current > longest:
                longest = current
                best_range = (run_start, day["date"])
        else:
            current = 0
            run_start = None

    # Current streak: count backwards; tolerate today/yesterday being empty.
    streak = 0
    for day in reversed(days):
        if day["count"] > 0:
            streak += 1
        elif streak:
            break
        else:
            continue

    busiest = max(days, key=lambda d: (d["count"], d["date"]))
    months: OrderedDict[str, int] = OrderedDict()
    for day in days:
        key = day["date"].strftime("%Y-%m")
        months[key] = months.get(key, 0) + day["count"]

    return {
        "total": total,
        "active": active_days,
        "days": len(days),
        "pct": active_days / len(days) * 100 if days else 0,
        "longest": longest,
        "current": streak,
        "best_range": best_range,
        "busiest": busiest,
        "months": months,
    }


def month_label(key: str) -> str:
    return datetime.strptime(key, "%Y-%m").strftime("%b")


def long_day(value: date) -> str:
    return f"{value.strftime('%b')} {value.day}, {value.year}"


def read_portrait() -> tuple[str, str] | None:
    if not PORTRAIT.exists():
        return None
    mime = "image/png" if PORTRAIT.suffix.lower() == ".png" else "image/jpeg"
    return base64.b64encode(PORTRAIT.read_bytes()).decode("ascii"), mime


# ── Hero ─────────────────────────────────────────────────────────────────────


def hero_card(stats: dict, portrait_asset: tuple[str, str] | None) -> Card:
    w, h = 1200, 400
    name = PROFILE["name"]
    first, last = name.split(" ", 1)
    total = integer(stats["total"])
    active = integer(stats["active"])

    if portrait_asset:
        portrait_b64, portrait_mime = portrait_asset
        portrait_markup = f"""
  <g class="a-pop" style="--d:.28s">
    <circle cx="1002" cy="198" r="119" fill="{WHITE}" opacity="0.55"/>
    <clipPath id="portraitClip"><circle cx="1002" cy="198" r="108"/></clipPath>
    <image href="data:{portrait_mime};base64,{portrait_b64}" x="894" y="90" width="216" height="216"
           preserveAspectRatio="xMidYMid slice" clip-path="url(#portraitClip)"/>
    <circle cx="1002" cy="198" r="108" fill="none" stroke="{PRIMARY}" stroke-width="1.5" opacity="0.35"/>
  </g>"""
    else:
        portrait_markup = f"""
  <g class="a-pop" style="--d:.28s">
    <circle cx="1002" cy="198" r="109" fill="{PALE}" stroke="{BORDER}" stroke-width="1"/>
    <text x="1002" y="226" text-anchor="middle" class="serif" font-size="82" font-weight="600" fill="{PRIMARY}">MU</text>
  </g>"""

    body = f"""
{make_defs(f'<clipPath id="heroClip"><rect x="10" y="10" width="{w - 20}" height="{h - 20}" rx="30"/></clipPath>')}
{card_rect(w, h, 30, "url(#heroBg)")}
<g clip-path="url(#heroClip)">
  <circle cx="1010" cy="190" r="275" fill="{PALE}" opacity="0.30"/>
  <circle cx="1028" cy="196" r="230" fill="none" stroke="{BORDER}" stroke-width="1" opacity="0.55"/>
  <path d="M 700 380 C 790 310 860 330 930 280" fill="none" stroke="{BORDER}" stroke-width="1.2" opacity="0.7"/>
  <path d="M 760 400 C 850 330 920 350 1000 300" fill="none" stroke="{BORDER}" stroke-width="1.2" opacity="0.45"/>
</g>

<g class="a-rise" style="--d:.02s">
  {leaf_mark(56, 44, 36)}
  {text(104, 60, "PORTFOLIO", size=10.5, fill=PRIMARY, weight=600, letter_spacing=2.4)}
  {text(104, 75, "APPLIED AI · FULL-STACK", size=9.5, fill=MUTED, weight=500, letter_spacing=1.5)}
</g>

{text(56, 130, "A PRACTICAL AI ENGINEER", size=10.5, fill=PRIMARY, weight=600, letter_spacing=2.2, cls="a-rise", style="--d:.10s")}

<g class="a-rise" style="--d:.18s">
  <text x="55" y="208" class="serif" font-size="76" font-weight="600" fill="{INK}">{esc(first)}<tspan fill="{PRIMARY}" font-style="italic"> {esc(last)}</tspan></text>
</g>

{text(56, 254, PROFILE["tagline"][0], size=20, fill=BODY, cls="a-rise", style="--d:.30s")}
{text(56, 282, PROFILE["tagline"][1], size=20, fill=BODY, cls="a-rise", style="--d:.36s")}

<g class="a-fade" style="--d:.46s">
  <line x1="56" y1="311" x2="760" y2="311" stroke="{BORDER}" stroke-width="1"/>
  <circle cx="62" cy="337" r="3.5" fill="{ACCENT}"/>
  {text(76, 341, f"{total} contributions", size=13, fill=INK_SOFT, weight=600)}
  {text(196, 341, "·", size=13, fill=MUTED)}
  {text(212, 341, f"{active} active days", size=13, fill=BODY, weight=500)}
  {text(324, 341, "·", size=13, fill=MUTED)}
  {text(340, 341, "building in public since 2025", size=13, fill=BODY, weight=500)}
</g>

<g class="a-blob" opacity="0.95">
  <path d="M1000 38c92 0 158 62 162 148 4 84-62 150-156 152-96 2-164-62-168-148-4-84 68-152 162-152z" fill="url(#blob)" opacity="0.16"/>
</g>

{portrait_markup}

<g class="a-rise" style="--d:.52s">
  {pill(846, 92, 62, 26, WHITE, BORDER)}
  {text(877, 109, "RAG", size=9.5, fill=PRIMARY, weight=600, anchor="middle", letter_spacing=1.2)}
</g>
<g class="a-rise" style="--d:.60s">
  {pill(1042, 286, 88, 26, WHITE, BORDER)}
  {text(1086, 303, "AGENTS", size=9.5, fill=PRIMARY, weight=600, anchor="middle", letter_spacing=1.2)}
</g>
<g class="a-fade" style="--d:.70s" opacity="0.8">
  <path d="M 872 132 l 4 10 10 4 -10 4 -4 10 -4 -10 -10 -4 10 -4z" fill="{ACCENT}"/>
  <path d="M 1112 158 l 3 7 7 3 -7 3 -3 7 -3 -7 -7 -3 7 -3z" fill="{LIGHT}"/>
</g>
"""
    return Card(
        "hero.svg",
        w,
        h,
        f"{name} — applied AI engineer",
        "Hero card with portrait, tagline and contribution totals.",
        0.0,
        body,
    )


# ── Tiles ────────────────────────────────────────────────────────────────────


def tile_motif(index: int, colour: str) -> str:
    if index == 1:
        return (
            f'<path d="M 354 72 L 372 54 M 372 54 L 390 70 M 354 72 L 390 70" '
            f'fill="none" stroke="{colour}" stroke-width="1.3" stroke-linecap="round"/>'
            f'<circle cx="354" cy="72" r="4" fill="{BG}" stroke="{colour}" stroke-width="1.3"/>'
            f'<circle cx="372" cy="54" r="4" fill="{BG}" stroke="{colour}" stroke-width="1.3"/>'
            f'<circle cx="390" cy="70" r="4" fill="{colour}" opacity="0.55"/>'
        )
    if index == 2:
        return (
            f'<path d="M 350 60 L 374 48 L 398 60 L 374 72 Z" fill="none" stroke="{colour}" stroke-width="1.3" stroke-linejoin="round"/>'
            f'<path d="M 350 68 L 374 80 L 398 68" fill="none" stroke="{colour}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="M 350 76 L 374 88 L 398 76" fill="none" stroke="{colour}" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>'
        )
    return (
        f'<path d="M 348 78 C 347 55 365 41 390 43 C 390 66 372 80 348 78 Z" fill="none" stroke="{colour}" stroke-width="1.5"/>'
        f'<path d="M 351 76 C 362 63 374 54 386 48" fill="none" stroke="{colour}" stroke-width="1.2" stroke-linecap="round"/>'
    )


def tile_card(tile: dict, index: int) -> Card:
    w, h = 420, 210
    colour = tile["colour"]
    body = f"""
{make_defs()}
{card_rect(w, h, 24)}
<rect x="10" y="10" width="{w - 20}" height="{h - 20}" rx="24" fill="url(#heroBg)" opacity="0.55"/>
<rect x="20" y="34" width="4" height="24" rx="2" fill="{colour}"/>

<g class="a-fade" style="--d:.04s">
  {text(34, 52, tile["eyebrow"], size=9.5, fill=colour, weight=600, letter_spacing=1.8)}
</g>
<g class="a-rise" style="--d:.10s">
  {text(34, 105, tile["title"], size=29, fill=INK, weight=600, cls="serif")}
</g>
<g class="a-rise" style="--d:.18s">
  {text(34, 132, tile["sub"], size=13.5, fill=BODY)}
</g>

<g class="a-fade" style="--d:.24s">
  <line x1="34" y1="151" x2="386" y2="151" stroke="{BORDER}" stroke-width="1"/>
  {text(34, 174, tile["cta"], size=8.5, fill=MUTED, weight=600, letter_spacing=1.6)}
</g>

<g class="a-nudge">
  <circle cx="356" cy="166" r="18" fill="{PALE}"/>
  {arrow_path(356, 166, 13, colour, 1.8)}
</g>

<g class="a-fade" style="--d:.30s" opacity="0.22">
  {tile_motif(index, colour)}
</g>

<g class="a-fade" style="--d:.34s" opacity="0.55">
  <circle cx="386" cy="34" r="3" fill="{colour}"/>
</g>
"""
    return Card(
        tile["file"],
        w,
        h,
        f"{tile['title']} — {tile['sub']}",
        tile["alt"],
        0.35 + index * 0.13,
        body,
    )


# ── Chart ────────────────────────────────────────────────────────────────────


def chart_card(stats: dict) -> Card:
    w, h = 1200, 440
    months = list(stats["months"].items())[-13:]
    values = [count for _, count in months]
    peak = max(values) if values else 1
    scale_max = 180 if peak <= 180 else int(math.ceil(peak / 30) * 30)
    chart_top = 206
    baseline = 356
    chart_h = baseline - chart_top
    x0 = 78
    step = 52
    bar_w = 30
    peak_key = max(months, key=lambda item: item[1])[0]
    current_key = months[-1][0] if months else ""
    avg = sum(values) / len(values) if values else 0

    bars = []
    labels = []
    for i, (key, count) in enumerate(months):
        x = x0 + i * step
        bar_h = count / scale_max * chart_h
        y = baseline - bar_h
        fill = "url(#bar)"
        if key == peak_key:
            fill = "url(#barPeak)"
        elif key == current_key:
            fill = "url(#barNow)"
        delay = 0.16 + i * 0.035
        bars.append(
            f'<rect class="a-grow" style="--d:{delay:.3f}s" x="{x}" y="{num(y)}" '
            f'width="{bar_w}" height="{num(max(bar_h, 2))}" rx="6" fill="{fill}"/>'
        )
        if count:
            label_fill = INK if key == peak_key else MUTED
            weight = 600 if key == peak_key else 500
            labels.append(
                text(
                    x + bar_w / 2,
                    y - 9,
                    str(count),
                    size=10,
                    fill=label_fill,
                    weight=weight,
                    anchor="middle",
                    cls="a-fade",
                    style=f"--d:{delay + 0.20:.3f}s",
                )
            )
        month_fill = PRIMARY if key == current_key else MUTED
        month_weight = 600 if key == current_key else 500
        labels.append(
            text(
                x + bar_w / 2,
                baseline + 24,
                month_label(key),
                size=10.5,
                fill=month_fill,
                weight=month_weight,
                anchor="middle",
                cls="a-fade",
                style=f"--d:{0.28 + i * 0.035:.3f}s",
            )
        )
        if key == current_key:
            labels.append(
                text(
                    x + bar_w / 2,
                    baseline + 38,
                    "MTD",
                    size=8,
                    fill=PRIMARY,
                    weight=600,
                    anchor="middle",
                    letter_spacing=1.0,
                    cls="a-fade",
                    style=f"--d:{0.28 + i * 0.035:.3f}s",
                )
            )

    grid = []
    for tick in range(0, scale_max + 1, 60):
        y = baseline - tick / scale_max * chart_h
        grid.append(
            f'<line x1="72" y1="{num(y)}" x2="762" y2="{num(y)}" stroke="{BORDER}" '
            f'stroke-width="1" opacity="{0.95 if tick == 0 else 0.55}" stroke-dasharray="{"" if tick == 0 else "3 5"}"/>'
        )
        grid.append(text(64, y + 4, str(tick), size=9.5, fill=MUTED, weight=500, anchor="end"))

    avg_y = baseline - avg / scale_max * chart_h
    busiest = stats["busiest"]
    first_key, last_key = months[0][0], months[-1][0]
    range_label = (
        f"{month_label(first_key)} {first_key[:4]} — {month_label(last_key)} {last_key[:4]}"
    )

    stat_rows = [
        ("BEST STREAK", integer(stats["longest"]), f"{stats['current']} days current", 76),
        ("ACTIVE DAYS", integer(stats["active"]), f"{stats['pct']:.0f}% of the year", 178),
        ("BUSIEST DAY", integer(busiest["count"]), long_day(busiest["date"]), 280),
    ]
    stat_markup = []
    for i, (label, value, sub, y) in enumerate(stat_rows):
        delay = 0.12 + i * 0.08
        stat_markup.append(
            f'<g class="a-rise" style="--d:{delay:.2f}s">'
            + text(820, y, label, size=9.5, fill=PRIMARY, weight=600, letter_spacing=1.8)
            + text(820, y + 46, value, size=42, fill=INK, weight=600, cls="serif")
            + text(820, y + 66, sub, size=12, fill=BODY, weight=500)
            + "</g>"
        )
        if i < 2:
            stat_markup.append(
                f'<line x1="820" y1="{y + 82}" x2="1144" y2="{y + 82}" stroke="{BORDER}" stroke-width="1"/>'
            )

    body = f"""
{make_defs()}
{card_rect(w, h, 30)}
<rect x="10" y="10" width="{w - 20}" height="{h - 20}" rx="30" fill="url(#heroBg)" opacity="0.28"/>

<g class="a-rise" style="--d:.02s">
  {text(56, 58, "THE YEAR IN GREEN", size=10.5, fill=PRIMARY, weight=600, letter_spacing=2.2)}
</g>
<g class="a-rise" style="--d:.08s">
  {text(56, 103, "A year of showing up.", size=38, fill=INK, weight=600, cls="serif")}
</g>
<g class="a-fade" style="--d:.15s">
  {text(56, 130, f"{integer(stats['total'])} contributions across {integer(stats['active'])} active days.", size=14.5, fill=BODY)}
</g>

{''.join(stat_markup)}

<line x1="56" y1="170" x2="762" y2="170" stroke="{BORDER}" stroke-width="1"/>
{text(762, 188, range_label.upper(), size=8.5, fill=MUTED, weight=600, anchor="end", letter_spacing=1.4)}

{''.join(grid)}
<line x1="72" y1="{num(avg_y)}" x2="762" y2="{num(avg_y)}" stroke="{MID}" stroke-width="1" stroke-dasharray="4 5" opacity="0.55"/>
{text(770, avg_y + 4, f"AVG {avg:.0f}", size=8.5, fill=MID, weight=600, letter_spacing=0.8)}

{''.join(bars)}
{''.join(labels)}
"""
    return Card(
        "chart.svg",
        w,
        h,
        "Contributions by month",
        f"{integer(stats['total'])} contributions, a best streak of {stats['longest']} days, {integer(stats['active'])} active days and a busiest day of {busiest['count']} contributions.",
        0.82,
        body,
    )


# ── Repo cards ───────────────────────────────────────────────────────────────


def chip(x: float, y: float, label: str, fill: str, fg: str, stroke: str | None) -> tuple[str, float]:
    width = 18 + len(label) * 6.35
    stroke_attr = f' stroke="{stroke}" stroke-width="1"' if stroke else ""
    markup = (
        f'<rect x="{num(x)}" y="{num(y)}" width="{num(width)}" height="22" rx="11" fill="{fill}"{stroke_attr}/>'
        + text(x + width / 2, y + 14.5, label.upper(), size=8.5, fill=fg, weight=600, anchor="middle", letter_spacing=0.8)
    )
    return markup, width


def repo_card(repo: dict, index: int) -> Card:
    w, h = 1200, 168
    colour = repo["colour"]
    chips = []
    cursor = 112
    for value in repo["chips"]:
        if value.upper() == "LIVE":
            markup, width = chip(cursor, 106, value, INK, BG, None)
        else:
            markup, width = chip(cursor, 106, value, WHITE, PRIMARY, BORDER)
        chips.append(markup)
        cursor += width + 8

    external = external_arrow(1126, 80, 14, BG, 1.8)
    body = f"""
{make_defs()}
{card_rect(w, h, 24)}
<rect x="18" y="42" width="5" height="84" rx="2.5" fill="{colour}"/>
{text(40, 96, f"{index:02d}", size=26, fill=colour, weight=600, cls="serif", opacity=0.55)}
<line x1="88" y1="42" x2="88" y2="126" stroke="{BORDER}" stroke-width="1"/>

<g class="a-rise" style="--d:.04s">
  {text(112, 66, repo["name"], size=29, fill=INK, weight=600, cls="serif")}
</g>
<g class="a-rise" style="--d:.12s">
  {text(112, 94, repo["desc"], size=14.5, fill=BODY)}
</g>
<g class="a-fade" style="--d:.20s">
  {''.join(chips)}
</g>

<g class="a-fade" style="--d:.26s">
  <circle cx="1126" cy="80" r="25" fill="{INK}"/>
  {external}
  {text(1126, 125, "OPEN", size=8, fill=MUTED, weight=600, anchor="middle", letter_spacing=1.4)}
</g>
"""
    return Card(
        f"repo-{index:02d}-{repo['slug']}.svg",
        w,
        h,
        f"{repo['name']} — featured project",
        repo["desc"],
        1.00 + index * 0.14,
        body,
    )


# ── Contribution graph ───────────────────────────────────────────────────────


def graph_card(data: dict, stats: dict) -> Card:
    w, h = 1200, 350
    days = data["days"]
    last = days[-1]["date"]
    first = days[0]["date"]
    start = first - timedelta(days=(first.weekday() + 1) % 7)  # back to Sunday
    total_weeks = ((last - start).days + 7) // 7
    weeks = min(total_weeks, 53)
    start = last - timedelta(days=(weeks * 7) - 1)
    start -= timedelta(days=(start.weekday() + 1) % 7)
    use = [d for d in days if d["date"] >= start]

    x0, y0 = 56, 170
    cell, gap = 15, 4
    step = cell + gap
    level_fill = {
        0: DARK_CELL,
        1: "#2d6a4f",
        2: "#40916c",
        3: "#74c69d",
        4: "#b7e4c7",
    }

    cells = []
    today_index = None
    for d in use:
        index = (d["date"] - start).days
        col, row = divmod(index, 7)
        if col >= 53:
            continue
        x = x0 + col * step
        y = y0 + row * step
        level = max(0, min(4, d["level"]))
        delay = 0.18 + col * 0.012 + row * 0.007
        cells.append(
            f'<rect class="a-pop" style="--d:{delay:.3f}s" x="{x}" y="{y}" width="{cell}" height="{cell}" '
            f'rx="3.5" fill="{level_fill[level]}"/>'
        )
        if d["date"] == last:
            today_index = (x, y, level)

    # Month labels: first column of every new month.
    month_marks = []
    seen = set()
    prev_month = None
    for d in use:
        key = (d["date"].year, d["date"].month)
        if key != prev_month:
            prev_month = key
            index = (d["date"] - start).days
            col = index // 7
            if col not in seen and col < 53:
                seen.add(col)
                label = d["date"].strftime("%b")
                month_marks.append(
                    text(x0 + col * step, y0 - 12, label, size=9.5, fill=LIGHT, weight=500, opacity=0.72)
                )

    weekday_labels = []
    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        weekday_labels.append(
            text(x0 - 12, y0 + row * step + 11.5, label, size=9, fill=LIGHT, weight=500, anchor="end", opacity=0.55)
        )

    legend_x = 894
    legend = [
        text(legend_x, 112, "LESS", size=8, fill=LIGHT, weight=600, letter_spacing=1.2, opacity=0.70),
    ]
    for i in range(5):
        legend.append(
            f'<rect x="{legend_x + 36 + i * 19}" y="100" width="14" height="14" rx="3.5" fill="{level_fill[i]}"/>'
        )
    legend.append(
        text(legend_x + 136, 112, "MORE", size=8, fill=LIGHT, weight=600, letter_spacing=1.2, opacity=0.70)
    )

    today = ""
    if today_index:
        x, y, level = today_index
        today = (
            f'<rect class="a-halo" x="{x - 3.5}" y="{y - 3.5}" width="{cell + 7}" height="{cell + 7}" rx="5.5" '
            f'fill="none" stroke="{PALE}" stroke-width="1.5"/>'
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3.5" fill="{level_fill[level]}" '
            f'stroke="{PALE}" stroke-width="1"/>'
        )

    body = f"""
{make_defs(f'<clipPath id="graphClip"><rect x="10" y="10" width="{w - 20}" height="{h - 20}" rx="30"/></clipPath>')}
{card_rect(w, h, 30, INK, "#2d6a4f")}
<g clip-path="url(#graphClip)">
  <circle cx="1080" cy="40" r="190" fill="{MID}" opacity="0.12"/>
  <circle cx="120" cy="330" r="170" fill="{ACCENT}" opacity="0.07"/>
</g>

<g class="a-rise" style="--d:.02s">
  {text(56, 54, "THE LONG VIEW", size=10.5, fill="{LIGHT}", weight=600, letter_spacing=2.2)}
</g>
<g class="a-rise" style="--d:.08s">
  {text(56, 98, "Every day counts.", size=36, fill=BG, weight=600, cls="serif")}
</g>
<g class="a-fade" style="--d:.15s">
  {text(56, 126, f"{stats['days']} days · {integer(stats['active'])} active · {stats['longest']}-day best streak", size=13, fill="#a9c9b8", weight=500)}
</g>

{''.join(legend)}
{''.join(month_marks)}
{''.join(weekday_labels)}
<g>{''.join(cells)}</g>
{today}

<g class="a-fade" style="--d:.72s">
  {text(56, 315, "SYNCED DAILY VIA GITHUB ACTIONS", size=8, fill=LIGHT, weight=600, letter_spacing=1.7, opacity=0.72)}
  {text(1144, 315, "MOEENUDDIN01", size=8, fill=LIGHT, weight=600, anchor="end", letter_spacing=1.7, opacity=0.55)}
</g>
"""
    return Card(
        "contributions.svg",
        w,
        h,
        f"{PROFILE['name']} — contribution graph",
        f"{integer(stats['total'])} contributions over {stats['days']} days.",
        1.78,
        body,
    )


# ── README + preview ─────────────────────────────────────────────────────────


def write_readme() -> None:
    tile_links = []
    for tile in TILES:
        tile_links.append(
            f'  <a href="{tile["url"]}"><img src="cards/{tile["file"]}" width="32.5%" alt="{esc(tile["alt"])}"></a>'
        )
    repo_links = []
    for i, repo in enumerate(FEATURED, start=1):
        repo_links.append(
            f'<a href="{repo["url"]}"><img src="cards/repo-{i:02d}-{repo["slug"]}.svg" width="100%" alt="{esc(repo["name"])} — {esc(repo["desc"])}"></a>'
        )

    readme = f"""<!-- Generated by render_cards.py. Edit the script, not this file. -->

<img src="cards/hero.svg" width="100%" alt="{esc(PROFILE['name'])} — applied AI engineer">

<p align="center">
{chr(10).join(tile_links)}
</p>

<img src="cards/chart.svg" width="100%" alt="Contributions by month, with streak, active days and busiest day">

<img src="cards/contributions.svg" width="100%" alt="{esc(PROFILE['name'])}'s contribution graph">

{chr(10).join(repo_links)}

<p align="center"><sub>More experiments at <a href="{PROFILE['github']}">github.com/{PROFILE['login']}</a></sub></p>
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")


def write_preview() -> None:
    tiles = "\n".join(
        f'<a href="{tile["url"]}"><img src="cards/{tile["file"]}" alt="{esc(tile["alt"])}"></a>'
        for tile in TILES
    )
    repos = "\n".join(
        f'<a href="{repo["url"]}"><img src="cards/repo-{i:02d}-{repo["slug"]}.svg" alt="{esc(repo["name"])}"></a>'
        for i, repo in enumerate(FEATURED, start=1)
    )
    preview = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Profile card preview</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    padding: 26px 24px 40px;
    background: #e7f0e9;
    display: flex;
    justify-content: center;
  }}
  main {{ width: 1200px; max-width: 100%; }}
  img {{ display: block; width: 100%; height: auto; }}
  .tiles {{ display: flex; gap: 0.8%; }}
  .tiles a {{ display: block; width: 32.5%; }}
  .repo {{ margin-top: 0; }}
  footer {{
    margin-top: 14px;
    text-align: center;
    font: 500 12px/1.5 system-ui, sans-serif;
    color: #4a6355;
  }}
  footer a {{ color: #2d6a4f; }}
  @media (max-width: 700px) {{
    body {{ padding: 10px; }}
    .tiles {{ gap: 0.8%; }}
  }}
</style>
</head>
<body>
<main>
  <img src="cards/hero.svg" alt="{esc(PROFILE['name'])} — applied AI engineer">
  <div class="tiles">
    {tiles}
  </div>
  <img src="cards/chart.svg" alt="Contributions by month">
  <img src="cards/contributions.svg" alt="Contribution graph">
  {repos}
  <footer>More experiments at <a href="{PROFILE['github']}">github.com/{PROFILE['login']}</a></footer>
</main>
</body>
</html>
"""
    (ROOT / "preview.html").write_text(preview, encoding="utf-8")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    data = load_data()
    stats = compute_stats(data["days"])
    portrait = read_portrait()

    cards: list[Card] = [hero_card(stats, portrait)]
    cards.extend(tile_card(tile, i) for i, tile in enumerate(TILES, start=1))
    cards.append(chart_card(stats))
    cards.extend(repo_card(repo, i) for i, repo in enumerate(FEATURED, start=1))
    cards.append(graph_card(data, stats))

    print(f"Rendering {len(cards)} cards{' (STATIC final frame)' if STATIC else ''}")
    print(f"  data  {integer(stats['total'])} contributions · {stats['active']} active · "
          f"{stats['longest']}-day best streak · {stats['current']}-day current streak")

    faces = build_font_faces(cards)

    CARDS.mkdir(exist_ok=True)
    for old in CARDS.glob("repo-*.svg"):
        old.unlink()

    total_bytes = 0
    for card in cards:
        svg = assemble(card, faces)
        (CARDS / card.filename).write_text(svg, encoding="utf-8")
        size = len(svg.encode("utf-8"))
        total_bytes += size
        print(f"  card  {card.filename:28} {size / 1024:6.1f} kB")

    write_readme()
    write_preview()
    print(f"  total {total_bytes / 1024:.1f} kB · README.md + preview.html written")

    if STATIC:
        print(
            "\nSTATIC=1: cards contain no animation. Screenshot preview.html now;\n"
            "run `python render_cards.py` again before committing to restore motion."
        )


if __name__ == "__main__":
    main()
