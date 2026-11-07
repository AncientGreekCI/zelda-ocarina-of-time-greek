#!/usr/bin/env python3
"""
polytonic_map.py

Complete Polytonic Ancient Greek character map for Ocarina of Time (NTSC 1.2).
Supports 224 glyph tiles (0x20 - 0xFF) in nes_font_static and 224 float widths in sFontWidths:
- 0x20 - 0x40: Digits (0-9), basic punctuation ( ! " ' ( ) , - . / : ; ? ), plus extra polytonic slots in unused ASCII (# $ % & * + < = > @).
- 0x41 - 0x5A: 24 Greek uppercase letters (14 homoglyphs + 10 unique capitals) + 2 polytonic slots (0x52, 0x55).
- 0x5B - 0x7F: 36 Polytonic Greek characters (0x61-0x7A, 0x5B-0x60, 0x7B-0x7F).
- 0x80 - 0x9E: 31 Core Greek characters (α-ω, ·, «, », ά, έ, ή).
- 0x9F - 0xAB: Preserved Nintendo controller button icons ([A], [B], [C], [L], [R], [Z], [C-Up/Down/Left/Right], ▼, [Control-Pad], [D-Pad]).
- 0xAC - 0xFF: 84 Extended Polytonic Greek characters (all remaining breathings, accents, iota subscripts, and accented capitals).
"""

import unicodedata
from typing import Dict, List, Tuple

# Layout metrics
R_TEXT_INIT_XPOS = 65
R_TEXT_MAX_XPOS = 275
MAX_LINE_WIDTH_PX = R_TEXT_MAX_XPOS - R_TEXT_INIT_XPOS  # 210 px
R_TEXT_CHAR_SCALE = 75
MESSAGE_SPACE_WIDTH = 6
MAX_CHARS_PER_LINE = 34

BUTTON_MAP = {
    '[A]':           0x9F,
    '[B]':           0xA0,
    '[C]':           0xA1,
    '[L]':           0xA2,
    '[R]':           0xA3,
    '[Z]':           0xA4,
    '[C-Up]':        0xA5,
    '[C-Down]':      0xA6,
    '[C-Left]':      0xA7,
    '[C-Right]':     0xA8,
    '▼':             0xA9,
    '[Control-Pad]': 0xAA,
    '[D-Pad]':       0xAB,
}

# 14 Greek capital letters identical to Latin uppercase
GREEK_HOMOGLYPHS = {
    'Α': 'A',  # 0x41
    'Β': 'B',  # 0x42
    'Ε': 'E',  # 0x45
    'Ζ': 'Z',  # 0x5A
    'Η': 'H',  # 0x48
    'Ι': 'I',  # 0x49
    'Κ': 'K',  # 0x4B
    'Μ': 'M',  # 0x4D
    'Ν': 'N',  # 0x4E
    'Ο': 'O',  # 0x4F
    'Ρ': 'P',  # 0x50
    'Τ': 'T',  # 0x54
    'Υ': 'Y',  # 0x59
    'Χ': 'X',  # 0x58
}

# 10 Unique Greek capitals mapped to Latin uppercase slots
GREEK_UNIQUE_CAPITALS = {
    'Γ': 0x43, # C
    'Δ': 0x44, # D
    'Φ': 0x46, # F
    'Θ': 0x47, # G
    'Ψ': 0x4A, # J
    'Λ': 0x4C, # L
    'Ω': 0x51, # Q
    'Σ': 0x53, # S
    'Ξ': 0x56, # V
    'Π': 0x57, # W
}

