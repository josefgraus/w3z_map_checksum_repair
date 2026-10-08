W3Z MAP-CHECKSUM REPAIR  (Python 3.8+, standard library only; tested on Python 3.13.16 / zlib 1.3)

Fixes Warcraft III campaign saves that a patch broke because the map checksum changed.
Confirmed working on: Forsaken Kingdom, UndeadRE02 (Act Two), latest.w3z.
  result SHA-256 12890515a6dfa720b67817d706a2632e74086037c245b506c084723992962cc6

FILES
  repair.py            the repair (all checks built in)
  w3z.py               inspect/verify a save:  python3 w3z.py SAVE.w3z [dump.raw]
  statstring.py        decode statstring:      python3 statstring.py dump.raw
  probe_blocks.py      show block framing:     python3 probe_blocks.py SAVE.w3z
  match_compressor.py  confirm zlib settings:  python3 match_compressor.py SAVE.w3z 1,2,3

USAGE
  python3 repair.py BROKEN.w3z FRESH_SAME_MAP.w3z REPAIRED.w3z

  FRESH_SAME_MAP = a save made on the same map under the current patch.
  The output must not exist yet. A copy of BROKEN is written as REPAIRED.w3z.orig.bak.
  Keep your own backups too.

WHAT IT CHANGES (and nothing else)
  - the map checksum inside the encoded statstring (same length after re-encoding)
  - exactly two unencoded copies of the checksum, found by searching, not fixed offsets
  - recompresses only the 1 MiB blocks it touched, using the game's own method:
    zlib level 1, memLevel 8, finished with Z_SYNC_FLUSH (no zlib terminator)
    (v1 used a normal zlib finish and crashed the game; this was the fix)
  - updates block checksums, file size (header 0x20) and header CRC (0x40)
  - leaves the build marker (header 0x38, e.g. 7000) unchanged; changing it crashed the game

IT STOPS WITHOUT WRITING ANYTHING IF
  - either input is corrupt (header CRC, size, or block checksum fails)
  - the two saves are on different maps, or the checksums already match
  - it does not find exactly 2 unencoded copies of the checksum
  - the statstring is missing, does not decode cleanly, or has an unexpected layout
  - recompressing an original block does not reproduce it byte for byte
  - the finished file fails its own re-check (checksums, length, build, intended bytes)

COMPANION / AREA SAVES (Blizzard\Zones, e.g. UndeadRE01.w3z, UndeadRE01_02.w3z ...)
  Repair each one separately, using a fresh current-patch save from THAT area's map.
  Update every copy, including the working files in Blizzard\Zones. Loading a main save
  can put an old companion back over a repaired one, so compare file hashes and, if
  needed, copy the repaired file in after the main save loads and before you travel.
  Companion saves have not been tested with this script. If it stops on one, the layout
  differs; inspect it with w3z.py and statstring.py.