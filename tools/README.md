# Build tools

Requirements: Python 3.11+, `pip install -r tools/requirements.txt`, and a clean Pokémon FireRed (USA) 1.0 ROM
(md5 `e26ee0d44e809351c8ce2d73c7400cdd`). Run everything from the repository root.

## Build the apworld

```
python tools/make_apworld.py "<FireRed 1.0.gba>"
```

This transplants the hack into the Archipelago base ROM, writes `data/ztt_plan.bin`, regenerates
`data/extracted_data.json` and the evolution events, checks that the runtime path from a clean ROM reproduces the build
byte for byte, and writes `dist/pokemon_z_team_training.apworld`. It also leaves `build/transplanted_base.gba`, which
the tracker port reads.

## Build the tracker

Unzip the upstream [Pokémon FireRed/LeafGreen tracker](https://github.com/vyneras/pokemon-frlg-tracker/releases)
somewhere (for example `build/tracker_upstream`), then:

```
python tools/port_tracker.py "<FireRed 1.0.gba>" build/tracker_upstream
```

This writes `tracker/` and `dist/pokemon-z-team-training-tracker.zip`.

## Scripts

| Script | Purpose |
|---|---|
| `make_apworld.py` | Full build of the world (see above). |
| `port_tracker.py` | Ports the FRLG PopTracker pack: game name, species names and the hack's icons. |
| `transplant.py` | The transplant passes (in-place data, species, moves, trainers, items, graphics, tilesets, layouts, animations, music, code literals). |
| `core.py` | ROM loading, symbol mapping between the vanilla and Archipelago layouts, allocator, plan writer. |
| `anim.py` | Battle animation script parser. |
| `battlescript.py`, `battlescript_table.py` | Battle script parser and command table (move effects). |
| `mapcheck.py` | Movement/reachability model for maps (collision, elevation, ledges, Surf, Waterfall, special tiles, encounters). |
| `mapport.py` | Decides which of the hack's map layouts and tilesets keep Archipelago's reachability. |
| `verify_maps.py` | Re-checks every map of the built ROM against the Archipelago base. |
| `render_map.py` | Renders a map from a ROM to an image, for visual checks. |
| `species_rename.py` | Gives Archipelago the hack's species and item names. |
| `place_rename.py` | Renames locations and Archipelago-only items after the hack's places, characters and trainers. |
| `regen.py` | Re-derives species, moves, trainers, encounters, trades and TM data from a ROM, like the upstream extractor. |
| `evolutions.py` | Rebuilds the evolution events from the hack's evolution table. |
| `species_table.py` | Writes `docs/species_names.md`. |
| `align.py` | Derives `data/shipped_syms.json` from a local build of the Archipelago decomp. Only needed when the upstream base patch changes. |
| `check_regen.py` | Checks that `regen.py` reproduces the upstream data from the untouched Archipelago ROM. |
| `check_mapping.py` | Checks the vanilla → Archipelago symbol mapping. |
| `data/setmetatile.json` | Metatiles that scripts/field code swap at runtime, per tileset (from the decomp). |
| `patch_apztt.py` | Patches a `.apztt` outside Archipelago, for testing. |
| `testing/boot_smoke.lua` | BizHawk script: mashes through the intro and saves screenshots (`ZT_OUT` env var = output prefix). |
| `bps.py`, `gba_text.py`, `paths.py` | BPS applier, GBA text decoder, repository paths. |

## Updating to a new upstream world version

1. Replace `tools/upstream/pokemon_frlg` with the new release.
2. Build the matching `vyneras/pokefirered` commit, copy its `.sym` to `tools/data/pokefirered_ap.sym`, and run
   `python tools/align.py "<FireRed 1.0.gba>" <built pokefirered_ap.gba>`.
3. Copy the new upstream world code into `worlds/pokemon_z_team_training`, re-applying this world's changes
   (`rom.py`, `zt_patch.py`, `world.py`, `client.py`, `options.py`, `archipelago.json`, docs).
4. Run `check_regen.py`, then `make_apworld.py`.
