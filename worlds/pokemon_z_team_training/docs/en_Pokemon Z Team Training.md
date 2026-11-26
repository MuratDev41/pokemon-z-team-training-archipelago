# Pokemon Z Team Training

## What is this game?

Pokemon Z Team Training (by Z-MAX) is a Dragon Ball Z themed hack of Pokémon FireRed. This world combines it with the
full Pokémon FireRed and LeafGreen Archipelago randomizer: every location, option and piece of logic from that world
works here, while the game you play shows the hack's characters, moves, items, trainers, graphics, title screen and music.

You only need a clean **Pokémon FireRed (USA) 1.0** ROM. The hack's patch is bundled with this world and applied for you
when you open your `.apztt` patch file.

## What comes from Pokemon Z Team Training

- 180 species replaced by Dragon Ball characters (Goku, Vegeta, Gohan, Piccolo, Frieza, Cell, Buu, Broly, Jiren...),
  with their names, front/back sprites, shiny palettes, icons, footprints, Pokédex entries, base stats, types,
  abilities, evolutions, level-up learnsets and TM compatibility. See [species names](species_names.md).
- 151 reworked moves (names, power, accuracy, type, effects, descriptions), their battle animations, and the hack's
  rewritten move effect (a triple stat boost for SSB KAIOKEN and SAIYAN POWER).
- Item names, descriptions and icons (Capsules, Senzu, Dragon Balls...), wherever Archipelago doesn't use the item itself.
- Trainer names, classes, sprites and parties, ability names and descriptions, the type chart.
- Wild encounter tables and in-game trades.
- The hack's rewritten dialogue and menu text, NPC overworld sprites, the professor, the title screen, intro, credits,
  battle backgrounds, Poké Ball and menu graphics, and the hack's new music for the title, wild battles and more.

## What stays from Pokémon FireRed and LeafGreen (Archipelago)

Archipelago's logic is built around FireRed's maps, events and scripts, so these keep the Archipelago version:

- **Story and events.** The hack scripts its own story (who gives what, what blocks the way). Archipelago's
  locations, roadblock options and entrance randomization run on its own scripts, so those stay.
- **Maps.** The hack's map designs are used wherever they provably keep Archipelago's logic: 38 redesigned maps
  (all gyms, the Elite Four, Lavender Town, Namek Town/Cerulean, Saffron, One and Four Island, Routes 4, 5, 8, 20,
  21 and 23, and more) and the hack's art on 54 more. Every swapped map is checked by the build: each warp, item,
  NPC, sign, trigger, map edge and grass/surf/fishing spot must be reachable exactly as before (ledges, Surf,
  Waterfall and elevation included), and tiles that scripts change at runtime must keep their behaviour. The 21
  redesigned maps that fail keep Archipelago's version (for example Pallet Town, where the hack moved the
  player's house door).
- **Shop, prize and gift scripts** are Archipelago's, which fills them with items.
- **Pokédex numbering** stays FireRed's. The hack renumbers the dex and even gives five species the same numbers as
  Gen 3 Pokémon, which would break Pokédex checks. Every character still gets its own Pokédex entry.
- **Cries** stay FireRed's. The hack doesn't add cries: it points every new character at a picture in the ROM, which
  plays as noise.
- Two hack features are only started by its own story scripts (special-moveset gifts and story battle backgrounds), so
  nothing in this game triggers them.

## Names in Archipelago

Archipelago uses the in-game names: hints, items and locations say `GOKU`, `Pokedex - SSJ GOKU`, `Static BUUHAN`, and
YAML species lists (starter or legendary blacklists, for example) take the same names. The
[species names](species_names.md) page maps them to the original Pokémon. Items use the hack's names as well
(CAPSULE, SENZU, HOLY WATER, DRAGONBALL 1...), except the few items Archipelago itself renames or repurposes.

## What does randomization do to this game?

Everything the Pokémon FireRed and LeafGreen world does: items, trainers, wild and static encounters, starters, moves,
types, abilities, base stats, TM/HM compatibility, entrances, fly destinations, shops, and more. The randomizer works
from the hack's data, so a randomized evolution chain, learnset or trainer party is built from the Dragon Ball roster.

## What is the goal?

Become the Champion (or beat the Champion rematch), as set by the `goal` option.

## Credits

- **Pokemon Z Team Training** by Z-MAX. The hack's patch is redistributed inside this world; all of its content belongs
  to its author.
- **Pokémon FireRed and LeafGreen for Archipelago** by Vyneras and contributors
  ([vyneras/Archipelago](https://github.com/vyneras/Archipelago), [vyneras/pokefirered](https://github.com/vyneras/pokefirered)).
- **Pokemon Z Team Training for Archipelago** by MuratDeveloper.
- Pokémon is © Nintendo / Game Freak / The Pokémon Company. Dragon Ball is © Bird Studio / Shueisha / Toei Animation.
