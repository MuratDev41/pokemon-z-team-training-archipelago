"""
Transplant Pokemon Z Team Training content into the Archipelago FireRed base ROM.

Policy (AP-first): Archipelago's maps, event scripts, item/flag logic and code stay as they are.
The hack's content is carried over wherever it does not touch that logic:
species, moves, abilities, items' text/icons, trainers, texts, graphics, tilesets,
music/cries and the title/intro screens.
"""
import bisect
import struct
import sys

from core import Ctx, ROM, VANILLA_END, is_vanilla, u8, u16, u32, s16, lz_len

CODE_END = 0x1E8000
NUM_SPECIES = 412
NUM_MOVES = 355

# Symbols the generic in-place pass must leave alone: AP owns map logic, shops, heal points,
# the header, and these get typed handling elsewhere.
SKIP_SUBSTR = ("EventScript", "MapScripts", "Movement", "OnTransition", "OnFrame", "OnLoad", "OnResume",
               "OnWarp", "OnReturnToField", "_Items", "ObjectEvents", "MapWarps", "MapCoordEvents",
               "MapBGEvents", "MapEvents", "Layout_Blockdata", "Layout_Border", "MetatileAttributes",
               "RomHeader", "gMultiBoot", "sTrainerTowerFloor", "mus_", "se_", "LevelUpLearnset",
               "sHealLocations", "gBattleMoves", "gTrainers", "gItems", "Std_", "Common_", "EventScript_",
               "_Script", "Script_", "gBattleAnims", "Move_", "gBattleScripts", "BattleScript_",
               "gMonFrontPicTable", "gMonBackPicTable", "gMonPaletteTable", "gMonShinyPaletteTable",
               "gMonFootprintTable", "gMonIconTable", "gTrainerFrontPicTable", "gTrainerFrontPicPaletteTable",
               "gBallSprite", "gTileset_", "gCryTable", "gSongTable", "sItemIconTable", "voicegroup",
               "gPokedexEntries", "DirectSoundWaveData", "Cry_",
               # the hack renumbers the national dex; Archipelago keeps the original numbers
               "sSpeciesToNationalPokedexNum",
               # dex texts are repacked by the hack; pokedex_entries() copies each species' text instead
               "PokedexText",
               # tileset data: General is merged per metatile and secondaries are copied (pass_maps)
               "gTilesetTiles_", "gTilesetPalettes_", "gMetatiles_")


# pointer-free tables whose bytes merely look like pointers
PLAIN = {"gEnemyMonElevation", "gTypeEffectiveness", "gSpeciesInfo"}
PLAIN_PREFIX = ("gMonIcon_", "gObjectEventPic_", "gTilesetTiles_", "gMetatiles_")


