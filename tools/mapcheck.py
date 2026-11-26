"""
Reachability model for FireRed maps, used to decide which of the hack's map layouts can replace Archipelago's.

A layout may replace Archipelago's only if, for every movement mode, every point of interest Archipelago uses
(warps, object events, signs / hidden items, triggers, map edges) reaches exactly the same other points.
Movement follows pokefirered: collision bits, the elevation-mismatch rule (event_object_movement.c), directional
impassable tiles, one-way ledges, and water needing Surf. Archipelago's object events block their tiles (Cut trees,
Strength boulders, NPCs); each check also runs with objects removed.
"""
import struct
from collections import deque

ROM = 0x08000000

MB_SURFABLE = {0x10, 0x11, 0x12, 0x13, 0x15, 0x1A, 0x1B, 0x50, 0x51, 0x52, 0x53}
MB_JUMP = {0x38: (1, 0), 0x39: (-1, 0), 0x3A: (0, -1), 0x3B: (0, 1)}
# MB_IMPASSABLE_*: direction(s) you cannot move into the tile from
MB_IMPASSABLE = {0x30: {(1, 0)}, 0x31: {(-1, 0)}, 0x32: {(0, -1)}, 0x33: {(0, 1)},
                 0x34: {(1, 0), (0, -1)}, 0x35: {(-1, 0), (0, -1)}, 0x36: {(1, 0), (0, 1)}, 0x37: {(-1, 0), (0, 1)}}
MB_WARPS = set(range(0x60, 0x72)) | {0x13}
MB_WATERFALL = 0x13
# tiles whose exact positions matter for logic or puzzles: waterfalls, ice, forced movement, currents,
# spinners, holes, Strength switches, cycling road slopes
MB_SPECIAL = {0x13, 0x14, 0x20, 0x23, 0x26, 0x27, 0x66, 0xD0, 0xD1} | set(range(0x40, 0x48)) | set(range(0x50, 0x59))
ENC_LAND, ENC_WATER = 1, 2
DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def s16(b, o): return struct.unpack_from("<h", b, o)[0]


class Layout:
    """Blocks of one map plus the attribute tables that give each metatile its behaviour."""

    def __init__(self, w, h, blocks, prim_attrs, sec_attrs):
        self.w, self.h = w, h
        self.blocks = blocks            # list of u16
        self.prim = prim_attrs          # list of u32, 640 entries
        self.sec = sec_attrs            # list of u32

    def block(self, x, y):
        return self.blocks[y * self.w + x]

    def attr(self, x, y):
        m = self.block(x, y) & 0x3FF
        tab, i = (self.prim, m) if m < 0x280 else (self.sec, m - 0x280)
        return tab[i] if i < len(tab) else 0

    def behavior(self, x, y):
        return self.attr(x, y) & 0x1FF

    def encounter(self, x, y):
        return (self.attr(x, y) >> 24) & 7

    def collision(self, x, y):
        return (self.block(x, y) >> 10) & 3

    def elevation(self, x, y):
        return self.block(x, y) >> 12

    def signature(self, x, y):
        """Everything about a tile that matters for movement and warps."""
        return (self.collision(x, y) != 0, self.elevation(x, y), self.behavior(x, y), self.encounter(x, y))


def read_attrs(rom, tileset_ptr, count):
    ts = tileset_ptr - ROM
    attrs = u32(rom, ts + 20) - ROM
    return [u32(rom, attrs + 4 * i) for i in range(count)]


def read_layout(rom, layout_ptr, prim=None, sec=None):
    lo = layout_ptr - ROM
    w, h = u32(rom, lo), u32(rom, lo + 4)
    bp = u32(rom, lo + 12) - ROM
    blocks = [u16(rom, bp + 2 * i) for i in range(w * h)]
    if prim is None:
        prim = read_attrs(rom, u32(rom, lo + 16), 0x280)
    if sec is None:
        sec = read_attrs(rom, u32(rom, lo + 20), 0x180)
    return Layout(w, h, blocks, prim, sec)


def read_events(rom, header_ptr):
    """Archipelago's events for a map: objects, warps, coord events, bg events."""
    h = header_ptr - ROM
    e = u32(rom, h + 4) - ROM
    no, nw, nc, nb = rom[e:e + 4]
    po, pw, pc, pb = [u32(rom, e + 4 + 4 * i) - ROM for i in range(4)]
    objs = [(s16(rom, po + 24 * i + 4), s16(rom, po + 24 * i + 6)) for i in range(no)]
    warps = [(s16(rom, pw + 8 * i), s16(rom, pw + 8 * i + 2)) for i in range(nw)]
    coords = [(s16(rom, pc + 16 * i), s16(rom, pc + 16 * i + 2)) for i in range(nc)]
    bgs = [(s16(rom, pb + 12 * i), s16(rom, pb + 12 * i + 2)) for i in range(nb)]
    return objs, warps, coords, bgs


