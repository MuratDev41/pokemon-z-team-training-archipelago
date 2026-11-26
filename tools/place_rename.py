"""
Rename Archipelago locations and Archipelago-only items after the hack's places, characters and trainers.

Everything is read from the ROMs:
  places      sMapNames (Pallet Town -> Mount Paozu, Silph Co. -> Capsule Corp., ...)
  characters  gym leaders, Elite Four and Giovanni from gTrainers; Oak, Bill and Mr. Fuji from the Fame Checker
  trainers    each trainer location gets that trainer's class and name in the hack, matched by trainer id
  species     species named inside location names (Pokedex locations are handled by species_rename)
Real game items keep their in-game names (species_rename.apply_items); only Archipelago's own items with a place
in their name (gym keys, fly unlocks, Safari Pass) are renamed here.
"""
import json
import os
import re

from core import ROM, u32
from gba_text import dec

# sMapNames index -> how Archipelago writes that place (where it differs from simple title case)
AP_PLACE_STYLE = {108: "Celadon Department Store"}
# trainer ids whose names stand for a character everywhere (leaders, Elite Four, Giovanni)
CHARACTER_TRAINERS = (348, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420)
# Fame Checker entries for characters who are not trainers: (symbol, how Archipelago writes them)
FAME_CHARACTERS = (("gFameCheckerPersonName_ProfOak", ("Professor Oak", "Prof. Oak", "Oak")),
                   ("gFameCheckerPersonName_Bill", ("Bill",)),
                   ("gFameCheckerPersonName_MrFuji", ("Mr. Fuji",)))
# Archipelago-only items that carry a place name (renamed through the place map)
AP_ITEM_PREFIXES = ("Fly Unlock (", )
AP_ITEM_EXACT = ("Pewter Key", "Cerulean Key", "Vermilion Key", "Celadon Key", "Fuchsia Key", "Saffron Key",
                 "Cinnabar Key", "Viridian Key", "Safari Pass")


def title(s):
    """Hack text (upper case) -> Archipelago style: 'ROSHI‘S ISLAND' -> "Roshi's Island", 'R.R.‘S CAVE' -> "R.R.'s Cave"."""
    s = s.replace("‘", "'").replace("’", "'").replace("é", "e").strip()
    out = []
    for w in s.split(" "):
        if not w:
            continue
        if re.fullmatch(r"([A-Z]\.)+('S)?", w):                     # initials: R.R. / R.R.'S
            out.append(w[:-2] + "'s" if w.endswith("'S") else w)
            continue
        if w == "PKMN":
            out.append("Pokemon")
            continue
        parts = w.split("-")
        parts = [p[:1].upper() + p[1:].lower() for p in parts]
        out.append("-".join(parts).replace("'S", "'s"))
    return " ".join(out)


def _ftext(rom, off, n=20):
    t = dec(rom, off, n)
    return re.sub(r"\{[^}]*\}|\[[0-9a-f]{2}\]", "", t).strip()


