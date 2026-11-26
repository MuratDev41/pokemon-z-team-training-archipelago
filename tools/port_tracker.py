"""
Port the Pokemon FireRed/LeafGreen PopTracker pack to Pokemon Z Team Training.

  python port_tracker.py "<FireRed 1.0 .gba>" <upstream pack folder>

Locations, logic, maps and autotracking are unchanged: the world uses the same Archipelago map logic,
datastorage keys and tracker checksum. What changes:
  - manifest: game name / uid / title, so PopTracker pairs it with "Pokemon Z Team Training" slots
  - species display names: the in-game names, which the world uses too
  - species images: the hack's own 32x32 menu icons, rendered from the ROM
"""
import json
import os
import re
import shutil
import sys
import zipfile

from PIL import Image

from core import Ctx, ROM, u16, u32
from paths import WORLD, TRACKER as OUT, DIST, HACK_BPS, AP_BASE_PATCH, FINAL_BASE_ROM, UPSTREAM_WORLD
from evolutions import all_species
from gba_text import dec


vanilla_path, upstream = sys.argv[1], sys.argv[2]
ctx = Ctx(vanilla_path, HACK_BPS, AP_BASE_PATCH)
final = open(FINAL_BASE_ROM, "rb").read()
ed = json.load(open(os.path.join(WORLD, "data", "extracted_data.json"), encoding="utf-8"))

if os.path.exists(OUT):
    shutil.rmtree(OUT)
shutil.copytree(upstream, OUT)

# ---------- manifest ----------
mpath = os.path.join(OUT, "manifest.json")
m = json.load(open(mpath, encoding="utf-8-sig"))
m["name"] = "Pokemon Z Team Training Tracker"
m["game_name"] = "Pokemon Z Team Training"
m["package_uid"] = "pokemon_z_team_training"
m["package_version"] = "1.1.0"
m["author"] = "Vyneras, MuratDeveloper"
m.pop("versions_url", None)   # the upstream URL would offer FRLG updates
json.dump(m, open(mpath, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

# ---------- species: code -> species id ----------
src = open(os.path.join(OUT, "scripts", "autotracking", "pokemon_mapping.lua"), encoding="utf-8").read()
dex_to_code = {int(a): b for a, b in re.findall(r'\[(\d+)\]\s*=\s*"([a-z0-9_]+)"', src)}
species = all_species(UPSTREAM_WORLD)
dex_to_species = {}
dex_to_apname = {}
for const, name, dex in species:
    dex_to_species[dex] = ed["constants"][const]
    dex_to_apname[dex] = name

names_v = ctx.va("gSpeciesNames")
names_a = ctx.aa("gSpeciesNames")
icon_v, icon_a = ctx.va("gMonIconTable"), ctx.aa("gMonIconTable")
idx_a = ctx.aa("gMonIconPaletteIndices")
pals_a = ctx.aa("gMonIconPalettes")


def palette(i):
    out = []
    for c in range(16):
        w = u16(final, pals_a + 32 * i + 2 * c)
        out.append(((w & 31) * 255 // 31, ((w >> 5) & 31) * 255 // 31, ((w >> 10) & 31) * 255 // 31))
    return out


def render_icon(sid):
    """First frame (32x32, 4bpp, 4x4 tiles) of the species' menu icon from the final ROM."""
    gfx = u32(final, icon_a + 4 * sid) - ROM
    pal = palette(final[idx_a + sid])
    img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    px = img.load()
    for t in range(16):
        tx, ty = (t % 4) * 8, (t // 4) * 8
        for y in range(8):
            for x in range(8):
                b = final[gfx + 32 * t + 4 * y + x // 2]
                c = (b >> 4) if x & 1 else (b & 15)
                if c:
                    px[tx + x, ty + y] = pal[c] + (255,)
    return img


def icon_changed(sid):
    gv = u32(ctx.V, icon_v + 4 * sid) - ROM
    gf = u32(final, icon_a + 4 * sid) - ROM
    return ctx.V[gv:gv + 0x200] != final[gf:gf + 0x200]


code_to_label = {}
icons = 0
for dex, code in dex_to_code.items():
    sid = dex_to_species.get(dex)
    if sid is None:
        continue
    game_name = dec(final, names_a + 11 * sid, 11)
    vanilla_name = dec(ctx.V, names_v + 11 * sid, 11)
    if game_name != vanilla_name:
        code_to_label[code] = game_name   # the world uses the in-game names too
    if icon_changed(sid):
        render_icon(sid).save(os.path.join(OUT, "images", "pokemon", code + ".png"))
        icons += 1

# ---------- item names ----------
ipath = os.path.join(OUT, "items", "pokemon.json")
items = json.load(open(ipath, encoding="utf-8-sig"))
renamed = 0
for it in items:
    codes = [s.get("codes") for s in it.get("stages", []) if s.get("codes")] + [it.get("codes")]
    code = next((c for c in codes if c), None)
    if code in code_to_label:
        it["name"] = code_to_label[code]
        renamed += 1
json.dump(items, open(ipath, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

# ---------- readme ----------
rpath = os.path.join(OUT, "README.md")
readme = open(rpath, encoding="utf-8").read()
open(rpath, "w", encoding="utf-8").write(
    "# Pokemon Z Team Training Tracker\n\n"
    "A port of the Pokémon FireRed/LeafGreen tracker pack by Vyneras for the Pokemon Z Team Training Archipelago "
    "world. Locations, logic and autotracking are unchanged (the world uses the same Archipelago map logic); "
    "species show the hack's names and icons, the same names the world uses.\n\n"
    "For Universal Tracker, set `ut_poptracker_path` under `pokemon_z_team_training_settings` in host.yaml to this zip.\n\n"
    "---\n\n" + readme)

# ---------- package (files at the zip root, like the upstream pack) ----------
os.makedirs(DIST, exist_ok=True)
zpath = os.path.join(DIST, "pokemon-z-team-training-tracker.zip")
with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(OUT):
        for fn in files:
            full = os.path.join(root, fn)
            z.write(full, os.path.relpath(full, OUT).replace(os.sep, "/"))
print("renamed", renamed, "species items; rendered", icons, "icons; wrote", zpath, os.path.getsize(zpath))
