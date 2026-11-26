"""
Give species their Pokemon Z Team Training names on the Archipelago side too.

Only species identities are renamed: the ALL_SPECIES list in data.py, "Pokedex - X" locations, "Static X" event
items, and the two rules that name a species. Place names ("Diglett's Cave", "Pidgey House", "Hidden Item Under
Snorlax", "Static Marowak Scaling") stay as they are. Everything is regenerated from the upstream world, so running it
again gives the same result.
"""
import json
import os
import re

from core import ROM
from evolutions import all_species
from gba_text import dec

# rules.py lines that check for a specific species by name
RULE_SPECIES = ("Magikarp", "Togepi", "Togetic")


def build_map(ctx, final_rom, upstream_world, ed):
    """Archipelago name -> in-game name, for species the hack renamed."""
    names_v, names_a = ctx.va("gSpeciesNames"), ctx.aa("gSpeciesNames")
    mapping = {}
    for const, name, _ in all_species(upstream_world):
        sid = ed["constants"][const]
        game = dec(final_rom, names_a + 11 * sid, 11)
        if game != dec(ctx.V, names_v + 11 * sid, 11):
            mapping[name] = game
    if len(set(mapping.values()) | (set(n for _, n, _ in all_species(upstream_world)) - set(mapping))) != \
            len(all_species(upstream_world)):
        raise ValueError("renamed species would collide with another species name")
    return mapping


def apply(world, upstream_world, mapping):
    # data.py: species list only
    src = open(os.path.join(upstream_world, "data.py"), encoding="utf-8").read()
    start = src.index("ALL_SPECIES: List[Tuple[str, str, int]] = [")
    end = src.index("\n]", start)
    block = src[start:end]

    def rename(m):
        new = mapping.get(m.group(2), m.group(2))
        return '("%s", %s, %s)' % (m.group(1), json.dumps(new, ensure_ascii=False), m.group(3))

    block = re.sub(r'\("(SPECIES_\w+)", "((?:[^"\\]|\\.)*)", (\d+)\)', rename, block)
    open(os.path.join(world, "data.py"), "w", encoding="utf-8").write(src[:start] + block + src[end:])

    # rules.py: species named in rules
    rules = open(os.path.join(upstream_world, "rules.py"), encoding="utf-8").read()
    for name in RULE_SPECIES:
        if name in mapping:
            old = 'Has("%s")' % name
            assert old in rules, old
            rules = rules.replace(old, "Has(%s)" % json.dumps(mapping[name], ensure_ascii=False))
    open(os.path.join(world, "rules.py"), "w", encoding="utf-8").write(rules)

    # locations.json: dexsanity locations (text replacement keeps upstream's formatting)
    text = open(os.path.join(upstream_world, "data", "locations.json"), encoding="utf-8-sig").read()
    renamed = 0
    for old, new in mapping.items():
        key = '"name": %s' % json.dumps("Pokedex - " + old, ensure_ascii=False)
        if key in text:
            assert text.count(key) == 1, key
            text = text.replace(key, '"name": %s' % json.dumps("Pokedex - " + new, ensure_ascii=False))
            renamed += 1
    open(os.path.join(world, "data", "locations.json"), "w", encoding="utf-8", newline="").write(text)
    return renamed


def rename_static_events(events, mapping):
    """'Static X' event items (static encounters) name the species they give."""
    for ev in events.values():
        item = ev.get("item", "")
        if item.startswith("Static ") and item[len("Static "):] in mapping:
            ev["item"] = "Static " + mapping[item[len("Static "):]]
    return events


# ---------------------------------------------------------------------------
# Items: the hack renamed 32 items (Capsules, Senzu, Dragon Balls...)
# ---------------------------------------------------------------------------
def build_item_map(ctx, final_rom, upstream_world, ed):
    """Archipelago item name -> in-game name, for items whose in-game name the build changed.
    Items Archipelago renamed itself keep Archipelago's name (the transplant left those alone)."""
    items = json.load(open(os.path.join(upstream_world, "data", "items.json"), encoding="utf-8-sig"))
    va, aa = ctx.va("gItems"), ctx.aa("gItems")
    mapping = {}
    for const, item in items.items():
        iid = ed["constants"].get(const)
        if iid is None or iid >= 375:
            continue
        final = dec(final_rom, aa + 44 * iid, 14)
        if final != dec(ctx.A0, aa + 44 * iid, 14):
            mapping[item["name"]] = final
    names = [i["name"] for i in items.values()]
    new = [mapping.get(n, n).lower() for n in names]
    if len(set(new)) != len(new):
        raise ValueError("renamed items would collide")
    return mapping


def apply_items(world, upstream_world, mapping):
    text = open(os.path.join(upstream_world, "data", "items.json"), encoding="utf-8-sig").read()
    for old, new in mapping.items():
        key = '"name": %s' % json.dumps(old, ensure_ascii=False)
        assert text.count(key) == 1, key
        text = text.replace(key, '"name": %s' % json.dumps(new, ensure_ascii=False))
    open(os.path.join(world, "data", "items.json"), "w", encoding="utf-8", newline="").write(text)
    src = open(os.path.join(upstream_world, "items.py"), encoding="utf-8").read()
    for old, new in mapping.items():
        src = src.replace(json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False))
    open(os.path.join(world, "items.py"), "w", encoding="utf-8").write(src)
