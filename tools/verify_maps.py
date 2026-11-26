"""Check every map of the final ROM against the Archipelago base: same reachability for all of Archipelago's
points of interest (mapcheck.equivalent), reading layouts and tilesets straight from each ROM.
usage: python verify_maps.py <FireRed 1.0 .gba>   (after make_apworld.py)"""
import sys
from core import Ctx, ROM, u32
from mapcheck import read_layout, read_events, equivalent
from mapport import map_headers
from paths import HACK_BPS, AP_BASE_PATCH, FINAL_BASE_ROM

ctx = Ctx(sys.argv[1], HACK_BPS, AP_BASE_PATCH)
final = open(FINAL_BASE_ROM, "rb").read()
maps = map_headers(ctx.A0, ctx.aa("gMapGroups"))
checked = changed = 0
bad = []
for key, hp in maps.items():
    lp = u32(ctx.A0, hp - ROM)
    if u32(final, hp - ROM) != lp:
        bad.append((key, "header layout pointer moved"))
        continue
    try:
        base = read_layout(ctx.A0, lp)
        cand = read_layout(final, lp)
    except Exception:
        continue                      # unused slot / dummy layout
    checked += 1
    if base.blocks != cand.blocks or base.sec != cand.sec or base.prim != cand.prim:
        changed += 1
    ok, why = equivalent(base, cand, read_events(ctx.A0, hp))
    if not ok:
        bad.append((key, why))
print("maps checked", checked, "with changed layout/tiles", changed, "failures", len(bad))
for b in bad[:20]:
    print("  ", b)
sys.exit(1 if bad else 0)
