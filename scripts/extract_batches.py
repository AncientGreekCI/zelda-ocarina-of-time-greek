#!/usr/bin/env python3
"""
extract_batches.py

Extracts all 2,075 messages from oot/extracted/ntsc-1.2/text_en_orig/message_data.h
(and message_data_staff.h) into 16 structured JSON batches inside translations/.
Also preserves any already-translated Greek messages from oot/extracted/ntsc-1.2/text/message_data.h.
"""

import os
import re
import json
from typing import Dict, List, Tuple

ORIG_H = os.path.join("oot", "extracted", "ntsc-1.2", "text_en_orig", "message_data.h")
ORIG_STAFF_H = os.path.join("oot", "extracted", "ntsc-1.2", "text_en_orig", "message_data_staff.h")
CURR_H = os.path.join("oot", "extracted", "ntsc-1.2", "text", "message_data.h")
OUT_DIR = "translations"


def parse_message_header(filepath: str, is_staff: bool = False) -> List[Dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split on DEFINE_MESSAGE
    raw_entries = content.split("DEFINE_MESSAGE(")[1:]
    parsed = []

    for raw in raw_entries:
        # Header line: 0xXXXX, TEXTBOX_TYPE_..., TEXTBOX_POS_...,
        first_newline = raw.find("\n")
        header_line = raw[:first_newline].strip()
        parts = [p.strip() for p in header_line.rstrip(",").split(",")]
        msg_id = parts[0]
        box_type = parts[1]
        box_pos = parts[2]

        body = raw[first_newline + 1 :]
        # Find MSG(...) blocks inside body
        # Each MSG( ... ) starts with "MSG(\n" or "MSG(" and ends with "\n)\n" or "/* MISSING */)"
        msg_blocks = []
        pos = 0
        while True:
            idx = body.find("MSG(", pos)
            if idx == -1:
                break
            start_inner = idx + 4
            if body.startswith("/* MISSING */)", start_inner):
                msg_blocks.append("/* MISSING */")
                pos = start_inner + len("/* MISSING */)")
                continue
            # Otherwise find matching "\n)" at start of line
            end_match = re.search(r"\n\)\s*(?:,|\))", body[start_inner:])
            if not end_match:
                break
            inner = body[start_inner : start_inner + end_match.start()].strip()
            msg_blocks.append(inner)
            pos = start_inner + end_match.end() - 1

        if is_staff:
            en_msg = msg_blocks[0] if msg_blocks else ""
            jpn_msg = ""
        else:
            jpn_msg = msg_blocks[0] if len(msg_blocks) > 0 else ""
            en_msg = msg_blocks[1] if len(msg_blocks) > 1 else ""

        parsed.append({
            "id": msg_id,
            "id_int": int(msg_id, 16),
            "box_type": box_type,
            "box_pos": box_pos,
            "jpn_msg": jpn_msg,
            "en_msg": en_msg,
        })

    return parsed


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    orig_msgs = parse_message_header(ORIG_H, is_staff=False)
    curr_msgs = parse_message_header(CURR_H, is_staff=False)
    curr_by_id = {m["id"]: m["en_msg"] for m in curr_msgs}

    # Pilot messages already translated in CURR_H
    pilot_ids = {"0x0310", "0x0312", "0x031F", "0x1095", "0x1096"}

    for m in orig_msgs:
        mid = m["id"]
        if mid in pilot_ids and mid in curr_by_id and curr_by_id[mid] != m["en_msg"]:
            m["el_msg"] = curr_by_id[mid]
        elif m["en_msg"] == "/* MISSING */" or not m["en_msg"].strip():
            m["el_msg"] = m["en_msg"]
        else:
            m["el_msg"] = ""

    # Group by prefix and create the 15 main batches + 1 staff batch
    by_prefix: Dict[str, List[Dict]] = {}
    for m in orig_msgs:
        prefix = m["id"][2:4].upper()
        by_prefix.setdefault(prefix, []).append(m)

    batch_specs = [
        ("batch_01_items_1.json",              by_prefix["00"][:126]),
        ("batch_02_items_2.json",              by_prefix["00"][126:]),
        ("batch_03_navi_bestiary.json",        by_prefix["01"]),
        ("batch_04_doors_signs_songs.json",    by_prefix["02"] + by_prefix["03"]),
        ("batch_05_gossip_hints_masks.json",   by_prefix["04"] + by_prefix["06"] + by_prefix["08"]),
        ("batch_06_kokiri_1.json",             by_prefix["10"][:112]),
        ("batch_07_kokiri_deku_2.json",        by_prefix["10"][112:]),
        ("batch_08_hyrule_ranch_castle.json",  by_prefix["20"]),
        ("batch_09_goron_death_mountain.json", by_prefix["30"]),
        ("batch_10_zora_lake.json",            by_prefix["40"]),
        ("batch_11_kakariko_temple_sheik.json",by_prefix["50"]),
        ("batch_12_gerudo_spirit.json",        by_prefix["60"]),
        ("batch_13_market_npcs_1.json",        by_prefix["70"][:128]),
        ("batch_14_minigames_trade_2.json",    by_prefix["70"][128:]),
        ("batch_15_sages_ganon_ending.json",   by_prefix["71"]),
    ]

    if os.path.exists(ORIG_STAFF_H):
        staff_msgs = parse_message_header(ORIG_STAFF_H, is_staff=True)
        for m in staff_msgs:
            m["el_msg"] = ""
        batch_specs.append(("batch_16_staff_credits.json", staff_msgs))

    total_count = 0
    for filename, items in batch_specs:
        out_path = os.path.join(OUT_DIR, filename)
        clean_items = [
            {
                "id": it["id"],
                "box_type": it["box_type"],
                "box_pos": it["box_pos"],
                "en_msg": it["en_msg"],
                "el_msg": it["el_msg"],
            }
            for it in items
        ]
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(clean_items, f, ensure_ascii=False, indent=2)
        total_count += len(clean_items)
        print(f"[+] Wrote {filename:36s}: {len(clean_items):3d} messages")

    print(f"[+] Total messages extracted across {len(batch_specs)} batches: {total_count}")


if __name__ == "__main__":
    main()
