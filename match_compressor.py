"""Find zlib parameters that reproduce the game's ORIGINAL compressed blocks byte-for-byte."""
import sys, zlib, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from w3z import parse

b, info, bl = parse(sys.argv[1])
test = [int(x) for x in sys.argv[2].split(",")]
for lvl in range(0, 10):
    for mem in (8, 9):
        for strat in (zlib.Z_DEFAULT_STRATEGY, zlib.Z_FILTERED):
            for flush in (zlib.Z_SYNC_FLUSH, zlib.Z_FULL_FLUSH):
                ok = True
                for n in test:
                    raw = zlib.decompressobj().decompress(bl[n]["data"])
                    co = zlib.compressobj(lvl, zlib.DEFLATED, 15, mem, strat)
                    c = co.compress(raw) + co.flush(flush)
                    if c != bl[n]["data"]:
                        ok = False; break
                if ok:
                    print("EXACT MATCH level", lvl, "memLevel", mem, "strategy", strat, "flush", flush, "blocks", test)
print("zlib runtime", zlib.ZLIB_RUNTIME_VERSION)
