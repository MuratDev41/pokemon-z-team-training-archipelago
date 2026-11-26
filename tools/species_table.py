"""Write docs/species_names.md: Archipelago species name -> name shown in Pokemon Z Team Training."""
import os, sys
from core import Ctx
from paths import WORLD, HACK_BPS, AP_BASE_PATCH
from gba_text import dec
from evolutions import all_species
ctx = Ctx(sys.argv[1], HACK_BPS, AP_BASE_PATCH)
import json
ed = json.load(open(os.path.join(WORLD, "data", "extracted_data.json"), encoding="utf-8"))
o = ctx.va("gSpeciesNames")
TYPES = ["Normal", "Fighting", "Flying", "Poison", "Ground", "Rock", "Bug", "Ghost", "Steel", "???", "Fire", "Water",
         "Grass", "Electric", "Psychic", "Ice", "Dragon", "Dark"]
rows = []
for const, name, dex in all_species(WORLD):
    sid = ed["constants"][const]
    hack = dec(ctx.Z, o + 11 * sid, 11)
    van = dec(ctx.V, o + 11 * sid, 11)
    if hack == van:
        continue
    t = ed["species"][sid]["types"]
    types = TYPES[t[0]] + ("" if t[0] == t[1] else " / " + TYPES[t[1]])
    rows.append("| %d | %s | %s | %s |" % (dex, name, hack, types))
doc = ["# Species names", "",
       "Archipelago item, location and option names (for example `Pokedex - Bulbasaur`, `Static Mewtwo`,",
       "or the species lists in your YAML) keep the original Pokémon names, so they stay compatible with",
       "trackers and existing logic. In game, those species are the Pokemon Z Team Training characters below.",
       "Species not listed here keep their original Pokémon name in game too.", "",
       "| Dex # | Archipelago name | In game | Type |", "|---|---|---|---|"] + rows
open(os.path.join(WORLD, "docs", "species_names.md"), "w", encoding="utf-8").write("\n".join(doc) + "\n")
print(len(rows), "rows")
