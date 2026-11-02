#!/usr/bin/env python3
"""Draw plan + elevations from kitchen_data.scad (no OpenSCAD needed).
usage: python3 draw.py kitchen_data.scad out_prefix
Frame: X east, Y north, origin at the inside SW corner (the L corner).
Window wall = south wall along y = 0, oven wall = west wall along x = 0.
"""
import re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

src = open(sys.argv[1]).read()
src = re.sub(r"//[^\n]*", "", src)
ns = {}
# scalar assignments, in order
for m in re.finditer(r"^\s*([A-Za-z_]\w*)\s*=\s*([^\[;]+?)\s*;", src, re.M):
    ns[m.group(1)] = eval(m.group(2), {}, ns)
# list assignments
for m in re.finditer(r"^\s*([A-Za-z_]\w*)\s*=\s*(\[.*?\])\s*;", src, re.M | re.S):
    body = re.sub(r",\s*\]", "]", m.group(2))
    ns[m.group(1)] = eval(body, {}, ns)

S, W = ns["south_len"], ns["west_len"]
wo = ns["west_offset"]
SHOW_N = 130   # how far north the plan and the west elevation go
KC = {"base": "#c9a97a", "wall": "#d9b98a", "tall": "#b8905c", "filler": "#888888", "zone": "#eeeeee"}

def wall_rect(wall, pos, w, d, off):
    """plan-view rectangle (x, y, w, h) for an item on a wall.
    south: pos from the east wall.  west: pos from the south wall."""
    if wall == "south":
        return (S - pos - w, off, w, d)
    return (off, pos, d, w)

fig, ax = plt.subplots(figsize=(11, 14))
ax.set_title("Plan view, north up (inches from the SW corner)")
ax.add_patch(Rectangle((0, 0), S, SHOW_N, fill=False, lw=2))
for o in ns["openings"]:
    _, wall, pos, w, sill, head = o
    if wall == "south":
        ax.plot([S - pos - w, S - pos], [0, 0], color="dodgerblue", lw=6)
    else:
        ax.plot([0, 0], [pos, pos + w], color="dodgerblue", lw=6)
for c in ns["cabinets"]:
    id_, wall, pos, w, h, d, z, kind = c[:8]
    off = (wo if (wall == "west" and kind != "wall") else 0)
    x, y, rw, rh = wall_rect(wall, pos, w, d, off)
    ax.add_patch(Rectangle((x, y), rw, rh, fc=KC[kind], ec="k", lw=0.6, alpha=0.9 if kind != "wall" else 0.35))
    ax.text(x + rw / 2, y + rh / 2, f"{id_}\n{w}", ha="center", va="center", fontsize=6)
for a in ns["appliances"]:
    id_, _, wall, pos, w, h, d, z, off = a[:9]
    x, y, rw, rh = wall_rect(wall, pos, w, d, off)
    ax.add_patch(Rectangle((x, y), rw, rh, fc="royalblue", ec="navy", alpha=0.35))
    ax.text(x + rw / 2, y + rh / 2, id_, ha="center", va="center", fontsize=7, color="navy")
ax.set_xlim(-8, S + 5); ax.set_ylim(-5, SHOW_N); ax.set_aspect("equal"); ax.grid(True, lw=0.3)
fig.savefig(sys.argv[2] + "_plan.png", dpi=110, bbox_inches="tight")

# elevations, looking at the wall from inside the room.
# south wall: east is on your left, pos is from the east wall  -> pos runs left to right, no flip.
# west wall:  south is on your left, pos is from the south wall -> pos runs left to right, no flip.
for wall, length in (("south", S), ("west", SHOW_N)):
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.set_title(f"{wall} wall elevation, looking at the wall from inside")
    ax.add_patch(Rectangle((0, 0), length, ns["ceiling_h"], fill=False, lw=2))
    for o in ns["openings"]:
        if o[1] == wall:
            door = o[4] == 0
            ax.add_patch(Rectangle((o[2], o[4]), o[3], o[5] - o[4], fc="#e8e8e8" if door else "lightblue", ec="k" if door else "dodgerblue"))
            ax.text(o[2] + o[3] / 2, (o[4] + o[5]) / 2, f"{o[0]}\n{o[3]} wide", ha="center", va="center", fontsize=7)
    for c in ns["cabinets"]:
        id_, cw, pos, w, h, d, z, kind = c[:8]
        if cw != wall: continue
        ax.add_patch(Rectangle((pos, z), w, h, fc=KC[kind], ec="k", lw=0.6))
        ax.text(pos + w / 2, z + h / 2, f"{id_}\n{w} x {h}", ha="center", va="center", fontsize=6)
        if kind in ("base", "zone", "filler") and z + h <= ns["counter_h"] + 0.01:
            ax.add_patch(Rectangle((pos, z + h), w, ns["counter_t"], fc="white", ec="k", lw=0.6))
    for a in ns["appliances"]:
        if a[2] != wall: continue
        id_, _, _, pos, w, h, d, z, off = a[:9]
        ax.add_patch(Rectangle((pos, z), w, h, fc="royalblue", ec="navy", alpha=0.35))
        ax.text(pos + w / 2, z + h / 2, f"{id_}\n{w} x {h}", ha="center", va="center", fontsize=7, color="navy")
    ax.axhline(ns["counter_h"], color="r", lw=0.5, ls="--")
    ax.set_xlim(-3, length + 3)
    ax.set_ylim(-2, ns["ceiling_h"] + 2); ax.set_aspect("equal"); ax.grid(True, lw=0.3)
    fig.savefig(f"{sys.argv[2]}_{wall}.png", dpi=110, bbox_inches="tight")