def points_of_interest(lay, events):
    objs, warps, coords, bgs = events
    pois = []

    def inside(x, y):
        return 0 <= x < lay.w and 0 <= y < lay.h

    def around(x, y):
        return frozenset((x + dx, y + dy) for dx, dy in DIRS if inside(x + dx, y + dy))

    for i, (x, y) in enumerate(warps):
        if inside(x, y):
            pois.append(("warp%d" % i, frozenset({(x, y)})))
    for i, (x, y) in enumerate(coords):
        if inside(x, y):
            pois.append(("coord%d" % i, frozenset({(x, y)})))
    for i, (x, y) in enumerate(objs):
        if inside(x, y):
            pois.append(("obj%d" % i, around(x, y)))
    for i, (x, y) in enumerate(bgs):
        if inside(x, y):
            pois.append(("bg%d" % i, around(x, y) | {(x, y)}))
    pois.append(("edgeN", frozenset((x, 0) for x in range(lay.w))))
    pois.append(("edgeS", frozenset((x, lay.h - 1) for x in range(lay.w))))
    pois.append(("edgeW", frozenset((0, y) for y in range(lay.h))))
    pois.append(("edgeE", frozenset((lay.w - 1, y) for y in range(lay.h))))
    return pois


def reach(lay, sources, blocked, surf, waterfall=False):
    """Tiles reachable from any source tile. State = (x, y, elevation, on_water)."""
    def standable(x, y):
        return 0 <= x < lay.w and 0 <= y < lay.h and (x, y) not in blocked and lay.collision(x, y) == 0

    seen = set()
    tiles = set()
    q = deque()
    for (x, y) in sources:
        if standable(x, y):
            st = (x, y, lay.elevation(x, y), lay.behavior(x, y) in MB_SURFABLE)
            if st[3] and not surf:
                continue
            seen.add(st)
            q.append(st)
    while q:
        x, y, z, water = q.popleft()
        tiles.add((x, y))
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < lay.w and 0 <= ny < lay.h):
                continue
            b = lay.behavior(nx, ny)
            if b in MB_JUMP:
                if MB_JUMP[b] != (dx, dy) or water:
                    continue
                nx, ny = nx + dx, ny + dy           # jump over the ledge
                if not standable(nx, ny):
                    continue
                b = lay.behavior(nx, ny)
            elif not standable(nx, ny):
                continue
            if (dx, dy) in MB_IMPASSABLE.get(b, ()):
                continue
            nwater = b in MB_SURFABLE
            if nwater and not surf:
                continue
            if b == MB_WATERFALL and not waterfall:
                continue
            ne = lay.elevation(nx, ny)
            if nwater == water:
                if z not in (0, 15) and ne not in (0, 15) and ne != z:
                    continue                          # elevation mismatch
            nz = z if ne == 15 else ne
            st = (nx, ny, nz, nwater)
            if st not in seen:
                seen.add(st)
                q.append(st)
    return tiles


def reach_matrix(lay, pois, objs, surf, objects_block, waterfall=False):
    """For each point: which points it reaches, and whether it reaches grass, surf and fishing encounters."""
    blocked = set(objs) if objects_block else set()
    out = {}
    for name, tiles in pois:
        r = reach(lay, tiles, blocked, surf, waterfall)
        land = any(lay.encounter(x, y) == ENC_LAND for x, y in r)
        water = any(lay.encounter(x, y) == ENC_WATER for x, y in r)
        fish = any(0 <= x + dx < lay.w and 0 <= y + dy < lay.h and lay.encounter(x + dx, y + dy) == ENC_WATER
                   for x, y in r for dx, dy in DIRS)
        out[name] = (frozenset(n for n, t in pois if t & r), land, water, fish)
    return out


def equivalent(base, cand, events):
    """True if cand keeps every point-of-interest relation of base, warp tiles and map edges."""
    if (base.w, base.h) != (cand.w, cand.h):
        return False, "size changed"
    if all(base.signature(x, y) == cand.signature(x, y) for y in range(base.h) for x in range(base.w)):
        return True, "identical movement"          # fast path: nothing that matters for movement changed
    objs, warps, coords, bgs = events
    for (x, y) in warps:
        if 0 <= x < base.w and 0 <= y < base.h and base.signature(x, y) != cand.signature(x, y):
            return False, "warp tile (%d,%d) changed" % (x, y)
    for (x, y) in objs:
        # an object standing on a tile that becomes a wall/water would look wrong and change interaction
        if 0 <= x < base.w and 0 <= y < base.h and base.signature(x, y) != cand.signature(x, y):
            return False, "object tile (%d,%d) changed" % (x, y)
    for x in range(base.w):
        for y in (0, base.h - 1):
            if base.signature(x, y) != cand.signature(x, y):
                return False, "map edge (%d,%d) changed" % (x, y)
    for y in range(base.h):
        for x in (0, base.w - 1):
            if base.signature(x, y) != cand.signature(x, y):
                return False, "map edge (%d,%d) changed" % (x, y)
    special = lambda lay: {(x, y, lay.behavior(x, y)) for y in range(lay.h) for x in range(lay.w)
                           if lay.behavior(x, y) in MB_SPECIAL}
    if special(base) != special(cand):
        return False, "special tiles (waterfall/ice/currents/holes) moved"
    pois = points_of_interest(base, events)
    for surf, waterfall in ((False, False), (True, False), (True, True)):
        for ob in (True, False):
            if reach_matrix(base, pois, objs, surf, ob, waterfall) != reach_matrix(cand, pois, objs, surf, ob, waterfall):
                return False, "reachability differs (surf=%s, waterfall=%s, objects=%s)" % (surf, waterfall, ob)
    return True, "ok"
