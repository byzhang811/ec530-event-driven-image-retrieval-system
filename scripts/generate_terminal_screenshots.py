#!/usr/bin/env python3
"""Render terminal log files as screenshot-style PNG images."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "artifacts" / "logs"
OUT_DIR = ROOT / "artifacts" / "screenshots"

BG = (17, 24, 39)
FG = (226, 232, 240)
DIM = (148, 163, 184)
ACCENT_RED = (251, 113, 133)
ACCENT_YELLOW = (250, 204, 21)
ACCENT_GREEN = (74, 222, 128)


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/Library/Fonts/Menlo.ttc",
    ]
    for path in candidates:
        p = Path(path)
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def color_for_line(line: str) -> tuple[int, int, int]:
    stripped = line.strip()
    if stripped.startswith("$ "):
        return ACCENT_GREEN
    if stripped.startswith("==>"):
        return ACCENT_YELLOW
    if "ERROR" in stripped or "Traceback" in stripped:
        return ACCENT_RED
    if not stripped:
        return DIM
    return FG


def render_log_to_png(log_path: Path, out_path: Path, title: str) -> None:
    font = load_font(24)
    title_font = load_font(30)

    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        lines = ["(empty log)"]

    max_lines = 26
    if len(lines) > max_lines:
        lines = lines[:max_lines] + ["... (truncated for slide screenshot)"]

    line_height = 35
    left_pad = 44
    top_pad = 84
    width = 1700
    height = top_pad + line_height * len(lines) + 60
    height = max(height, 580)

    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((24, 18, width - 24, height - 24), radius=18, outline=(51, 65, 85), width=2)
    draw.text((44, 34), title, font=title_font, fill=FG)
    draw.ellipse((width - 140, 36, width - 124, 52), fill=ACCENT_RED)
    draw.ellipse((width - 112, 36, width - 96, 52), fill=ACCENT_YELLOW)
    draw.ellipse((width - 84, 36, width - 68, 52), fill=ACCENT_GREEN)

    y = top_pad
    for line in lines:
        draw.text((left_pad, y), line, font=font, fill=color_for_line(line))
        y += line_height

    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)


def main() -> None:
    mapping = [
        ("01_redis_status.log", "01_redis_status.png", "Redis Startup / Status"),
        ("02_pytest.log", "02_pytest.png", "Unit Test Result"),
        ("03_demo_memory.log", "03_demo_memory.png", "Demo Run (In-Memory Bus)"),
        ("04_demo_redis.log", "04_demo_redis.png", "Demo Run (Redis Bus)"),
    ]

    for log_name, img_name, title in mapping:
        log_path = LOG_DIR / log_name
        if not log_path.exists():
            continue
        render_log_to_png(log_path, OUT_DIR / img_name, title)
        print(OUT_DIR / img_name)


if __name__ == "__main__":
    main()
