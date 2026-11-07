#!/usr/bin/env python3
"""
export_charmap.py

Exports our Ancient (Polytonic) Greek character map into oot/assets/text/charmap.nes.txt
so that the decomp's msgenc.py compiler automatically encodes UTF-8 Greek strings into
the proper 1-byte game character codes during the build.
"""

import os
from scripts.polytonic_map import generate_default_charmap, BUTTON_MAP, GREEK_HOMOGLYPHS

def export_charmap(filepath: str):
    charmap = generate_default_charmap()

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# Determines how text sequences should be encoded for NES text encoding.\n")
        f.write("# Auto-generated for Polytonic Ancient Greek translation.\n{\n")
        f.write("    '\\n'            : 0x01,\n\n")

        f.write("    # Controller buttons\n")
        for btn, code in BUTTON_MAP.items():
            f.write(f"    {repr(btn):16}: 0x{code:02X},\n")

        f.write("\n    # Greek Homoglyphs (mapped to Latin ASCII codepoints)\n")
        for gk, lat in GREEK_HOMOGLYPHS.items():
            f.write(f"    {repr(gk):16}: 0x{ord(lat):02X}, # -> {lat}\n")

        f.write("\n    # Greek Characters & Custom Symbols (0x41 - 0x9E)\n")
        # Write any mapping where key is not basic ASCII identical to value
        custom_items = sorted(
            [(k, v) for k, v in charmap.items() if (ord(k) != v if len(k) == 1 else True) and k not in BUTTON_MAP and k not in GREEK_HOMOGLYPHS],
            key=lambda x: x[1]
        )
        for char, code in custom_items:
            f.write(f"    {repr(char):16}: 0x{code:02X},\n")

        f.write("}\n")

    print(f"[+] Successfully exported {len(charmap)} mappings to {filepath}")

if __name__ == "__main__":
    target = os.path.join("oot", "assets", "text", "charmap.nes.txt")
    export_charmap(target)
