"""Check that regen.py reproduces the upstream extracted data from the untouched AP base ROM.

usage: python check_regen.py <FireRed 1.0 .gba>

Only FireRed values are compared: this world sets every version key to the FireRed value on purpose.
"""
import json
import sys

import bsdiff4

from paths import AP_BASE_PATCH, UPSTREAM_DATA
from regen import regen

VERSION_KEYS = {"firered", "firered_rev1", "leafgreen", "leafgreen_rev1"}


def firered_only(x):
    if isinstance(x, dict):
        if x and set(x) <= VERSION_KEYS:
            return x.get("firered")
        return {k: firered_only(v) for k, v in x.items()}
    if isinstance(x, list):
        return [firered_only(v) for v in x]
    return x


V = open(sys.argv[1], "rb").read()
A = bsdiff4.patch(V, open(AP_BASE_PATCH, "rb").read())
ed = json.load(open(UPSTREAM_DATA, encoding="utf-8-sig"))
new, _ = regen(ed, A)
bad = [k for k in ("species", "moves", "trainers", "maps", "trade_pokemon", "tmhm_moves")
       if firered_only(ed[k]) != firered_only(new[k])]
print("OK: regen reproduces the upstream data" if not bad else "MISMATCH in: " + ", ".join(bad))
sys.exit(1 if bad else 0)
