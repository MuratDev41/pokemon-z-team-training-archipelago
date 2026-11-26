"""
Core of the Pokemon Z Team Training -> Archipelago transplant builder.

Three ROMs are involved:
  V  vanilla FireRed 1.0 (the player's ROM)
  Z  V + the DBZ Team Training BPS patch (binary hack, vanilla layout)
  A  V + the Archipelago base patch (rebuilt from source, different layout)

The builder copies the hack's content from Z into A. Every write is recorded in a
plan made of two operation kinds:
  COPY  dst_in_A  src_in_Z  length   (bytes taken from the hack ROM at patch time)
  WRITE dst_in_A  bytes              (pointers / ids / small glue computed here)
so the shipped plan holds offsets and pointers, not the hack's content.
"""
import bisect
import json
import os
import struct

from paths import DATA

ROM = 0x08000000
VANILLA_END = 0x71A23C          # first free byte of vanilla FireRed 1.0
GFX_START, GFX_END = 0xD00000, 0xEB0B20   # vanilla's second data block (graphics)


def is_vanilla(off):
    """True if off lies in vanilla FireRed's data (anything else in the hack is its own free-space data)."""
    return 0 <= off < VANILLA_END or GFX_START <= off < GFX_END
FREE_START = 0x742000           # AP base ROM data ends at 0x741980
FREE_END = 0xD00000             # AP keeps data at 0xD00000+ (gfx_data, sound table)


def u8(b, o): return b[o]
def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def s16(b, o): return struct.unpack_from("<h", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]


def is_rom_ptr(p):
    return ROM <= p < ROM + 0x01000000


def load_sym(path):
    """name -> (rom offset, size) for ROM symbols, plus a sorted list for lookups."""
    names = {}
    lst = []
    for line in open(path):
        p = line.split()
        if len(p) < 4:
            continue
        a = int(p[0], 16)
        if not (ROM <= a < ROM + 0x02000000):
            continue
        n = p[3]
        if n in (".text", ".rodata", ".data") or n.startswith(".gcc2") or n.startswith("$"):
            continue
        size = int(p[2], 16)
        names.setdefault(n, (a - ROM, size))
        lst.append((a - ROM, size, n))
    lst.sort()
    return names, lst


def load_ram_sym(path):
    d = {}
    for line in open(path):
        p = line.split()
        if len(p) >= 4:
            a = int(p[0], 16)
            if 0x02000000 <= a < 0x04000000:
                d.setdefault(p[3], (a, int(p[2], 16)))
    return d


def lz_len(b, o):
    """Length in bytes of the LZ77 (type 0x10) stream at o, or None if it is not one."""
    if b[o] != 0x10:
        return None
    size = b[o + 1] | (b[o + 2] << 8) | (b[o + 3] << 16)
    if size == 0 or size > 0x40000:
        return None
    i = o + 4
    out = 0
    while out < size:
        flags = b[i]
        i += 1
        for bit in range(8):
            if out >= size:
                break
            if flags & (0x80 >> bit):
                ln = (b[i] >> 4) + 3
                disp = ((b[i] & 0xF) << 8 | b[i + 1]) + 1
                if disp > out:
                    return None
                i += 2
                out += ln
            else:
                i += 1
                out += 1
    return i - o


def lz_decompress(b, o):
    size = b[o + 1] | (b[o + 2] << 8) | (b[o + 3] << 16)
    out = bytearray()
    i = o + 4
    while len(out) < size:
        flags = b[i]
        i += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> bit):
                ln = (b[i] >> 4) + 3
                disp = ((b[i] & 0xF) << 8 | b[i + 1]) + 1
                i += 2
                for _ in range(ln):
                    out.append(out[-disp])
            else:
                out.append(b[i])
                i += 1
    return bytes(out[:size])


