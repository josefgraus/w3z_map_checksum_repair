import sys, zlib, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from w3z import parse

for f in sys.argv[1:]:
    b, info, bl = parse(f)
    print("==", f)
    for n in (0, 1, 100, len(bl) - 1):
        x = bl[n]; d = zlib.decompressobj(); out = d.decompress(x["data"])
        print(f"  blk{n}: c={x['c']} eof={d.eof} unused={len(d.unused_data)} out={len(out)} "
              f"head={x['data'][:2].hex()} tail={x['data'][-10:].hex()}")
