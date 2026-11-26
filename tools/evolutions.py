"""Rebuild the evolution events (events.json EVOLVE_* and the Evolutions region) from the hack's evolution table."""
import ast
import json
import os
import re


def all_species(world_dir):
    src = open(os.path.join(world_dir, "data.py"), encoding="utf-8").read()
    m = re.search(r"ALL_SPECIES: List\[Tuple\[str, str, int\]\] = (\[.*?\n\])", src, re.S)
    return ast.literal_eval(m.group(1))


def rebuild(world_dir, ed, upstream_world_dir):
    species = all_species(world_dir)
    const = ed["constants"]
    by_id = {const[c]: (c, name) for c, name, _ in species}
    events_path = os.path.join(world_dir, "data", "events.json")
    region_path = os.path.join(world_dir, "data", "regions", "unique.json")
    # always start from the upstream files so rebuilding is idempotent
    events = json.load(open(os.path.join(upstream_world_dir, "data", "events.json"), encoding="utf-8-sig"))
    regions = json.load(open(os.path.join(upstream_world_dir, "data", "regions", "unique.json"), encoding="utf-8-sig"))

    new_events = {}
    order = []
    for c, name, _ in species:
        sid = const[c]
        evos = ed["species"][sid]["evolutions"]
        base = "EVOLVE_" + c[len("SPECIES_"):]
        for i, evo in enumerate(evos, 1):
            if evo["species"] not in by_id:
                continue
            target = by_id[evo["species"]][1]
            key = base if len(evos) == 1 else "%s_%d" % (base, i)
            label = name if len(evos) == 1 else "%s %d" % (name, i)
            new_events[key] = {"name": "Evolution - " + label, "item": "Evolved " + target,
                               "category": "EVENT_EVOLUTION_POKEMON"}
            order.append(key)

    merged = {}
    inserted = False
    for k, v in events.items():
        if k.startswith("EVOLVE_"):
            if not inserted:
                merged.update(new_events)
                inserted = True
            continue
        merged[k] = v
    with open(events_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    regions["REGION_EVOLUTION"]["events"] = order
    with open(region_path, "w", encoding="utf-8") as f:
        json.dump(regions, f, indent=2, ensure_ascii=False)
    old = [k for k in events if k.startswith("EVOLVE_")]
    return {"evolution_events": len(order), "upstream": len(old),
            "removed": sorted(set(old) - set(order))[:20], "added": sorted(set(order) - set(old))[:20]}
