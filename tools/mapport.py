"""
Decide which of the hack's map layouts and tilesets can replace Archipelago's, without changing what any
Archipelago location, warp, connection or scripted tile change needs (see mapcheck.py).

Each map layout (shared by every map that uses it) gets the first option that passes for all of its maps:
  HACK_LAYOUT   the hack's blocks and its own copy of the hack's secondary tileset
  HACK_TILESET  Archipelago's blocks (unchanged by the hack) with the hack's tileset copy, i.e. the hack's re-skin
  KEEP          Archipelago's blocks and tileset
The shared primary tileset (General) takes the hack's changed metatiles; the hack and Archipelago edit different
metatiles there, and every map is checked with the merged set.
"""
import json
import os

from core import ROM, u16, u32
from mapcheck import Layout, read_attrs, read_events, equivalent
from paths import DATA

HACK_LAYOUT, HACK_MERGED, HACK_TILESET, KEEP = "hack_layout", "hack_merged", "hack_tileset", "keep"


def map_headers(rom, groups_off, ngroups=43):
    out = {}
    for g in range(ngroups):
        gp = u32(rom, groups_off + 4 * g)
        nxt = u32(rom, groups_off + 4 * (g + 1)) if g + 1 < ngroups else None
        if not (ROM <= gp < ROM + len(rom)):
            break
        n = 0
        while True:
            off = gp - ROM + 4 * n
            if nxt and off == nxt - ROM:
                break
            hp = u32(rom, off)
            if not (ROM <= hp < ROM + len(rom)) or n > 120:
                break
            out[(g, n)] = hp
            n += 1
    return out


def blocks_of(rom, layout_ptr):
    lo = layout_ptr - ROM
    w, h = u32(rom, lo), u32(rom, lo + 4)
    bp = u32(rom, lo + 12) - ROM
    if not (0 < w <= 0x100 and 0 < h <= 0x100 and 0 <= bp and bp + 2 * w * h <= len(rom)):
        raise ValueError("not a layout")
    return w, h, [u16(rom, bp + 2 * i) for i in range(w * h)]