# 26 Polytonic accented vowels and capitals mapped to 0x61 - 0x7A
POLYTONIC_INVENTORY_26 = [
    'ί', # 0x61
    'ό', # 0x62
    'ύ', # 0x63
    'ἀ', # 0x64
    'Ἆ', # 0x65
    'ἐ', # 0x66
    'Ἐ', # 0x67
    'Ἔ', # 0x68
    'Ἡ', # 0x69
    'ἰ', # 0x6A
    'ἶ', # 0x6B
    'Ἴ', # 0x6C
    'Ὁ', # 0x6D
    'ὕ', # 0x6E
    'Ὑ', # 0x6F
    'ὦ', # 0x70
    'ὰ', # 0x71
    'ὴ', # 0x72
    'ὶ', # 0x73
    'ὸ', # 0x74
    'ὼ', # 0x75
    'ᾳ', # 0x76
    'ῆ', # 0x77
    'ῇ', # 0x78
    'ῖ', # 0x79
    'ῥ', # 0x7A
]

# Extra polytonic glyphs in 0x5B - 0x60 & 0x7B - 0x7F & 0x52/0x55 & unused ASCII symbols
POLYTONIC_EXTRA = {
    'ὺ': 0x5B, # [
    'ὲ': 0x5C, # \
    'ὁ': 0x5E, # ^
    'ᾶ': 0x5F, # _
    'ώ': 0x60, # `
    'ῦ': 0x7B, # {
    'ῳ': 0x7C, # |
    'ῶ': 0x7D, # }
    'ῷ': 0x7E, # ~
    'ἁ': 0x7F, # DEL
    'ἑ': 0x52, # R
    'ἡ': 0x55, # U
    # Unused ASCII symbols (0x23-0x26, 0x2A-0x2B, 0x3C-0x3E, 0x40)
    'ἱ': 0x23, # #
    'ὀ': 0x24, # $
    'ὐ': 0x25, # %
    'ὑ': 0x26, # &
    'ὠ': 0x2A, # *
    'ὡ': 0x2B, # +
    'ἠ': 0x3C, # <
    'ἄ': 0x3D, # =
    'ἅ': 0x3E, # >
    'ἔ': 0x40, # @
}

# 31 Core Greek characters in 0x80 - 0x9E
CORE_GREEK_31 = [
    'α', 'β', 'γ', 'δ', 'ε', 'ζ', 'η', 'θ', 'ι', 'κ',
    'λ', 'μ', 'ν', 'ξ', 'ο', 'π', 'ρ', 'σ', 'ς', 'τ',
    'υ', 'φ', 'χ', 'ψ', 'ω',
    '·', # 0x99 ano teleia
    '«', # 0x9A
    '»', # 0x9B
    'ά', # 0x9C
    'έ', # 0x9D
    'ή'  # 0x9E
]

# 84 Extended Polytonic Greek characters in 0xAC - 0xFF
EXTENDED_POLYTONIC_84 = [
    # Breathing + Oxia (remaining 11)
    'ἕ', 'ἤ', 'ἥ', 'ἴ', 'ἵ', 'ὄ', 'ὅ', 'ὔ', 'ὤ', 'ὥ',
    # Breathing + Perispomeni (9)
    'ἆ', 'ἇ', 'ἦ', 'ἧ', 'ἷ', 'ὖ', 'ὗ', 'ὧ',
    # Breathing + Varia (12)
    'ἂ', 'ἃ', 'ἒ', 'ἓ', 'ἢ', 'ἣ', 'ἲ', 'ἳ', 'ὂ', 'ὃ', 'ὢ', 'ὣ',
    # Iota Subscript forms (23)
    'ῃ', 'ᾴ', 'ῄ', 'ῴ', 'ᾷ',
    'ᾀ', 'ᾁ', 'ᾄ', 'ᾅ', 'ᾆ', 'ᾇ',
    'ᾐ', 'ᾑ', 'ᾔ', 'ᾕ', 'ᾖ', 'ᾗ',
    'ᾠ', 'ᾡ', 'ᾤ', 'ᾥ', 'ᾦ', 'ᾧ',
    # Diaeresis (4)
    'ϊ', 'ϋ', 'ΐ', 'ΰ',
    # Capital Vowels with Breathing / Accents (25)
    'Ἀ', 'Ἁ', 'Ἄ', 'Ἅ', 'Ἑ', 'Ἕ',
    'Ἠ', 'Ἤ', 'Ἥ', 'Ἦ',
    'Ἰ', 'Ἱ', 'Ἵ', 'Ἶ',
    'Ὀ', 'Ὄ', 'Ὅ',
    'Ὕ', 'Ὗ',
    'Ὠ', 'Ὡ', 'Ὤ', 'Ὥ', 'Ὦ', 'Ῥ',
]
assert len(EXTENDED_POLYTONIC_84) <= 84, f"Too many extended chars: {len(EXTENDED_POLYTONIC_84)}"

