"""Battle animation script parsing (pokefirered battle_anim_script.inc)."""
from core import u32, ROM

SIMPLE = {0x00: 3, 0x01: 3, 0x04: 2, 0x05: 1, 0x06: 1, 0x07: 1, 0x09: 3, 0x0A: 2, 0x0B: 2, 0x0C: 3, 0x0D: 1,
          0x10: 4, 0x14: 2, 0x15: 1, 0x16: 1, 0x17: 1, 0x18: 2, 0x19: 4, 0x1A: 2, 0x1B: 7, 0x1C: 6, 0x1D: 5,
          0x1E: 3, 0x20: 1, 0x22: 2, 0x23: 2, 0x25: 4, 0x26: 7, 0x27: 7, 0x28: 2, 0x29: 1, 0x2A: 2, 0x2B: 2,
          0x2C: 2, 0x2D: 2, 0x2E: 2, 0x2F: 1}
TERMINATORS = (0x08, 0x0F)


def parse(rom, off, limit=0x4000, lenient=False):
    """Linear parse from off until end/return/goto. Returns (end, pointers) where pointers are
    (position, kind) with kind in 'script', 'template', 'func'."""
    i = off
    ptrs = []
    last_op = off
    after_call = None
    while True:
        if i - off > limit:
            raise ValueError("runaway anim script at %x" % off)
        op = rom[i]
        if op in SIMPLE or op in (0x02, 0x03, 0x0E, 0x12, 0x1F, 0x21, 0x24):
            last_op = i
        if op in TERMINATORS:
            return i + 1, ptrs
        if op in SIMPLE:
            i += SIMPLE[op]
        elif op == 0x02:
            ptrs.append((i + 1, "template"))
            argc = rom[i + 6]
            i += 7 + 2 * argc
        elif op == 0x03:
            ptrs.append((i + 1, "func"))
            argc = rom[i + 6]
            i += 7 + 2 * argc
        elif op == 0x1F:
            ptrs.append((i + 1, "func"))
            argc = rom[i + 5]
            i += 6 + 2 * argc
        elif op == 0x0E:
            ptrs.append((i + 1, "script"))
            i += 5
            after_call = i
        elif op == 0x11:
            # choosetwoturnanim branches to one of two scripts: flow never falls through
            ptrs.append((i + 1, "script"))
            ptrs.append((i + 5, "script"))
            return i + 9, ptrs
        elif op == 0x12:
            ptrs.append((i + 2, "script"))
            i += 6
        elif op == 0x13:
            ptrs.append((i + 1, "script"))
            return i + 5, ptrs
        elif op == 0x21:
            ptrs.append((i + 4, "script"))
            i += 8
        elif op == 0x24:
            ptrs.append((i + 1, "script"))
            i += 5
        else:
            if lenient and after_call is not None:
                # junk after a `call` whose sub-script ends the animation: never executed
                return after_call, [x for x in ptrs if x[0] < after_call]
            raise ValueError("bad anim opcode %02x at %x" % (op, i))
