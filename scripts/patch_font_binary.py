#!/usr/bin/env python3
"""
patch_font_binary.py

Generates and patches all 224 16x16 I4 font textures (0x20 - 0xFF, 28,672 bytes)
into the OoT baserom nes_font_static binary:
- 0x20 - 0x9E: ASCII digits/punctuation, Greek capitals, and core + polytonic Greek glyphs
- 0x9F - 0xAA: PRESERVES original Nintendo controller button graphics verbatim!
- 0xAB - 0xFF: Extended Polytonic Greek glyphs (all remaining breathings, accents, iota subscripts, and accented capitals)
"""

import os
from PIL import ImageFont
from scripts.generate_font import render_glyph, image_to_i4_bytes
from scripts.polytonic_map import (
    GREEK_HOMOGLYPHS,
    GREEK_UNIQUE_CAPITALS,
    POLYTONIC_INVENTORY_26,
    POLYTONIC_EXTRA,
    CORE_GREEK_31,
    EXTENDED_POLYTONIC_84,
)

FONT_PATH = "fonts/GentiumPlus-Regular.ttf"
TARGET_BIN = os.path.join("oot", "extracted", "ntsc-1.2", "baserom", "nes_font_static")


def get_char_for_byte(byte_val: int) -> str:
    """Returns the Unicode character rendered at the given 1-byte code (0x20 - 0xFF)."""
    if byte_val == 0x20:
        return " "

    # Check POLYTONIC_EXTRA first (covers 0x5B-0x60, 0x7B-0x7F, 0x52, 0x55, and repurposed ASCII symbols)
    inv_extra = {v: k for k, v in POLYTONIC_EXTRA.items()}
    if byte_val in inv_extra:
        return inv_extra[byte_val]

    # 0x21 - 0x40: Digits & basic punctuation
    if 0x21 <= byte_val <= 0x40:
        return chr(byte_val)

    # 0x41 - 0x5A: Greek capitals
    inv_unique = {v: k for k, v in GREEK_UNIQUE_CAPITALS.items()}
    if byte_val in inv_unique:
        return inv_unique[byte_val]
    inv_homo = {ord(v): k for k, v in GREEK_HOMOGLYPHS.items()}
    if byte_val in inv_homo:
        return inv_homo[byte_val]
    if 0x41 <= byte_val <= 0x5A:
        return chr(byte_val)

    if byte_val == 0x5D:
        return "]"

    # 0x61 - 0x7A: 26 Polytonic inventory
    if 0x61 <= byte_val <= 0x7A:
        return POLYTONIC_INVENTORY_26[byte_val - 0x61]

    # 0x80 - 0x9E: 31 Core Greek
    if 0x80 <= byte_val <= 0x9E:
        return CORE_GREEK_31[byte_val - 0x80]

    # 0xAC - 0xFF: Extended Polytonic
    if 0xAC <= byte_val <= 0xFF:
        idx = byte_val - 0xAC
        if idx < len(EXTENDED_POLYTONIC_84):
            return EXTENDED_POLYTONIC_84[idx]
        return " "

    return " "


def patch_font():
    if not os.path.exists(TARGET_BIN):
        print(f"[-] Target binary not found: {TARGET_BIN}")
        return

    bak_path = TARGET_BIN + ".bak"
    if not os.path.exists(bak_path):
        with open(TARGET_BIN, "rb") as f_in, open(bak_path, "wb") as f_bak:
            f_bak.write(f_in.read())
        print(f"[+] Created backup at {bak_path}")

    with open(bak_path, "rb") as f:
        orig_data = bytearray(f.read())

    # Expand to 224 tiles (0x20 - 0xFF = 28,672 bytes)
    rom_data = bytearray(224 * 128)
    rom_data[: len(orig_data)] = orig_data

    font = ImageFont.truetype(FONT_PATH, 13)

    patched_count = 0
    for byte_val in range(0x20, 0x100):
        # Preserve original Nintendo controller button tiles at 0x9F - 0xAB
        if 0x9F <= byte_val <= 0xAB:
            continue

        tile_idx = byte_val - 0x20
        offset = tile_idx * 128
        ch = get_char_for_byte(byte_val)
        img, _ = render_glyph(font, ch, y_offset=-1)
        rom_data[offset : offset + 128] = image_to_i4_bytes(img)
        patched_count += 1

    with open(TARGET_BIN, "wb") as f_out:
        f_out.write(rom_data)

    print(f"[+] Rendered and patched {patched_count} tiles across 0x20-0x9E & 0xAC-0xFF.")
    print(f"[+] Preserved controller buttons at 0x9F-0xAA.")
    print(f"[+] Written 224-tile nes_font_static ({len(rom_data)} bytes) to {TARGET_BIN}!")


if __name__ == "__main__":
    patch_font()
