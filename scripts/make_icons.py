#!/usr/bin/env python3
"""Generate the PWA icons. Requires Pillow (not needed at runtime)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "icons"

BACKGROUND = "#8c2f39"
FOREGROUND = "#fdf6e9"
FONT_CANDIDATES = [
    "/usr/share/fonts/google-noto-vf/NotoSerif[wght].ttf",
    "/usr/share/fonts/liberation-serif-fonts/LiberationSerif-Bold.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            font = ImageFont.truetype(candidate, size)
            try:
                font.set_variation_by_axes([700])
            except (AttributeError, OSError):
                pass
            return font
    return ImageFont.load_default()


def make_icon(size: int) -> Image.Image:
    image = Image.new("RGB", (size, size), BACKGROUND)
    draw = ImageDraw.Draw(image)

    inset = max(2, round(size * 0.06))
    draw.rounded_rectangle(
        (inset, inset, size - inset, size - inset),
        radius=round(size * 0.18),
        outline=FOREGROUND,
        width=max(1, round(size * 0.012)),
    )

    font = load_font(round(size * 0.66))
    draw.text(
        (size / 2, size * 0.47),
        "P",
        font=font,
        fill=FOREGROUND,
        anchor="mm",
    )

    dot = round(size * 0.028)
    draw.ellipse(
        (
            size * 0.63 - dot,
            size * 0.66 - dot,
            size * 0.63 + dot,
            size * 0.66 + dot,
        ),
        fill=FOREGROUND,
    )
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for size, name in [
        (512, "icon-512.png"),
        (192, "icon-192.png"),
        (180, "apple-touch-icon.png"),
        (32, "favicon-32.png"),
    ]:
        make_icon(size).save(OUT / name, optimize=True)
        print(f"wrote {OUT / name}")


if __name__ == "__main__":
    main()