class Ctx:
    def __init__(self, vanilla_path, bps_path, ap_base_bsdiff):
        import bsdiff4
        from bps import apply_bps
        self.V = open(vanilla_path, "rb").read()
        self.Z = apply_bps(self.V, open(bps_path, "rb").read())
        self.A0 = bsdiff4.patch(self.V, open(ap_base_bsdiff, "rb").read())
        self.A = bytearray(self.A0)

        self.vsym, self.vlist = load_sym(os.path.join(DATA, "firered.sym"))
        self.vaddrs = [x[0] for x in self.vlist]
        bsym, blist = load_sym(os.path.join(DATA, "pokefirered_ap.sym"))
        shipped = json.load(open(os.path.join(DATA, "shipped_syms.json")))
        # AP: name -> list of (offset in the shipped AP base ROM, size from the build)
        occ = {}
        self.alists = {}
        for o, s, n in blist:
            if o >= 0x01000000:
                continue
            k = occ.get(n, 0)
            occ[n] = k + 1
            key = "%s#%d" % (n, k)
            if key in shipped:
                self.alists.setdefault(n, []).append((shipped[key], s))
        vcount = {}
        for o, s, n in self.vlist:
            vcount[n] = vcount.get(n, 0) + 1
        self.vdup = {n for n, c in vcount.items() if c > 1}
        # unique names: the plain table
        self.asym = {n: l[0] for n, l in self.alists.items() if len(l) == 1 and n not in self.vdup}
        # vanilla entry index -> AP (offset, size), resolving duplicated static names by proximity
        self.vmap = {}
        last_anchor = None
        for idx, (o, s, n) in enumerate(self.vlist):
            if n in self.asym:
                last_anchor = (o, self.asym[n][0])
                self.vmap[idx] = self.asym[n]
            elif n in self.alists and last_anchor:
                exp = last_anchor[1] + (o - last_anchor[0])
                self.vmap[idx] = min(self.alists[n], key=lambda t: abs(t[0] - exp))
        # vsym for duplicated names resolves to the first occurrence only; use symbol() for those
        self.vsym_idx = {}
        for idx, (o, s, n) in enumerate(self.vlist):
            self.vsym_idx.setdefault(n, []).append(idx)
        self.vram = load_ram_sym(os.path.join(DATA, "firered.sym"))
        self.aram = load_ram_sym(os.path.join(DATA, "pokefirered_ap.sym"))

        self.plan = []
        self.alloc_ptr = FREE_START
        self.copied = {}            # (kind, hack offset) -> AP offset
        self.log = []
        self.unmapped = {}

    # ---------- symbol helpers ----------
    def vfind(self, off):
        """vanilla offset -> (name, sym offset, size, delta) of the innermost symbol starting at or before off"""
        k = bisect.bisect_right(self.vaddrs, off) - 1
        if k < 0:
            return None
        o, s, n = self.vlist[k]
        # prefer the largest enclosing sized symbol when several start at o
        return n, o, s, off - o

    def va(self, name):
        return self.vsym[name][0]

    def aa(self, name):
        if name in self.asym:
            return self.asym[name][0]
        return self.vmap[self.vsym_idx[name][0]][0]

    def asize(self, name):
        if name in self.asym:
            return self.asym[name][1]
        return self.vmap[self.vsym_idx[name][0]][1]

    def map_entry(self, idx):
        return self.vmap.get(idx)

    def has(self, name):
        return name in self.vsym and name in self.asym

    # ---------- pointer translation ----------
    def map_vanilla_off(self, off, strict=False):
        """Translate an offset in the vanilla layout to the AP layout via symbols."""
        k = bisect.bisect_right(self.vaddrs, off) - 1
        # candidates: every symbol starting at the nearest start address <= off,
        # then enclosing sized symbols further back
        j = k
        tried = 0
        while j >= 0 and tried < 64:
            o, s, n = self.vlist[j]
            idx = j
            j -= 1
            if s and off >= o + s and o != off:
                continue  # sized symbol that ends before off
            tried += 1
            if idx not in self.vmap:
                continue
            ao, asz = self.vmap[idx]
            d = off - o
            if strict and d != 0:
                continue
            if asz and d > asz:
                continue
            return ao + d
        return None

    def map_ptr(self, p, strict=False):
        """Pointer value in the hack/vanilla layout -> pointer value in AP, for vanilla-region targets."""
        if p == 0:
            return 0
        if not is_rom_ptr(p & ~1):
            return None
        off = (p & ~1) - ROM
        if not is_vanilla(off):
            return None
        m = self.map_vanilla_off(off, strict)
        if m is None:
            self.unmapped[p] = self.unmapped.get(p, 0) + 1
            return None
        return ROM + m + (p & 1)

    def map_ram(self, p):
        for n, (a, s) in self.vram.items():
            if a <= p < a + max(s, 1):
                if n in self.aram:
                    return self.aram[n][0] + (p - a)
        return None

    # ---------- allocation / writing ----------
    def alloc(self, size, align=4):
        self.alloc_ptr = (self.alloc_ptr + align - 1) & ~(align - 1)
        o = self.alloc_ptr
        self.alloc_ptr += size
        if self.alloc_ptr > FREE_END:
            raise RuntimeError("out of free space")
        assert all(x == 0xFF for x in self.A0[o:o + size]), hex(o)
        return o

    def copy(self, dst, src, length):
        """A[dst:dst+len] = Z[src:src+len], recorded as a COPY."""
        if length <= 0:
            return
        self.A[dst:dst + length] = self.Z[src:src + length]
        self.plan.append(("C", dst, src, length))

    def write(self, dst, data):
        data = bytes(data)
        if not data:
            return
        self.A[dst:dst + len(data)] = data
        self.plan.append(("W", dst, data))

    def w16(self, dst, v): self.write(dst, struct.pack("<H", v))
    def w32(self, dst, v): self.write(dst, struct.pack("<I", v))

    def copy_diff(self, dst, src, length, base):
        """Copy only the bytes of Z[src:src+len] that differ from base[src..], as COPY runs."""
        i = 0
        while i < length:
            if self.Z[src + i] != base[src + i]:
                j = i
                while j < length and (self.Z[src + j] != base[src + j] or
                                      (j + 1 < length and self.Z[src + j + 1] != base[src + j + 1]) or
                                      (j + 2 < length and self.Z[src + j + 2] != base[src + j + 2])):
                    j += 1
                self.copy(dst + i, src + i, j - i)
                i = j
            else:
                i += 1

    # ---------- blob copiers (memoized on the hack offset) ----------
    def _blob(self, kind, p, length, align=4):
        # data pointers: bit 0 is part of the address (only code pointers carry a Thumb bit)
        off = p - ROM
        key = (kind, off)
        if key in self.copied:
            return ROM + self.copied[key]
        dst = self.alloc(length, align)
        self.copy(dst, off, length)
        self.copied[key] = dst
        return ROM + dst

    def ptr_or_copy(self, p, kind, length_fn, align=4):
        """
        Resolve a hack pointer to data with no internal pointers.
        - vanilla-region target untouched by the hack: reuse AP's copy (symbol mapping)
        - otherwise copy the hack's bytes into AP free space
        """
        if p == 0:
            return 0
        off = p - ROM
        if not (0 <= off < len(self.Z)):
            raise ValueError("%s pointer %x is not in ROM" % (kind, p))
        if is_vanilla(off):
            n = length_fn(self.Z, off)
            if n and self.Z[off:off + n] == self.V[off:off + n]:
                m = self.map_ptr(p)
                if m is not None:
                    return m
        n = length_fn(self.Z, off)
        if not n:
            raise ValueError("cannot size %s at %x" % (kind, off))
        return self._blob(kind, p, n, align)

    def lz(self, p):
        return self.ptr_or_copy(p, "lz", lz_len)

    def text(self, p):
        def tl(b, o):
            i = o
            while b[i] != 0xFF:
                i += 1
            return i - o + 1
        return self.ptr_or_copy(p, "text", tl, 1)

    def raw(self, p, n, align=4):
        return self.ptr_or_copy(p, "raw%d" % n, lambda b, o: n, align)

    # ---------- plan output ----------
    def save_plan(self, path):
        """Binary plan: 'ZTP1', count, then ops. C: 0x43 dst src len (u32 x3). W: 0x57 dst len data."""
        out = bytearray(b"ZTP1")
        out += struct.pack("<I", len(self.plan))
        for op in self.plan:
            if op[0] == "C":
                out += b"C" + struct.pack("<III", op[1], op[2], op[3])
            else:
                out += b"W" + struct.pack("<II", op[1], len(op[2])) + op[2]
        open(path, "wb").write(bytes(out))
        return len(out)


def apply_plan(ap_rom, hack_rom, plan):
    """Runtime side (mirrored in the apworld)."""
    rom = bytearray(ap_rom)
    assert plan[:4] == b"ZTP1"
    n = struct.unpack_from("<I", plan, 4)[0]
    i = 8
    for _ in range(n):
        t = plan[i]
        if t == 0x43:
            d, s, ln = struct.unpack_from("<III", plan, i + 1)
            rom[d:d + ln] = hack_rom[s:s + ln]
            i += 13
        else:
            d, ln = struct.unpack_from("<II", plan, i + 1)
            rom[d:d + ln] = plan[i + 9:i + 9 + ln]
            i += 9 + ln
    return bytes(rom)