# Rare polytonic fallback normalization table (maps ultra-rare forms to closest visual equivalent)
RARE_FALLBACKS = {
    '\u037E': ';',   # Greek question mark U+037E -> ASCII semicolon
    '\u2019': "'",   # Right single quotation mark -> ASCII apostrophe
    '\u2018': "'",   # Left single quotation mark -> ASCII apostrophe
    '\u02BC': "'",   # Modifier letter apostrophe -> ASCII apostrophe
    '\u1FBF': "'",   # Greek psili -> ASCII apostrophe
    '\u1FBD': "'",   # Greek koronis -> ASCII apostrophe
    '\u2014': "-",   # Em-dash -> hyphen
    '\u2013': "-",   # En-dash -> hyphen
    '\u2026': "...", # Ellipsis
    '\u00A0': " ",   # Non-breaking space
    'é': 'e',        # English loanword accent fallback before translation
    # Ultra-rare iota subscript + varia or capital perispomeni + dasia
    'ᾲ': 'ὰ', 'ῂ': 'ὴ', 'ῲ': 'ὼ',
    'Ά': 'Ἄ', 'Έ': 'Ἔ', 'Ή': 'Ἤ', 'Ί': 'Ἴ', 'Ό': 'Ὄ', 'Ύ': 'Ὕ', 'Ώ': 'Ὤ',
    '\u0386': 'Ἄ', '\u0388': 'Ἔ', '\u0389': 'Ἤ', '\u038A': 'Ἴ', '\u038C': 'Ὄ', '\u038E': 'Ὕ', '\u038F': 'Ὤ',
    'ᾂ': 'ἂ', 'ᾃ': 'ἃ', 'ᾒ': 'ἢ', 'ᾓ': 'ἣ', 'ᾢ': 'ὢ', 'ᾣ': 'ὣ',
    'ὒ': 'ὺ', 'ὓ': 'ὺ', 'ῒ': 'ϊ', 'ῢ': 'ϋ', 'ῧ': 'ῦ', 'ῤ': 'ρ',
    'Ἇ': 'Ἁ', 'Ἧ': 'Ἡ', 'Ἷ': 'Ἱ', 'Ὧ': 'Ὡ',
    'Ἂ': 'Ἀ', 'Ἃ': 'Ἁ', 'Ἒ': 'Ἐ', 'Ἓ': 'Ἑ', 'Ἲ': 'Ἰ', 'Ἳ': 'Ἱ',
    'Ὂ': 'Ὀ', 'Ὃ': 'Ὁ', 'Ὓ': 'Ὑ', 'Ὢ': 'Ὠ', 'Ὣ': 'Ὡ',
    'ᾈ': 'Ἀ', 'ᾉ': 'Ἁ', 'ᾌ': 'Ἄ', 'ᾍ': 'Ἅ', 'ᾎ': 'Ἆ', 'ᾏ': 'Ἁ',
    'ᾘ': 'Ἠ', 'ᾙ': 'Ἡ', 'ᾜ': 'Ἤ', 'ᾝ': 'Ἥ', 'ᾞ': 'Ἦ', 'ᾟ': 'Ἡ',
    'ᾨ': 'Ὠ', 'ᾩ': 'Ὡ', 'ᾬ': 'Ὤ', 'ᾭ': 'Ὥ', 'ᾮ': 'Ὦ', 'ᾯ': 'Ὡ',
    'ᾼ': 'Α', 'ῌ': 'Η', 'ῼ': 'Ω',
    'Ὰ': 'Α', 'Ὲ': 'Ε', 'Ὴ': 'Η', 'Ὶ': 'Ι', 'Ὸ': 'Ο', 'Ὺ': 'Υ', 'Ὼ': 'Ω',
    # Modern Greek monotonic oxia variants (U+1F71 etc.) -> NFC standard
    '\u1F71': '\u03AC', # ά
    '\u1F73': '\u03AD', # έ
    '\u1F75': '\u03AE', # ή
    '\u1F77': '\u03AF', # ί
    '\u1F79': '\u03CC', # ό
    '\u1F7B': '\u03CD', # ύ
    '\u1F7D': '\u03CE', # ώ
    '\u1FBB': '\u0386', # Ά
    '\u1FC9': '\u0388', # Έ
    '\u1FCB': '\u0389', # Ή
    '\u1FDB': '\u038A', # Ί
    '\u1FF9': '\u038C', # Ό
    '\u1FEB': '\u038E', # Ύ
    '\u1FFB': '\u038F', # Ώ
    '\u1FD3': '\u0390', # ΐ
    '\u1FE3': '\u03B0', # ΰ
}


