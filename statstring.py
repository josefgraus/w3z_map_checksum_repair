import sys

def find_stat(raw):
    # statstring follows "<map path>\0\0<game name>\0" ... "Local Game\0\0" ; locate by the null after game name
    i = raw.index(b"Local Game\x00") + len(b"Local Game\x00") + 1
    j = raw.index(b"\x00", i)
    return i, j  # encoded bytes raw[i:j]

def decode(enc):
    out = bytearray(); pos = []
    for g in range(0, len(enc), 8):
        mask = enc[g]
        for k, c in enumerate(enc[g+1:g+8]):
            out.append(c if mask & (1 << (k + 1)) else c - 1)
            pos.append(g + 1 + k)
    return bytes(out), pos

def encode(dec):
    out = bytearray()
    for g in range(0, len(dec), 7):
        chunk = dec[g:g+7]; mask = 1; enc = bytearray()
        for k, c in enumerate(chunk):
            if c % 2 == 0:
                enc.append(c + 1)
            else:
                mask |= 1 << (k + 1); enc.append(c)
        out.append(mask); out += enc
    return bytes(out)

if __name__ == "__main__":
    for p in sys.argv[1:]:
        raw = open(p, "rb").read(4096)
        i, j = find_stat(raw)
        enc = raw[i:j]; dec, _ = decode(enc)
        print(p, "enc off", i, "len", len(enc), "dec len", len(dec), "re-encode identical:", encode(dec) == enc)
        print("  dec hex:", dec.hex(" "))
        print("  dec txt:", dec)
