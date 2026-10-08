#!/usr/bin/env python3
"""Repair a Warcraft III .w3z save whose map checksum is stale after a patch.

usage: python3 repair.py BROKEN.w3z FRESH_SAME_MAP.w3z OUTPUT.w3z

- BROKEN:  the old save to recover (never modified; a .bak copy is also written next to OUTPUT)
- FRESH:   a save made on the SAME map under the CURRENT patch (source of the new checksum)
- OUTPUT:  must not already exist

Changes ONLY the map checksum: once inside the encoded statstring and at exactly two unencoded
references. Same length, no shifted data, build marker (header 0x38) untouched. Affected 1 MiB
blocks are recompressed the way the game does it (zlib level 1, memLevel 8, Z_SYNC_FLUSH, no
stream terminator), proven by first reproducing the original block byte-for-byte.
"""
import os, shutil, struct, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from w3z import parse, decompress, block_cksum, header_crc
from statstring import find_stat, decode, encode

BS = 1 << 20

def die(msg):
    sys.exit("ERROR: " + msg)

def comp(data):
    co = zlib.compressobj(1, zlib.DEFLATED, 15, 8, zlib.Z_DEFAULT_STRATEGY)
    return co.compress(data) + co.flush(zlib.Z_SYNC_FLUSH)

def stat_checksum(raw, label):
    try:
        i, j = find_stat(raw)
    except ValueError:
        die(f"{label}: statstring not found (no 'Local Game' marker) - format differs, inspect manually")
    dec, _ = decode(raw[i:j])
    if encode(dec) != raw[i:j]:
        die(f"{label}: statstring does not round-trip through decode/encode")
    path = raw[:raw.index(b"\0")]
    if not dec[13:].startswith(path):
        die(f"{label}: decoded statstring does not contain the map path at byte 13; layout differs")
    return i, j, dec

def main():
    if len(sys.argv) != 4:
        die(__doc__)
    src, ref, dst = sys.argv[1:4]
    if os.path.exists(dst):
        die(f"{dst} already exists; refusing to overwrite")
    if os.path.abspath(dst) in (os.path.abspath(src), os.path.abspath(ref)):
        die("output must differ from inputs")

    b, info, blocks = parse(src)
    _, rinfo, rblocks = parse(ref)
    for lbl, inf, bl in (("broken", info, blocks), ("fresh", rinfo, rblocks)):
        if inf["hcrc"] != inf["hcrc_calc"] or inf["csize"] != inf["filelen"]:
            die(f"{lbl}: header CRC/size invalid")
        bad = [n for n, x in enumerate(bl) if x["ck"] != x["ck_calc"]]
        if bad:
            die(f"{lbl}: block checksum mismatch at {bad}")

    raw, _ = decompress(blocks)
    rraw = zlib.decompressobj().decompress(rblocks[0]["data"])
    i, j, dec = stat_checksum(raw, "broken")
    _, _, rdec = stat_checksum(rraw, "fresh")
    old, new = dec[9:13], rdec[9:13]
    mp, rp = raw[:raw.index(b"\0")], rraw[:rraw.index(b"\0")]
    print("map path      " + mp.decode("latin1"))
    print("fresh path    " + rp.decode("latin1"))
    print(f"old checksum  0x{old[::-1].hex()}   new checksum 0x{new[::-1].hex()}")
    print(f"build marker  broken={info['build']} fresh={rinfo['build']} (broken value kept)")
    if old == new:
        die("checksums already match - nothing to repair (wrong reference map, or already repaired)")
    if mp.lower().replace(b"\\", b"/") != rp.lower().replace(b"\\", b"/"):
        die("broken and fresh saves are on DIFFERENT maps - use a fresh save from the same map")

    hits, k = [], raw.find(old)
    while k != -1:
        hits.append(k); k = raw.find(old, k + 1)
    if len(hits) != 2:
        die(f"expected exactly 2 unencoded checksum references, found {len(hits)} at {hits[:10]}")
    print(f"unencoded refs at decompressed offsets {hits}")

    patched = bytearray(raw)
    newenc = encode(dec[:9] + new + dec[13:])
    if len(newenc) != j - i:
        die("re-encoded statstring length changed")
    patched[i:j] = newenc
    for h in hits:
        patched[h:h + 4] = new
    patched = bytes(patched)
    diff = [x for a, z in ((i, j), (hits[0], hits[0] + 4), (hits[1], hits[1] + 4))
            for x in range(a, z) if raw[x] != patched[x]]
    affected = sorted({x // BS for x in diff})
    print(f"changed decompressed bytes: {len(diff)} at {diff}")
    print(f"affected blocks: {affected}")

    out = bytearray(b[:info["hsize"]])
    for n, bl in enumerate(blocks):
        if n not in affected:
            out += b[bl["off"]:bl["off"] + 12 + bl["c"]]
            continue
        if comp(raw[n * BS:(n + 1) * BS]) != bl["data"]:
            die(f"compressor does not reproduce original block {n}; refusing to recompress")
        chunk = patched[n * BS:(n + 1) * BS]
        c = comp(chunk)
        hdr = bytearray(struct.pack("<III", len(c), bl["d"], 0))
        struct.pack_into("<I", hdr, 8, block_cksum(bytes(hdr), c))
        out += hdr + c
        print(f"block {n}: compressed {bl['c']} -> {len(c)} bytes")
    out += b[info["end"]:]
    struct.pack_into("<I", out, 0x20, len(out))
    struct.pack_into("<I", out, 0x40, header_crc(bytes(out[:0x44])))

    # ---- self-verification of the output before writing ----
    tmp = dst + ".tmp"
    open(tmp, "wb").write(out)
    _, oinfo, oblocks = parse(tmp)
    oraw, _ = decompress(oblocks)
    problems = []
    if oinfo["hcrc"] != oinfo["hcrc_calc"] or oinfo["csize"] != oinfo["filelen"]:
        problems.append("header CRC/size")
    if any(x["ck"] != x["ck_calc"] for x in oblocks):
        problems.append("block checksum")
    if len(oraw) != len(raw) or oinfo["dsize"] != info["dsize"] or oinfo["build"] != info["build"]:
        problems.append("length/build changed")
    for n in affected:
        dd = zlib.decompressobj(); dd.decompress(oblocks[n]["data"])
        if dd.eof:
            problems.append(f"block {n} has stream terminator")
    if oraw != patched:
        problems.append("decompressed content differs from intended patch")
    hdr_changed = [x for x in range(info["hsize"]) if b[x] != out[x]]
    if any(x not in (0x20, 0x21, 0x22, 0x23, 0x40, 0x41, 0x42, 0x43) for x in hdr_changed):
        problems.append(f"unexpected header bytes changed {hdr_changed}")
    if problems:
        os.remove(tmp); die("verification failed: " + ", ".join(problems))
    os.replace(tmp, dst)
    bak = dst + ".orig.bak"
    if not os.path.exists(bak):
        shutil.copy2(src, bak)
    print(f"verified and wrote {dst} ({len(out)} bytes); original copied to {bak}")

if __name__ == "__main__":
    main()
