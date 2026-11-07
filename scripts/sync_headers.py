#!/usr/bin/env python3
"""
sync_headers.py

Rebuilds oot/extracted/ntsc-1.2/text/message_data.h and message_data_staff.h
from the translated JSON batches in translations/batch_*.json.
"""

import os
import glob
import json
from typing import Dict

ORIG_H = os.path.join("oot", "extracted", "ntsc-1.2", "text_en_orig", "message_data.h")
ORIG_STAFF_H = os.path.join("oot", "extracted", "ntsc-1.2", "text_en_orig", "message_data_staff.h")
OUT_H = os.path.join("oot", "extracted", "ntsc-1.2", "text", "message_data.h")
OUT_STAFF_H = os.path.join("oot", "extracted", "ntsc-1.2", "text", "message_data_staff.h")


def sync_all_headers():
    translations: Dict[str, str] = {}
    staff_translations: Dict[str, str] = {}

    for bf in sorted(glob.glob(os.path.join("translations", "batch_*.json"))):
        with open(bf, "r", encoding="utf-8") as f:
            items = json.load(f)
        is_staff = "staff" in os.path.basename(bf)
        for it in items:
            mid = it["id"]
            el = it.get("el_msg", "").strip()
            if el:
                if is_staff:
                    staff_translations[mid] = el
                else:
                    translations[mid] = el

    # Rebuild message_data.h
    with open(ORIG_H, "r", encoding="utf-8") as f:
        orig_content = f.read()

    parts = orig_content.split("DEFINE_MESSAGE(")
    out_parts = [parts[0]]
    replaced = 0

    for raw in parts[1:]:
        first_nl = raw.find("\n")
        header = raw[:first_nl]
        mid = header.split(",")[0].strip()
        if mid in translations and translations[mid] != "/* MISSING */":
            # Replace the 2nd MSG(...) block (NES)
            # Find 1st MSG( and 2nd MSG(
            m1 = raw.find("MSG(")
            m2 = raw.find("MSG(", m1 + 4)
            if m2 != -1:
                # Find end of 2nd MSG block: "\n)\n,"
                end_m2 = raw.find("\n)\n,", m2)
                if end_m2 != -1:
                    new_raw = raw[: m2 + 4] + "\n" + translations[mid] + raw[end_m2:]
                    out_parts.append(new_raw)
                    replaced += 1
                    continue
        out_parts.append(raw)

    with open(OUT_H, "w", encoding="utf-8") as f:
        f.write("DEFINE_MESSAGE(".join(out_parts))

    print(f"[+] Synced {replaced} translated Greek messages to {OUT_H}")

    # Rebuild message_data_staff.h
    if os.path.exists(ORIG_STAFF_H):
        with open(ORIG_STAFF_H, "r", encoding="utf-8") as f:
            orig_staff_content = f.read()

        s_parts = orig_staff_content.split("DEFINE_MESSAGE(")
        out_s_parts = [s_parts[0]]
        s_replaced = 0

        for raw in s_parts[1:]:
            first_nl = raw.find("\n")
            header = raw[:first_nl]
            mid = header.split(",")[0].strip()
            if mid in staff_translations and staff_translations[mid] != "/* MISSING */":
                m1 = raw.find("MSG(")
                if m1 != -1:
                    end_m1 = raw.rfind("\n)")
                    if end_m1 != -1:
                        new_raw = raw[: m1 + 4] + "\n" + staff_translations[mid] + raw[end_m1:]
                        out_s_parts.append(new_raw)
                        s_replaced += 1
                        continue
            out_s_parts.append(raw)

        with open(OUT_STAFF_H, "w", encoding="utf-8") as f:
            f.write("DEFINE_MESSAGE(".join(out_s_parts))

        print(f"[+] Synced {s_replaced} translated Greek staff messages to {OUT_STAFF_H}")


if __name__ == "__main__":
    sync_all_headers()
