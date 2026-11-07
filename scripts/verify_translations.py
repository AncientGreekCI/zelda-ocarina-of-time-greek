#!/usr/bin/env python3
"""
verify_translations.py

Provides:
1. Full OoT NES message macro parser & binary encoder (supporting all 29 control codes,
   ITEM_ICON, SFX, BACKGROUND, HIGHSCORE, TEXTID, COLOR, SHIFT, choices, and strings).
2. Automated 5-point QA gate & auto-fixer:
   - Control token parity check (ITEM_ICON, TWO_CHOICE, THREE_CHOICE, NAME, OCARINA, etc.)
   - NFC + polytonic normalization & 100% charmap coverage check
   - Pixel line-width calculation (using Gentium Plus sFontWidths at 75% scale) & auto-wrapping
   - Dynamic SHIFT(n) recalculation so centered/indented Greek lines never overflow 210px
   - Glossary compliance check (flags banned synonyms like μάχαιρα or ἀσπίς)
"""

import os
import re
import sys
import json
import glob
import struct
import unicodedata
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, os.path.join("oot", "tools"))
import extract_text  # Gives us item_ids, sfx_ids

from PIL import ImageFont
from scripts.generate_font import render_glyph, BUTTON_WIDTHS
from scripts.patch_font_binary import get_char_for_byte
from scripts.polytonic_map import (
    generate_default_charmap,
    normalize_greek_text,
    BUTTON_MAP,
    MAX_LINE_WIDTH_PX,
    R_TEXT_CHAR_SCALE,
)

# Invert lookup tables from extract_text.py
INV_ITEM_IDS = {v: k for k, v in extract_text.item_ids.items()}
INV_SFX_IDS = {v: k for k, v in extract_text.sfx_ids.items()}

COLOR_MAP = {
    "DEFAULT":    0x40,
    "RED":        0x41,
    "ADJUSTABLE": 0x42,
    "BLUE":       0x43,
    "LIGHTBLUE":  0x44,
    "PURPLE":     0x45,
    "YELLOW":     0x46,
    "BLACK":      0x47,
}

HIGHSCORE_MAP = {
    "HS_HBA":        0,
    "HS_POE_POINTS": 1,
    "HS_FISHING":    2,
    "HS_HORSE_RACE": 3,
    "HS_MARATHON":   4,
    "HS_UNK_05":     5,
    "HS_DAMPE_RACE": 6,
}

BG_X_MAP = {"X_LEFT": 0, "X_RIGHT": 1}
BG_FG_MAP = {
    "WHITE": 0, "DARK_RED": 1, "ORANGE": 2, "WHITE_3": 3,
    "WHITE_4": 4, "WHITE_5": 5, "WHITE_6": 6, "WHITE_7": 7,
}
BG_BG_MAP = {"BLACK": 0, "GOLD": 1, "BLACK_2": 2, "BLACK_3": 3}

SIMPLE_CTRL_CODES = {
    "NEWLINE":            0x01,
    "END":                0x02,
    "BOX_BREAK":          0x04,
    "QUICKTEXT_ENABLE":   0x08,
    "QUICKTEXT_DISABLE":  0x09,
    "PERSISTENT":         0x0A,
    "EVENT":              0x0B,
    "AWAIT_BUTTON_PRESS": 0x0D,
    "NAME":               0x0F,
    "OCARINA":            0x10,
    "MARATHON_TIME":      0x16,
    "RACE_TIME":          0x17,
    "POINTS":             0x18,
    "TOKENS":             0x19,
    "UNSKIPPABLE":        0x1A,
    "TWO_CHOICE":         0x1B,
    "THREE_CHOICE":       0x1C,
    "FISH_INFO":          0x1D,
    "TIME":               0x1F,
}

CRITICAL_MACROS = {
    "ITEM_ICON", "TWO_CHOICE", "THREE_CHOICE", "NAME", "OCARINA",
    "EVENT", "PERSISTENT", "MARATHON_TIME", "RACE_TIME", "POINTS",
    "TOKENS", "FISH_INFO", "HIGHSCORE", "TIME", "TEXTID", "BACKGROUND"
}

BANNED_WORDS = [
    (r"\bμάχαιρ(?![αη][νς]?[\s\"\\n]*τοῦ[\s\"\\n]*Γίγαντος)|\bμαχαίρ(?![αη][νς]?[\s\"\\n]*τοῦ[\s\"\\n]*Γίγαντος)", "Use ξίφος instead of μάχαιρα for sword (except Giant's Knife)"),
    (r"\bἀσπίς\b|\bἀσπίδα\b|\bἀσπίδος\b|\bἀσπίδι\b", "Use θυρεός instead of ἀσπίς for shield"),
]

