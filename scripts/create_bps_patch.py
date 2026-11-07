import os
import sys
import zlib
import hashlib

def encode_vli(data):
    out = bytearray()
    while True:
        b = data & 0x7f
        data >>= 7
        if data == 0:
            out.append(b | 0x80)
            break
        out.append(b)
        data -= 1
    return bytes(out)

def decode_vli(stream, offset):
    data = 0
    shift = 1
    while True:
        b = stream[offset]
        offset += 1
        data += (b & 0x7f) * shift
        if b & 0x80:
            break
        shift <<= 7
        data += shift
    return data, offset

def create_bps_patch(source_bytes, target_bytes, metadata=b""):
    """Creates a standard BPS (Beat Patching System) patch."""
    patch = bytearray(b"BPS1")
    patch.extend(encode_vli(len(source_bytes)))
    patch.extend(encode_vli(len(target_bytes)))
    patch.extend(encode_vli(len(metadata)))
    if metadata:
        patch.extend(metadata)

    src_len = len(source_bytes)
    tgt_len = len(target_bytes)
    
    tgt_pos = 0
    src_pos = 0

    while tgt_pos < tgt_len:
        # Check identical run with source
        if tgt_pos < src_len and source_bytes[tgt_pos] == target_bytes[tgt_pos]:
            run_start = tgt_pos
            while tgt_pos < src_len and tgt_pos < tgt_len and source_bytes[tgt_pos] == target_bytes[tgt_pos]:
                tgt_pos += 1
            length = tgt_pos - run_start
            # SourceRead (action 0)
            cmd = ((length - 1) << 2) | 0
            patch.extend(encode_vli(cmd))
            src_pos = tgt_pos
        else:
            # Differing or extra bytes -> TargetRead (action 1)
            diff_start = tgt_pos
            while tgt_pos < tgt_len:
                if tgt_pos < src_len and source_bytes[tgt_pos] == target_bytes[tgt_pos]:
                    # Check if match continues for at least 4 bytes to avoid thrashing
                    ahead = 0
                    while (tgt_pos + ahead < src_len and 
                           tgt_pos + ahead < tgt_len and 
                           source_bytes[tgt_pos + ahead] == target_bytes[tgt_pos + ahead]):
                        ahead += 1
                    if ahead >= 4:
                        break
                tgt_pos += 1
            length = tgt_pos - diff_start
            cmd = ((length - 1) << 2) | 1
            patch.extend(encode_vli(cmd))
            patch.extend(target_bytes[diff_start:tgt_pos])

    # Footer
    src_crc = zlib.crc32(source_bytes) & 0xffffffff
    tgt_crc = zlib.crc32(target_bytes) & 0xffffffff
    patch.extend(src_crc.to_bytes(4, "little"))
    patch.extend(tgt_crc.to_bytes(4, "little"))
    patch_crc = zlib.crc32(patch) & 0xffffffff
    patch.extend(patch_crc.to_bytes(4, "little"))
    return bytes(patch)

def verify_bps_patch(patch_bytes, source_bytes, expected_target):
    """Verifies that patch applies cleanly to source_bytes and matches expected_target."""
    assert patch_bytes[:4] == b"BPS1", "Invalid BPS magic"
    offset = 4
    src_sz, offset = decode_vli(patch_bytes, offset)
    tgt_sz, offset = decode_vli(patch_bytes, offset)
    meta_sz, offset = decode_vli(patch_bytes, offset)
    offset += meta_sz

    target = bytearray()
    src_offset = 0
    tgt_offset = 0

    while offset < len(patch_bytes) - 12:
        cmd, offset = decode_vli(patch_bytes, offset)
        action = cmd & 3
        length = (cmd >> 2) + 1

        if action == 0:  # SourceRead
            target.extend(source_bytes[tgt_offset:tgt_offset + length])
            tgt_offset += length
        elif action == 1:  # TargetRead
            target.extend(patch_bytes[offset:offset + length])
            offset += length
            tgt_offset += length
        else:
            raise NotImplementedError(f"Action {action} not used in linear patch")

    assert len(target) == tgt_sz, f"Target size mismatch: {len(target)} vs {tgt_sz}"
    assert bytes(target) == expected_target, "Target content mismatch!"
    
    src_crc = int.from_bytes(patch_bytes[-12:-8], "little")
    tgt_crc = int.from_bytes(patch_bytes[-8:-4], "little")
    chk_crc = int.from_bytes(patch_bytes[-4:], "little")
    assert src_crc == (zlib.crc32(source_bytes) & 0xffffffff), "Source CRC mismatch"
    assert tgt_crc == (zlib.crc32(target) & 0xffffffff), "Target CRC mismatch"
    assert chk_crc == (zlib.crc32(patch_bytes[:-4]) & 0xffffffff), "Patch CRC mismatch"
    return True

