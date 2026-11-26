"""Battle script parser (linear, follows the pokefirered command table)."""
from battlescript_table import COMMANDS

TERMINATORS = {"goto", "return", "end", "end2", "end3", "jumptocalledmove"}


def parse(rom, off, limit=0x2000):
    """Parse from off until a terminator. Returns (end, fields) with fields = [(pos, size, arg, cmd)]."""
    i = off
    fields = []
    while True:
        if i - off > limit:
            raise ValueError("runaway battle script at %x" % off)
        op = rom[i]
        if op not in COMMANDS:
            raise ValueError("bad battle script opcode %02x at %x" % (op, i))
        name, args = COMMANDS[op]
        p = i + 1
        for size, arg in args:
            fields.append((p, size, arg, name))
            p += size
        i = p
        if name in TERMINATORS:
            return i, fields
