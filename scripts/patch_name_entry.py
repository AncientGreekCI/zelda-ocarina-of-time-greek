#!/usr/bin/env python3
"""
patch_name_entry.py

Enables Greek character selection in the Ocarina of Time File Select / Name Entry menu:
1. Renders Gentium Plus glyphs for:
   - 24 uppercase Greek letters (Α-Ω) + 2 breathings (ἑ, ἡ) into kanji tiles 156-181
   - 25 lowercase Greek letters (α-ω, including medial σ and final ς) + ano teleia (·) into kanji tiles 182-207
   - Digits 1-9, 0 and punctuation (., -) into kanji tiles
2. Updates `kanji` binary in extracted baserom and injects into target ROM at 0x004DA490.
3. Patches `gCharPageEng` (65 shorts) in extracted ovl_file_choose and target ROM at 0x00BB01C8
   with the Greek alphabetical layout.
4. Patches the lowercase playerName decode instruction in z_message at ROM 0x00B51760:
   addiu $s0, $s0, -0x45 (maps playerName 197..222 directly to 0x80..0x99 in nes_font_static).
"""

import os
import struct
from PIL import Image, ImageDraw, ImageFont
import ipl3checksum

from scripts.generate_font import image_to_i4_bytes

FONT_PATH = "fonts/GentiumPlus-Regular.ttf"
KANJI_BIN = os.path.join("oot", "extracted", "ntsc-1.2", "baserom", "kanji")
OVL_BIN = os.path.join("oot", "extracted", "ntsc-1.2", "baserom", "ovl_file_choose")

OFFSET_KANJI_ROM = 0x004DA490
OFFSET_GCHARPAGEENG_ROM = 0x00BB01C8
OFFSET_OVL_GCHARPAGEENG = 0xEC50 + 0x288  # 0x0000EED8 in ovl_file_choose binary
OFFSET_Z_MSG_LOWER_DECODE_ROM = 0x00B51760

# 65-key Greek Alphabetical Keyboard Layout (5 rows of 13 keys)
# Maps each keyboard slot (0..64) to its corresponding fontBuf index
G_CHAR_PAGE_GREEK = [
    # Row 0: Α, Β, Γ, Δ, Ε, Ζ, Η, Θ, Ι, Κ, Λ, Μ, ἑ
    171, 172, 173, 174, 175, 196, 178, 177, 179, 181, 182, 183, 188,
    # Row 1: Ν, Ξ, Ο, Π, Ρ, Σ, Τ, Υ, Φ, Χ, Ψ, Ω, ἡ
    184, 192, 185, 193, 186, 189, 190, 195, 176, 194, 180, 187, 191,
    # Row 2: α, β, γ, δ, ε, ζ, η, θ, ι, κ, λ, μ, ·
    197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 222,
    # Row 3: ν, ξ, ο, π, ρ, σ, ς, τ, υ, φ, χ, ψ, ω
    209, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221,
    # Row 4: 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, ., -, ' '
    1,   2,   3,   4,   5,   6,   7,   8,   9,   0,   234, 228, 223,
]