def create_ips_patch(source_bytes, target_bytes):
    """Creates a standard IPS patch. Handles files up to 16MB and file expansion."""
    patch = bytearray(b"PATCH")
    src_len = len(source_bytes)
    tgt_len = len(target_bytes)
    
    pos = 0
    while pos < tgt_len:
        # Skip identical bytes
        while pos < src_len and pos < tgt_len and source_bytes[pos] == target_bytes[pos]:
            pos += 1
        if pos >= tgt_len:
            break
            
        start = pos
        while pos < tgt_len:
            if pos < src_len and source_bytes[pos] == target_bytes[pos]:
                ahead = 0
                while pos + ahead < src_len and pos + ahead < tgt_len and source_bytes[pos + ahead] == target_bytes[pos + ahead]:
                    ahead += 1
                if ahead >= 6:  # 6 bytes overhead for new record
                    break
            if pos - start >= 0xffff:  # Max record length
                break
            pos += 1
            
        length = pos - start
        patch.extend(start.to_bytes(3, "big"))
        patch.extend(length.to_bytes(2, "big"))
        patch.extend(target_bytes[start:pos])
        
    patch.extend(b"EOF")
    # For file expansion beyond 1MB, some IPS specs write truncate offset:
    if tgt_len > src_len:
        patch.extend(tgt_len.to_bytes(3, "big"))
    return bytes(patch)

if __name__ == "__main__":
    src_path = sys.argv[1]
    tgt_path = sys.argv[2]
    out_prefix = sys.argv[3] if len(sys.argv) > 3 else "ages_greek"

    with open(src_path, "rb") as f:
        src = f.read()
    with open(tgt_path, "rb") as f:
        tgt = f.read()

    src_crc = zlib.crc32(src) & 0xffffffff
    tgt_crc = zlib.crc32(tgt) & 0xffffffff
    src_md5 = hashlib.md5(src).hexdigest()
    tgt_md5 = hashlib.md5(tgt).hexdigest()

    print(f"Source ROM: {src_path}")
    print(f"  Size:  {len(src):,} bytes")
    print(f"  CRC32: {src_crc:08X}")
    print(f"  MD5:   {src_md5}")
    print(f"Target ROM: {tgt_path}")
    print(f"  Size:  {len(tgt):,} bytes")
    print(f"  CRC32: {tgt_crc:08X}")
    print(f"  MD5:   {tgt_md5}")

    # 1. BPS
    bps_path = f"{out_prefix}.bps"
    bps_data = create_bps_patch(src, tgt)
    with open(bps_path, "wb") as f:
        f.write(bps_data)
    print(f"\nGenerated BPS patch: {bps_path} ({len(bps_data):,} bytes)")
    
    # Verify BPS
    verify_bps_patch(bps_data, src, tgt)
    print("  -> BPS patch verified byte-for-byte against target ROM! PASS")

    # 2. IPS
    ips_path = f"{out_prefix}.ips"
    ips_data = create_ips_patch(src, tgt)
    with open(ips_path, "wb") as f:
        f.write(ips_data)
    print(f"\nGenerated IPS patch: {ips_path} ({len(ips_data):,} bytes)")
