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
- 151 reworked moves (names, power, accuracy, type, effects, descriptions) and their battle animations.
- Item names, descriptions and icons (Capsules, Senzu, Dragon Balls...), wherever Archipelago doesn't use the item itself.
- Trainer names, classes, sprites and parties, ability names and descriptions, the type chart.
- Wild encounter tables and in-game trades.
- The hack's rewritten dialogue and menu text, NPC overworld sprites, the professor, the title screen, intro, credits,
  battle backgrounds, Poké Ball and menu graphics, and the hack's new music for the title, wild battles and more.

## What stays from Pokémon FireRed and LeafGreen (Archipelago)

Archipelago needs the map layouts, events and scripts it was built around, so these keep the Archipelago FireRed version:

- **Maps, events and story.** The hack rebuilt many maps and scripted its own story. Those layouts and scripts are not
  used: you walk the Archipelago version of Kanto and the Sevii Islands, with all of its item locations, roadblock options
  and entrance randomization. Towns and buildings whose maps the hack rebuilt keep FireRed's tileset graphics, so they
  don't show the hack's art on a layout it wasn't drawn for.
- **Shop, prize and gift scripts** are Archipelago's (Archipelago fills them with items).
- **Cries** stay FireRed's: the hack points the new characters at a cry that isn't valid sound data.
- A handful of hack-only features driven by its story scripts (a custom-moveset gift routine, script-selected battle
  backgrounds) are left out because nothing in the Archipelago game triggers them.

## Names in Archipelago

Item, location, option and hint names keep the original Pokémon names (for example `Pokedex - Bulbasaur` is Goku's
Pokédex entry), so YAMLs, trackers and the existing logic stay compatible. The [species names](species_names.md) page
lists every renamed species. In game, everything shows the Pokemon Z Team Training names.

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
