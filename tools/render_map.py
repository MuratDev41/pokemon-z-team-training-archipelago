"""Render a map layout from a ROM to an image (for checking ported maps without walking to them)."""
from PIL import Image

from core import ROM, u16, u32, lz_decompress

NUM_TILES_PRIMARY = 640
NUM_METATILES_PRIMARY = 640
NUM_PALS_PRIMARY = 7


def _tiles(rom, ts):
    p = u32(rom, ts + 4) - ROM
    if rom[ts]:
        return lz_decompress(rom, p)
    return rom[p:p + 0x8000]


def _pals(rom, ts):
    p = u32(rom, ts + 8) - ROM
    out = []
    for i in range(16):
        pal = []
        for c in range(16):
            w = u16(rom, p + 32 * i + 2 * c)
            pal.append(((w & 31) * 255 // 31, ((w >> 5) & 31) * 255 // 31, ((w >> 10) & 31) * 255 // 31))
        out.append(pal)
    return out


def render(rom, layout_ptr):
    lo = layout_ptr - ROM
    w, h = u32(rom, lo), u32(rom, lo + 4)
    blocks = u32(rom, lo + 12) - ROM
    prim, sec = u32(rom, lo + 16) - ROM, u32(rom, lo + 20) - ROM
    tiles = (_tiles(rom, prim), _tiles(rom, sec))
    pals = _pals(rom, prim)[:NUM_PALS_PRIMARY] + _pals(rom, sec)[NUM_PALS_PRIMARY:]
    metas = (u32(rom, prim + 12) - ROM, u32(rom, sec + 12) - ROM)
    img = Image.new("RGB", (w * 16, h * 16))
    px = img.load()
    cache = {}

    def draw_tile(entry, ox, oy, transparent):
        t = entry & 0x3FF
        hf, vf, pal = entry & 0x400, entry & 0x800, pals[(entry >> 12) & 15] if (entry >> 12) < len(pals) else pals[0]
        src, ti = (tiles[0], t) if t < NUM_TILES_PRIMARY else (tiles[1], t - NUM_TILES_PRIMARY)
        base = 32 * ti
        for y in range(8):
            for x in range(8):
                if base + 4 * y + x // 2 >= len(src):
                    continue
                b = src[base + 4 * y + x // 2]
                c = (b >> 4) if x & 1 else (b & 15)
                if c == 0 and transparent:
                    continue
                dx = 7 - x if hf else x
                dy = 7 - y if vf else y
                px[ox + dx, oy + dy] = pal[c]

    for by in range(h):
        for bx in range(w):
            mid = u16(rom, blocks + 2 * (by * w + bx)) & 0x3FF
            mt = metas[0] + 16 * mid if mid < NUM_METATILES_PRIMARY else metas[1] + 16 * (mid - NUM_METATILES_PRIMARY)
            for layer in range(2):
                for k in range(4):
                    e = u16(rom, mt + 8 * layer + 2 * k)
                    draw_tile(e, bx * 16 + (k % 2) * 8, by * 16 + (k // 2) * 8, layer == 1)
    return img
