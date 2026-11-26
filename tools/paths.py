"""Repository layout used by every build tool."""
import os

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
WORLD = os.path.join(ROOT, "worlds", "pokemon_z_team_training")
TRACKER = os.path.join(ROOT, "tracker")
DIST = os.path.join(ROOT, "dist")              # release artifacts (not tracked)
BUILD = os.path.join(ROOT, "build")            # local build cache, ROMs (not tracked)
DATA = os.path.join(TOOLS, "data")             # symbol maps
UPSTREAM_WORLD = os.path.join(TOOLS, "upstream", "pokemon_frlg")

HACK_BPS = os.path.join(WORLD, "data", "pokemon_z_team_training.bps")
AP_BASE_PATCH = os.path.join(UPSTREAM_WORLD, "data", "base_patch_firered.bsdiff4")
UPSTREAM_DATA = os.path.join(UPSTREAM_WORLD, "data", "extracted_data.json")
FINAL_BASE_ROM = os.path.join(BUILD, "transplanted_base.gba")