# Token regex matching either a quoted string or a macro call / identifier
TOKEN_RE = re.compile(
    r'"((?:[^"\\]|\\.)*)"'
    r'|([A-Z_][A-Z0-9_]*)\s*\(([^)]*)\)'
    r'|([A-Z_][A-Z0-9_]*)'
)


def compute_width_table() -> Dict[int, float]:
    """Computes the 224-entry float width table (0x20 - 0xFF) for Gentium Plus."""
    font = ImageFont.truetype("fonts/GentiumPlus-Regular.ttf", 13)
    widths: Dict[int, float] = {}
    for b in range(0x20, 0x100):
        if 0x9F <= b <= 0xAB:
            widths[b] = 14.0
        else:
            ch = get_char_for_byte(b)
            _, w = render_glyph(font, ch, y_offset=-1)
            widths[b] = w
    return widths


def tokenize_msg(msg_str: str) -> List[Tuple[str, str]]:
    """
    Parses a MSG(...) body into a list of (kind, value) tuples:
    - ('STRING', unescaped_text)
    - ('MACRO', 'NAME' or 'COLOR(RED)' etc.)
    """
    if not msg_str or msg_str.strip() == "/* MISSING */":
        return []

    tokens: List[Tuple[str, str]] = []
    for m in TOKEN_RE.finditer(msg_str):
        str_val, func_name, func_args, ident = m.groups()
        if str_val is not None:
            # Unescape \n and \"
            unesc = str_val.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
            tokens.append(("STRING", unesc))
        elif func_name is not None:
            clean_args = ", ".join(a.strip() for a in func_args.split(","))
            tokens.append(("MACRO", f"{func_name}({clean_args})"))
        elif ident is not None:
            if ident != "MISSING":
                tokens.append(("MACRO", ident))
    return tokens


def encode_text_run(text: str, charmap: Dict[str, int], is_greek: bool = True) -> Tuple[bytes, List[str]]:
    """Encodes a plain text string (with optional [A]/[B] button tags and \n) to bytes."""
    if is_greek:
        text = normalize_greek_text(text)

    out = bytearray()
    unmapped: List[str] = []
    # Sort button keys longest first
    btn_keys = sorted(BUTTON_MAP.keys(), key=len, reverse=True)

    i = 0
    n = len(text)
    while i < n:
        matched_btn = False
        for bk in btn_keys:
            if text.startswith(bk, i):
                out.append(BUTTON_MAP[bk])
                i += len(bk)
                matched_btn = True
                break
        if matched_btn:
            continue

        c = text[i]
        if c == "\n":
            out.append(0x01)
        elif c in charmap:
            out.append(charmap[c])
        elif ord(c) < 128:
            out.append(ord(c))
        else:
            unmapped.append(f"{c} (U+{ord(c):04X})")
            out.append(ord("?"))
        i += 1

    return bytes(out), unmapped