# Mapping from kanji tile index to the character to render
KANJI_TILE_GLYPHS = {
    # Uppercase ASCII slots in nes_font_static (0x41..0x5A) -> kanji tiles 156..181
    156: 'Α',  # 0x41 'A' -> fontBuf 171
    157: 'Β',  # 0x42 'B' -> fontBuf 172
    158: 'Γ',  # 0x43 'C' -> fontBuf 173
    159: 'Δ',  # 0x44 'D' -> fontBuf 174
    160: 'Ε',  # 0x45 'E' -> fontBuf 175
    161: 'Φ',  # 0x46 'F' -> fontBuf 176
    162: 'Θ',  # 0x47 'G' -> fontBuf 177
    163: 'Η',  # 0x48 'H' -> fontBuf 178
    164: 'Ι',  # 0x49 'I' -> fontBuf 179
    165: 'Ψ',  # 0x4A 'J' -> fontBuf 180
    166: 'Κ',  # 0x4B 'K' -> fontBuf 181
    167: 'Λ',  # 0x4C 'L' -> fontBuf 182
    168: 'Μ',  # 0x4D 'M' -> fontBuf 183
    169: 'Ν',  # 0x4E 'N' -> fontBuf 184
    170: 'Ο',  # 0x4F 'O' -> fontBuf 185
    171: 'Ρ',  # 0x50 'P' -> fontBuf 186
    172: 'Ω',  # 0x51 'Q' -> fontBuf 187
    173: 'ἑ',  # 0x52 'R' -> fontBuf 188
    174: 'Σ',  # 0x53 'S' -> fontBuf 189
    175: 'Τ',  # 0x54 'T' -> fontBuf 190
    176: 'ἡ',  # 0x55 'U' -> fontBuf 191
    177: 'Ξ',  # 0x56 'V' -> fontBuf 192
    178: 'Π',  # 0x57 'W' -> fontBuf 193
    179: 'Χ',  # 0x58 'X' -> fontBuf 194
    180: 'Υ',  # 0x59 'Y' -> fontBuf 195
    181: 'Ζ',  # 0x5A 'Z' -> fontBuf 196

    # Lowercase Greek letters (α-ω, ·) in nes_font_static (0x80..0x99) -> kanji tiles 182..207
    182: 'α',  # 0x80 -> fontBuf 197
    183: 'β',  # 0x81 -> fontBuf 198
    184: 'γ',  # 0x82 -> fontBuf 199
    185: 'δ',  # 0x83 -> fontBuf 200
    186: 'ε',  # 0x84 -> fontBuf 201
    187: 'ζ',  # 0x85 -> fontBuf 202
    188: 'η',  # 0x86 -> fontBuf 203
    189: 'θ',  # 0x87 -> fontBuf 204
    190: 'ι',  # 0x88 -> fontBuf 205
    191: 'κ',  # 0x89 -> fontBuf 206
    192: 'λ',  # 0x8A -> fontBuf 207
    193: 'μ',  # 0x8B -> fontBuf 208
    194: 'ν',  # 0x8C -> fontBuf 209
    195: 'ξ',  # 0x8D -> fontBuf 210
    196: 'ο',  # 0x8E -> fontBuf 211
    197: 'π',  # 0x8F -> fontBuf 212
    198: 'ρ',  # 0x90 -> fontBuf 213
    199: 'σ',  # 0x91 -> fontBuf 214
    200: 'ς',  # 0x92 -> fontBuf 215
    201: 'τ',  # 0x93 -> fontBuf 216
    202: 'υ',  # 0x94 -> fontBuf 217
    203: 'φ',  # 0x95 -> fontBuf 218
    204: 'χ',  # 0x96 -> fontBuf 219
    205: 'ψ',  # 0x97 -> fontBuf 220
    206: 'ω',  # 0x98 -> fontBuf 221
    207: '·',  # 0x99 -> fontBuf 222

    # Digits and symbols
    147: '1',  # fontBuf 1
    148: '2',  # fontBuf 2
    149: '3',  # fontBuf 3
    150: '4',  # fontBuf 4
    151: '5',  # fontBuf 5
    152: '6',  # fontBuf 6
    153: '7',  # fontBuf 7
    154: '8',  # fontBuf 8
    155: '9',  # fontBuf 9
    146: '0',  # fontBuf 0
    4:   '.',  # fontBuf 234
    60:  '-',  # fontBuf 228
    0:   ' ',  # fontBuf 223
}


def render_kanji_glyph(font: ImageFont.FreeTypeFont, char: str) -> bytes:
    """Renders a single character into a 16x16 I4 texture (128 bytes)."""
    img = Image.new("L", (16, 16), color=0)
    if char != ' ' and char:
        draw = ImageDraw.Draw(img)
        bb = font.getbbox(char)
        w = bb[2] - bb[0]
        # Center horizontally
        x = (16 - w) // 2 - bb[0]
        # Align vertically with consistent baseline
        y = -5
        draw.text((x, y), char, font=font, fill=255)
    return image_to_i4_bytes(img)


