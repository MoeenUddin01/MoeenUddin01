#!/usr/bin/env python3
"""
Render Moeen Uddin's profile README as a Broadsheet: a stack of printed
sections on warm paper, assembled from SVG cards.

The cards use only things that survive GitHub's <img> sandbox:
  * an inline <style> block with CSS keyframes
  * fonts subset with pyftsubset and embedded as base64 WOFF data URIs
  * no scripts, no external requests, no SMIL

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

# ── Broadsheet palette ───────────────────────────────────────────────────────
PAPER = "#f2ede1"
INK = "#171a14"
MOSS = "#2f4a38"
BODY = "#4a4a3e"
MUTED = "#6b6a5b"
FAINT = "#8a8676"
RULE = "#b9b09a"
RULE_SOFT = "#d8d0bd"
RUST = "#a4492f"

DARK = "#1b2a20"
DARK_RULE = "#33503e"
DARK_MUTED = "#8aa595"
DARK_GREEN = "#95d5b2"
DARK_CELLS = {0: "#23352a", 1: "#33543f", 2: "#477a59", 3: "#6aa87f", 4: "#a8d8b9"}

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
        "tag": "PYTHON · RAG",
        "url": "https://github.com/MoeenUddin01/SpecRAG",
    },
    {
        "slug": "finora",
        "name": "Finora",
        "desc": "Accounting and invoicing for customers, suppliers, products, sales, purchases, taxes and reports.",
        "tag": "FASTAPI · REACT",
        "url": "https://github.com/MoeenUddin01/Finora",
    },
    {
        "slug": "aegisarm",
        "name": "AegisArm",
        "desc": "Closed-loop robotic predictive maintenance with PyTorch LSTMs and PyBullet physics.",
        "tag": "PYTORCH · PYBULLET",
        "url": "https://github.com/MoeenUddin01/AegisArm",
    },
    {
        "slug": "plantdoc",
        "name": "PlantDoc",
        "desc": "Upload a leaf, get an instant diagnosis — EfficientNet-B2 paired with retrieval-augmented generation.",
        "tag": "LIVE · RAG",
        "url": PROFILE["site"],
    },
    {
        "slug": "football",
        "name": "Football prediction",
        "desc": "Elo ratings, leak-free time-series features and XGBoost/Poisson tournament simulation.",
        "tag": "PYTHON · XGBOOST",
        "url": "https://github.com/MoeenUddin01/-Football-Match-Outcome-And-Score-Prediction",
    },
]

INDEX = [
    {
        "eyebrow": "01 / APPLIED AI",
        "title": "Retrieval & agents",
        "sub": "SpecRAG, evaluation, tool use",
        "cta": "VIEW PROJECT",
        "icon": "network",
    },
    {
        "eyebrow": "02 / PRODUCT",
        "title": "Full-stack systems",
        "sub": "FastAPI · React · Frappe",
        "cta": "VIEW PROJECT",
        "icon": "stack",
    },
    {
        "eyebrow": "03 / LIVE",
        "title": "PlantDoc",
        "sub": "Try the diagnosis demo",
        "cta": "LIVE DEMO",
        "icon": "leaf",
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
  <filter id="mono" x="-2%" y="-2%" width="104%" height="104%">
    <feColorMatrix type="saturate" values="0"/>
    <feComponentTransfer>
      <feFuncR type="linear" slope="1.06" intercept="-0.03"/>
      <feFuncG type="linear" slope="1.06" intercept="-0.03"/>
      <feFuncB type="linear" slope="1.06" intercept="-0.03"/>
    </feComponentTransfer>
  </filter>
  <pattern id="dots" width="3" height="3" patternUnits="userSpaceOnUse">
    <circle cx="1.5" cy="1.5" r="0.6" fill="{INK}"/>
  </pattern>
  {extra}
</defs>"""


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
    ]
    if anchor != "start":
        bits.append(f'text-anchor="{anchor}"')
    if cls:
        bits.append(f'class="{cls}"')
    if letter_spacing is not None:
        bits.append(f'letter-spacing="{num(letter_spacing)}"')
    if style:
        bits.append(f'style="{style}"')
    if opacity is not None:
        bits.append(f'opacity="{num(opacity)}"')
    return f"<text {' '.join(bits)}>{esc(value)}</text>"


