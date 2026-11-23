"""Generate the 1280x640 GitHub social preview image for LoopBridge.

Usage:
    python scripts/make_social_preview.py

Writes docs/assets/social-preview.png. Uses Pillow and Windows fonts.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "assets" / "social-preview.png"

FONTS = Path("C:/Windows/Fonts")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS / name
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def main() -> int:
    W, H = 1280, 640
    img = Image.new("RGB", (W, H), "#070a12")
    d = ImageDraw.Draw(img)

    for y in range(H):
        t = y / H
        r = int(7 + (17 - 7) * t)
        g = int(10 + (24 - 10) * t)
        b = int(18 + (39 - 18) * t)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    for x in range(0, W, 40):
        d.line([(x, 0), (x, H)], fill=(24, 32, 48), width=1)
    for y in range(0, H, 40):
        d.line([(0, y), (W, y)], fill=(24, 32, 48), width=1)

    d.rectangle([0, 0, W, 6], fill=(184, 255, 30))

    title_font = font("segoeuib.ttf", 104)
    sub_font = font("segoeui.ttf", 32)
    mono_font = font("consola.ttf", 22)
    mono_bold = font("consolab.ttf", 22)
    small_font = font("consola.ttf", 17)

    d.text((64, 54), "PHNT-011 // RELAY TOOL", font=small_font, fill=(107, 114, 128))
    d.text((60, 92), "LOOPBRIDGE", font=title_font, fill=(184, 255, 30))
    d.text((66, 216), "CHATGPT \u2194 OPENCODE \u2014 AUTOMATED RELAY LOOP",
           font=sub_font, fill=(229, 231, 235))
    d.text((66, 262), "Windows 11 \u00b7 UIA + CDP + CLI drivers \u00b7 watchdog \u00b7 dry-run",
           font=mono_font, fill=(0, 229, 255))

    chips = [
        ("PYTHON 3.10+", (184, 255, 30)),
        ("PYSIDE6", (125, 211, 252)),
        ("UIAUTOMATION", (134, 239, 172)),
        ("CDP", (0, 229, 255)),
        ("MIT", (255, 59, 59)),
    ]
    x = 66
    for label, colour in chips:
        box = d.textbbox((0, 0), label, font=mono_bold)
        w = box[2] - box[0] + 28
        d.rounded_rectangle([x, 322, x + w, 364], radius=8, fill=(13, 18, 32),
                            outline=(38, 48, 65), width=1)
        d.text((x + 14, 331), label, font=mono_bold, fill=colour)
        x += w + 12

    # Relay diagram
    left = (742, 300, 960, 396)
    right = (1002, 300, 1216, 396)
    d.rounded_rectangle(left, radius=12, fill=(13, 18, 32), outline=(37, 99, 235), width=2)
    d.rounded_rectangle(right, radius=12, fill=(13, 18, 32), outline=(22, 163, 74), width=2)
    d.text((left[0] + 20, left[1] + 22), "CHATGPT", font=mono_bold, fill=(147, 197, 253))
    d.text((left[0] + 20, left[1] + 54), "Brave window", font=small_font, fill=(154, 163, 184))
    d.text((right[0] + 20, right[1] + 22), "OPENCODE", font=mono_bold, fill=(134, 239, 172))
    d.text((right[0] + 20, right[1] + 54), "PowerShell", font=small_font, fill=(154, 163, 184))

    d.line([(966, 330), (996, 330)], fill=(184, 255, 30), width=3)
    d.polygon([(996, 330), (986, 324), (986, 336)], fill=(184, 255, 30))
    d.line([(996, 366), (966, 366)], fill=(0, 229, 255), width=3)
    d.polygon([(966, 366), (976, 360), (976, 372)], fill=(0, 229, 255))

    d.text((742, 430), "copy \u2192 paste \u2192 wait \u2192 copy \u2192 paste \u2192 loop",
           font=mono_font, fill=(154, 163, 184))

    d.text((66, 560), "$ python run.py --simulate --count 2",
           font=mono_font, fill=(154, 163, 184))
    d.text((66, 592), "\u2713 loop complete \u00b7 2 iterations \u00b7 0 errors",
           font=mono_font, fill=(134, 239, 172))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