class Transplanter:
    def __init__(self, ctx: Ctx):
        self.c = ctx
        self.starts = sorted(set(x[0] for x in ctx.vlist))
        self.vstart_set = set(self.starts)
        self.stats = {}
        self.skipped = []
        self.done_ranges = []
        self.needs_typed = []

    def stat(self, k, n=1):
        self.stats[k] = self.stats.get(k, 0) + n

    def extent(self, idx):
        o, s, n = self.c.vlist[idx]
        if s:
            return s
        j = bisect.bisect_right(self.starts, o)
        return (self.starts[j] if j < len(self.starts) else VANILLA_END) - o

    # ------------------------------------------------------------------
    # Pass 1: in-place data the AP base never touched (texts, names, stats, graphics, parties ...)
    # ------------------------------------------------------------------
    def pass_inplace(self):
        c = self.c
        seen = set()
        for idx, (o, s, n) in enumerate(c.vlist):
            if not is_vanilla(o) or o in seen:
                continue
            ln = self.extent(idx)
            if ln <= 0 or ln > 0x40000:
                continue
            z = c.Z[o:o + ln]
            v = c.V[o:o + ln]
            if z == v:
                continue
            seen.add(o)
            if any(k in n for k in SKIP_SUBSTR):
                self.stat("inplace_skip_policy")
                continue
            if o < CODE_END and "Text" not in n:
                # code / script region: only text is carried over generically
                self.stat("inplace_skip_code")
                self.skipped.append(n)
                continue
            m = c.map_entry(idx)
            if not m:
                self.stat("inplace_unmapped")
                self.skipped.append(n)
                continue
            ao, asz = m
            if asz and asz != ln and s:
                self.stat("inplace_size_mismatch")
                self.skipped.append(n)
                continue
            if c.A0[ao:ao + ln] != v:
                self.stat("inplace_ap_changed")
                self.skipped.append(n)
                continue
            if "Text" in n and o < CODE_END:
                # a text in the script area must still terminate inside its own slot
                if 0xFF not in z:
                    self.stat("inplace_text_overflow")
                    self.skipped.append(n)
                    continue
            if n not in PLAIN and not n.startswith(PLAIN_PREFIX) and self.hack_wrote_pointer(o, ln):
                self.stat("inplace_has_pointer")
                self.needs_typed.append(n)
                continue
            c.copy_diff(ao, o, ln, c.V)
            self.stat("inplace_ok")

    def hack_wrote_pointer(self, o, ln):
        c = self.c
        for i in range(0, ln - 3):
            if (o + i) % 4:
                continue
            zw = u32(c.Z, o + i)
            if zw == u32(c.V, o + i) or not (ROM <= (zw & ~1) < ROM + 0x01000000):
                continue
            t = (zw & ~1) - ROM
            if is_vanilla(t):
                if t in self.vstart_set:
                    return True
            elif c.Z[t:t + 4] != bytes(4 * [0xFF]):
                return True
        return False

    # ------------------------------------------------------------------
    # Species
    # ------------------------------------------------------------------
    def table_ptrs(self, name, entry, count, ptr_off, resolver, fallback=None):
        """Per-entry pointer table: translate/copy the pointer, copy changed non-pointer bytes.
        fallback(i) gives a replacement hack pointer when the hack's own pointer is unusable."""
        c = self.c
        vo, ao = c.va(name), c.aa(name)
        for i in range(count):
            ve, ae = vo + entry * i, ao + entry * i
            z = c.Z[ve:ve + entry]
            if z == c.V[ve:ve + entry]:
                continue
            for po in ptr_off:
                zp = u32(z, po)
                vp = u32(c.V, ve + po)
                if zp != vp:
                    if vp and c.map_ptr(vp) != u32(c.A0, ae + po):
                        self.c.log.append("%s[%d]+%d: AP customised this entry, kept AP" % (name, i, po))
                        self.stat(name + "_ap_kept")
                        continue
                    try:
                        np = resolver(zp)
                    except ValueError as e:
                        np = None
                        if fallback:
                            try:
                                np = resolver(fallback(i))
                            except ValueError:
                                np = None
                        self.c.log.append("%s[%d]: %s -> %s" % (name, i, e, "fallback" if np else "kept AP"))
                    if np is None:
                        self.stat(name + "_unresolved")
                        continue
                    c.w32(ae + po, np)
            # other bytes
            for k in range(entry):
                if any(po <= k < po + 4 for po in ptr_off):
                    continue
                if z[k] != c.V[ve + k]:
                    c.copy(ae + k, ve + k, 1)
            self.stat(name)

    def pass_species(self):
        c = self.c
        lz = c.lz
        self.table_ptrs("gMonFrontPicTable", 8, NUM_SPECIES, (0,), lz)
        self.table_ptrs("gMonBackPicTable", 8, NUM_SPECIES, (0,), lz)
        self.table_ptrs("gMonPaletteTable", 8, NUM_SPECIES, (0,), lz)
        pal = c.va("gMonPaletteTable")
        self.table_ptrs("gMonShinyPaletteTable", 8, NUM_SPECIES, (0,), lz,
                        fallback=lambda i: u32(c.Z, pal + 8 * i))
        self.table_ptrs("gMonIconTable", 4, 440, (0,), lambda p: c.raw(p, 0x400))
        self.table_ptrs("gMonIconPaletteIndices", 1, 440, (), None)
        self.table_ptrs("gMonFootprintTable", 4, 413, (0,), lambda p: c.raw(p, 32))
        self.pokedex_entries()
        self.learnsets()
        self.evolutions()

    def pokedex_entries(self):
        """The hack renumbers the national Pokedex. Archipelago's client and logic read Pokedex flags by the
        original numbers, so the original numbering stays and each species' hack entry is moved to its slot.
        Entry: categoryName[12], height, weight, description*, unusedDescription*, scales/offsets."""
        c = self.c
        nat = c.va("sSpeciesToNationalPokedexNum")
        vo, ao = c.va("gPokedexEntries"), c.aa("gPokedexEntries")
        done = set()
        for sp in range(1, NUM_SPECIES):
            vd = u16(c.V, nat + 2 * (sp - 1))
            hd = u16(c.Z, nat + 2 * (sp - 1))
            if not vd or vd in done or vd > 386 or hd > 386:
                continue
            names = c.va("gSpeciesNames") + 11 * sp
            renamed = c.Z[names:names + 11] != c.V[names:names + 11]
            if hd != vd and not renamed:
                # e.g. Dratini..Mew: the hack parked these on Gen 3 slots; keep FireRed's entry
                continue
            done.add(vd)
            src, dst = vo + 36 * hd, ao + 36 * vd
            if c.Z[src:src + 36] == c.V[vo + 36 * vd:vo + 36 * vd + 36]:
                continue
            for k in (0, 12, 24):
                end = {0: 12, 12: 16, 24: 36}[k]
                c.copy(dst + k, src + k, end - k)
            for po in (16, 20):
                c.w32(dst + po, c.text(u32(c.Z, src + po)))
            self.stat("gPokedexEntries")

    def learnset_moves(self, rom, off):
        out = []
        while True:
            w = u16(rom, off + 2 * len(out))
            if w == 0xFFFF:
                return out
            out.append(w)
            if len(out) > 64:
                raise ValueError("learnset too long at %x" % off)

    def learnsets(self):
        c = self.c
        vt, at = c.va("gLevelUpLearnsets"), c.aa("gLevelUpLearnsets")
        self.learnset_info = {}
        for sp in range(NUM_SPECIES):
            vp = u32(c.V, vt + 4 * sp) - ROM
            zp = u32(c.Z, vt + 4 * sp) - ROM
            ap = u32(c.A0, at + 4 * sp) - ROM
            vl = self.learnset_moves(c.V, vp)
            zl = self.learnset_moves(c.Z, zp)
            al = self.learnset_moves(c.A0, ap)
            if zl == vl:
                continue
            # AP pads short learnsets with blank level-1 entries so the randomizer has room
            pad = len(al) - len(vl) if al[len(al) - len(vl):] == vl else 0
            new = [1 << 9] * pad + zl     # level 1, move 0
            data = b"".join(struct.pack("<H", w) for w in new) + b"\xff\xff"
            if len(new) <= len(al):
                dst = ap
            else:
                dst = c.alloc(len(data))
                c.w32(at + 4 * sp, ROM + dst)
            # blank padding entries are WRITEs; the hack's moves are COPYs
            c.write(dst, data[:2 * pad])
            c.copy(dst + 2 * pad, zp, 2 * len(zl))
            c.write(dst + 2 * len(new), b"\xff\xff")
            self.stat("learnsets")

    def evolutions(self):
        c = self.c
        vo, ao = c.va("gEvolutionTable"), c.aa("gEvolutionTable")
        for sp in range(NUM_SPECIES):
            for e in range(5):
                o = 40 * sp + 8 * e
                z = c.Z[vo + o:vo + o + 8]
                v = c.V[vo + o:vo + o + 8]
                a = c.A0[ao + o:ao + o + 8]
                if z == v:
                    continue
                # AP rewrites some evolutions (e.g. trade evolutions); the hack's own edit wins
                c.copy(ao + o, vo + o, 8)
                self.stat("evolutions" + ("_over_ap" if a != v else ""))

    # ------------------------------------------------------------------
    # Moves and abilities
    # ------------------------------------------------------------------
    def pass_moves(self, damage_type_table):
        c = self.c
        vo, ao = c.va("gBattleMoves"), c.aa("gBattleMoves")
        for m in range(NUM_MOVES):
            z = c.Z[vo + 12 * m:vo + 12 * m + 12]
            v = c.V[vo + 12 * m:vo + 12 * m + 12]
            if z == v:
                continue
            c.copy(ao + 12 * m, vo + 12 * m, 9)          # everything up to flags
            power, mtype = z[1], z[2]
            cat = 2 if power == 0 else damage_type_table[mtype]
            c.write(ao + 12 * m + 9, bytes([cat]))      # AP's physical/special category byte
            self.stat("moves")
        self.table_ptrs("gMoveDescriptionPointers", 4, NUM_MOVES - 1, (0,), c.text)
        self.table_ptrs("gAbilityDescriptionPointers", 4, 78, (0,), c.text)

    # ------------------------------------------------------------------
    # Trainers
    # ------------------------------------------------------------------
    def pass_trainers(self):
        c = self.c
        vo, ao = c.va("gTrainers"), c.aa("gTrainers")
        for t in range(743):
            ve, ae = vo + 40 * t, ao + 40 * t
            z, v = c.Z[ve:ve + 40], c.V[ve:ve + 40]
            if z == v:
                continue
            for k in range(36):
                if z[k] != v[k]:
                    c.copy(ae + k, ve + k, 1)
            if u32(z, 36) != u32(v, 36):
                np = c.map_ptr(u32(z, 36))
                assert np is not None
                c.w32(ae + 36, np)
            self.stat("trainers")
        self.table_ptrs("gTrainerFrontPicTable", 8, 148, (0,), c.lz)
        self.table_ptrs("gTrainerFrontPicPaletteTable", 8, 148, (0,), c.lz)

    # ------------------------------------------------------------------
    # Generic graphics resolver
    # ------------------------------------------------------------------
    def gfx(self, p, vanilla_ptr=None):
        """LZ data if the target is a valid LZ stream, else raw data sized like the vanilla asset it replaces."""
        c = self.c
        off = p - ROM
        if not (0 <= off < len(c.Z) - 4):
            raise ValueError("not a ROM pointer: %x" % p)
        n = lz_len(c.Z, off)
        if n:
            return c.lz(p)
        size = None
        if vanilla_ptr:
            f = c.vfind(vanilla_ptr - ROM)
            if f and f[2] and f[3] == 0:
                size = f[2]
        if not size:
            raise ValueError("cannot size raw gfx at %x" % off)
        return c.raw(p, size)

    # ------------------------------------------------------------------
    # Items: names, descriptions, hold effects and icons where AP left the item alone
    # ------------------------------------------------------------------
    def pass_items(self):
        c = self.c
        vo, ao = c.va("gItems"), c.aa("gItems")
        for i in range(375):
            ve, ae = vo + 44 * i, ao + 44 * i
            z, v, a = c.Z[ve:ve + 44], c.V[ve:ve + 44], c.A0[ae:ae + 44]
            if z == v:
                continue
            if z[0:14] != v[0:14] and a[0:14] == v[0:14]:
                c.copy(ae, ve, 14)
                self.stat("item_names")
            if z[18:20] != v[18:20] and a[18:20] == v[18:20]:
                c.copy(ae + 18, ve + 18, 2)
                self.stat("item_hold")
            zd, vd = u32(z, 20), u32(v, 20)
            if zd != vd and c.map_ptr(vd) == u32(a, 20):
                c.w32(ae + 20, c.text(zd))
                self.stat("item_desc")
        self.table_ptrs("sItemIconTable", 8, 376, (0, 4), c.lz)

    # ------------------------------------------------------------------
    # Tilesets (the hack repointed tile graphics) and map blockdata
    # ------------------------------------------------------------------
    def pass_tilesets(self):
        c = self.c
        for idx, (o, s, n) in enumerate(c.vlist):
            if not n.startswith("gTileset_") or s != 24 or not is_vanilla(o):
                continue
            if c.V[o + 1]:
                continue                                      # secondary: handled by pass_maps
            z, v = c.Z[o:o + 24], c.V[o:o + 24]
            if z == v:
                continue
            m = c.map_entry(idx)
            if not m:
                continue
            ao = m[0]
            # tiles, palettes, metatiles (callback and attributes stay AP's: they define behaviour)
            for fo in (4, 8, 12):
                zp, vp = u32(z, fo), u32(v, fo)
                if zp == vp:
                    continue
                if c.map_ptr(vp) != u32(c.A0, ao + fo):
                    self.stat("tileset_ap_kept")
                    continue
                if fo == 4:
                    np = c.lz(zp) if z[0] else self.gfx(zp, vp)
                else:
                    np = self.gfx(zp, vp)
                c.w32(ao + fo, np)
                self.stat("tileset_ptrs")

    # ------------------------------------------------------------------
    # Maps: the hack's layouts and tilesets where Archipelago's reachability is provably unchanged (mapport.py)
    # ------------------------------------------------------------------
    def tileset_copy(self, name):
        """A separate copy of the hack's version of a secondary tileset, so maps can switch one by one."""
        c = self.c
        key = ("tileset", name)
        if key in c.copied:
            return ROM + c.copied[key]
        zt, vt, at = c.va("gTileset_" + name), c.va("gTileset_" + name), c.aa("gTileset_" + name)

        def size_of(vptr):
            f = c.vfind(vptr - ROM)
            if not f or not f[2] or f[3]:
                raise ValueError("cannot size %s data at %x" % (name, vptr))
            return f[2]

        z, v = c.Z[zt:zt + 24], c.V[vt:vt + 24]
        tiles = u32(z, 4)
        tiles_np = c.lz(tiles) if z[0] else c.raw(tiles, size_of(u32(v, 4)))
        pals_np = c.raw(u32(z, 8), size_of(u32(v, 8)))
        meta_np = c.raw(u32(z, 12), size_of(u32(v, 12)))
        attr_np = c.raw(u32(z, 20), size_of(u32(v, 20)))
        dst = c.alloc(24)
        c.copied[key] = dst
        c.copy(dst, zt, 4)                                   # isCompressed, isSecondary
        for off, val in ((4, tiles_np), (8, pals_np), (12, meta_np), (20, attr_np)):
            c.w32(dst + off, val)
        c.w32(dst + 16, u32(c.A0, at + 16))                  # Archipelago's tile animation callback
        self.stat("map_tileset_copies")
        return ROM + dst

    def merge_general(self):
        """The hack's changed metatiles in the shared General tileset (Archipelago changes different ones)."""
        c = self.c
        for sym, entry in (("gMetatiles_General", 16), ("gMetatileAttributes_General", 4)):
            vo, s = c.vsym[sym]
            ao = c.aa(sym)
            for i in range(s // entry):
                z = c.Z[vo + entry * i:vo + entry * (i + 1)]
                v = c.V[vo + entry * i:vo + entry * (i + 1)]
                a = c.A0[ao + entry * i:ao + entry * (i + 1)]
                if z != v:
                    assert a == v, "%s %d edited by both" % (sym, i)
                    c.copy(ao + entry * i, vo + entry * i, entry)
                    self.stat("general_" + sym.split("_")[0][1:])

    def pass_maps(self):
        from mapport import MapPorter, HACK_LAYOUT, HACK_MERGED, HACK_TILESET
        c = self.c
        self.merge_general()
        porter = MapPorter(c)
        decisions, self.map_rejections = porter.solve()
        self.map_porter, self.map_decisions = porter, decisions
        for a_lay, choice in decisions.items():
            info = porter.layouts[a_lay]
            ao = a_lay - ROM
            if choice in (HACK_LAYOUT, HACK_MERGED, HACK_TILESET) and porter.tileset_changed(info["sec"]):
                c.w32(ao + 20, self.tileset_copy(info["sec"]))
            if choice in (HACK_LAYOUT, HACK_MERGED):
                ab = u32(c.A0, ao + 12) - ROM
                zb = u32(c.Z, info["z_lay"] - ROM + 12) - ROM
                w, h = u32(c.A0, ao), u32(c.A0, ao + 4)
                take = [True] * (w * h)
                if choice == HACK_MERGED:
                    _, _, ablk = info["a"]
                    _, _, vblk = info["v"]
                    take = [a == v for a, v in zip(ablk, vblk)]
                k = 0
                while k < w * h:                              # copy runs of taken blocks
                    if not take[k]:
                        k += 1
                        continue
                    j = k
                    while j < w * h and take[j]:
                        j += 1
                    c.copy(ab + 2 * k, zb + 2 * k, 2 * (j - k))
                    k = j
                # border blocks (what you see past the map edge)
                zl = info["z_lay"] - ROM
                if c.Z[zl + 24:zl + 26] == c.A0[ao + 24:ao + 26]:
                    bw, bh = c.A0[ao + 24], c.A0[ao + 25]
                    c.copy(u32(c.A0, ao + 8) - ROM, u32(c.Z, zl + 8) - ROM, 2 * bw * bh)
            self.stat("maps_" + choice)

    # ------------------------------------------------------------------
    # Misc graphics tables
    # ------------------------------------------------------------------
    def pass_graphics(self):
        c = self.c
        self.table_ptrs("gBallSpriteSheets", 8, 12, (0,), c.lz)
        self.table_ptrs("gBallSpritePalettes", 8, 12, (0,), c.lz)
        self.table_ptrs("gBattleAnimPicTable", 8, 289, (0,), c.lz)
        self.table_ptrs("gBattleAnimPaletteTable", 8, 289, (0,), c.lz)
        # start menu poke ball: uncompressed SpriteSheet {data, size, tag} / SpritePalette {data, tag}
        o = c.va("sSpriteSheet_MenuPokeball")
        size = u16(c.Z, o + 4)
        self.table_ptrs("sSpriteSheet_MenuPokeball", 8, 1, (0,), lambda p: c.raw(p, size))
        self.table_ptrs("sSpritePalette_MenuPokeball", 8, 1, (0,), lambda p: c.raw(p, 32))
        # battle backgrounds: the hack moved sBattleTerrainTable to 0x08F000B0 (20 x 5 pointers)
        vt, at = c.va("sBattleTerrainTable"), c.aa("sBattleTerrainTable")
        ht = 0xF000B0
        for i in range(20):
            for f in range(5):
                zp = u32(c.Z, ht + 20 * i + 4 * f)
                vp = u32(c.V, vt + 20 * i + 4 * f)
                if zp == vp:
                    continue
                if c.map_ptr(vp) != u32(c.A0, at + 20 * i + 4 * f):
                    self.stat("terrain_ap_kept")
                    continue
                try:
                    c.w32(at + 20 * i + 4 * f, self.gfx(zp, vp))
                    self.stat("terrain_ptrs")
                except ValueError as e:
                    c.log.append("terrain %d.%d: %s" % (i, f, e))

    # ------------------------------------------------------------------
    # Code: literal-pool repoints (graphics/text the hack swapped) and tiny immediate tweaks
    # ------------------------------------------------------------------
    GFX_LITERALS = ("CB2_InitTitleScreen", "LoadPokeStorageMenuGfx", "IntroCB_Scene2", "IntroCB_Scene3_Entrance",
                    "LoadCreditsMonPic", "LoadTrainerPic", "LoadBallGfx", "AddScrollIndicatorArrowPair")
    TEXT_LITERALS = ("GetProfOaksRatingMessageByCount",)
    # immediates worth carrying (title-screen cry, credits pic); roamer/intro-species tweaks are left to AP
    # (CreateNidoranFSprite is AP's: it shows the seed's randomized intro species)
    CODE_TWEAKS = ("SetTitleScreenScene_Cry", "LoadCreditsMonPic")

    def find_literal(self, af, asize, value):
        c = self.c
        hits = [i for i in range(af, af + asize + 0x200, 4) if u32(c.A0, i) == value]
        return hits

    def pass_code(self):
        c = self.c
        for name in self.GFX_LITERALS + self.TEXT_LITERALS + self.CODE_TWEAKS:
            vo, vs = c.vsym[name]
            af, asz = c.aa(name), c.asize(name)
            span = vs + 0x80
            i = 0
            while i < span:
                if c.V[vo + i] == c.Z[vo + i]:
                    i += 1
                    continue
                w = (vo + i) & ~3
                vw, zw = u32(c.V, w), u32(c.Z, w)
                i = w + 4 - vo
                is_ptr = ROM <= (vw & ~1) < ROM + 0x01000000 and ROM <= (zw & ~1) < ROM + 0x01000000
                if is_ptr:
                    if name in self.CODE_TWEAKS and name not in self.GFX_LITERALS:
                        continue
                    target = c.map_ptr(vw)
                    hits = self.find_literal(af, asz, target) if target else []
                    if len(hits) > 1 and af + (w - vo) in hits:
                        hits = [af + (w - vo)]      # same position as in vanilla: AP compiled it identically
                    if len(hits) != 1:
                        c.log.append("%s: literal %x not found once in AP (%d)" % (name, vw, len(hits)))
                        self.stat("code_literal_missing")
                        continue
                    try:
                        if is_vanilla((zw & ~1) - ROM):
                            np = c.map_ptr(zw)
                        elif name in self.TEXT_LITERALS:
                            np = c.text(zw)
                        else:
                            np = self.gfx(zw, vw)
                    except ValueError as e:
                        c.log.append("%s: %s" % (name, e))
                        continue
                    if np is None:
                        continue
                    c.w32(hits[0], np)
                    self.stat("code_literals")
                elif name in self.CODE_TWEAKS:
                    # instruction change: only if AP's function is byte-identical around it
                    d = w - vo
                    if af + d + 4 <= af + asz and c.A0[af + d - 4:af + d + 8] == c.V[w - 4:w + 8]:
                        c.copy(af + d, w, 4)
                        self.stat("code_tweaks")
                    else:
                        c.log.append("%s+%x: AP code differs, tweak skipped" % (name, d))

    # ------------------------------------------------------------------
    # Music: songs the hack replaced (title, credits, wild battle, ...)
    # ------------------------------------------------------------------
    def m4a_track_end(self, rom, off):
        i = off
        while True:
            b = rom[i]
            if b == 0xB1:
                return i + 1
            if b in (0xB2, 0xB3):
                i += 5
            elif b == 0xB5:
                i += 6
            else:
                i += 1
            if i - off > 0x20000:
                raise ValueError("runaway track at %x" % off)

    def copy_song(self, hp):
        c = self.c
        h = hp - ROM
        ntracks = c.Z[h]
        tracks = [u32(c.Z, h + 8 + 4 * t) - ROM for t in range(ntracks)]
        lo = min(tracks)
        hi = max(self.m4a_track_end(c.Z, t) for t in tracks)
        blob = c.alloc(hi - lo)
        c.copy(blob, lo, hi - lo)
        # relocate GOTO / PATT / REPT pointers inside the blob
        for t in tracks:
            i = t
            end = self.m4a_track_end(c.Z, t)
            while i < end:
                b = c.Z[i]
                if b in (0xB2, 0xB3, 0xB5):
                    po = i + (2 if b == 0xB5 else 1)
                    p = u32(c.Z, po) - ROM
                    if lo <= p < hi:
                        c.w32(blob + (po - lo), ROM + blob + (p - lo))
                    else:
                        mp = c.map_ptr(p + ROM)
                        if mp is None:
                            raise ValueError("song pointer %x outside" % p)
                        c.w32(blob + (po - lo), mp)
                    i = po + 4
                else:
                    i += 1
        hdr = c.alloc(8 + 4 * ntracks)
        c.copy(hdr, h, 4)
        vg = u32(c.Z, h + 4)
        mvg = c.map_ptr(vg)
        if mvg is None:
            raise ValueError("song voicegroup %x not vanilla" % vg)
        c.w32(hdr + 4, mvg)
        for t in range(ntracks):
            c.w32(hdr + 8 + 4 * t, ROM + blob + (tracks[t] - lo))
        return ROM + hdr

    def pass_audio(self):
        c = self.c
        vo, ao = c.va("gSongTable"), c.aa("gSongTable")
        for i in range(347):
            zp, vp = u32(c.Z, vo + 8 * i), u32(c.V, vo + 8 * i)
            if zp == vp:
                continue
            if c.map_ptr(vp) != u32(c.A0, ao + 8 * i):
                c.log.append("song %d: AP changed, kept" % i)
                continue
            try:
                if is_vanilla(zp - ROM):
                    np = c.map_ptr(zp)
                else:
                    np = self.copy_song(zp)
            except ValueError as e:
                c.log.append("song %d: %s" % (i, e))
                continue
            c.w32(ao + 8 * i, np)
            self.stat("songs")

    # ------------------------------------------------------------------
    # Battle animations
    # ------------------------------------------------------------------
    def anim_reusable(self, off, stack=None):
        """A vanilla script the hack left byte-identical (including everything it reaches) maps to AP's copy."""
        from anim import parse
        c = self.c
        memo = self._anim_reuse
        if off in memo:
            return memo[off]
        if not is_vanilla(off):
            memo[off] = False
            return False
        memo[off] = True  # optimistic for cycles
        try:
            end, ptrs = parse(c.Z, off, lenient=True)
        except ValueError:
            memo[off] = False
            return False
        ok = c.Z[off:end] == c.V[off:end] and c.map_ptr(ROM + off) is not None
        if ok:
            for pos, kind in ptrs:
                raw = u32(c.Z, pos)
                q = ((raw & ~1) if kind == "func" else raw) - ROM
                if kind == "script":
                    ok = self.anim_reusable(q)
                elif not is_vanilla(q):
                    ok = False
                if not ok:
                    break
        memo[off] = ok
        return ok

    def anim_template(self, p):
        c = self.c
        off = p - ROM
        if is_vanilla(off):
            return c.map_ptr(p)
        key = ("tmpl", off)
        if key in c.copied:
            return ROM + c.copied[key]
        dst = c.alloc(24)
        c.copied[key] = dst
        c.copy(dst, off, 4)
        for f in range(4, 24, 4):
            q = u32(c.Z, off + f)
            if q == 0:
                c.w32(dst + f, 0)
                continue
            mq = c.map_ptr(q)
            if mq is None:
                raise ValueError("template %x field %d -> %x not vanilla" % (off, f, q))
            c.w32(dst + f, mq)
        self.stat("anim_templates")
        return ROM + dst

    def anim_script(self, off):
        from anim import parse
        c = self.c
        if self.anim_reusable(off):
            return c.map_ptr(ROM + off)
        key = ("anim", off)
        if key in c.copied:
            return ROM + c.copied[key]
        end, ptrs = parse(c.Z, off, lenient=True)
        dst = c.alloc(end - off, 1)
        c.copied[key] = dst
        c.copy(dst, off, end - off)
        for pos, kind in ptrs:
            q = u32(c.Z, pos)
            if kind == "script":
                np = self.anim_script(q - ROM)
            elif kind == "template":
                np = self.anim_template(q)
            else:
                np = c.map_ptr(q)
            if np is None:
                raise ValueError("anim pointer %x at %x unresolved" % (q, pos))
            c.w32(dst + (pos - off), np)
        self.stat("anim_scripts")
        return ROM + dst

    def pass_anims(self):
        c = self.c
        self._anim_reuse = {}
        vt, at = c.va("gBattleAnims_Moves"), c.aa("gBattleAnims_Moves")
        for m in range(355):
            zp, vp = u32(c.Z, vt + 4 * m), u32(c.V, vt + 4 * m)
            if zp == vp and self.anim_reusable(zp - ROM):
                continue
            if c.map_ptr(vp) != u32(c.A0, at + 4 * m):
                c.log.append("anim %d: AP changed, kept" % m)
                continue
            try:
                np = self.anim_script(zp - ROM)
            except ValueError as e:
                c.log.append("anim %d: %s (kept AP)" % (m, e))
                self.stat("anim_failed")
                continue
            c.w32(at + 4 * m, np)
            self.stat("anim_moves")

    # ------------------------------------------------------------------
    # Header: own ROM name (so the FRLG client never claims this ROM) and build checksum
    # ------------------------------------------------------------------
    ROM_NAME = b"pokemon z team training AP"

    def pass_finalize(self):
        import zlib
        c = self.c
        c.write(0x108, self.ROM_NAME.ljust(32, b"\0"))
        h = zlib.crc32(repr([(op[0], op[1], op[2] if op[0] == "C" else op[2].hex(),
                              op[3] if op[0] == "C" else 0) for op in c.plan]).encode())
        self.checksum = (h & 0x7FFFFFFF) or 1
        c.w32(0x1B8, self.checksum)

    # ------------------------------------------------------------------
    # Battle scripts for move effects the hack rewrote (e.g. effect 137, a triple stat boost)
    # ------------------------------------------------------------------
    def battle_script(self, off):
        from battlescript import parse
        c = self.c
        if is_vanilla(off):
            end, _ = parse(c.Z, off)
            if c.Z[off:end] == c.V[off:end]:
                mp = c.map_ptr(ROM + off)
                if mp is not None:
                    return mp
        key = ("bscript", off)
        if key in c.copied:
            return ROM + c.copied[key]
        end, fields = parse(c.Z, off)
        dst = c.alloc(end - off, 1)
        c.copied[key] = dst
        c.copy(dst, off, end - off)
        for pos, size, arg, cmd in fields:
            if size != 4:
                continue
            v = u32(c.Z, pos)
            if ROM <= v < ROM + 0x01000000:
                t = v - ROM
                if is_vanilla(t):
                    nv = c.map_ptr(v)
                else:
                    nv = self.battle_script(t)   # hack-only targets are script labels
            elif 0x02000000 <= v < 0x04000000:
                nv = c.map_ram(v)
            else:
                continue
            if nv is None:
                raise ValueError("battle script %x: cannot map %x (%s %s)" % (off, v, cmd, arg))
            c.w32(dst + (pos - off), nv)
        self.stat("battle_scripts")
        return ROM + dst

    def pass_battle_scripts(self):
        c = self.c
        vt, at = c.va("gBattleScriptsForMoveEffects"), c.aa("gBattleScriptsForMoveEffects")
        for e in range(214):
            zp, vp = u32(c.Z, vt + 4 * e), u32(c.V, vt + 4 * e)
            if zp == vp:
                continue
            if c.map_ptr(vp) != u32(c.A0, at + 4 * e):
                c.log.append("battle effect %d: AP changed, kept" % e)
                continue
            try:
                c.w32(at + 4 * e, self.battle_script(zp - ROM))
                self.stat("battle_effects")
            except ValueError as err:
                c.log.append("battle effect %d: %s (kept AP)" % (e, err))