def label(x: float, y: float, value: str, *, fill: str = MUTED, size: float = 7.5,
          weight: int = 600, anchor: str = "start", tracking: float = 1.8,
          cls: str = "", style: str = "") -> str:
    """Small uppercase editorial label."""
    return text(x, y, value.upper(), size=size, fill=fill, weight=weight, anchor=anchor,
                letter_spacing=tracking, cls=cls, style=style)


def rule(x1: float, y1: float, x2: float, y2: float, colour: str = RULE, width: float = 1,
         cls: str = "", style: str = "") -> str:
    bits = [f'x1="{num(x1)}"', f'y1="{num(y1)}"', f'x2="{num(x2)}"', f'y2="{num(y2)}"',
            f'stroke="{colour}"', f'stroke-width="{num(width)}"']
    if cls:
        bits.append(f'class="{cls}"')
    if style:
        bits.append(f'style="{style}"')
    return f"<line {' '.join(bits)}/>"


def arrow_path(cx: float, cy: float, size: float, colour: str, width: float = 1.4) -> str:
    s = size
    return (
        f'<path d="M {num(cx - s * 0.55)} {num(cy)} H {num(cx + s * 0.55)} '
        f'M {num(cx + s * 0.12)} {num(cy - s * 0.42)} L {num(cx + s * 0.55)} {num(cy)} '
        f'L {num(cx + s * 0.12)} {num(cy + s * 0.42)}" fill="none" '
        f'stroke="{colour}" stroke-width="{num(width)}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def external_arrow(cx: float, cy: float, size: float, colour: str, width: float = 1.4) -> str:
    s = size
    return (
        f'<path d="M {num(cx - s * 0.5)} {num(cy + s * 0.5)} L {num(cx + s * 0.5)} {num(cy - s * 0.5)} '
        f'M {num(cx - s * 0.05)} {num(cy - s * 0.5)} H {num(cx + s * 0.5)} V {num(cy + s * 0.05)}" '
        f'fill="none" stroke="{colour}" stroke-width="{num(width)}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def halftone(x: float, y: float, w: float, h: float, asset: tuple[str, str] | None,
             *, opacity: float = 0.34) -> str:
    if not asset:
        return (
            f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="{PAPER}" stroke="{RULE}"/>'
            + text(x + w / 2, y + h / 2 + 24, "MU", size=h * 0.32, fill=MOSS, weight=600,
                   anchor="middle", cls="serif")
        )
    payload, mime = asset
    return (
        f'<image href="data:{mime};base64,{payload}" x="{num(x)}" y="{num(y)}" '
        f'width="{num(w)}" height="{num(h)}" preserveAspectRatio="xMidYMid slice" filter="url(#mono)"/>'
        f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}" fill="url(#dots)" '
        f'opacity="{num(opacity)}"/>'
        f'<rect x="{num(x + 0.5)}" y="{num(y + 0.5)}" width="{num(w - 1)}" height="{num(h - 1)}" '
        f'fill="none" stroke="{RULE}" stroke-width="1"/>'
    )


# ── Motion ───────────────────────────────────────────────────────────────────

BASE_CSS = """
text { font-family: 'DM Sans', Arial, Helvetica, sans-serif; }
.serif { font-family: 'Fraunces', Georgia, 'Times New Roman', serif; }
"""

# Deliberately no SMIL: inside an <img>, SMIL ignores prefers-reduced-motion,
# so it could not satisfy "every animation off". CSS keyframes can be switched
# off by the media query below and by STATIC=1.
MOTION_CSS = """
.a-rise,.a-fade,.a-grow,.a-pop { animation-fill-mode: both; }
.a-rise {
  animation-name: rise; animation-duration: .8s;
  animation-timing-function: cubic-bezier(.20,.80,.24,1);
  animation-delay: calc(var(--base) + var(--d, 0s));
}
.a-fade {
  animation-name: fade; animation-duration: .9s;
  animation-timing-function: ease-out;
  animation-delay: calc(var(--base) + var(--d, 0s));
}
.a-grow {
  animation-name: grow; animation-duration: .8s;
  animation-timing-function: cubic-bezier(.16,.84,.28,1);
  animation-delay: calc(var(--base) + var(--d, 0s));
  transform-box: fill-box; transform-origin: bottom center;
}
.a-pop {
  animation-name: pop; animation-duration: .4s;
  animation-timing-function: cubic-bezier(.20,.90,.30,1.1);
  animation-delay: calc(var(--base) + var(--d, 0s));
  transform-box: fill-box; transform-origin: center;
}
.a-draw {
  animation-name: draw; animation-duration: 1.1s;
  animation-timing-function: cubic-bezier(.30,.80,.30,1);
  animation-delay: calc(var(--base) + var(--d, 0s));
}
@keyframes rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes grow { from { opacity: .3; transform: scaleY(.02); } to { opacity: 1; transform: scaleY(1); } }
@keyframes pop { from { opacity: 0; transform: scale(.2); } to { opacity: 1; transform: scale(1); } }
@keyframes draw { from { opacity: 0; transform: scaleX(.2); } to { opacity: 1; transform: scaleX(1); } }
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


# ── Hero / masthead ──────────────────────────────────────────────────────────


def hero_card(stats: dict, portrait_asset: tuple[str, str] | None) -> Card:
    w, h = 880, 330
    name = PROFILE["name"]
    first, last = name.split(" ", 1)
    total = integer(stats["total"])
    active = integer(stats["active"])

    body = f"""
{make_defs()}
<rect width="{w}" height="{h}" fill="{PAPER}"/>

<g class="a-fade" style="--d:.02s">
  {label(32, 34, "The Profile", fill=BODY, size=8, tracking=2.3)}
  {label(440, 34, "Vol. 01 — November 2026", fill=BODY, size=8, tracking=2.3, anchor="middle")}
  {label(848, 34, "Dhaka, BD", fill=BODY, size=8, tracking=2.3, anchor="end")}
  {rule(32, 44, 848, 44, INK, 2)}
  {rule(32, 48, 848, 48, INK, 1)}
</g>

<g class="a-rise" style="--d:.06s">
  {label(32, 84, "Applied AI Engineer", fill=MOSS, size=8.5, tracking=2.6)}
</g>

<g class="a-rise" style="--d:.12s">
  <text x="31" y="156" class="serif" font-size="76" font-weight="600" fill="{INK}" letter-spacing="-2.2">{esc(first)} <tspan font-style="italic">{esc(last)}</tspan></text>
</g>

<g class="a-rise" style="--d:.20s">
  {text(32, 194, PROFILE["tagline"][0], size=17, fill=BODY, cls="serif")}
  {text(32, 218, PROFILE["tagline"][1], size=17, fill=BODY, cls="serif")}
</g>

<g class="a-fade" style="--d:.30s">
  {rule(32, 242, 480, 242, RULE)}
  {label(32, 262, f"{total} contributions", fill=BODY, size=8, tracking=1.2)}
  {rule(158, 248, 158, 267, RULE)}
  {label(174, 262, f"{active} active days", fill=BODY, size=8, tracking=1.2)}
  {rule(276, 248, 276, 267, RULE)}
  {label(292, 262, f"{stats['longest']}-day streak", fill=BODY, size=8, tracking=1.2)}
</g>

<g class="a-fade" style="--d:.22s">
  {halftone(608, 60, 240, 222, portrait_asset)}
  {label(608, 298, "Fig. 1 — The engineer, 2026", fill=FAINT, size=7.5, tracking=1.7)}
</g>
"""
    return Card(
        "hero.svg",
        w,
        h,
        f"{name} — applied AI engineer",
        "Masthead with name, standfirst, contribution totals and a halftone portrait.",
        0.0,
        body,
    )


# ── Index ────────────────────────────────────────────────────────────────────


def icon(kind: str, x: float, y: float) -> str:
    stroke = MOSS
    if kind == "network":
        return (
            f'<g transform="translate({num(x)} {num(y)})" fill="none" stroke="{stroke}" '
            f'stroke-width="1.1" stroke-linecap="round">'
            '<circle cx="5" cy="4" r="2.4"/><circle cx="21" cy="4" r="2.4"/><circle cx="13" cy="20" r="2.4"/>'
            '<path d="M6.9 6.2 11.6 17.8M19.1 6.2 14.4 17.8M7.4 4h11.2"/></g>'
        )
    if kind == "stack":
        return (
            f'<g transform="translate({num(x)} {num(y)})" fill="none" stroke="{stroke}" '
            f'stroke-width="1.1" stroke-linejoin="round" stroke-linecap="round">'
            '<path d="M13 2 24 8 13 14 2 8 13 2Z"/><path d="M2 14 13 20 24 14M2 19 13 25 24 19"/></g>'
        )
    return (
        f'<g transform="translate({num(x)} {num(y)})" fill="none" stroke="{stroke}" '
        f'stroke-width="1.1" stroke-linejoin="round" stroke-linecap="round">'
        '<path d="M22 3C14 4 7 9 6 18c0 2.6 1.8 4.4 4.4 4.4C18 22 21 13 22 3Z"/>'
        '<path d="M6 25c1.8-7 6-10.6 11.5-13.5"/></g>'
    )


def index_card() -> Card:
    w, h = 880, 176
    col_w = 272
    parts = [f'<rect width="{w}" height="{h}" fill="{PAPER}"/>',
             rule(0, 2, w, 2, INK, 3)]
    for i, item in enumerate(INDEX):
        x = 32 + i * col_w
        tx = x + (20 if i else 0)
        delay = 0.08 + i * 0.10
        parts.append(f'<g class="a-rise" style="--d:{delay:.2f}s">')
        parts.append(label(tx, 36, item["eyebrow"], fill=MUTED, size=7.5, tracking=1.8))
        parts.append(icon(item["icon"], tx, 48))
        parts.append(text(tx, 106, item["title"], size=21, fill=INK, weight=600, cls="serif"))
        parts.append(text(tx, 126, item["sub"], size=10, fill=BODY))
        parts.append(label(tx, 152, item["cta"], fill=MOSS, size=7.5, tracking=1.5))
        parts.append(arrow_path(tx + 8 + len(item["cta"]) * 5.6, 150, 8, MOSS, 1.2))
        parts.append("</g>")
        if i:
            parts.append(rule(x, 18, x, 156, RULE))
    parts.append(rule(0, 174, w, 174, RULE))
    body = "\n".join(parts)
    return Card(
        "index.svg",
        w,
        h,
        "Index — applied AI, product systems and the live demo",
        "Three-column index: retrieval and agents, full-stack systems, and the PlantDoc live demo.",
        0.30,
        body,
    )


# ── Chart ────────────────────────────────────────────────────────────────────


def chart_card(stats: dict) -> Card:
    w, h = 880, 388
    months = list(stats["months"].items())[-13:]
    values = [count for _, count in months]
    peak = max(values) if values else 1
    scale_max = 180 if peak <= 180 else int(math.ceil(peak / 30) * 30)

    left, right = 60, 600
    top, bottom = 168, 330
    plot_h = bottom - top
    slot = (right - left) / len(months)
    bar_w = 20
    avg = sum(values) / len(values) if values else 0
    current_key = months[-1][0] if months else ""

    grid = []
    for tick in range(0, scale_max + 1, 60):
        y = bottom - tick / scale_max * plot_h
        grid.append(rule(left, y, right, y, RULE, 1,
                         style="" if tick == 0 else "stroke-dasharray:2 4"))
        grid.append(text(left - 8, y + 2.5, str(tick), size=7, fill=FAINT, anchor="end"))

    avg_y = bottom - avg / scale_max * plot_h
    grid.append(rule(left, avg_y, right, avg_y, RUST, 0.9, style="stroke-dasharray:3 4"))
    grid.append(text(left + 2, avg_y - 5, f"AVG {avg:.0f}", size=7, fill=RUST,
                     weight=600, letter_spacing=0.8))

    bars = []
    for i, (key, count) in enumerate(months):
        x = left + i * slot + (slot - bar_w) / 2
        bar_h = max(1.5, count / scale_max * plot_h)
        y = bottom - bar_h
        fill = INK if key == current_key else MOSS
        delay = 0.20 + i * 0.03
        bars.append(
            f'<rect class="a-grow" style="--d:{delay:.3f}s" x="{num(x)}" y="{num(y)}" '
            f'width="{bar_w}" height="{num(bar_h)}" fill="{fill}"/>'
        )
        if count:
            bars.append(text(x + bar_w / 2, y - 4, str(count), size=7.5, fill=BODY,
                             weight=600, anchor="middle", cls="a-fade",
                             style=f"--d:{delay + 0.22:.3f}s"))
        bars.append(text(x + bar_w / 2, bottom + 16, month_label(key), size=7, fill=MUTED,
                         weight=500, anchor="middle", letter_spacing=0.6, cls="a-fade",
                         style=f"--d:{0.28 + i * 0.03:.3f}s"))
        if key == current_key:
            bars.append(text(x + bar_w / 2, bottom + 29, "MTD", size=5.6, fill=RUST,
                             weight=600, anchor="middle", letter_spacing=0.8, cls="a-fade",
                             style=f"--d:{0.30 + i * 0.03:.3f}s"))

    busiest = stats["busiest"]
    rail = []
    items = [
        ("Best streak", integer(stats["longest"]), f"{stats['current']} days current"),
        ("Active days", integer(stats["active"]), f"{stats['pct']:.0f}% of the year"),
        ("Busiest day", integer(busiest["count"]), long_day(busiest["date"])),
    ]
    for i, (head, value, sub) in enumerate(items):
        y = 168 + i * 72
        rail.append(f'<g class="a-rise" style="--d:{0.34 + i * 0.08:.2f}s">')
        rail.append(label(654, y, head, fill=MUTED, size=7.5, tracking=1.6))
        rail.append(text(654, y + 34, value, size=36, fill=INK, weight=600, cls="serif",
                         letter_spacing=-1))
        rail.append(text(654, y + 52, sub, size=9, fill=BODY))
        rail.append("</g>")
        if i < 2:
            rail.append(rule(654, y + 64, 848, y + 64, RULE_SOFT))

    body = f"""
{make_defs()}
<rect width="{w}" height="{h}" fill="{PAPER}"/>

<g class="a-rise" style="--d:.02s">
  {label(32, 52, "The year in green", fill=MOSS, size=8, tracking=2.4)}
</g>
<g class="a-rise" style="--d:.08s">
  <text x="31" y="96" class="serif" font-size="40" font-weight="600" fill="{INK}" letter-spacing="-1">A year of <tspan font-style="italic">showing up.</tspan></text>
</g>
<g class="a-rise" style="--d:.14s">
  {text(32, 120, f"{integer(stats['total'])} contributions across {integer(stats['active'])} active days.", size=13.5, fill=BODY, cls="serif")}
</g>

{rule(32, 140, 848, 140, RULE)}
{' '.join(grid)}
<g>{''.join(bars)}</g>

{rule(630, 150, 630, 366, RULE)}
{''.join(rail)}
"""
    return Card(
        "chart.svg",
        w,
        h,
        "Contributions by month",
        f"{integer(stats['total'])} contributions by month, with a best streak of "
        f"{stats['longest']} days, {integer(stats['active'])} active days and a busiest "
        f"day of {busiest['count']} on {long_day(busiest['date'])}.",
        0.82,
        body,
    )


# ── Contribution graph (dark plate) ──────────────────────────────────────────


def graph_card(data: dict, stats: dict) -> Card:
    w, h = 880, 264
    days = data["days"]
    first, last = days[0]["date"], days[-1]["date"]
    start = first - timedelta(days=(first.weekday() + 1) % 7)  # back to Sunday
    total_weeks = ((last - start).days + 7) // 7
    weeks = min(total_weeks, 53)

    cell, gap = 10, 4.5
    step = cell + gap
    grid_w = weeks * step - gap
    gx = 32 + (816 - grid_w) / 2
    gy = 100

    cells = []
    for d in days:
        col = (d["date"] - start).days // 7
        if col >= weeks:
            continue
        row = (d["date"].weekday() + 1) % 7
        x, y = gx + col * step, gy + row * step
        level = max(0, min(4, d["level"]))
        delay = 0.12 + col * 0.006 + row * 0.004
        cells.append(
            f'<rect class="a-pop" style="--d:{delay:.3f}s" x="{num(x)}" y="{num(y)}" '
            f'width="{cell}" height="{cell}" fill="{DARK_CELLS[level]}"/>'
        )
        if d["date"] == last:
            cells.append(
                f'<rect x="{num(x)}" y="{num(y)}" width="{cell}" height="{cell}" '
                f'fill="{DARK_CELLS[level]}" stroke="{PAPER}" stroke-width="1"/>'
            )

    month_marks = []
    seen = set()
    prev = None
    for d in days:
        key = (d["date"].year, d["date"].month)
        if key != prev:
            prev = key
            col = (d["date"] - start).days // 7
            if col not in seen and col < weeks:
                seen.add(col)
                month_marks.append(
                    text(gx + col * step, gy - 10, d["date"].strftime("%b").upper(), size=6.5,
                         fill=DARK_MUTED, weight=500, letter_spacing=1, opacity=0.9)
                )

    weekdays = "\n".join(
        text(gx - 7, gy + row * step + 8, name, size=6, fill=DARK_MUTED, weight=500,
             anchor="end", letter_spacing=1, opacity=0.8)
        for row, name in ((1, "MON"), (3, "WED"), (5, "FRI"))
    )

    legend = [label(646, 236, "Less", fill=DARK_MUTED, size=6, tracking=1.6)]
    for i in range(5):
        legend.append(
            f'<rect x="{num(680 + i * 11)}" y="228" width="8" height="8" fill="{DARK_CELLS[i]}"/>'
        )
    legend.append(label(742, 236, "More", fill=DARK_MUTED, size=6, tracking=1.6))

    body = f"""
{make_defs()}
<rect width="{w}" height="{h}" fill="{DARK}"/>

<g class="a-rise" style="--d:.02s">
  {label(32, 42, "The long view", fill=DARK_GREEN, size=7.5, tracking=2.4)}
  {label(848, 42, f"{stats['days']} days · {integer(stats['active'])} active · {stats['longest']}-day best streak", fill=DARK_MUTED, size=8.5, tracking=1.3, anchor="end")}
</g>
<g class="a-rise" style="--d:.08s">
  <text x="31" y="78" class="serif" font-size="34" font-weight="600" fill="{PAPER}" font-style="italic" letter-spacing="-0.6">Every day counts.</text>
</g>

{''.join(month_marks)}
{weekdays}
<g>{''.join(cells)}</g>

<g class="a-fade" style="--d:.60s">
  {rule(32, 214, 848, 214, DARK_RULE)}
  {label(32, 236, "Synced daily via GitHub Actions", fill=DARK_MUTED, size=7, tracking=1.6)}
</g>
{''.join(legend)}
"""
    return Card(
        "contributions.svg",
        w,
        h,
        f"{PROFILE['name']} — contribution graph",
        f"{integer(stats['total'])} contributions over {stats['days']} days, "
        f"{integer(stats['active'])} active days and a {stats['longest']}-day best streak.",
        1.60,
        body,
    )


# ── Selected work ────────────────────────────────────────────────────────────


def repos_head_card() -> Card:
    w, h = 880, 64
    body = f"""
<rect width="{w}" height="{h}" fill="{PAPER}"/>
<g class="a-fade" style="--d:.02s">
  {label(32, 28, "Selected work", fill=MOSS, size=8, tracking=2.2)}
  {label(848, 28, "Five entries", fill=FAINT, size=8, tracking=2.2, anchor="end")}
  {rule(32, 40, 848, 40, INK, 2)}
</g>
"""
    return Card(
        "repos-head.svg", w, h,
        "Selected work",
        "Section heading for five featured repositories.",
        1.90, body,
    )


def repo_card(repo: dict, index: int) -> Card:
    w, h = 880, 88
    body = f"""
<rect width="{w}" height="{h}" fill="{PAPER}"/>
<g class="a-rise" style="--d:.04s">
  {text(32, 54, f"{index:02d}", size=26, fill="#a8a18c", weight=600, cls="serif")}
  {text(82, 38, repo["name"], size=22, fill=INK, weight=600, cls="serif")}
  {text(82, 58, repo["desc"], size=10.5, fill=BODY)}
  {label(772, 50, repo["tag"], fill=MOSS, size=7.5, tracking=1.3, anchor="end")}
  {external_arrow(836, 46, 10, INK, 1.3)}
  {rule(32, 87, 848, 87, RULE_SOFT)}
</g>
"""
    return Card(
        f"repo-{index:02d}-{repo['slug']}.svg", w, h,
        f"{repo['name']} — featured project",
        repo["desc"],
        2.02 + index * 0.08,
        body,
    )


def footer_card(stats: dict) -> Card:
    w, h = 880, 84
    body = f"""
<rect width="{w}" height="{h}" fill="{PAPER}"/>
<g class="a-fade" style="--d:.02s">
  {rule(32, 6, 848, 6, INK, 2)}
  {label(32, 32, f"More experiments at github.com/{PROFILE['login']}", fill=MOSS, size=8, tracking=1.6)}
  {external_arrow(842, 27, 9, MOSS, 1.2)}
  {label(32, 58, "Set in Fraunces & DM Sans · Dhaka · 2026", fill=FAINT, size=7, tracking=1.4)}
  {label(848, 58, f"Updated daily · {integer(stats['total'])} contributions", fill=FAINT, size=7, tracking=1.4, anchor="end")}
  {rule(32, 72, 848, 72, INK, 2)}
</g>
"""
    return Card(
        "footer.svg", w, h,
        "Colophon",
        "Footer with archive link and colophon.",
        2.60, body,
    )


# ── README + preview ─────────────────────────────────────────────────────────


def readme_alt(card: Card) -> str:
    return card.desc


def write_readme(cards: list[Card]) -> None:
    rows = []
    repo_index = 0
    for card in cards:
        src = f'cards/{card.filename}'
        alt = esc(readme_alt(card))
        if card.filename.startswith("repo-"):
            url = FEATURED[repo_index]["url"]
            repo_index += 1
            rows.append(
                f'<a href="{url}"><img src="{src}" width="100%" align="left" alt="{alt}"></a>'
            )
        else:
            rows.append(f'<img src="{src}" width="100%" align="left" alt="{alt}">')

    readme = (
        "<!-- Generated by render_cards.py. Edit the script, not this file. -->\n\n"
        "<div>\n"
        + "\n".join(rows)
        + "\n<br clear=\"all\">\n</div>\n"
    )
    (ROOT / "README.md").write_text(readme, encoding="utf-8")


def write_preview(cards: list[Card]) -> None:
    imgs = "\n".join(
        f'  <img src="cards/{card.filename}" alt="{esc(card.desc)}">' for card in cards
    )
    preview = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light">
<title>Broadsheet — profile preview</title>
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  html {{ background: #0d1117; }}
  body {{
    margin: 0;
    padding: 40px 20px 60px;
    background: #0d1117;
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  main {{ width: 880px; max-width: 100%; box-shadow: 0 34px 90px -34px #000; }}
  img {{ display: block; width: 100%; height: auto; }}
  footer {{
    width: 880px;
    max-width: 100%;
    margin: 14px auto 0;
    display: flex;
    justify-content: space-between;
    font: 500 9px/1.5 system-ui, sans-serif;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: #6e7681;
  }}
  footer a {{ color: #8aa595; text-decoration: none; }}
</style>
</head>
<body>
<main>
{imgs}
</main>
<footer>
  <span>Local preview — Broadsheet</span>
  <a href="{PROFILE['github']}">github.com/{PROFILE['login']}</a>
</footer>
</body>
</html>
"""
    (ROOT / "preview.html").write_text(preview, encoding="utf-8")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    data = load_data()
    stats = compute_stats(data["days"])
    portrait = read_portrait()

    cards: list[Card] = [
        hero_card(stats, portrait),
        index_card(),
        chart_card(stats),
        graph_card(data, stats),
        repos_head_card(),
    ]
    cards.extend(repo_card(repo, i) for i, repo in enumerate(FEATURED, start=1))
    cards.append(footer_card(stats))

    print(f"Rendering {len(cards)} cards{' (STATIC final frame)' if STATIC else ''}")
    print(f"  data  {integer(stats['total'])} contributions · {stats['active']} active · "
          f"{stats['longest']}-day best streak · {stats['current']}-day current streak")

    faces = build_font_faces(cards)

    CARDS.mkdir(exist_ok=True)
    for old in CARDS.glob("*.svg"):
        old.unlink()

    total_bytes = 0
    for card in cards:
        svg = assemble(card, faces)
        (CARDS / card.filename).write_text(svg, encoding="utf-8")
        size = len(svg.encode("utf-8"))
        total_bytes += size
        print(f"  card  {card.filename:28} {size / 1024:6.1f} kB")

    write_readme(cards)
    write_preview(cards)
    print(f"  total {total_bytes / 1024:.1f} kB · README.md + preview.html written")

    if STATIC:
        print(
            "\nSTATIC=1: cards contain no animation. Screenshot preview.html now;\n"
            "run `python3 render_cards.py` again before committing to restore motion."
        )


if __name__ == "__main__":
    main()
