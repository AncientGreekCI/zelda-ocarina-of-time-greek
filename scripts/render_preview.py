#!/usr/bin/env python3
"""
render_preview.py

Generates authentic Ocarina of Time dialogue box mockups and font tile sheet
previews for Ancient (Polytonic) Greek using Gentium Plus.
"""

import os
import sys
import unicodedata
from PIL import Image, ImageFont, ImageDraw, ImageFilter

ARTIFACT_DIR = r"C:\Users\User\.gemini\antigravity\brain\2c6249bd-2d9f-49bd-aa56-be71667ca167"
FONT_PATH = "fonts/GentiumPlus-Regular.ttf"

def render_tile(font, char: str, size=13, y_offset=-1) -> Image.Image:
    """Renders single 16x16 I4-style character tile with alpha/intensity."""
    im = Image.new("L", (16, 16), color=0)
    if char == " " or not char:
        return im
    draw = ImageDraw.Draw(im)
    bbox = font.getbbox(char)
    x = 1
    y = -bbox[1] + y_offset
    if y < 0:
        y = 0
    draw.text((x, y), char, font=font, fill=255)
    # Quantize to 4-bit (16 levels) to authentically match I4 texture format
    quantized = im.point(lambda p: round((p / 255.0) * 15) * 17)
    return quantized

