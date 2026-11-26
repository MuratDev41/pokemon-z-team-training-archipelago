"""
Re-derive the ROM-dependent parts of extracted_data.json from a (transplanted) AP FireRed ROM.

Only the "firered" values are read from the ROM. The other version keys are set to the same value,
since this world only supports FireRed 1.0 (the hack's patch requires it).
usage (as a module): regen(extracted_data_dict, rom_bytes) -> (new_dict, report)
"""
import copy
import struct

ROM = 0x08000000
EVO_METHODS = ["LEVEL", "LEVEL_ATK_LT_DEF", "LEVEL_ATK_EQ_DEF", "LEVEL_ATK_GT_DEF", "LEVEL_SILCOON",
               "LEVEL_CASCOON", "LEVEL_NINJASK", "LEVEL_SHEDINJA", "ITEM", "ITEM_HELD", "FRIENDSHIP"]
# pokefirered EVO_* constants -> apworld enum
# same mapping as tools/extractor/extractor.cpp in the AP decomp (AP's ROM has no trade/day/night/beauty methods)
EVO_FROM_ROM = {1: "FRIENDSHIP", 4: "LEVEL", 7: "ITEM", 8: "LEVEL_ATK_GT_DEF", 9: "LEVEL_ATK_EQ_DEF",
                10: "LEVEL_ATK_LT_DEF", 11: "LEVEL_SILCOON", 12: "LEVEL_CASCOON", 13: "LEVEL_NINJASK",
                14: "LEVEL_SHEDINJA", 16: "ITEM_HELD"}
DATA_TYPES = ["NO_ITEM_DEFAULT_MOVES", "NO_ITEM_CUSTOM_MOVES", "ITEM_DEFAULT_MOVES", "ITEM_CUSTOM_MOVES"]


def u8(b, o): return b[o]
def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]


def fr(addr):
    return addr["firered"] if isinstance(addr, dict) else addr


def all_versions(value, template):
    return {k: value for k in template}


def regen(ed, rom, rom_addresses=None):
    ed = copy.deepcopy(ed)
    ra = ed["misc_rom_addresses"]
    report = {}

    def changed(k):
        report[k] = report.get(k, 0) + 1

    # ---- species ----
    lul = fr(ra["gLevelUpLearnsets"])
    evo = fr(ra["gEvolutionTable"])
    tmhm = fr(ra["sTMHMLearnsets"])
    for sid, sp in enumerate(ed["species"]):
        if sp is None:
            continue
        a = fr(sp["address"])
        new = dict(sp)
        new["base_stats"] = list(rom[a:a + 6])
        new["types"] = [rom[a + 6], rom[a + 7]]
        new["catch_rate"] = rom[a + 8]
        new["friendship"] = rom[a + 18]
        new["abilities"] = [rom[a + 22], rom[a + 23]]
        evos = []
        for e in range(5):
            o = evo + 40 * sid + 8 * e
            method, param, target = u16(rom, o), u16(rom, o + 2), u16(rom, o + 4)
            if method == 0:
                continue
            m = EVO_FROM_ROM.get(method)
            if m is None:
                raise ValueError("species %d: unknown evolution method %d" % (sid, method))
            p2 = u16(rom, o + 6)
            evos.append({"method": m, "param": param, "param2": p2, "species": target})
        new["evolutions"] = evos
        lp = u32(rom, lul + 4 * sid) - ROM
        moves = []
        i = lp
        while u16(rom, i) != 0xFFFF:
            w = u16(rom, i)
            moves.append({"level": w >> 9, "move_id": w & 0x1FF})
            i += 2
        new["learnset"] = {"address": all_versions(lp, sp["learnset"]["address"]), "moves": moves}
        new["tmhm_learnset"] = "%016X" % struct.unpack_from("<Q", rom, tmhm + 8 * sid)[0]
        if new != sp:
            changed("species")
        ed["species"][sid] = new

    # ---- moves ----
    for name, mv in ed["moves"].items():
        a = fr(mv["address"])
        new = dict(mv)
        new.update(effect=rom[a], power=rom[a + 1], type=rom[a + 2], accuracy=rom[a + 3], pp=rom[a + 4],
                   secondary_effect_chance=rom[a + 5], target=rom[a + 6], priority=struct.unpack_from("<b", rom, a + 7)[0],
                   flags=rom[a + 8], category=rom[a + 9])
        if new != mv:
            changed("moves")
        ed["moves"][name] = new

    # ---- trainers ----
    for name, tr in ed["trainers"].items():
        a = fr(tr["address"])
        flags = rom[a]
        size = u32(rom, a + 32)
        pa = (u32(rom, a + 36) - ROM) & 0xFFFFFFFF   # unsigned, like the upstream extractor (null party)
        dt = DATA_TYPES[flags & 3]
        step = 16 if flags & 1 else 8
        party = []
        for k in range(size):
            o = pa + step * k
            p = {"level": rom[o + 2], "species": u16(rom, o + 4)}
            if flags & 1:
                mo = o + (8 if flags & 2 else 6)
                p["moves"] = [u16(rom, mo + 2 * j) for j in range(4)]
            party.append(p)
        new = dict(tr)
        new["data_type"] = dt
        new["party"] = party
        new["party_address"] = all_versions(pa, tr["party_address"])
        if party and "base_level" in tr:
            # base_level is what level scaling anchors to; the original data uses the party's minimum
            new["base_level"] = min([100] + [p["level"] for p in party])
        if new != tr:
            changed("trainers")
        ed["trainers"][name] = new

    # ---- wild encounters ----
    for mname, m in ed["maps"].items():
        for enc in ("land_encounters", "water_encounters", "fishing_encounters"):
            if enc not in m:
                continue
            a = fr(m[enc]["address"])
            slots = m[enc]["slots"]["firered"]
            new = []
            for k, s in enumerate(slots):
                o = a + 4 * k
                new.append({"default_species": u16(rom, o + 2), "max_level": rom[o + 1], "min_level": rom[o]})
            if new != slots:
                changed("encounters")
                m[enc]["slots"]["firered"] = new

    # ---- in-game trades ----
    for name, t in ed["trade_pokemon"].items():
        s = u16(rom, fr(t["species_address"]))
        r = u16(rom, fr(t["requested_species_address"]))
        if s != t["species"]["firered"] or r != t["requested_species"]["firered"]:
            changed("trades")
        t["species"]["firered"] = s
        t["requested_species"]["firered"] = r

    # ---- TM / HM moves ----
    tm = fr(ra["sTMHMMoves"])
    new = [u16(rom, tm + 2 * i) for i in range(len(ed["tmhm_moves"]))]
    if new != ed["tmhm_moves"]:
        changed("tmhm_moves")
    ed["tmhm_moves"] = new
    return ed, report
