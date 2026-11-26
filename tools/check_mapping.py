"""Sanity check: vanilla data symbols should map to AP data that is identical once pointers are translated."""
import struct
import sys
from core import Ctx, VANILLA_END, ROM
from paths import HACK_BPS, AP_BASE_PATCH
ctx = Ctx(sys.argv[1], HACK_BPS, AP_BASE_PATCH)
same = ptrsame = sizediff = missing = 0
bad = []
for idx, (o, s, n) in enumerate(ctx.vlist):
    if not s or s > 0x20000 or o >= VANILLA_END or o < 0x1E8000:
        continue
    m = ctx.map_entry(idx)
    if not m: missing += 1; continue
    ao, asz = m
    if asz != s: sizediff += 1; continue
    a = ctx.A0[ao:ao + s]; v = ctx.V[o:o + s]
    if a == v: same += 1; continue
    ok = True
    for i in range(0, s - 3, 4):
        vw = struct.unpack_from("<I", v, i)[0]; aw = struct.unpack_from("<I", a, i)[0]
        if vw == aw: continue
        if ROM <= vw < ROM + VANILLA_END and ctx.map_ptr(vw) == aw: continue
        ok = False; break
    if ok and s % 4 == 0: ptrsame += 1
    else: bad.append((n, hex(o), hex(ao), s))
print("same", same, "same-after-ptr-map", ptrsame, "sizediff", sizediff, "missing", missing, "differs", len(bad))
for b in bad[:40]: print(*b)