def patch_name_entry(rom_path: str = "oot_ancient_greek.z64"):
    """Patches kanji segment, ovl_file_choose, and ROM for Greek name entry."""
    print("=== Patching Greek Name Entry Menu ===")
    font = ImageFont.truetype(FONT_PATH, 14)

    # 1. Update kanji extracted binary
    if os.path.exists(KANJI_BIN):
        with open(KANJI_BIN, "rb") as f:
            kanji_data = bytearray(f.read())
    else:
        kanji_data = bytearray(508672)

    rendered_count = 0
    for tile_idx, char in KANJI_TILE_GLYPHS.items():
        tex_bytes = render_kanji_glyph(font, char)
        offset = tile_idx * 128
        kanji_data[offset : offset + 128] = tex_bytes
        rendered_count += 1

    with open(KANJI_BIN, "wb") as f:
        f.write(kanji_data)
    print(f"[+] Rendered {rendered_count} Greek glyphs into {KANJI_BIN}")

    # 2. Update gCharPageEng in extracted ovl_file_choose
    if os.path.exists(OVL_BIN):
        with open(OVL_BIN, "rb") as f:
            ovl_data = bytearray(f.read())
        packed_table = struct.pack(">65h", *G_CHAR_PAGE_GREEK)
        ovl_data[OFFSET_OVL_GCHARPAGEENG : OFFSET_OVL_GCHARPAGEENG + 130] = packed_table
        with open(OVL_BIN, "wb") as f:
            f.write(ovl_data)
        print(f"[+] Updated gCharPageEng in {OVL_BIN}")

    # 3. Inject directly into playable ROM
    if os.path.exists(rom_path):
        with open(rom_path, "rb") as f:
            rom = bytearray(f.read())

        # Inject patched kanji segment into ROM
        rom[OFFSET_KANJI_ROM : OFFSET_KANJI_ROM + len(kanji_data)] = kanji_data
        print(f"[+] Injected patched kanji segment ({len(kanji_data):,} bytes) at 0x{OFFSET_KANJI_ROM:08X}")

        # Inject gCharPageEng into ovl_file_choose inside ROM
        packed_table = struct.pack(">65h", *G_CHAR_PAGE_GREEK)
        rom[OFFSET_GCHARPAGEENG_ROM : OFFSET_GCHARPAGEENG_ROM + 130] = packed_table
        print(f"[+] Injected Greek gCharPageEng (65 keys) at 0x{OFFSET_GCHARPAGEENG_ROM:08X}")

        # Patch z_message lowercase decode instruction: addiu $s0, $s0, -0x45 (26 10 FF BB)
        # Originally: addiu $s0, $s0, -0x64 (26 10 FF 9C)
        rom[OFFSET_Z_MSG_LOWER_DECODE_ROM : OFFSET_Z_MSG_LOWER_DECODE_ROM + 4] = bytes([0x26, 0x10, 0xFF, 0xBB])
        print(f"[+] Patched z_message lowercase playerName decode at 0x{OFFSET_Z_MSG_LOWER_DECODE_ROM:08X} (addiu $s0, $s0, -0x45)")

        # Recalculate CIC-6105 Checksum
        crc = ipl3checksum.CICKind.CIC_X105.calculateChecksum(bytes(rom))
        rom[0x10:0x18] = struct.pack(">II", crc[0], crc[1])
        print(f"[+] Updated CIC-6105 checksum: CRC1 = 0x{crc[0]:08X}, CRC2 = 0x{crc[1]:08X}")

        with open(rom_path, "wb") as f:
            f.write(rom)
        print(f"[+] SUCCESS: Name entry screen fully updated with Greek characters in {rom_path}")


if __name__ == "__main__":
    patch_name_entry()