class MapPorter:
    def __init__(self, ctx):
        self.c = c = ctx
        self.ap_maps = map_headers(c.A0, c.aa("gMapGroups"))
        self.v_maps = map_headers(c.V, c.va("gMapGroups"))
        self.z_maps = map_headers(c.Z, c.va("gMapGroups"))
        gen_a, gen_v = c.aa("gTileset_General"), c.va("gTileset_General")
        a_attr = read_attrs(c.A0, ROM + gen_a, 0x280)
        v_attr = read_attrs(c.V, ROM + gen_v, 0x280)
        z_attr = read_attrs(c.Z, ROM + gen_v, 0x280)
        self.general_hack_ids = [i for i in range(0x280) if z_attr[i] != v_attr[i]]
        self.general_ap = a_attr
        self.general_merged = [z_attr[i] if i in self.general_hack_ids else a_attr[i] for i in range(0x280)]
        # metatiles that scripts and field code swap in at runtime (setmetatile / MapGridSetMetatileIdAt),
        # keyed by the tileset their label belongs to
        self.script_tiles = {k: set(v) for k, v in json.load(open(os.path.join(DATA, "setmetatile.json"))).items()}
        self._cache = {}
        self.layouts = self._group_layouts()

    # ---------- helpers ----------
    def tileset_name(self, ptr):
        f = self.c.vfind(ptr - ROM)
        return f[0][len("gTileset_"):] if f and f[0].startswith("gTileset_") else None

    def tileset_changed(self, name):
        """True if the hack changed the tileset's graphics, palettes, metatiles or attributes."""
        c = self.c
        if name is None or "gTileset_" + name not in c.vsym:
            return False
        t = c.va("gTileset_" + name)
        if c.Z[t:t + 24] != c.V[t:t + 24]:
            return True
        for sym in ("gTilesetTiles_", "gTilesetPalettes_", "gMetatiles_", "gMetatileAttributes_"):
            if sym + name in c.vsym:
                o, s = c.vsym[sym + name]
                if s and c.Z[o:o + s] != c.V[o:o + s]:
                    return True
        return False

    def _group_layouts(self):
        """AP layout pointer -> info about the layout and every map that uses it."""
        c = self.c
        groups = {}
        for key, ahp in self.ap_maps.items():
            vhp, zhp = self.v_maps.get(key), self.z_maps.get(key)
            if not vhp or not zhp:
                continue
            a_lay, v_lay, z_lay = u32(c.A0, ahp - ROM), u32(c.V, vhp - ROM), u32(c.Z, zhp - ROM)
            if not all(ROM <= p < ROM + len(c.A0) for p in (a_lay, v_lay, z_lay)):
                continue
            try:
                a = blocks_of(c.A0, a_lay)
                v = blocks_of(c.V, v_lay)
                z = blocks_of(c.Z, z_lay)
            except ValueError:
                continue
            g = groups.setdefault(a_lay, dict(maps=[], a=a, v=v, z=z, v_lay=v_lay, z_lay=z_lay,
                                              sec=self.tileset_name(u32(c.V, v_lay - ROM + 20))))
            g["maps"].append((key, ahp))
        return groups

    def options(self, info):
        hack_edited = info["z"] != info["v"]
        ap_edited = info["a"] != info["v"]
        ts_changed = self.tileset_changed(info["sec"])
        opts = []
        if hack_edited and not ap_edited:
            opts.append(HACK_LAYOUT)
        if hack_edited and ap_edited and info["z"][:2] == info["a"][:2] == info["v"][:2]:
            opts.append(HACK_MERGED)
        if not hack_edited and not ap_edited and ts_changed:
            opts.append(HACK_TILESET)
        return opts, hack_edited, ap_edited, ts_changed

    @staticmethod
    def merged_blocks(info):
        """The hack's blocks, with Archipelago's own block edits (vs vanilla) laid back on top."""
        _, _, ablk = info["a"]
        _, _, vblk = info["v"]
        _, _, zblk = info["z"]
        return [a if a != v else z for a, v, z in zip(ablk, vblk, zblk)]

    def check(self, a_lay, option):
        ck = (a_lay, option)
        if ck in self._cache:
            return self._cache[ck]
        c = self.c
        info = self.layouts[a_lay]
        aw, ah, ablk = info["a"]
        base_sec = read_attrs(c.A0, u32(c.A0, a_lay - ROM + 20), 0x180)
        base = Layout(aw, ah, ablk, self.general_ap, base_sec)
        sec_ptr_v = u32(c.V, info["v_lay"] - ROM + 20)
        if option == KEEP:
            cand = Layout(aw, ah, ablk, self.general_merged, base_sec)
        else:
            hack_sec = read_attrs(c.Z, sec_ptr_v, 0x180) if self.tileset_changed(info["sec"]) else base_sec
            if option == HACK_LAYOUT:
                zw, zh, zblk = info["z"]
                cand = Layout(zw, zh, zblk, self.general_merged, hack_sec)
            elif option == HACK_MERGED:
                cand = Layout(aw, ah, self.merged_blocks(info), self.general_merged, hack_sec)
            else:
                cand = Layout(aw, ah, ablk, self.general_merged, hack_sec)
        result = (True, "ok")
        # tiles that scripts swap in at runtime must behave the same
        for mid in self.script_tiles.get("General", set()) | self.script_tiles.get(info["sec"], set()):
            tb, tc = (base.prim, cand.prim) if mid < 0x280 else (base.sec, cand.sec)
            i = mid if mid < 0x280 else mid - 0x280
            if i < len(tb) and i < len(tc) and tb[i] != tc[i]:
                result = (False, "scripted metatile %#x changes behaviour" % mid)
                break
        for key, ahp in info["maps"]:
            if not result[0]:
                break
            ok, why = equivalent(base, cand, read_events(c.A0, ahp))
            if not ok:
                result = (False, "%s: %s" % (key, why))
                break
        self._cache[ck] = result
        return result

    def solve(self):
        """Per layout: the chosen option, plus the reasons hack layouts were not taken."""
        decisions, reasons = {}, {}
        for a_lay, info in self.layouts.items():
            opts, hack_edited, _, _ = self.options(info)
            choice = KEEP
            for o in opts:
                ok, why = self.check(a_lay, o)
                if ok:
                    choice = o
                    break
                reasons[a_lay] = why
            if choice == KEEP:
                ok, why = self.check(a_lay, KEEP)
                if not ok:
                    raise RuntimeError("layout %x fails even unchanged: %s" % (a_lay, why))
            decisions[a_lay] = choice
        return decisions, reasons
