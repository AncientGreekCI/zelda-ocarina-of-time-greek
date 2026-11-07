#!/usr/bin/env python3
"""
generate_font.py

Rasterizes TrueType font (.ttf) files into 16x16 I4 grayscale tiles and
generates character width tables compatible with the Zelda 64 / OoT decompilation.

Features:
- Subpixel/antialiased glyph rasterization into 16x16 cells.
- Configurable font size (scale) and vertical Y-offset to provide headroom
  for stacked polytonic breathing marks and accents.
- Exports individual .i4.png files following OoT decomp conventions.
- Exports font_widths.h array compatible with sFontWidths in z_message.c.
- Exports raw 16x16 I4 binary (.font_static) for traditional binary injection.
"""

import os
import sys
import argparse
import unicodedata
from typing import List, Tuple, Dict
from PIL import Image, ImageFont, ImageDraw

# Standard button widths defined in z64font
BUTTON_WIDTHS = [
    14.0, # 0x9F [A]
    14.0, # 0xA0 [B]
    14.0, # 0xA1 [C]
    14.0, # 0xA2 [L]
    14.0, # 0xA3 [R]
    14.0, # 0xA4 [Z]
    14.0, # 0xA5 [C-Up]
    14.0, # 0xA6 [C-Down]
    14.0, # 0xA7 [C-Left]
    14.0, # 0xA8 [C-Right]
    14.0, # 0xA9 ▼
    14.0, # 0xAA [Control-Pad]
    14.0, # 0xAB [D-Pad]
    14.0, # 0xAC ?
    14.0, # 0xAD ?
    14.0, # 0xAE ?
    14.0, # 0xAF ?
]

def load_decomp_filenames(fn_file: str) -> List[str]:
    """Loads destination PNG filenames from oot_decomp_fn.txt."""
    if not os.path.exists(fn_file):
        return []
    with open(fn_file, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def load_codepoints(codepoint_file: str) -> Tuple[str, List[str]]:
    """
    Loads codepoints.txt.
    Line 1: Sample preview text
    Line 2+: Character glyphs corresponding to 0x20..0x..
    """
    with open(codepoint_file, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\r\n") for line in f]
    sample = lines[0] if lines else ""
    chars = lines[1:] if len(lines) > 1 else []
    return sample, chars

def render_glyph(font: ImageFont.FreeTypeFont, char: str, y_offset: int = 0, x_pad: int = 0) -> Tuple[Image.Image, float]:
    """
    Renders a character inside a 16x16 grayscale image with given y_offset.
    Returns (16x16 PIL Image in 'L' mode, advance width float).
    """
    img = Image.new("L", (16, 16), color=0)
    draw = ImageDraw.Draw(img)

    if char == " " or not char:
        return img, 6.0 + x_pad

    # Calculate bounding box and metrics
    bbox = font.getbbox(char)
    # bbox is (left, top, right, bottom)
    # Gentium ascenders need slight downward placement to fit within 16px tile
    # Center horizontally if needed, or align to 1px left margin
    x_pos = 1
    # Place vertically so that top accents fit inside [0..15]
    y_pos = -bbox[1] + y_offset

    # Clamp top so it doesn't go negative
    if y_pos < 0:
        y_pos = 0

    draw.text((x_pos, y_pos), char, font=font, fill=255)

    # Calculate advance width
    # In Pillow, font.getlength(char) gives advance width
    advance = font.getlength(char)
    width = advance + x_pad
    # Round to 1 decimal place or integer
    return img, round(width, 1)

def image_to_i4_bytes(img: Image.Image) -> bytes:
    """Converts 16x16 grayscale (8-bit) Image to 128 bytes I4 binary."""
    pixels = list(img.getdata())
    i4_bytes = bytearray(128)
    for i in range(0, 256, 2):
        p1 = round((pixels[i] / 255.0) * 15) & 0x0F
        p2 = round((pixels[i + 1] / 255.0) * 15) & 0x0F
        i4_bytes[i // 2] = (p1 << 4) | p2
    return bytes(i4_bytes)

def main():
    parser = argparse.ArgumentParser(description="Rasterize TrueType fonts for OoT decomp.")
    parser.add_argument("--font", required=True, help="Path to TTF font file")
    parser.add_argument("--codepoints", default="z64font/codepoints/oot.txt", help="Path to codepoints file")
    parser.add_argument("--fn-list", default="z64font/codepoints/oot_decomp_fn.txt", help="Decomp PNG filenames list")
    parser.add_argument("--size", type=int, default=13, help="Font point size (recommended: 13-14 for Gentium Plus)")
    parser.add_argument("--y-offset", type=int, default=-1, help="Vertical Y offset for accents headroom")
    parser.add_argument("--x-pad", type=int, default=0, help="Horizontal padding added to width")
    parser.add_argument("--out-dir", default=None, help="Directory to export .i4.png tiles")
    parser.add_argument("--out-widths", default=None, help="Header file to export character widths")
    parser.add_argument("--out-bin", default=None, help="Binary file to export raw font_static")

    args = parser.parse_args()

    if not os.path.isfile(args.font):
        print(f"[-] Font not found: {args.font}")
        sys.exit(1)

    font = ImageFont.truetype(args.font, args.size)
    _, chars = load_codepoints(args.codepoints)
    fn_list = load_decomp_filenames(args.fn_list)

    if args.out_dir:
        os.makedirs(args.out_dir, exist_ok=True)

    widths: List[float] = []
    all_i4_bytes = bytearray()

    print(f"[+] Rasterizing {len(chars)} glyphs using font '{os.path.basename(args.font)}' (size={args.size}, y_offset={args.y_offset})...")

    for idx, char in enumerate(chars):
        char = unicodedata.normalize("NFC", char)
        img, width = render_glyph(font, char, y_offset=args.y_offset, x_pad=args.x_pad)
        widths.append(width)
        all_i4_bytes.extend(image_to_i4_bytes(img))

        if args.out_dir:
            fn = fn_list[idx] if idx < len(fn_list) else f"msg_char_{0x20 + idx:02x}.i4.png"
            out_png = os.path.join(args.out_dir, fn)
            img.save(out_png)

    # Append button widths if required
    # In z64font decomp export, 17 extra widths are appended for buttons 0x9F..0xAF
    # only if not already covered
    if len(widths) < 144:
        for bw in BUTTON_WIDTHS:
            if len(widths) >= 144:
                break
            widths.append(bw)

    if args.out_widths:
        os.makedirs(os.path.dirname(os.path.abspath(args.out_widths)), exist_ok=True)
        with open(args.out_widths, "w", encoding="utf-8") as f:
            f.write("/* Auto-generated font width table for OoT */\n")
            for w in widths:
                f.write(f"    {w:.1f}f,\n")
        print(f"[+] Exported {len(widths)} width entries to {args.out_widths}")

    if args.out_bin:
        with open(args.out_bin, "wb") as f:
            f.write(all_i4_bytes)
        print(f"[+] Exported {len(all_i4_bytes)} bytes binary font to {args.out_bin}")

    print("[+] Done!")

if __name__ == "__main__":
    main()
