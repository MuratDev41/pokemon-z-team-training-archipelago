# Pokemon Z Team Training Setup Guide

## Required Software

* [Archipelago](https://github.com/ArchipelagoMW/Archipelago/releases) 0.6.7 or newer
* `pokemon_z_team_training.apworld`
* [BizHawk](https://tasvideos.org/BizHawk/ReleaseHistory) 2.10 or newer
* A clean English **Pokémon FireRed (USA) 1.0** ROM
  * `md5: e26ee0d44e809351c8ce2d73c7400cdd`, `sha1: 41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc`
  * FireRed 1.1, LeafGreen and pre-patched Pokemon Z Team Training ROMs do **not** work.
    You do not need the hack's ROM or `.bps` patch: it is included in the apworld.

Place `pokemon_z_team_training.apworld` in your Archipelago installation's `custom_worlds` folder
(default on Windows: `%programdata%/Archipelago/custom_worlds`), or double-click it to install.

This world can be installed next to the Pokémon FireRed and LeafGreen world. They are separate games.

## Generating and Patching

1. Open `ArchipelagoLauncher.exe` and select "Generate Template Options" to create a default YAML for
   "Pokemon Z Team Training", or use the Options Creator.
2. Edit the YAML and place it in the `Players` folder.
3. Run `ArchipelagoGenerate.exe`. Your patch file ends in `.apztt`.
4. Open `ArchipelagoLauncher.exe`, select "Open Patch" and choose your `.apztt` file.
5. The first time, you are asked for your FireRed (USA) 1.0 ROM. It is stored in `host.yaml` under
   `pokemon_z_team_training_settings`.
6. A patched `.gba` file is created next to the patch file.
7. The first time you open a patch with the BizHawk Client, you are also asked for `EmuHawk.exe`.

## Connecting to a Server

Opening a patch file normally does steps 1–5 for you.

1. Pokemon Z Team Training uses Archipelago's BizHawk Client. Reopen it from the launcher if needed.
2. Make sure EmuHawk is running the patched ROM.
3. In EmuHawk, open `Tools > Lua Console` and keep it open while playing.
4. In the Lua Console, choose `Script > Open Script…`.
5. Open `data/lua/connector_bizhawk_generic.lua` from your Archipelago folder.
6. The BizHawk Client shows that it connected and recognised Pokemon Z Team Training.
7. Enter your room's address (for example `archipelago.gg:38281`) in the client and click Connect.

It is safe to play offline; progress syncs when you reconnect.

## Tracking

Use `pokemon-z-team-training-tracker.zip`, the Pokémon FireRed/LeafGreen PopTracker pack ported to this game
(DBZ names and icons, same locations and autotracking). Put it in PopTracker's `packs` folder, load
"Pokemon Z Team Training Tracker", click the AP icon and connect with your room address and slot name.
For Universal Tracker, set `ut_poptracker_path` under `pokemon_z_team_training_settings` in `host.yaml` to the zip.
