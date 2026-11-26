"""Write docs/species_names.md: Archipelago species name -> name shown in Pokemon Z Team Training."""
import os, sys
from core import Ctx
from paths import WORLD, HACK_BPS, AP_BASE_PATCH, UPSTREAM_WORLD
from gba_text import dec
from evolutions import all_species
ctx = Ctx(sys.argv[1], HACK_BPS, AP_BASE_PATCH)
import json
ed = json.load(open(os.path.join(WORLD, "data", "extracted_data.json"), encoding="utf-8"))
o = ctx.va("gSpeciesNames")
TYPES = ["Normal", "Fighting", "Flying", "Poison", "Ground", "Rock", "Bug", "Ghost", "Steel", "???", "Fire", "Water",
         "Grass", "Electric", "Psychic", "Ice", "Dragon", "Dark"]
rows = []
for const, name, dex in all_species(UPSTREAM_WORLD):
    sid = ed["constants"][const]
    hack = dec(ctx.Z, o + 11 * sid, 11)
    van = dec(ctx.V, o + 11 * sid, 11)
    if hack == van:
        continue
    t = ed["species"][sid]["types"]
    types = TYPES[t[0]] + ("" if t[0] == t[1] else " / " + TYPES[t[1]])
    rows.append("| %d | %s | %s | %s |" % (dex, name, hack, types))
doc = ["# Species names", "",
       "Pokemon Z Team Training replaces 180 Pokémon with Dragon Ball characters. Archipelago uses the same names as",
       "the game: items, locations, hints and YAML species lists say `GOKU`, `Pokedex - GOKU`, `Static SSB VEGETA`, etc.",
       "This table maps them to the original Pokémon (and its Pokédex number), which helps when reading guides or",
       "trackers written for Pokémon FireRed and LeafGreen. Species not listed keep their Pokémon name.", "",
       "| Dex # | Original Pokémon | Name in this game | Type |", "|---|---|---|---|"] + rows
open(os.path.join(WORLD, "docs", "species_names.md"), "w", encoding="utf-8").write("\n".join(doc) + "\n")
print(len(rows), "rows")
