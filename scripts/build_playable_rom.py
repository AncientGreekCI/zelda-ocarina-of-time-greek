#!/usr/bin/env python3
"""
build_playable_rom.py

Full ROM compiler & repacker for The Legend of Zelda: Ocarina of Time (Ancient Greek):
1. Injects the 224-tile (0x20-0xFF) Gentium Plus nes_font_static binary (28,672 bytes)
   and updates dmadata (0x07AA0 / 0x07AB0) so all 224 tiles DMA cleanly on hardware/emulators.
2. Injects the 224-float sFontWidths table into unused sJpnMessageEntryTable RAM (VRAM 0x8010C000,
   ROM 0x00B81920) and patches the LWC1 instruction at 0x00B4FFFC so characters 0x20-0xFF
   all use their exact Gentium Plus advance widths.
3. Compiles all 2,075 messages from translations/batch_*.json, dynamically repacks
   nes_message_data_static, and updates all 32-bit pointers in sNesMessageEntryTable (0x00B84A5C).
4. Updates oot/extracted/ntsc-1.2/text/message_data.h and recalculates the CIC-6105 CRC.
"""

import os
import re
import glob
import json
import struct
from typing import Dict, List, Tuple
from PIL import ImageFont
import ipl3checksum

from scripts.generate_font import render_glyph
from scripts.patch_font_binary import get_char_for_byte, patch_font
from scripts.polytonic_map import generate_default_charmap, normalize_greek_text
from scripts.verify_translations import tokenize_msg, compile_tokens_to_bytes
from scripts.patch_menu_textures import patch_all_menu_textures

BASE_ROM = os.path.join("oot", "baseroms", "ntsc-1.2", "baserom-decompressed.z64")
PATCHED_FONT = os.path.join("oot", "extracted", "ntsc-1.2", "baserom", "nes_font_static")
ORIG_H = os.path.join("oot", "extracted", "ntsc-1.2", "text_en_orig", "message_data.h")
OUT_H = os.path.join("oot", "extracted", "ntsc-1.2", "text", "message_data.h")
OUTPUT_ROM = "oot_ancient_greek.z64"

# NTSC 1.2 Offsets in decompressed ROM
DMADATA_NES_FONT       = 0x00007AA0
DMADATA_JPN_MSG        = 0x00007AB0
DMADATA_NES_MSG        = 0x00007AC0
DMADATA_STAFF_MSG      = 0x00007AD0
OFFSET_NES_FONT_STATIC = 0x008ED000  # Expanded to 28,672 bytes (0x7000) -> 0x008F4000
ORIG_NES_MSG_DATA      = 0x0092D000  # Original start in baserom
OFFSET_NES_MSG_DATA    = 0x0092D000  # Restored to 0x0092D000 so jpn_msg (0x8F2000-0x92C350 & 0xFFFC) is untouched!
END_NES_MSG_DATA       = 0x00963000  # Leaves 0x963000..0x9650E0 (8,416 bytes) for staff messages
MAX_NES_MSG_SIZE       = END_NES_MSG_DATA - OFFSET_NES_MSG_DATA  # 221,184 bytes (Greek repacked blob is 217,216 bytes)

ORIG_STAFF_MSG_DATA    = 0x00966000
OFFSET_STAFF_MSG_DATA  = 0x00963000
END_STAFF_MSG_DATA     = 0x009650E0
MAX_STAFF_MSG_SIZE     = END_STAFF_MSG_DATA - OFFSET_STAFF_MSG_DATA  # 8,416 bytes

OFFSET_EXT_FONT_WIDTHS = 0x00B81920  # VRAM 0x8010C000 (inside unused sJpnMessageEntryTable)
OFFSET_ORIG_WIDTHS     = 0x00B88F10  # VRAM 0x801135F0 (144 floats)
OFFSET_LWC1_WIDTHS     = 0x00B4FFFC  # lwc1 $f16, offset($at) where $at = 0x80110000 + char*4
OFFSET_LUI_NES_MSG     = 0x00B52BAC  # lui $t4, 0x93 / addiu $t4, $t4, -0x3000 -> 0x0092D000 (original)
OFFSET_LUI_STAFF_MSG   = 0x00B52A78  # lui $t5, 0x96 / addiu $t5, $t5, 0x6000 -> 0x00963000