# ---- checks: 1D along each wall. Exit code 1 on any FAIL so a commit hook can use it.
def checks(ns):
    fails = []
    cabs = [c for c in ns["cabinets"]]
    for wall in ("south", "west"):
        run = sorted([c for c in cabs if c[1] == wall and c[7] != "wall" and not (c[7] == "zone" and "HOOD" in c[0])],
                     key=lambda c: c[2])
        for a, b in zip(run, run[1:]):
            gap = b[2] - (a[2] + a[3])
            if gap < -0.01: fails.append(f"{wall}: {a[0]} and {b[0]} overlap by {-gap:.3f}")
            if gap > 0.01:  fails.append(f"{wall}: {gap:.3f} unaccounted between {a[0]} and {b[0]}")
        end = run[-1][2] + run[-1][3]
        if wall == "south":
            # the run ends where the west run's depth begins
            west_d = max(c[5] for c in cabs if c[1] == "west" and c[7] == "base")
            target = ns["south_len"] - ns["west_offset"] - west_d
            if abs(end - target) > 0.01: fails.append(f"south run ends at {end:.3f}, west run side is at {target:.3f}")
        else:
            opening = [o for o in ns["openings"] if o[1] == "west" and o[4] == 0]
            if opening and end > opening[0][2] + 0.01: fails.append(f"west run ends at {end:.3f}, past the opening at {opening[0][2]}")
    # each appliance opening sits inside the cabinet zone it belongs to
    home = {"DW": "S_DW", "FR1": "S_FRIDGE_BAY", "FR2": "S_FRIDGE_BAY", "CT": "W_OVEN30", "OV": "W_OVEN30"}
    byid = {c[0]: c for c in cabs}
    for a in ns["appliances"]:
        if a[0] not in home: continue
        c = byid[home[a[0]]]
        # CT may cut 3/16 into each side (the cooktop notch); everything else stays inside the 3/4 sides
        inset = 0 if a[0] == "DW" else 0.75 - 0.1875 if a[0] == "CT" else 0.75
        lo, hi = c[2] + inset, c[2] + c[3] - inset
        if a[3] < lo - 0.01 or a[3] + a[4] > hi + 0.01:
            fails.append(f"{a[0]} {a[3]:.3f}..{a[3] + a[4]:.3f} outside the interior of {c[0]} {lo:.3f}..{hi:.3f}")
    ct = [a for a in ns["appliances"] if a[0] == "CT"][0]; ov = [a for a in ns["appliances"] if a[0] == "OV"][0]
    if abs((ct[3] + ct[4] / 2) - (ov[3] + ov[4] / 2)) > 0.01: fails.append("cooktop and oven cutouts are not on the same centre")
    # counter height: every base top + slab must equal counter_h
    for c in cabs:
        if c[7] == "base" and abs(c[6] + c[4] + ns["counter_t"] - ns["counter_h"]) > 0.01:
            fails.append(f"{c[0]}: top of box + slab = {c[6] + c[4] + ns['counter_t']:.3f}, counter_h is {ns['counter_h']}")
    # cooktop rear clearance to the wall finish, 2 7/8 to a combustible surface
    rear = ns["west_counter_oh"] + ns["base_d"] - 2.75 - 19.8125 + ns["west_offset"]
    print(f"cooktop cutout rear edge to the bare wall: {rear:.4f} (needs 2.875 to a combustible surface, after the wall finish)")
    for f in fails: print("FAIL", f)
    print("checks:", "PASS" if not fails else f"{len(fails)} FAIL")
    return not fails

ok = checks(ns)
sys.exit(0 if ok else 1)
