"""Derive symbol addresses in the shipped AP base ROM from a local build of the AP decomp.
Output: tools/data/shipped_syms.json = {"name#occ": shipped_offset}"""
import json, sys
import os
import bsdiff4
from core import load_sym, ROM
from paths import AP_BASE_PATCH, DATA
V = open(sys.argv[1], "rb").read()
a = bsdiff4.patch(V, open(AP_BASE_PATCH, "rb").read())   # shipped
b = open(sys.argv[2], "rb").read()                                            # local build
_, lst = load_sym(os.path.join(DATA, "pokefirered_ap.sym"))
lst = [x for x in lst if x[0] < 0x01000000]
occ = {}
keyed = []
for o, s, n in lst:
    k = occ.get(n, 0); occ[n] = k + 1
    keyed.append((o, s, "%s#%d" % (n, k)))
def score(o, sh, ln):
    ln = min(ln, 64)
    if o + sh < 0 or ln <= 0: return 0
    return sum(1 for i in range(ln) if a[o + sh + i] == b[o + i]) / ln
shift = 0; res = {}; changes = []
starts = sorted(set(x[0] for x in keyed))
import bisect
for o, s, key in keyed:
    j = bisect.bisect_right(starts, o)
    nxt = starts[j] if j < len(starts) else o + max(s, 4)
    ln = max(4, min(s if s else nxt - o, nxt - o))
    if ln >= 8 and score(o, shift, ln) < 0.75:
        best = None
        for cand in range(-0x800, 0x100, 2):
            if score(o, cand, ln) >= 0.9 and (best is None or abs(cand - shift) < abs(best - shift)):
                best = cand
        if best is not None and best != shift:
            changes.append((key, hex(o), shift, best)); shift = best
    res[key] = o + shift
json.dump(res, open(os.path.join(DATA, "shipped_syms.json"), "w"))
print(len(res), "symbols;", len(changes), "shift changes")
for c in changes: print(*c)