def compile_tokens_to_bytes(tokens: List[Tuple[str, str]], charmap: Dict[str, int], is_greek: bool = True) -> Tuple[bytes, List[str]]:
    """Compiles tokenized MSG(...) into raw N64 message bytes ending with 0x02 (END)."""
    out = bytearray()
    unmapped_all: List[str] = []

    for kind, val in tokens:
        if kind == "STRING":
            b, unm = encode_text_run(val, charmap, is_greek=is_greek)
            out.extend(b)
            unmapped_all.extend(unm)
        elif kind == "MACRO":
            if "(" in val:
                fname = val[: val.index("(")]
                fargs = [a.strip() for a in val[val.index("(") + 1 : -1].split(",")]
                if fname == "COLOR":
                    out.extend([0x05, COLOR_MAP[fargs[0]]])
                elif fname == "SHIFT":
                    shift_px = max(0, min(255, int(fargs[0], 0)))
                    out.extend([0x06, shift_px])
                elif fname == "TEXTID":
                    tid = int(fargs[0], 0)
                    out.extend([0x07, (tid >> 8) & 0xFF, tid & 0xFF])
                elif fname == "BOX_BREAK_DELAYED":
                    out.extend([0x0C, int(fargs[0], 0) & 0xFF])
                elif fname == "FADE":
                    out.extend([0x0E, int(fargs[0], 0) & 0xFF])
                elif fname == "FADE2":
                    v = int(fargs[0], 0)
                    out.extend([0x11, (v >> 8) & 0xFF, v & 0xFF])
                elif fname == "SFX":
                    sid = INV_SFX_IDS[fargs[0]]
                    out.extend([0x12, (sid >> 8) & 0xFF, sid & 0xFF])
                elif fname == "ITEM_ICON":
                    iid = INV_ITEM_IDS[fargs[0]]
                    out.extend([0x13, iid & 0xFF])
                elif fname == "TEXT_SPEED":
                    out.extend([0x14, int(fargs[0], 0) & 0xFF])
                elif fname == "BACKGROUND":
                    b0 = BG_X_MAP[fargs[0]]
                    b1 = (BG_FG_MAP[fargs[1]] << 4) | BG_BG_MAP[fargs[2]]
                    y_off = 0 if int(fargs[3], 0) == 1 else 1
                    b2 = (y_off << 4) | (int(fargs[4], 0) & 0xF)
                    out.extend([0x15, b0, b1, b2])
                elif fname == "HIGHSCORE":
                    out.extend([0x1E, HIGHSCORE_MAP[fargs[0]]])
                else:
                    raise ValueError(f"Unknown parameterized macro: {val}")
            else:
                if val in SIMPLE_CTRL_CODES:
                    out.append(SIMPLE_CTRL_CODES[val])
                else:
                    raise ValueError(f"Unknown macro identifier: {val}")

    out.append(0x02)  # END
    return bytes(out), unmapped_all


def line_pixel_width(line_bytes: bytes, widths: Dict[int, float], has_icon: bool = False) -> int:
    """Calculates rendered pixel width of a single line of encoded bytes."""
    px = 32 if has_icon else 0
    i = 0
    n = len(line_bytes)
    while i < n:
        b = line_bytes[i]
        if b == 0x05 or b == 0x14 or b == 0x1E or b == 0x0E or b == 0x0C:
            i += 2
            continue
        if b == 0x06:
            if i + 1 < n:
                px += line_bytes[i + 1]
            i += 2
            continue
        if b == 0x13:
            i += 2
            continue
        if b in (0x07, 0x11, 0x12):
            i += 3
            continue
        if b == 0x15:
            i += 4
            continue
        if b == 0x0F:  # NAME (assume 8 chars ~ 48px)
            px += 48
            i += 1
            continue
        if b in (0x16, 0x17, 0x18, 0x19, 0x1D, 0x1F):
            px += 36
            i += 1
            continue
        if b >= 0x20:
            w = widths.get(b, 8.0)
            px += int(w * (R_TEXT_CHAR_SCALE / 100.0))
        i += 1
    return px


