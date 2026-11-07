#!/usr/bin/env python3
"""
profile_glyphs.py

Utility for scanning translated text files in Polytonic Ancient Greek for the
Zelda 64 (OoT) decompilation project.

Features:
- Scans text files or source message headers.
- Ignores engine control tags, escape codes, and macros (e.g., \\x08, COLOR(...), [A], BOX_BREAK).
- Normalizes unicode to NFC (precomposed polytonic glyphs).
- Gathers glyph frequency statistics and checks capacity against 1-byte limits.
- Generates a z64font-compatible codepoints.txt file:
    Line 1: Sample display text
    Lines 2+: One glyph per line corresponding to font index order.
- Generates a charmap mapping (for oot msgenc.py / charmap.nes.txt).
"""

import os
import sys
import re
import unicodedata
import argparse
from collections import Counter

# Standard ASCII baseline glyphs (0x20 - 0x7E)
ASCII_PRINTABLE = [chr(i) for i in range(0x20, 0x7F)]

# Game engine tags / control sequence regex patterns to exclude from glyph collection
CONTROL_SEQUENCE_PATTERNS = [
    r"\\x[0-9a-fA-F]{2}",                          # Hex escape codes like \x08, \x01
    r"\[(A|B|C|L|R|Z|C-Up|C-Down|C-Left|C-Right|Control-Pad|D-Pad)\]", # Button tags
    r"▼",                                          # Prompt triangle
    r"[A-Z_]+(?:\([^\)]*\))?",                     # C Macros like BOX_BREAK, COLOR(RED), SHIFT(2)
    r"\\[ntr\\'\"]",                               # Standard escape chars
]

COMBINED_CONTROL_REGEX = re.compile("|".join(f"(?:{p})" for p in CONTROL_SEQUENCE_PATTERNS))

def strip_control_sequences(text: str) -> str:
    """Removes engine control macros, escape sequences, and comments."""
    # Strip C/C++ style comments
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    text = re.sub(r"//.*?$", " ", text, flags=re.MULTILINE)
    # Strip control sequences
    clean_text = COMBINED_CONTROL_REGEX.sub(" ", text)
    return clean_text

def is_greek(char: str) -> bool:
    """Check if character belongs to Greek and Coptic or Greek Extended unicode blocks."""
    cp = ord(char)
    # Greek and Coptic: 0x0370 - 0x03FF
    # Greek Extended (Polytonic): 0x1F00 - 0x1FFF
    return (0x0370 <= cp <= 0x03FF) or (0x1F00 <= cp <= 0x1FFF)

def profile_text(text: str, nfc_normalize: bool = True):
    """
    Cleans text, normalizes, and extracts unique characters with frequency count.
    """
    if nfc_normalize:
        text = unicodedata.normalize('NFC', text)

    cleaned = strip_control_sequences(text)
    counter = Counter()

    for ch in cleaned:
        # Ignore newlines, carriage returns, tabs
        if ch in ('\r', '\n', '\t'):
            continue
        counter[ch] += 1

    return counter

def build_codepoints_list(unique_chars: set, base_ascii: bool = True):
    """
    Organizes characters into an ordered list for font generation.
    Preserves printable ASCII at 0x20-0x7E if base_ascii is True,
    and maps Greek/extended glyphs to 0x80+.
    """
    codepoints = []
    seen = set()

    if base_ascii:
        for ch in ASCII_PRINTABLE:
            codepoints.append(ch)
            seen.add(ch)

    # Add remaining characters (polytonic Greek, special punctuation, etc.) sorted
    greek_chars = sorted([c for c in unique_chars if c not in seen and is_greek(c)])
    other_chars = sorted([c for c in unique_chars if c not in seen and not is_greek(c)])

    codepoints.extend(greek_chars)
    codepoints.extend(other_chars)

    return codepoints