def create_dialogue_box(lines, title="Kokiri Forest - Navi", box_type="blue", scale=3):
    """
    Renders an authentic N64 Ocarina of Time style text box.
    Native resolution: 320x240. Text box width: ~260x70.
    Scaled by `scale` for crisp modern display.
    """
    font_13 = ImageFont.truetype(FONT_PATH, 13)
    header_font = ImageFont.truetype(FONT_PATH, 11)

    box_w = 280
    box_h = 76
    canvas = Image.new("RGBA", (box_w + 40, box_h + 50), (20, 24, 33, 255))
    draw = ImageDraw.Draw(canvas)

    # Ambient backdrop gradient / dungeon wall vignette
    bx = 20
    by = 30

    # Draw OoT Textbox Background (curved dark gradient)
    if box_type == "blue":
        bg_col = (12, 18, 42, 225)       # Navi / Kokiri Fairy Blue
        border_col = (140, 180, 245, 230)
        shadow_col = (5, 8, 18, 255)
    elif box_type == "wood":
        bg_col = (46, 26, 14, 230)       # Signpost wood brown
        border_col = (196, 150, 90, 240)
        shadow_col = (15, 8, 4, 255)
    else:
        bg_col = (15, 15, 20, 230)       # Standard black
        border_col = (180, 180, 190, 240)
        shadow_col = (0, 0, 0, 255)

    # Drop shadow
    draw.rounded_rectangle([bx + 3, by + 3, bx + box_w + 3, by + box_h + 3], radius=10, fill=shadow_col)
    # Box fill
    draw.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=10, fill=bg_col)
    # Double layered border
    draw.rounded_rectangle([bx, by, bx + box_w, by + box_h], radius=10, outline=border_col, width=2)
    draw.rounded_rectangle([bx + 3, by + 3, bx + box_w - 3, by + box_h - 3], radius=8, outline=(border_col[0]//2, border_col[1]//2, border_col[2]//2, 180), width=1)

    # Title header
    draw.text((bx + 12, by - 18), title, font=header_font, fill=(180, 200, 225, 255))

    # Render lines inside textbox
    start_x = bx + 16
    start_y = by + 12
    line_spacing = 15

    for line_idx, line in enumerate(lines):
        cur_x = start_x
        y = start_y + (line_idx * line_spacing)
        line = unicodedata.normalize("NFC", line)

        for char in line:
            if char == " ":
                cur_x += 6 # MESSAGE_SPACE_WIDTH
                continue

            tile = render_tile(font_13, char, size=13, y_offset=-1)
            adv = font_13.getlength(char)

            # Convert tile to RGBA with text color
            # OoT NES text is white with subtle dark drop shadow
            tile_shadow = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
            tile_fg = Image.new("RGBA", (16, 16), (0, 0, 0, 0))

            pixels = tile.load()
            for py in range(16):
                for px in range(16):
                    alpha = pixels[px, py]
                    if alpha > 0:
                        tile_shadow.putpixel((px, py), (0, 0, 0, int(alpha * 0.85)))
                        tile_fg.putpixel((px, py), (255, 255, 255, alpha))

            # Paste shadow (1px down-right)
            canvas.alpha_composite(tile_shadow, (int(cur_x) + 1, y + 1))
            # Paste foreground glyph
            canvas.alpha_composite(tile_fg, (int(cur_x), y))

            cur_x += max(int(adv), 4)

    # OoT blinking dialogue arrow at bottom right
    arrow_x = bx + box_w - 20
    arrow_y = by + box_h - 16
    draw.polygon([(arrow_x, arrow_y), (arrow_x + 8, arrow_y), (arrow_x + 4, arrow_y + 6)], fill=(245, 215, 80, 255))

    # Scale up for crisp modern viewing with nearest neighbor
    scaled = canvas.resize((canvas.width * scale, canvas.height * scale), Image.Resampling.NEAREST)
    return scaled

def create_glyph_sheet(sample_chars, scale=4):
    """Generates an inspection grid showing individual 16x16 I4 tiles magnified."""
    font_13 = ImageFont.truetype(FONT_PATH, 13)
    label_font = ImageFont.truetype(FONT_PATH, 9)

    cols = 8
    rows = (len(sample_chars) + cols - 1) // cols
    tile_size = 16
    cell_w = tile_size + 14
    cell_h = tile_size + 20

    sheet_w = cols * cell_w + 20
    sheet_h = rows * cell_h + 30

    img = Image.new("RGBA", (sheet_w, sheet_h), (24, 28, 38, 255))
    draw = ImageDraw.Draw(img)

    draw.text((12, 10), "Gentium Plus 16x16 I4 Polytonic Glyphs (N64 Font Cell)", font=label_font, fill=(180, 200, 230, 255))

    for idx, ch in enumerate(sample_chars):
        r = idx // cols
        c = idx % cols
        x = 10 + c * cell_w
        y = 28 + r * cell_h

        # Cell border
        draw.rectangle([x, y, x + tile_size + 1, y + tile_size + 1], outline=(55, 65, 85, 255), fill=(10, 12, 16, 255))

        # Render tile
        tile = render_tile(font_13, ch, size=13, y_offset=-1)
        tile_rgba = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        pxs = tile.load()
        for py in range(16):
            for px in range(16):
                a = pxs[px, py]
                if a > 0:
                    tile_rgba.putpixel((px, py), (255, 255, 255, a))
        img.alpha_composite(tile_rgba, (x + 1, y + 1))

        # Unicode codepoint / char label below
        cp_label = f"U+{ord(ch):04X}"
        draw.text((x - 1, y + tile_size + 4), cp_label, font=label_font, fill=(130, 150, 180, 255))

    scaled = img.resize((img.width * scale, img.height * scale), Image.Resampling.NEAREST)
    return scaled

def main():
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    # 1. Pilot Dialogue A: Navi Wake-up
    navi_lines = [
        "Χαῖρε, ὦ Λίγκε!",
        "Ἔγειρε! Ὁ μέγας Δένδρος",
        "Δέκου σοὶ λαλεῖν βούλεται."
    ]
    navi_box = create_dialogue_box(navi_lines, title="Kokiri Forest - Navi", box_type="blue", scale=3)
    navi_out = os.path.join(ARTIFACT_DIR, "dialogue_navi_preview.png")
    navi_box.save(navi_out)
    print(f"[+] Saved Navi dialogue preview to {navi_out}")

    # 2. Pilot Dialogue B: Signpost outside Link's House
    sign_lines = [
        "Ἡ τοῦ Λίγκου",
        "οἰκία."
    ]
    sign_box = create_dialogue_box(sign_lines, title="Signpost - Kokiri Forest", box_type="wood", scale=3)
    sign_out = os.path.join(ARTIFACT_DIR, "dialogue_sign_preview.png")
    sign_box.save(sign_out)
    print(f"[+] Saved Signpost dialogue preview to {sign_out}")

    # 3. Pilot Dialogue C: Great Deku Tree's intro
    deku_lines = [
        "Ὦ Λίγκε...",
        "Ἄκουσον τῶν ἐμῶν λόγων!",
        "Ἡ γῆ τῆς Ὑρουλίας κινδυνεύει."
    ]
    deku_box = create_dialogue_box(deku_lines, title="Great Deku Tree", box_type="black", scale=3)
    deku_out = os.path.join(ARTIFACT_DIR, "dialogue_deku_preview.png")
    deku_box.save(deku_out)
    print(f"[+] Saved Deku Tree dialogue preview to {deku_out}")

    # 4. Glyph Sheet Preview: Stacked polytonic diacritics
    glyphs_to_show = [
        "ἆ", "ᾄ", "Ὦ", "ὃ", "ἧ", "ᾷ", "ᾤ", "Ὕ",
        "Ἔ", "Ἕ", "ὦ", "ἵ", "ὕ", "ᾠ", "ᾡ", "ᾧ",
        "Ἀ", "Ἁ", "Ἐ", "Ἑ", "Ἰ", "Ἱ", "Ὀ", "Ὁ",
        "α", "β", "γ", "δ", "ε", "θ", "λ", "ξ"
    ]
    sheet = create_glyph_sheet(glyphs_to_show, scale=3)
    sheet_out = os.path.join(ARTIFACT_DIR, "glyph_sheet_preview.png")
    sheet.save(sheet_out)
    print(f"[+] Saved Glyph sheet preview to {sheet_out}")

if __name__ == "__main__":
    main()