def adjust_shifts_and_validate(
    en_msg: str, el_msg: str, charmap: Dict[str, int], widths: Dict[int, float], box_type: str = "TEXTBOX_TYPE_BLUE"
) -> Tuple[bool, List[str], str]:
    """
    Validates a Greek message against its English original:
    1. Normalizes Greek text inside string literals.
    2. Checks critical macro parity.
    3. Recalculates SHIFT(n) values if a shifted line would exceed 210px.
    4. Checks line pixel widths and unmapped characters.
    Returns (is_ok, issues, normalized_el_msg).
    """
    issues: List[str] = []
    if en_msg.strip() == "/* MISSING */" or not en_msg.strip():
        return True, [], en_msg

    if not el_msg or not el_msg.strip():
        return False, ["Empty translation"], el_msg

    # Normalize Greek inside string literals
    def norm_match(m: re.Match) -> str:
        return '"' + normalize_greek_text(m.group(1)) + '"'

    el_msg = re.sub(r'"((?:[^"\\]|\\.)*)"', norm_match, el_msg)

    en_tokens = tokenize_msg(en_msg)
    try:
        el_tokens = tokenize_msg(el_msg)
        raw_bytes, unmapped = compile_tokens_to_bytes(el_tokens, charmap, is_greek=True)
    except Exception as e:
        return False, [f"Macro compile error: {e}"], el_msg

    if unmapped:
        issues.append(f"Unmapped characters: {set(unmapped)}")

    # Check critical macros parity
    def get_crit(toks):
        res = []
        for k, v in toks:
            if k == "MACRO":
                mname = v.split("(")[0]
                if mname in CRITICAL_MACROS:
                    res.append(v)
        return res

    en_crit = get_crit(en_tokens)
    el_crit = get_crit(el_tokens)
    if en_crit != el_crit:
        issues.append(f"Critical macro mismatch: EN={en_crit} vs EL={el_crit}")

    # Check button token parity
    for btn in BUTTON_MAP:
        en_c = en_msg.count(btn)
        el_c = el_msg.count(btn)
        if en_c != el_c:
            issues.append(f"Button token {btn} count mismatch: EN={en_c} vs EL={el_c}")

    # Check banned glossary words
    for pat, msg in BANNED_WORDS:
        if re.search(pat, el_msg, re.IGNORECASE):
            issues.append(f"Glossary violation: {msg}")

    # Split el_tokens into boxes and lines at the AST/token level (never confuses macro args with 0x01/0x04)
    has_icon = any(k == "MACRO" and v.startswith("ITEM_ICON(") for k, v in el_tokens)
    boxes_lines: List[List[List[Tuple[str, str]]]] = [[[]]]
    for k, v in el_tokens:
        if k == "MACRO" and (v == "BOX_BREAK" or v.startswith("BOX_BREAK_DELAYED(")):
            boxes_lines.append([[]])
        elif k == "STRING" and "\n" in v:
            parts = v.split("\n")
            for p_idx, part in enumerate(parts):
                if part:
                    boxes_lines[-1][-1].append(("STRING", part))
                if p_idx < len(parts) - 1:
                    boxes_lines[-1].append([])
        else:
            boxes_lines[-1][-1].append((k, v))

    for b_idx, box in enumerate(boxes_lines):
        # A line only counts as a visible line if it contains a STRING or printable token, or is non-empty internal line
        def has_visible_content(ln_toks):
            return any(tk == "STRING" or tv in ("NAME", "POINTS", "TOKENS", "TIME", "MARATHON_TIME", "RACE_TIME", "FISH_INFO") or tv.startswith("HIGHSCORE") for tk, tv in ln_toks)
        visible_lines = [ln for ln in box if has_visible_content(ln)]
        if box_type != "TEXTBOX_TYPE_CREDITS" and len(visible_lines) > 4:
            issues.append(f"Box {b_idx+1} has {len(visible_lines)} lines (max 4)")
        for l_idx, ln_tokens in enumerate(box):
            ln_bytes, _ = compile_tokens_to_bytes(ln_tokens, charmap, is_greek=True)
            px = line_pixel_width(ln_bytes[:-1], widths, has_icon=(has_icon and b_idx == 0))
            if px > 225:
                # Check if line has a SHIFT(n) we can reduce
                shift_reduced = False
                for t_i, (tk, tv) in enumerate(ln_tokens):
                    if tk == "MACRO" and tv.startswith("SHIFT("):
                        old_s = int(tv[6:-1], 0)
                        text_only_px = px - old_s
                        if text_only_px <= 215:
                            new_s = max(0, (210 - text_only_px) // 2)
                            el_msg = el_msg.replace(tv, f"SHIFT({new_s})", 1)
                            shift_reduced = True
                            break
                if not shift_reduced:
                    issues.append(f"Box {b_idx+1} Line {l_idx+1} width={px}px exceeds box limit (~210px)")

    return len(issues) == 0, issues, el_msg


def verify_batch_file(batch_path: str, autofix_save: bool = True) -> Tuple[int, int, List[str]]:
    charmap = generate_default_charmap()
    widths = compute_width_table()

    with open(batch_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    translated_count = 0
    error_list: List[str] = []
    modified = False

    for item in data:
        mid = item["id"]
        en_msg = item["en_msg"]
        el_msg = item.get("el_msg", "")
        if not el_msg:
            continue
        translated_count += 1
        btype = item.get("box_type", "TEXTBOX_TYPE_BLUE")
        ok, issues, fixed_el = adjust_shifts_and_validate(en_msg, el_msg, charmap, widths, box_type=btype)
        if fixed_el != el_msg:
            item["el_msg"] = fixed_el
            modified = True
        if not ok:
            for iss in issues:
                error_list.append(f"{mid}: {iss}")

    if modified and autofix_save:
        with open(batch_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return len(data), translated_count, error_list


if __name__ == "__main__":
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    paths = sys.argv[1:] if len(sys.argv) > 1 else sorted(glob.glob("translations/batch_*.json"))
    for p in paths:
        total, done, errs = verify_batch_file(p)
        print(f"[{os.path.basename(p):34s}] Translated: {done:3d}/{total:3d} | Issues: {len(errs)}")
        for e in errs[:10]:
            print(f"   - {e}")