def normalize_greek_text(text: str) -> str:
    """Normalizes Greek text to NFC and replaces typographic variants or ultra-rare forms."""
    text = unicodedata.normalize("NFC", text)
    for k, v in RARE_FALLBACKS.items():
        if k in text:
            text = text.replace(k, unicodedata.normalize("NFC", v))
    return unicodedata.normalize("NFC", text)


def generate_default_charmap() -> Dict[str, int]:
    mapping: Dict[str, int] = {}

    # Standard ASCII (0x20 - 0x40), then overwritten where POLYTONIC_EXTRA uses unused symbols
    for i in range(0x20, 0x41):
        mapping[chr(i)] = i
    mapping[']'] = 0x5D

    # Greek uppercase homoglyphs (mapped to Latin ASCII)
    for gk, lat in GREEK_HOMOGLYPHS.items():
        mapping[unicodedata.normalize('NFC', gk)] = ord(lat)

    # 10 Unique Greek capitals in 0x41 - 0x5A
    for gk, code in GREEK_UNIQUE_CAPITALS.items():
        mapping[unicodedata.normalize('NFC', gk)] = code

    # Polytonic Greek in 0x61 - 0x7A (26 slots)
    for idx, c in enumerate(POLYTONIC_INVENTORY_26):
        mapping[unicodedata.normalize('NFC', c)] = 0x61 + idx

    # Extra polytonic in 0x5B-0x60, 0x7B-0x7F, 0x52, 0x55, and unused ASCII symbols
    for c, code in POLYTONIC_EXTRA.items():
        mapping[unicodedata.normalize('NFC', c)] = code

    # Core Greek in 0x80 - 0x9E (31 slots)
    for idx, c in enumerate(CORE_GREEK_31):
        mapping[unicodedata.normalize('NFC', c)] = 0x80 + idx

    # Buttons (0x9F - 0xAB)
    mapping.update(BUTTON_MAP)

    # Extended Polytonic in 0xAC - 0xFF (up to 84 slots)
    for idx, c in enumerate(EXTENDED_POLYTONIC_84):
        mapping[unicodedata.normalize('NFC', c)] = 0xAC + idx

    return mapping


def main():
    cm = generate_default_charmap()
    print(f"[+] Complete Polytonic Greek charmap initialized with {len(cm)} entries.")
    print(f"[+] Extended polytonic slots used: {len(EXTENDED_POLYTONIC_84)} / 84 (0xAC - 0x{0xAC + len(EXTENDED_POLYTONIC_84) - 1:02X})")


if __name__ == "__main__":
    main()
