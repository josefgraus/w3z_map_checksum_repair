import struct, zlib, sys

def fold(c):
    return (c ^ (c >> 16)) & 0xFFFF

def block_cksum(hdr12, data):
    h = bytearray(hdr12); h[8:12] = b"\0\0\0\0"
    return fold(zlib.crc32(bytes(h))) | (fold(zlib.crc32(data)) << 16)

def header_crc(h68):
    h = bytearray(h68); h[0x40:0x44] = b"\0\0\0\0"
    return zlib.crc32(bytes(h))

def parse(path):
    b = open(path, "rb").read()
    hdr = b[:0x44]
    hsize, csize, hver, dsize, nblk = struct.unpack_from("<IIIII", b, 0x1C)
    ident, ver, build, flags, length, hcrc = struct.unpack_from("<4sIHHII", b, 0x30)
    info = dict(hsize=hsize, csize=csize, filelen=len(b), hver=hver, dsize=dsize, nblk=nblk,
                ident=ident, ver=ver, build=build, flags=flags, length=length,
                hcrc=hcrc, hcrc_calc=header_crc(hdr))
    blocks = []; off = hsize
    for i in range(nblk):
        bh = b[off:off+12]
        c, d, ck = struct.unpack("<III", bh)
        data = b[off+12:off+12+c]
        blocks.append(dict(off=off, c=c, d=d, ck=ck, ck_calc=block_cksum(bh, data), data=data))
        off += 12 + c
    info["end"] = off
    return b, info, blocks

def decompress(blocks):
    out = bytearray(); lens = []
    for bl in blocks:
        raw = zlib.decompressobj().decompress(bl["data"])
        lens.append(len(raw)); out += raw
    return bytes(out), lens

if __name__ == "__main__":
    b, info, blocks = parse(sys.argv[1])
    print({k: v for k, v in info.items()})
    bad = [i for i, bl in enumerate(blocks) if bl["ck"] != bl["ck_calc"]]
    print("blocks", len(blocks), "checksum mismatches:", bad)
    raw, lens = decompress(blocks)
    print("decompressed", len(raw), "block raw lens unique:", sorted(set(lens))[:5], "declared d unique:", sorted(set(bl['d'] for bl in blocks))[:5])
    if len(sys.argv) > 2:
        open(sys.argv[2], "wb").write(raw)