def build(ctx, final_rom, ed, species_map):
    V, Z = ctx.V, ctx.Z
    # ---- places ----
    o, s = ctx.vsym["sMapNames"]
    places = []
    for i in range(s // 4):
        old = dec(V, u32(V, o + 4 * i) - ROM, 30)
        new = dec(Z, u32(Z, o + 4 * i) - ROM, 30)
        if old != new and new.strip():
            places.append((AP_PLACE_STYLE.get(i, title(old)), title(new)))
    # "Pewter Gym", "Viridian Pokemon Center": the town word alone stands for the town
    short = []
    for old, new in places:
        m = re.fullmatch(r"(\w+) (City|Town|Island)", old)
        if m:
            short.append((m.group(1), new))
    places = sorted(places, key=lambda p: -len(p[0])) + short
    # ---- characters ----
    t, cn = ctx.va("gTrainers"), ctx.va("gTrainerClassNames")
    people = []
    for tid in CHARACTER_TRAINERS:
        old, new = title(dec(V, t + 40 * tid + 4, 12)), title(dec(Z, t + 40 * tid + 4, 12))
        if old != new and (old, new) not in people:
            people.append((old, new))
    for sym, olds in FAME_CHARACTERS:
        fo = ctx.va(sym)
        new = title(_ftext(Z, fo))
        if new and new != title(_ftext(V, fo)):
            for old in olds:
                people.append((old, new if old != "Oak" else new.split(" ")[-1]))
    people.append(("Team Rocket", "Team Pilaf"))

    # ---- per-trainer tags ----
    def tag(rom, tid):
        return "%s %s" % (title(dec(rom, cn + 13 * rom[t + 40 * tid + 1], 13)), title(dec(rom, t + 40 * tid + 4, 12)))
    trainer_tags = {}
    for const, tid in ed["constants"].items():
        if const.startswith("TRAINER_") and isinstance(tid, int) and 0 < tid < 743:
            old, new = tag(V, tid), tag(Z, tid)
            if old != new:
                trainer_tags[const] = (old, new)
    return dict(places=places, people=people, trainer_tags=trainer_tags, species=species_map)


def _sub_words(text, old, new):
    return re.sub(r"(?<![\w'])" + re.escape(old) + r"(?![\w])", lambda m: new, text)


def rename_location(key, name, maps, log):
    prefix_dex = name.startswith("Pokedex - ")
    if key.startswith("TRAINER_"):
        const = re.sub(r"_(REWARD|INFO)$", "", key)
        if const in maps["trainer_tags"]:
            old, new = maps["trainer_tags"][const]
            pat = re.compile(re.escape(old), re.IGNORECASE)     # Archipelago writes e.g. "PokeManiac"
            if pat.search(name):
                name = pat.sub(lambda m: new, name, count=1)
            else:
                log.append("trainer tag %r not in %r" % (old, name))
    for old, new in maps["people"]:
        name = _sub_words(name, old, new)
    for old, new in maps["places"]:
        name = _sub_words(name, old, new)
    if not prefix_dex:
        for old, new in sorted(maps["species"].items(), key=lambda p: -len(p[0])):
            name = _sub_words(name, old, new)
    return name


def rename_item(name, maps):
    if name in AP_ITEM_EXACT or name.startswith(AP_ITEM_PREFIXES):
        for old, new in maps["places"]:
            name = _sub_words(name, old, new)
        name = name.replace("Safari Pass", "Babidi Pass") if "Safari" in name else name
    return name


def location_map(world, maps, log):
    locs = json.load(open(os.path.join(world, "data", "locations.json"), encoding="utf-8-sig"))
    out = {}
    for key, loc in locs.items():
        new = rename_location(key, loc["name"], maps, log)
        if new != loc["name"]:
            out[loc["name"]] = new
    names = [out.get(l["name"], l["name"]) for l in locs.values()]
    if len(set(names)) != len(names):
        raise ValueError("renamed locations collide")
    return out


def item_map(world, maps):
    items = json.load(open(os.path.join(world, "data", "items.json"), encoding="utf-8-sig"))
    out = {}
    for item in items.values():
        new = rename_item(item["name"], maps)
        if new != item["name"]:
            out[item["name"]] = new
    names = [out.get(i["name"], i["name"]).lower() for i in items.values()]
    if len(set(names)) != len(names):
        raise ValueError("renamed items collide")
    return out


def apply(world, name_map, json_file):
    """Rename names in a data JSON (keeping its formatting) and every exact quoted use in the world's code."""
    path = os.path.join(world, "data", json_file)
    text = open(path, encoding="utf-8-sig").read()
    for old, new in name_map.items():
        pat = re.compile(r'("name":\s*)' + re.escape(json.dumps(old, ensure_ascii=False)))
        text, n = pat.subn(lambda m: m.group(1) + json.dumps(new, ensure_ascii=False), text)
        assert n == 1, (old, n)
    open(path, "w", encoding="utf-8", newline="").write(text)
    changed = {}
    for fn in os.listdir(world):
        if not fn.endswith(".py"):
            continue
        p = os.path.join(world, fn)
        src = open(p, encoding="utf-8").read()
        orig = src
        for old, new in name_map.items():
            for q in ('"%s"' % old, "'%s'" % old):
                if q in src:
                    src = src.replace(q, q[0] + new + q[0])
        if src != orig:
            open(p, "w", encoding="utf-8", newline="").write(src)
            changed[fn] = True
    return sorted(changed)
