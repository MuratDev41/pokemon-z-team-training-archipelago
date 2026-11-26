"""Apply an .apztt the same way the apworld does (for testing outside Archipelago)."""
import io, json, sys, zipfile, os
import bsdiff4
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import WORLD  # noqa: E402
sys.path.insert(0, WORLD)
from zt_patch import apply_bps, apply_plan


def tokens(rom, token_data):
    rom = bytearray(rom)
    n = int.from_bytes(token_data[0:4], "little")
    p = 4
    for _ in range(n):
        t = token_data[p]
        off = int.from_bytes(token_data[p + 1:p + 5], "little")
        size = int.from_bytes(token_data[p + 5:p + 9], "little")
        d = token_data[p + 9:p + 9 + size]
        assert t == 0, "this world only emits WRITE tokens"
        rom[off:off + len(d)] = d
        p += 9 + size
    return bytes(rom)


def patch(apztt, vanilla, out):
    z = zipfile.ZipFile(apztt)
    files = {os.path.basename(n): z.read(n) for n in z.namelist()}
    v = open(vanilla, "rb").read()
    hack = apply_bps(v, files["pokemon_z_team_training.bps"])
    rom = bsdiff4.patch(v, files["base_patch_rev0.bsdiff4"])
    rom = apply_plan(rom, hack, files["ztt_plan.bin"])
    rom = tokens(rom, files["token_data_rev0.bin"])
    open(out, "wb").write(rom)


if __name__ == "__main__":
    patch(sys.argv[1], sys.argv[2], sys.argv[3])