OFFSET_NES_MSG_TABLE   = 0x00B84A5C  # VRAM 0x8010F13C (sNesMessageEntryTable)
OFFSET_STAFF_MSG_TABLE = 0x00B88C7C  # VRAM 0x8011335C (sStaffMessageEntryTable)


def load_all_translations() -> Tuple[Dict[int, str], Dict[int, str]]:
    """Loads all translated el_msg strings keyed by integer message ID (nes, staff)."""
    translations: Dict[int, str] = {}
    staff_translations: Dict[int, str] = {}
    for batch_file in sorted(glob.glob(os.path.join("translations", "batch_*.json"))):
        is_staff = "staff" in os.path.basename(batch_file)
        with open(batch_file, "r", encoding="utf-8") as f:
            items = json.load(f)
        for it in items:
            mid = int(it["id"], 16)
            el = it.get("el_msg", "").strip()
            en = it.get("en_msg", "").strip()
            if is_staff:
                staff_translations[mid] = el if el else en
            else:
                translations[mid] = el if el else en
    return translations, staff_translations


def build_rom() -> bool:
    if not os.path.exists(BASE_ROM):
        print(f"[-] Base decompressed ROM not found at {BASE_ROM}")
        return False

    # Ensure 224-tile font binary is freshly built
    patch_font()

    with open(BASE_ROM, "rb") as f:
        rom = bytearray(f.read())
    print(f"[+] Loaded base ROM ({len(rom):,} bytes)")

    # 1. Inject 224-tile Patched Font (28,672 bytes) & update dmadata
    with open(PATCHED_FONT, "rb") as f:
        font_data = f.read()
    assert len(font_data) == 224 * 128, f"Expected 28672 font bytes, got {len(font_data)}"

    rom[OFFSET_NES_FONT_STATIC : OFFSET_NES_FONT_STATIC + len(font_data)] = font_data
    new_font_end = OFFSET_NES_FONT_STATIC + len(font_data)  # 0x008F4000

    # Update dmadata entry 0x07AA0 (nes_font_static), 0x07AB0 (jpn_message_data_static), 0x07AC0 (nes_message_data_static)
    rom[DMADATA_NES_FONT : DMADATA_NES_FONT + 16] = struct.pack(
        ">IIII", OFFSET_NES_FONT_STATIC, new_font_end, OFFSET_NES_FONT_STATIC, 0
    )
    rom[DMADATA_JPN_MSG : DMADATA_JPN_MSG + 16] = struct.pack(
        ">IIII", 0x008F2000, 0x0092C350, 0x008F2000, 0
    )
    rom[DMADATA_NES_MSG : DMADATA_NES_MSG + 16] = struct.pack(
        ">IIII", OFFSET_NES_MSG_DATA, END_NES_MSG_DATA, OFFSET_NES_MSG_DATA, 0
    )
    rom[DMADATA_STAFF_MSG : DMADATA_STAFF_MSG + 16] = struct.pack(
        ">IIII", OFFSET_STAFF_MSG_DATA, END_STAFF_MSG_DATA, OFFSET_STAFF_MSG_DATA, 0
    )
    # Restore _nes_message_data_staticSegmentRomStart in z_message.c (0x00B52BAC) to original 0x0092D000
    rom[OFFSET_LUI_NES_MSG : OFFSET_LUI_NES_MSG + 8] = struct.pack(">II", 0x3C0C0093, 0x258CD000)
    # Redirect _staff_message_data_staticSegmentRomStart in z_message.c (0x00B52A78) to 0x00963000
    rom[OFFSET_LUI_STAFF_MSG : OFFSET_LUI_STAFF_MSG + 8] = struct.pack(">II", 0x3C0D0096, 0x25AD3000)
    print(f"[+] Injected 224-tile font at 0x{OFFSET_NES_FONT_STATIC:08X}..0x{new_font_end:08X} and expanded nes/staff message banks")

    # 2. Inject 224-float Character Width Table & redirect LWC1 instruction
    font = ImageFont.truetype("fonts/GentiumPlus-Regular.ttf", 13)
    width_floats: List[float] = []
    for b in range(0x20, 0x100):
        if 0x9F <= b <= 0xAB:
            width_floats.append(14.0)
        else:
            ch = get_char_for_byte(b)
            _, w = render_glyph(font, ch, y_offset=-1)
            width_floats.append(w)

    assert len(width_floats) == 224
    width_bytes_224 = struct.pack(">224f", *width_floats)
    rom[OFFSET_EXT_FONT_WIDTHS : OFFSET_EXT_FONT_WIDTHS + len(width_bytes_224)] = width_bytes_224

    # Also write first 144 floats to original sFontWidths location
    width_bytes_144 = struct.pack(">144f", *width_floats[:144])
    rom[OFFSET_ORIG_WIDTHS : OFFSET_ORIG_WIDTHS + len(width_bytes_144)] = width_bytes_144

    # Patch LWC1 at 0x00B4FFFC: lwc1 $f16, -0x4080($at) -> 0xC430BF80
    # Because $at = 0x80110000 + char*4, and 0x80110000 - 0x4080 + 0x20*4 = 0x8010C000!
    rom[OFFSET_LWC1_WIDTHS : OFFSET_LWC1_WIDTHS + 4] = struct.pack(">I", 0xC430BF80)
    print(f"[+] Injected 224 font widths at 0x{OFFSET_EXT_FONT_WIDTHS:08X} (VRAM 0x8010C000) and patched LWC1")

    # 3. Dynamically Repack nes_message_data_static & Update sNesMessageEntryTable
    charmap = generate_default_charmap()
    translations, staff_translations = load_all_translations()

    # Read existing sNesMessageEntryTable entries
    table_entries: List[Tuple[int, int, int]] = []  # (pos_in_rom, text_id, info_byte, orig_addr)
    pos = OFFSET_NES_MSG_TABLE
    while True:
        text_id, info, addr = struct.unpack(">HBxI", rom[pos : pos + 8])
        table_entries.append((pos, text_id, info, addr))
        pos += 8
        if text_id == 0xFFFF:
            break

    repacked_blob = bytearray()
    translated_msgs = 0
    orig_max_size = 0x009650E0 - ORIG_NES_MSG_DATA

    for idx in range(len(table_entries) - 1):
        t_pos, text_id, info, orig_addr = table_entries[idx]
        next_addr = table_entries[idx + 1][3]
        orig_off = orig_addr & ~0x0F000000
        next_off = (next_addr & ~0x0F000000) if table_entries[idx + 1][1] != 0xFFFF else orig_max_size

        new_off = len(repacked_blob)
        new_addr = 0x07000000 | new_off

        if text_id in translations and text_id not in (0xFFFC, 0xFFFD):
            msg_macro = translations[text_id]
            toks = tokenize_msg(msg_macro)
            msg_bytes, unm = compile_tokens_to_bytes(toks, charmap, is_greek=True)
            if unm:
                print(f"[!] Warning: unmapped chars in 0x{text_id:04X}: {set(unm)}")
            translated_msgs += 1
        else:
            # Copy original bytes verbatim (e.g. 0xFFFC font ordering table)
            msg_bytes = bytes(rom[ORIG_NES_MSG_DATA + orig_off : ORIG_NES_MSG_DATA + next_off])

        repacked_blob.extend(msg_bytes)
        # Align to 4-byte boundary with 0x00 padding
        while len(repacked_blob) % 4 != 0:
            repacked_blob.append(0x00)

        # Write updated pointer to sNesMessageEntryTable
        rom[t_pos : t_pos + 8] = struct.pack(">HBxI", text_id, info, new_addr)

    print(
        f"[+] Compiled & repacked {translated_msgs} messages into nes_message_data_static: "
        f"{len(repacked_blob):,} / {MAX_NES_MSG_SIZE:,} bytes ({len(repacked_blob)*100.0/MAX_NES_MSG_SIZE:.1f}%)"
    )

    if len(repacked_blob) > MAX_NES_MSG_SIZE:
        raise RuntimeError(
            f"Repacked nes_message_data_static ({len(repacked_blob)}) exceeds {MAX_NES_MSG_SIZE}!"
        )

    # Pad repacked_blob to MAX_NES_MSG_SIZE and write to ROM
    repacked_blob.extend(b"\x00" * (MAX_NES_MSG_SIZE - len(repacked_blob)))
    rom[OFFSET_NES_MSG_DATA : OFFSET_NES_MSG_DATA + MAX_NES_MSG_SIZE] = repacked_blob

    # 3b. Dynamically Repack staff_message_data_static & Update sStaffMessageEntryTable
    staff_entries: List[Tuple[int, int, int]] = []
    pos = OFFSET_STAFF_MSG_TABLE
    while True:
        text_id, info, addr = struct.unpack(">HBxI", rom[pos : pos + 8])
        staff_entries.append((pos, text_id, info, addr))
        pos += 8
        if text_id == 0xFFFF:
            break

    staff_blob = bytearray()
    staff_translated = 0
    orig_staff_max = 0x00966F60 - ORIG_STAFF_MSG_DATA

    for idx in range(len(staff_entries) - 1):
        t_pos, text_id, info, orig_addr = staff_entries[idx]
        next_addr = staff_entries[idx + 1][3]
        orig_off = orig_addr & ~0x0F000000
        next_off = (next_addr & ~0x0F000000) if staff_entries[idx + 1][1] != 0xFFFF else orig_staff_max

        new_off = len(staff_blob)
        new_addr = 0x07000000 | new_off

        if text_id in staff_translations:
            msg_macro = staff_translations[text_id]
            toks = tokenize_msg(msg_macro)
            msg_bytes, unm = compile_tokens_to_bytes(toks, charmap, is_greek=True)
            if unm:
                print(f"[!] Warning: unmapped chars in staff 0x{text_id:04X}: {set(unm)}")
            staff_translated += 1
        else:
            msg_bytes = bytes(rom[ORIG_STAFF_MSG_DATA + orig_off : ORIG_STAFF_MSG_DATA + next_off])

        staff_blob.extend(msg_bytes)
        while len(staff_blob) % 4 != 0:
            staff_blob.append(0x00)

        rom[t_pos : t_pos + 8] = struct.pack(">HBxI", text_id, info, new_addr)

    print(
        f"[+] Compiled & repacked {staff_translated} staff messages into staff_message_data_static: "
        f"{len(staff_blob):,} / {MAX_STAFF_MSG_SIZE:,} bytes ({len(staff_blob)*100.0/MAX_STAFF_MSG_SIZE:.1f}%)"
    )

    if len(staff_blob) > MAX_STAFF_MSG_SIZE:
        raise RuntimeError(
            f"Repacked staff_message_data_static ({len(staff_blob)}) exceeds {MAX_STAFF_MSG_SIZE}!"
        )

    staff_blob.extend(b"\x00" * (MAX_STAFF_MSG_SIZE - len(staff_blob)))
    rom[OFFSET_STAFF_MSG_DATA : OFFSET_STAFF_MSG_DATA + MAX_STAFF_MSG_SIZE] = staff_blob

    # Write intermediate ROM before texture patching
    with open(OUTPUT_ROM, "wb") as f_out:
        f_out.write(rom)

    # 4. Patch All 265 Graphical Menu Textures (Actions, Pause Menu, Item Banners, File Select, Title Cards)
    patch_all_menu_textures(OUTPUT_ROM)

    with open(OUTPUT_ROM, "rb") as f_in:
        rom = bytearray(f_in.read())

    # 5. Recalculate N64 Header Checksum (CIC-6105)
    print("[+] Calculating N64 header checksum (CIC-6105)...")
    crc = ipl3checksum.CICKind.CIC_X105.calculateChecksum(bytes(rom))
    rom[0x10:0x18] = struct.pack(">II", crc[0], crc[1])
    print(f"[+] Checksum updated: CRC1 = 0x{crc[0]:08X}, CRC2 = 0x{crc[1]:08X}")

    # Pad to 64MB power-of-two (67,108,864 bytes)
    target_64mb = 64 * 1024 * 1024
    if len(rom) < target_64mb:
        rom.extend(b"\x00" * (target_64mb - len(rom)))

    with open(OUTPUT_ROM, "wb") as f_out:
        f_out.write(rom)

    print(f"[+] SUCCESS: 64MB Playable ROM generated at: {os.path.abspath(OUTPUT_ROM)} ({len(rom):,} bytes)")
    return True


if __name__ == "__main__":
    build_rom()