def export_z64font_codepoints(filepath: str, codepoints: list, sample_text: str = None):
    """
    Writes z64font-compatible codepoints.txt file.
    Line 1: Sample preview text.
    Line 2+: One character per line.
    """
    if not sample_text:
        sample_text = "Ἐν ἀρχῇ ἦν ὁ Λόγος.\\nΟcarina of Time - Ancient Greek"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(sample_text + "\n")
        for cp in codepoints:
            f.write(cp + "\n")

def export_oot_charmap(filepath: str, codepoints: list, start_offset: int = 0x20):
    """
    Generates a python literal charmap dictionary compatible with tools/msgenc.py.
    """
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# Auto-generated charmap for Ancient Greek OoT translation\n")
        f.write("{\n")
        f.write("    '\\n'            : 0x01,\n\n")
        f.write("    # Controller buttons\n")
        f.write("    '[A]'           : 0x9F,\n")
        f.write("    '[B]'           : 0xA0,\n")
        f.write("    '[C]'           : 0xA1,\n")
        f.write("    '[L]'           : 0xA2,\n")
        f.write("    '[R]'           : 0xA3,\n")
        f.write("    '[Z]'           : 0xA4,\n")
        f.write("    '[C-Up]'        : 0xA5,\n")
        f.write("    '[C-Down]'      : 0xA6,\n")
        f.write("    '[C-Left]'      : 0xA7,\n")
        f.write("    '[C-Right]'     : 0xA8,\n")
        f.write("    '▼'             : 0xA9,\n")
        f.write("    '[Control-Pad]' : 0xAA,\n")
        f.write("    '[D-Pad]'       : 0xAB,\n\n")

        f.write("    # Custom Character Map\n")
        for idx, ch in enumerate(codepoints):
            byte_val = start_offset + idx
            if 0x9F <= byte_val <= 0xAB:
                # Reserved button range if keeping standard layout
                continue
            if byte_val > 0xFF:
                # Beyond 1-byte limit
                break
            # Skip standard ASCII if desired, or map explicitly
            f.write(f"    {repr(ch):16}: 0x{byte_val:02X},\n")
        f.write("}\n")

def main():
    parser = argparse.ArgumentParser(description="Profile Polytonic Greek glyphs and export z64font codepoints.")
    parser.add_argument("-i", "--inputs", nargs="+", help="Input text or source files to profile")
    parser.add_argument("-o", "--output-codepoints", default="codepoints.txt", help="Output path for z64font codepoints file")
    parser.add_argument("-c", "--output-charmap", default=None, help="Optional output path for oot msgenc charmap")
    parser.add_argument("-s", "--sample-text", default=None, help="Sample text for line 1 of z64font file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print verbose statistics")

    args = parser.parse_args()

    full_text = ""
    if args.inputs:
        for inp in args.inputs:
            if os.path.isfile(inp):
                with open(inp, "r", encoding="utf-8", errors="replace") as f:
                    full_text += f.read() + "\n"
            elif os.path.isdir(inp):
                for root, _, files in os.walk(inp):
                    for f in files:
                        if f.endswith((".c", ".h", ".txt", ".json")):
                            with open(os.path.join(root, f), "r", encoding="utf-8", errors="replace") as fp:
                                full_text += fp.read() + "\n"

    counter = profile_text(full_text)
    unique_chars = set(counter.keys())

    codepoints = build_codepoints_list(unique_chars, base_ascii=True)
    export_z64font_codepoints(args.output_codepoints, codepoints, args.sample_text)
    print(f"[+] Exported {len(codepoints)} codepoints to {args.output_codepoints}")

    if args.output_charmap:
        export_oot_charmap(args.output_charmap, codepoints)
        print(f"[+] Exported charmap to {args.output_charmap}")

    greek_count = sum(1 for c in unique_chars if is_greek(c))
    print(f"[i] Profile summary: {len(unique_chars)} unique glyphs scanned ({greek_count} Polytonic/Greek).")
    if len(codepoints) > 224: # rough safe limit for 1-byte encoding minus control bytes
        print(f"[!] WARNING: Total codepoints ({len(codepoints)}) exceeds 1-byte font tile allocation capacity!")

if __name__ == "__main__":
    main()
