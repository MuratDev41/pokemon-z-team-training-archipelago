"""
Pokemon Z Team Training layer.

The player only supplies a clean Pokemon FireRed (USA) 1.0 ROM. At patch time:
  1. the bundled Pokemon Z Team Training BPS patch is applied to it in memory,
  2. the Archipelago FireRed base patch is applied to the clean ROM,
  3. a transplant plan copies the hack's content (species, moves, graphics, text, music, ...)
     from the in-memory hack ROM into the Archipelago ROM.
The plan only holds offsets, lengths and pointers; every content byte is read from the hack ROM.
"""
import struct
import zlib

ROM_NAME = b"pokemon z team training AP"


def apply_bps(source: bytes, patch: bytes) -> bytes:
    if patch[:4] != b"BPS1":
        raise ValueError("not a BPS patch")
    if zlib.crc32(source) != int.from_bytes(patch[-12:-8], "little"):
        raise ValueError("The base ROM does not match the one the Pokemon Z Team Training patch expects "
                         "(Pokemon FireRed USA 1.0, MD5 e26ee0d44e809351c8ce2d73c7400cdd).")
    pos = 4

    def number() -> int:
        nonlocal pos
        value, shift = 0, 1
        while True:
            x = patch[pos]
            pos += 1
            value += (x & 0x7F) * shift
            if x & 0x80:
                return value
            shift <<= 7
            value += shift

    number()                                  # source size
    target = bytearray(number())
    metadata_size = number()                 # (read before advancing: number() moves pos)
    pos += metadata_size
    out = src_rel = tgt_rel = 0
    end = len(patch) - 12
    while pos < end:
        cmd = number()
        action, length = cmd & 3, (cmd >> 2) + 1
        if action == 0:                       # SourceRead
            target[out:out + length] = source[out:out + length]
            out += length
        elif action == 1:                     # TargetRead
            target[out:out + length] = patch[pos:pos + length]
            pos += length
            out += length
        else:
            offset = number()
            offset = -(offset >> 1) if offset & 1 else offset >> 1
            if action == 2:                   # SourceCopy
                src_rel += offset
                target[out:out + length] = source[src_rel:src_rel + length]
                src_rel += length
                out += length
            else:                             # TargetCopy (may overlap)
                tgt_rel += offset
                for _ in range(length):
                    target[out] = target[tgt_rel]
                    out += 1
                    tgt_rel += 1
    if zlib.crc32(target) != int.from_bytes(patch[-8:-4], "little"):
        raise ValueError("Pokemon Z Team Training patch produced a bad ROM (checksum mismatch)")
    return bytes(target)


def apply_plan(ap_rom: bytes, hack_rom: bytes, plan: bytes) -> bytes:
    if plan[:4] != b"ZTP1":
        raise ValueError("bad transplant plan")
    rom = bytearray(ap_rom)
    count = struct.unpack_from("<I", plan, 4)[0]
    i = 8
    for _ in range(count):
        if plan[i] == 0x43:   # 'C': copy from the hack ROM
            dst, src, length = struct.unpack_from("<III", plan, i + 1)
            rom[dst:dst + length] = hack_rom[src:src + length]
            i += 13
        else:                 # 'W': write literal bytes (pointers, ids)
            dst, length = struct.unpack_from("<II", plan, i + 1)
            rom[dst:dst + length] = plan[i + 9:i + 9 + length]
            i += 9 + length
    return bytes(rom)
