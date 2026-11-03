#!/usr/bin/env python3
"""cutlist.py -- part list, DXF per cabinet and order sheets for every box in kitchen_data.scad,
built per construction.scad.

usage: python3 cutlist.py kitchen_data.scad construction.scad out_dir

Writes into out_dir (stale .dxf files there are deleted first):
  cutlist.csv      one row per part: cabinet, part, qty, length, width, thickness, material, features
  fronts.csv       the Bofronts order: doors, drawer fronts, panels, fillers, toe kicks
  hardware.csv     runners, locking devices, hinges, plates, shelf pins, per cabinet
  countertop.csv   the two countertop cutouts for the counter fabricator
  ops.txt          layer legend: what each DXF layer means (face, tool, depth), and the setup rules
  summary.txt      sheet estimate, drawer schedule, the [verify] list
  <CABINET>.dxf    all parts of that cabinet laid flat

Conventions
  Every part is drawn with its FEATURE FACE up: for a side that is the inside face, front edge at x = 0,
  bottom edge at y = 0. For a slab (top, bottom, floor, shelf) it is the inside face, front edge at x = 0,
  low-pos end at y = 0 (east end on the window wall, south end on the oven wall). Features that would
  need the other face are made THROUGH so one setup cuts the part.
  Layers: OUTLINE (through, outside the line), THRU (through pocket, inside the line), POCKET_<mils>
  (pocket to that depth in thousandths of an inch), HOLE_<dia mils>_THRU, HOLE_<dia mils>_<depth mils>,
  DOGBONE (bit-diameter relief circles at inside corners of finger notches), NOTE (text).
"""
import csv, math, os, re, sys, glob

MM = 1 / 25.4

# ---------------------------------------------------------------- scad data reader
def read_scad(path, ns=None):
    ns = {} if ns is None else dict(ns)
    src = re.sub(r"//[^\n]*", "", open(path).read())
    for m in re.finditer(r"^\s*([A-Za-z_]\w*)\s*=\s*([^\[;]+?)\s*;", src, re.M):
        ns[m.group(1)] = eval(m.group(2), {}, ns)
    for m in re.finditer(r"^\s*([A-Za-z_]\w*)\s*=\s*(\[.*?\])\s*;", src, re.M | re.S):
        ns[m.group(1)] = eval(re.sub(r",\s*\]", "]", m.group(2)), {}, ns)
    return ns

# ---------------------------------------------------------------- tiny DXF writer
class DXF:
    def __init__(self):
        self.e = []
    def line(self, x1, y1, x2, y2, layer):
        self.e.append("0\nLINE\n8\n%s\n10\n%.4f\n20\n%.4f\n11\n%.4f\n21\n%.4f\n" % (layer, x1, y1, x2, y2))
    def poly(self, pts, layer):
        for (a, b) in zip(pts, pts[1:] + pts[:1]):
            self.line(a[0], a[1], b[0], b[1], layer)
    def rect(self, x, y, w, h, layer):
        self.poly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], layer)
    def circle(self, x, y, d, layer):
        self.e.append("0\nCIRCLE\n8\n%s\n10\n%.4f\n20\n%.4f\n40\n%.4f\n" % (layer, x, y, d / 2))
    def text(self, x, y, s, layer="NOTE", h=0.4):
        self.e.append("0\nTEXT\n8\n%s\n10\n%.4f\n20\n%.4f\n40\n%.3f\n1\n%s\n" % (layer, x, y, h, s))
    def save(self, path):
        with open(path, "w") as f:
            f.write("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n9\n$INSUNITS\n70\n1\n0\nENDSEC\n"
                    "0\nSECTION\n2\nENTITIES\n" + "".join(self.e) + "0\nENDSEC\n0\nEOF\n")

def mils(v):
    return "%03d" % int(round(v * 1000))

# ---------------------------------------------------------------- parts
class Part:
    """A flat piece L (x) by W (y) of thickness t. Outline is self.poly (counterclockwise).
    Features: ("THRU"|"POCKET", x, y, w, h, depth, note) and ("HOLE", x, y, dia, depth|None, note)."""
    def __init__(self, cab, name, L, W, t, mat, qty=1):
        self.cab, self.name, self.L, self.W, self.t, self.mat, self.qty = cab, name, L, W, t, mat, qty
        self.feats, self.notes = [], []
        self.poly = [(0, 0), (L, 0), (L, W), (0, W)]
        self.dogbones = []
    def pocket(self, x, y, w, h, depth, note):
        self.feats.append(("POCKET", x, y, w, h, depth, note))
    def thru(self, x, y, w, h, note):
        self.feats.append(("THRU", x, y, w, h, None, note))
    def hole(self, x, y, d, depth, note):
        self.feats.append(("HOLE", x, y, d, depth, None, note))
    def note(self, s):
        self.notes.append(s)
    def fingers(self, edges, bit_d):
        self.poly, self.dogbones = fingered_outline(self.L, self.W, edges, bit_d)
    def corner_notches(self, c):
        """Cut c x c off all four corners (back panels: tongues into side and slab dados)."""
        L, W = self.L, self.W
        self.poly = [(c, 0), (L - c, 0), (L - c, c), (L, c), (L, W - c), (L - c, W - c), (L - c, W),
                     (c, W), (c, W - c), (0, W - c), (0, c), (c, c)]
    def feature_text(self):
        return "; ".join(sorted({f[6] if f[0] != "HOLE" else f[6] for f in self.feats} | set(self.notes)))

def finger_profile(length, depth, fw, start_tab):
    """Points along an edge from 0 to length: (x, 0) on the envelope, (x, -depth) in a notch.
    n fingers of equal width, n = round(length / fw), at least 2."""
    n = max(2, int(round(length / fw)))
    f = length / n
    pts, corners = [], []
    tab, x = start_tab, 0.0
    for i in range(n):
        y0 = 0.0 if tab else -depth
        pts += [(x, y0), (x + f, y0)]
        if not tab:
            corners.append((x, x + f))
        x += f
        tab = not tab
    return pts, corners

def fingered_outline(L, W, edges, bit_d):
    """Counterclockwise outline of an L x W envelope. edges maps "bottom"|"right"|"top"|"left" to
    (depth, finger_w, start_tab). start_tab is "tab at x = 0" for bottom/top and "tab at y = 0" for
    left/right, so the same pattern on opposite edges of a part lines up. A straight edge that follows a
    fingered one starts where the fingered one ended (no backtracking corner, see audit F09)."""
    r = bit_d / 2
    poly, bones = [], []
    spec = [("bottom", (0, 0), (L, 0), (0, 1)), ("right", (L, 0), (L, W), (-1, 0)),
            ("top", (L, W), (0, W), (0, -1)), ("left", (0, W), (0, 0), (1, 0))]
    fingered = [bool(edges.get(n_)) for (n_, _, _, _) in spec]
    for idx, (name, p0, p1, inward) in enumerate(spec):
        e = edges.get(name)
        if not e:
            # a straight edge starts at its own corner only if the edge before it (cyclically) is straight too;
            # after a fingered edge it starts wherever that edge ended (audit F09)
            if not fingered[idx - 1]:
                poly.append(p0)
            continue
        depth, fw, start_tab = e
        reverse = name in ("top", "left")
        q0, q1 = (p1, p0) if reverse else (p0, p1)
        length = abs(q1[0] - q0[0]) + abs(q1[1] - q0[1])
        ux, uy = (q1[0] - q0[0]) / length, (q1[1] - q0[1]) / length
        pts, corners = finger_profile(length, depth, fw, start_tab)
        seq = [(q0[0] + ux * a - inward[0] * b, q0[1] + uy * a - inward[1] * b) for (a, b) in pts]
        poly.extend(reversed(seq) if reverse else seq)
        k = r / 2 ** 0.5
        for (a1, a2) in corners:
            # the two inside corners at the bottom of each notch, circle pushed into the notch
            for a, s in ((a1, +1), (a2, -1)):
                cx = q0[0] + ux * a + inward[0] * depth
                cy = q0[1] + uy * a + inward[1] * depth
                bones.append((cx + ux * k * s - inward[0] * k, cy + uy * k * s - inward[1] * k))
    # the left edge is last: if it was straight and the bottom edge is fingered starting with a notch,
    # the closing segment runs from the left edge down to the inset first point, which is correct.
    out = []
    for q in poly:
        if not out or abs(out[-1][0] - q[0]) > 1e-9 or abs(out[-1][1] - q[1]) > 1e-9:
            out.append(q)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-9 and abs(out[0][1] - out[-1][1]) < 1e-9:
        out.pop()
    return out, bones

def holes_row(part, x, z0, zmax, pitch, d, note):
    z = z0
    while z <= zmax:
        part.hole(x, z, d, None, note)
        z += pitch

# ---------------------------------------------------------------- carcass
def side_part(C, cab, name, D, side_h):
    s = Part(cab, name, D, side_h, C["ply_t"], "ply", 1)
    return s

def carcass(C, cab, W, H, D, variant, parts, extra=None):
    """variant: base | wall | sink | corner | oven. Builds sides, slabs, back, stretchers.
    extra: dict of per-cabinet additions (service holes, drainboard relief)."""
    t, bt, dd = C["ply_t"], C["back_t"], C["dado_depth"]
    fw, bit = C["finger_w"], C["bit_d"]
    extra = extra or {}
    inner = W - 2 * t
    side_h = H + (C["toe_h"] if variant == "oven" else 0)
    # ---- sides, two separate parts (A = low pos end, B = high pos end) so one can carry a hole
    sides = []
    for name in ("side_A", "side_B"):
        s = Part(cab, name, D, side_h, t, "ply", 1)
        edges = {}
        if variant != "oven":
            edges["bottom"] = (t, fw, True)
            if variant != "sink":
                edges["top"] = (t, fw, True)
        s.fingers(edges, bit)
        if variant == "oven":
            # sides run to the floor. Floor panel in a dado with its top face at ov_floor. No back, no top:
            # a flat rear stretcher and a vertical front rail at the top, a ledger and a toe board under the floor.
            fz = C["ov_floor"] - t
            s.pocket(0, fz, D, t, dd, "floor dado 3/8 deep, floor top face at %.3f" % C["ov_floor"])
            s.pocket(D - 3, side_h - t, 3, t, dd, "rear top stretcher dado 3/8 deep")
            s.pocket(0, side_h - 2.5, t, 2.5, dd, "front top rail dado 3/8 deep")
            s.pocket(D - t, 0, t, fz, dd, "rear ledger dado 3/8 deep")
            s.pocket(C["toe_setback"], 0, t, fz, dd, "toe board dado 3/8 deep, set back like the ladder")
            s.pocket(1.25, side_h - 3.5, 21.0625 - 1.25, 3.5, 3 / 16, "cooktop clamp relief 3/16 deep, inside face, under the countertop cutout zone")
            s.note("open back: gas and cord come through the open back; right-rear relief per cooktop guide p.2 is satisfied")
        else:
            s.pocket(D - C["back_in"] - bt, t, bt, side_h - 2 * t + (t if variant == "sink" else 0), dd, "back dado 3/8 deep")
            holes_row(s, C["row_front"], C["row_first_z"], side_h - 1, C["row_pitch"], C["row_hole_d"], "front 32 mm row, 5 mm x 13 mm deep")
            holes_row(s, D - C["back_in"] - bt - C["row_rear"], C["row_first_z"], side_h - 1, C["row_pitch"], C["row_hole_d"], "rear 32 mm row, 5 mm x 13 mm deep")
        if variant == "sink":
            s.pocket(0, side_h - 4, t, 4, dd, "front stretcher dado 3/8 deep")
            s.pocket(D - C["back_in"] - bt - t, side_h - 4, t, 4, dd, "rear stretcher dado 3/8 deep")
        sides.append(s)
    # service holes: ("A"|"B", x, y, dia, note)
    for (which, x, y, dia, note) in extra.get("holes", []):
        sides[0 if which == "A" else 1].hole(x, y, dia, None, note)
    # through rectangles on a side: ("A"|"B", x, y, w, h, note)
    for (which, x, y, w_, h_, note) in extra.get("thru", []):
        sides[0 if which == "A" else 1].thru(x, y, w_, h_, note)
    # drainboard relief on a side: ("A"|"B", x0, x1, depth)
    for (which, x0, x1, dep) in extra.get("side_relief", []):
        s = sides[0 if which == "A" else 1]
        s.thru(x0, s.W - dep, x1 - x0, dep + 0.01, "drainboard relief, top edge notched %.3f over x %.2f to %.2f" % (dep, x0, x1))
        s.note("drainboard relief cuts the top fingers in that zone")
    if variant == "corner":
        sides[0].note("blind corner: the 23 fixed panel closes the half toward the window wall")
    parts.extend(sides)
    # ---- slabs
    def slab(name):
        q = Part(cab, name, D, W, t, "ply")
        q.fingers({"bottom": (t, fw, False), "top": (t, fw, False)}, bit)
        q.pocket(D - C["back_in"] - bt, t, bt, W - 2 * t, dd, "back dado 3/8 deep")
        return q
    if variant == "oven":
        floor = Part(cab, "floor", D + 2 * 0, inner + 2 * dd, t, "ply")
        floor.note("sits in the side dados on the toe board and the rear ledger; 200 lb oven")
        parts.append(floor)
        parts.append(Part(cab, "toe_board", inner + 2 * dd, C["ov_floor"] - t, t, "ply"))
        parts.append(Part(cab, "rear_ledger", inner + 2 * dd, C["ov_floor"] - t, t, "ply"))
        parts.append(Part(cab, "rear_top_stretcher", inner + 2 * dd, 3, t, "ply"))
        parts.append(Part(cab, "front_top_rail", inner + 2 * dd, 2.5, t, "ply"))
    else:
        parts.append(slab("bottom"))
        if variant == "sink":
            for nm in ("front_stretcher", "rear_stretcher"):
                # vertical boards at the front (0 to 3/4) and in front of the back; the drainboard
                # depression runs from 1 1/2 to 19 1/4 behind the front, so neither meets it
                parts.append(Part(cab, nm, inner + 2 * dd, 4, t, "ply"))
        else:
            top = slab("top")
            for (x0, x1, y0, y1) in extra.get("top_relief", []):
                top.thru(x0, y0, x1 - x0, y1 - y0, "drainboard relief, through")
            parts.append(top)
        # back: tongues 3/8 into the side dados (full height between the slabs) and into the slab dados
        # (inner width); corners notched 3/8 so the three joints meet (audit F10)
        back_h = (H - 2 * t + 2 * dd) if variant != "sink" else (H - t + dd)
        back = Part(cab, "back", inner + 2 * dd, back_h, bt, "ply")
        back.corner_notches(dd)
        if variant == "sink":
            back.note("sits in the bottom dado and the side dados; top edge free behind the rear stretcher")
        parts.append(back)
    if variant == "corner":
        parts.append(Part(cab, "blind_panel", C["corner_blind_w"], H, t, "ply"))
    for n in range(extra.get("shelves", 0)):
        parts.append(Part(cab, "shelf", D - C["back_in"] - bt - 0.25, inner - 0.125, t, "ply"))

# ---------------------------------------------------------------- drawers
def drawer_boxes(C, cab, W, heights, parts, hw):
    """Blum TANDEM: inside drawer width = cabinet inside width - 42 mm; outside = inside + 2 t.
    Finger joints at all four corners, fingers 2 t tall so the back's hook zone sits in a solid tab.
    Sides: Tandem rear notch (through). Back: two hook holes (through, see ops.txt). Front: plain."""
    t, bt, bit = C["drawer_t"], C["drawer_bot_t"], C["bit_d"]
    inner = W - 2 * C["ply_t"]
    inside_w = inner - 42 * MM
    bw = inside_w + 2 * t
    fwd = 2 * t
    narrow = inside_w < 124 * MM
    overrides = {(o[0], o[1]): o[2] for o in C.get("drawer_depth", [])}
    for i, fh in enumerate(heights):
        bh = max(4, fh - C["box_h_minus"])
        depth = overrides.get((cab, i + 1), C["box_depth"])
        tag = "drawer%d" % (i + 1)
        side = Part(cab, tag + "_side", depth, bh, t, "bb", 2)
        side.fingers({"left": (t, fwd, False), "right": (t, fwd, False)}, bit)
        side.pocket(0, C["box_bot_up"], depth, bt, C["drawer_dado"], "bottom groove 1/4 deep")
        side.thru(depth - C["rear_notch_w"], 0, C["rear_notch_w"], C["rear_notch_h"], "Tandem rear notch 35 x 13 mm, through")
        if depth != C["box_depth"]:
            side.note("shortened box, %g runner: service cavity behind it" % depth)
        parts.append(side)
        front = Part(cab, tag + "_front", bw, bh, t, "bb", 1)
        front.fingers({"left": (t, fwd, True), "right": (t, fwd, True)}, bit)
        front.pocket(0, C["box_bot_up"], bw, bt, C["drawer_dado"], "bottom groove 1/4 deep")
        front.note("Bofronts front screws to this from inside")
        parts.append(front)
        back = Part(cab, tag + "_back", bw, bh, t, "bb", 1)
        back.fingers({"left": (t, fwd, True), "right": (t, fwd, True)}, bit)
        back.pocket(0, C["box_bot_up"], bw, bt, C["drawer_dado"], "bottom groove 1/4 deep")
        for x in (C["hook_hole_x"], bw - C["hook_hole_x"]):
            back.hole(x, C["hook_hole_z"], C["hook_hole_d"], 10 * MM, "Tandem rear hook hole 6 mm x 10 deep, from the REAR face (flip the part)")
        parts.append(back)
        parts.append(Part(cab, tag + "_bottom", depth - 2 * t + 2 * C["drawer_dado"], bw - 2 * t + 2 * C["drawer_dado"], bt, "bb"))
        hw.append([cab, tag, "Blum TANDEM 563H %d in pair, Blumotion" % depth, 1, "inside drawer width %.1f mm" % (inside_w / MM)])
        hw.append([cab, tag, "Blum locking devices L+R, %s" % ("narrow T51.0801.20 (95 to 124 mm inside) [verify part no.]" if narrow else "standard T51.1700.04 [verify part no.]"), 1,
                   "inside width %.1f mm; standard needs 124 min" % (inside_w / MM)])
    return bw

# ---------------------------------------------------------------- fridge bay
def fridge_bay(C, cab, W, H, D, parts, openings):
    t, fw, bit = C["ply_t"], C["finger_w"], C["bit_d"]
    for nm in ("end_panel_A", "end_panel_B"):
        end = Part(cab, nm, D, H, t, "ply", 1)
        end.fingers({"bottom": (t, fw, True), "top": (t, fw, True)}, bit)
        end.note("goes to the wall; closes the air channel at the side")
        parts.append(end)
    floor = Part(cab, "floor", D, W, t, "ply"); floor.fingers({"bottom": (t, fw, False), "top": (t, fw, False)}, bit)
    shelf = Part(cab, "shelf", D, W, t, "ply"); shelf.fingers({"bottom": (t, fw, False), "top": (t, fw, False)}, bit)
    toe = Part(cab, "toe_board", W, C["toe_h"], t, "ply")
    for (o, ow) in openings:
        floor.thru(D - C["fr_notch_d"], o + C["fr_notch_from"], C["fr_notch_d"], C["fr_notch_w"], "air notch, through [LG 190 x 220 mm]")
        shelf.thru(D - C["fr_top_slot_d"], o + ow / 2 - C["fr_top_slot_w"] / 2, C["fr_top_slot_d"], C["fr_top_slot_w"], "exhaust slot, through [LG 400 x 50 mm]")
        toe.thru(o + ow / 2 - C["fr_toe_grille_w"] / 2, (C["toe_h"] - C["fr_toe_grille_h"]) / 2, C["fr_toe_grille_w"], C["fr_toe_grille_h"], "grille opening, through [LG 404 x 51 mm]")
    div_y = openings[0][0] + openings[0][1]
    n, tw = 3, C["fr_tab_w"]
    for q in (floor, shelf):
        for i in range(n):
            q.thru((i + 0.5) * D / n - tw / 2, div_y, tw, t, "divider tab slot, through")
    div = Part(cab, "divider", D, H, t, "ply")
    xs = [((i + 0.5) * D / n - tw / 2, (i + 0.5) * D / n + tw / 2) for i in range(n)]
    def tabbed(ybase, sgn):
        out, x = [], 0.0
        for (a, b) in xs:
            out += [(x, ybase + sgn * t), (a, ybase + sgn * t), (a, ybase), (b, ybase), (b, ybase + sgn * t)]
            x = b
        out.append((D, ybase + sgn * t))
        return out
    bottom = tabbed(0, +1)
    top = [(x, H - y) for (x, y) in tabbed(0, +1)]
    div.poly = bottom + list(reversed(top))
    div.note("tabs %g x 3/4 into the floor and shelf slots, glued" % tw)
    parts += [div, floor, shelf, toe, Part(cab, "ceiling_vent_strip", W, C["fr_top_vent"], t, "ply")]

# ---------------------------------------------------------------- ladders
def ladders(C, cabs, parts):
    runs = {}
    for c in cabs:
        if c["ladder"]:
            runs.setdefault(c["wall"], []).append(c)
    n = 0
    for wall, cs in runs.items():
        cs.sort(key=lambda c: c["pos"])
        segs, start, end = [], cs[0]["pos"], cs[0]["pos"] + cs[0]["W"]
        for c in cs[1:]:
            if abs(c["pos"] - end) < 0.01:
                end = c["pos"] + c["W"]
            else:
                segs.append((start, end)); start, end = c["pos"], c["pos"] + c["W"]
        segs.append((start, end))
        for a, b in segs:
            n += 1
            L = b - a
            tag = "LADDER%d_%s_%g_to_%g" % (n, wall, a, b)
            parts.append(Part(tag, "rail", L, C["toe_h"], C["ply_t"], "ply", 2))
            parts.append(Part(tag, "cross", C["base_d"] - C["toe_setback"] - 2 * C["ply_t"], C["toe_h"], C["ply_t"], "ply", int(L // 24) + 2))

# ---------------------------------------------------------------- main
def main():
    K = read_scad(sys.argv[1])
    C = read_scad(sys.argv[2], K)
    out = sys.argv[3]; os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, "*.dxf")):
        os.remove(f)
    C["base_d"], C["toe_h"] = K["base_d"], K["toe_h"]
    ov = [a for a in K["appliances"] if a[0] == "OV"][0]
    C["ov_floor"] = ov[7]
    fronts = {f[0]: f for f in C["fronts"]}
    byid = {c[0]: c for c in K["cabinets"]}
    bt_ = C["back_t"]
    sink_drain = next((a for a in K["appliances"] if a[0] == "SINK_DRAIN"), None)

    parts, cabs, hw = [], [], []
    for c in K["cabinets"]:
        cid, wall, pos, W, H, D, z, kind = c[:8]
        rec = {"id": cid, "wall": wall, "pos": pos, "W": W, "ladder": False}
        extra = {}
        # drainboard relief: cabinets whose top slab lies under the drainboard depression
        if sink_drain and wall == sink_drain[2] and kind == "base":
            drop = sink_drain[5] - K["counter_t"]
            if drop > 0:
                d0, d1 = sink_drain[3] + 1, sink_drain[3] + sink_drain[4] - 1   # depression, 1 inside the rim
                lo, hi = max(pos, d0), min(pos + W, d1)
                if hi > lo:
                    x0 = 2 + 1 - K["counter_oh"]       # depression front from the box front: rim 2 behind the counter front, depression 1 inside the rim
                    x1 = x0 + sink_drain[6] - 2
                    y0, y1 = lo - pos, hi - pos
                    # through the top slab, including its finger zone where the side below is notched
                    extra["top_relief"] = [(x0, x1, y0 if lo - pos < 0.01 else y0 + 0.25, y1 if pos + W - hi < 0.01 else y1 - 0.25)]
                    rel = []
                    if lo - pos < 0.01: rel.append(("A", x0, x1, drop))
                    if pos + W - hi < 0.01: rel.append(("B", x0, x1, drop))
                    extra["side_relief"] = rel
        if cid == "W_OVEN30":
            extra["holes"] = [("B", D - 1.5, H + C["toe_h"] - 3, 1.25, "oven cable to the junction box in W_D30, 1 1/4 through, upper rear, behind the burner box zone")]
            carcass(C, cid, W, H, D, "oven", parts, extra)
        elif cid == "W_D30":
            extra["holes"] = [("A", D - 1.5, H - 3, 1.25, "oven cable in from W_OVEN30; junction box and cooktop receptacle live behind the shortened top drawer")]
            carcass(C, cid, W, H, D, "base", parts, extra); rec["ladder"] = True
        elif kind == "tall":
            frs = sorted([(a[3] - pos, a[4]) for a in K["appliances"] if a[0].startswith("FR")])
            fridge_bay(C, cid, W, H, D, parts, frs); rec["ladder"] = True
        elif kind == "wall":
            extra["shelves"] = 1
            carcass(C, cid, W, H, D, "wall", parts, extra)
        elif kind == "base":
            variant = "sink" if cid.startswith("S_SB") else "corner" if "CORNER" in cid else "base"
            if variant == "sink":
                # Bosch install p.10: 2.5 x 3.5 opening at the rear corner of the sink-facing side, for hoses and cord.
                # The dishwasher is on the east side of the sink base (side A), low-pos end.
                extra["thru"] = [("A", D - C["back_in"] - bt_ - 3.5, 1.0, 3.5, 2.5, "Bosch hose/cord opening 2.5 x 3.5, through, rear bottom corner (install p.10)")]
            if cid == "S_B8":
                # the DW receptacle lives in S_B8; the cord passes through its west side (side B) at the rear bottom
                extra["holes"] = [("B", D - C["back_in"] - bt_ - 2, 2.0, 1.25, "DW power cord passage, 1 1/4 through, rear bottom; receptacle on this cabinet's back")]
            if variant == "corner": extra["shelves"] = 1
            carcass(C, cid, W, H, D, variant, parts, extra); rec["ladder"] = True
        elif kind == "filler" and "WALLFILL" in cid:
            parts.append(Part(cid, "scribe_strip", H, W, C["ply_t"], "ply"))
        else:
            continue
        if cid in fronts and fronts[cid][1] == "drawers":
            drawer_boxes(C, cid, W, fronts[cid][2], parts, hw)
        cabs.append(rec)
    ladders(C, cabs, parts)

    # ---- cutlist.csv
    with open(os.path.join(out, "cutlist.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cabinet", "part", "qty", "length", "width", "thickness", "material", "features"])
        for p in parts:
            w.writerow([p.cab, p.name, p.qty, "%.4f" % p.L, "%.4f" % p.W, "%.3f" % p.t, p.mat, p.feature_text()])

    # ---- fronts.csv (Bofronts), nominal SEKTION sizes
    std_w, std_h = (12, 15, 18, 24, 30, 36), (5, 10, 15, 20, 30)
    with open(os.path.join(out, "fronts.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cabinet", "front", "qty", "nominal_w", "nominal_h", "note"])
        for c in K["cabinets"]:
            cid, W, H = c[0], c[3], c[4]
            if cid in fronts:
                fr = fronts[cid]
                if fr[1] == "doors":
                    n = fr[2]; dw = 24 if "CORNER" in cid else W / n
                    w.writerow([cid, "door", n, "%g" % dw, "%g" % H, "standard" if (dw in std_w and H in std_h) else "Bofronts custom"])
                    hw.append([cid, "doors", "Blum CLIP top BLUMOTION 110 hinge + 0 mm plate", 2 * n, "2 per door"])
                else:
                    for i, h in enumerate(fr[2]):
                        w.writerow([cid, "drawer front %d" % (i + 1), 1, "%g" % W, "%g" % h, "undrilled; " + ("standard" if (W in std_w and h in std_h) else "Bofronts custom")])
            if c[7] == "filler" and "END" in cid and W > 0:
                w.writerow([cid, "cover panel", 1, "25", "35", "base cover panel, trim to %g x %g on site" % (c[5] + 0.75, c[4] + K["toe_h"])])
            if cid == "S_GAP":
                w.writerow([cid, "filler strip", 1, "%g" % W, "30", "front filler closing the corner gap, flush with the fronts"])
            if "CORNER" in cid:
                w.writerow([cid, "blind panel face", 1, "%g" % C["corner_blind_w"], "30", "optional: Bofronts matching face on the fixed panel, else prefinished ply"])
        w.writerow(["S_DW", "dishwasher panel", 1, "24", "30", "Bofronts DW panel for SEKTION; Bosch p.15: 3 to 10 kg, max 30 1/2 high, 1/4 gap to the counter underside"])
        for u in ("FR1", "FR2"):
            w.writerow([u, "fridge door panel", 1, "%.4f" % C["fr_panel_w"], "%.4f" % C["fr_panel_fridge_h"], "Bofronts custom, LG jig, under 10 kg [verify height in the LG install manual]"])
            w.writerow([u, "freezer door panel", 1, "%.4f" % C["fr_panel_w"], "%.4f" % C["fr_panel_freezer_h"], "Bofronts custom, LG jig, under 10 kg [LG table: 701 mm at 20 mm sides]"])
        bay = next((c for c in K["cabinets"] if c[7] == "tall"), None)
        for p in parts:
            if p.name == "rail":
                m = re.match(r"LADDER\d+_(\w+)_([\d.]+)_to_([\d.]+)", p.cab)
                a, b = float(m.group(2)), float(m.group(3))
                L = p.L
                if bay and m.group(1) == bay[1] and a <= bay[2] < b:
                    L -= bay[3]   # the fridge bay has its own grilled toe board
                w.writerow([p.cab, "toe kick facing", 1, "%.3f" % L, "%g" % K["toe_h"], "Bofronts toe kick, or prefinished ply strip on the front rail, 3 behind the fronts"
                            + ("; the fridge bay segment is its own grilled toe board" if L != p.L else "")])

    # ---- hardware.csv
    with open(os.path.join(out, "hardware.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cabinet", "item", "part", "qty", "note"])
        for row in hw: w.writerow(row)
        for p in parts:
            if p.name == "shelf" and p.cab != "S_FRIDGE_BAY":
                w.writerow([p.cab, "shelf", "5 mm shelf pins", 4, "in the 32 mm rows"])
        w.writerow(["ALL", "fronts", "handles", "per fronts.csv count", "your choice"])
        w.writerow(["ALL", "carcass", "glue, 8 mm dowels optional at finished ends", "", "finger joints are glue only"])

    # ---- countertop.csv: cutouts for the counter fabricator
    ct = [a for a in K["appliances"] if a[0] == "CT"][0]
    with open(os.path.join(out, "countertop.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["wall", "cutout", "from_wall_corner_along_wall", "width_along_wall", "from_counter_front_edge", "depth", "note"])
        w.writerow([ct[2], "cooktop", "%.4f" % ct[3], "%.4f" % ct[4], "2.7500", "%.4f" % ct[6], "KitchenAid KCGG530PBL, 28 7/8 x 19 13/16, front edge 2 3/4 behind the counter front"])
        sk = [a for a in K["appliances"] if a[0] == "SINK"][0]
        w.writerow([sk[2], "sink", "%.4f" % (sk[3]), "47.2500", "2.0000", "19.6875", "top mount Segong 1200 x 500; cut to the sink's template, not to these numbers [verify]"])

    # ---- DXF per cabinet
    by_cab = {}
    for p in parts: by_cab.setdefault(p.cab, []).append(p)
    for cab, ps in by_cab.items():
        d = DXF(); x = 0
        for p in ps:
            for q in range(p.qty):
                d.poly([(x + a, b) for (a, b) in p.poly], "OUTLINE")
                for (cx, cy) in p.dogbones:
                    d.circle(x + cx, cy, C["bit_d"], "DOGBONE")
                d.text(x + 0.3, p.W + 0.5, "%s %s %.3f x %.3f x %.3f" % (cab, p.name, p.L, p.W, p.t))
                for ftr in p.feats:
                    if ftr[0] == "POCKET":
                        _, fx, fy, fw_, fh, dep, note = ftr
                        d.rect(x + fx, fy, fw_, fh, "POCKET_" + mils(dep)); d.text(x + fx, fy + fh + 0.05, note, h=0.2)
                    elif ftr[0] == "THRU":
                        _, fx, fy, fw_, fh, _, note = ftr
                        d.rect(x + fx, fy, fw_, fh, "THRU"); d.text(x + fx, fy + fh + 0.05, note, h=0.2)
                    else:
                        _, fx, fy, dia, dep, _, note = ftr
                        d.circle(x + fx, fy, dia, "HOLE_%s_%s" % (mils(dia), "THRU" if dep is None else mils(dep)))
                for i, nt in enumerate(p.notes):
                    d.text(x + 0.3, -0.5 - 0.3 * i, nt, h=0.2)
                x += p.L + 2
        d.save(os.path.join(out, cab + ".dxf"))

    # ---- ops.txt
    with open(os.path.join(out, "ops.txt"), "w") as f:
        f.write("""Layer legend, every part drawn with its feature face UP (see cutlist.py header for which face):
  OUTLINE        through cut, tool outside the line. Finger joints are in the outline.
  DOGBONE        1/4 relief circles at the inside corners of finger notches; keep, or let the CAM add its own.
  THRU           through pocket, tool inside the line (vent slots, tab slots, Tandem rear notch, drainboard relief).
  POCKET_375     pocket 0.375 deep: carcass dados and rabbets (back, floor, stretchers, rails, ledgers).
  POCKET_250     pocket 0.250 deep: drawer bottom grooves in 5/8 stock (1/2 bottoms).
  POCKET_188     pocket 0.1875 deep: cooktop clamp relief on the oven cabinet sides.
  POCKET_<other> drainboard relief on the sink base front stretcher, depth = drainboard drop - slab.
  HOLE_197_THRU  5 mm through? no: see below.
  HOLE_197_512   5 mm x 13 mm deep: the 32 mm system rows (hinge plates, shelf pins, optional runner screws).
  HOLE_236_394   6 mm x 10 mm deep: Tandem rear hook holes in the drawer backs, drilled from the REAR face. The back is drawn
                 inside face up for its groove; flip it for these two holes (the only second-face operation in the kitchen).
  HOLE_1250_THRU 1 1/4 through: oven cable / cooktop cord passage between W_OVEN30 and W_D30, upper rear corner.
  NOTE           text, not geometry.
Setup rules:
  Sides: inside face up, front edge at x = 0, bottom at y = 0. side_A is the low-pos end (east on the window wall,
  south on the oven wall), side_B the high-pos end. Slabs: inside face up, front at x = 0, low-pos end at y = 0.
  Stretchers and rails: top face up. Drawer parts: inside face up, bottom at y = 0, front/back ends at x = 0 and x = L.
  Joint fit: finger widths and slot sizes are nominal. Cut one coupon per stock sheet and set the CAM's
  fit allowance from it before cutting cabinets.
  Second setup: drawer backs only, flipped, for the two hook holes. Everything else is one face.
""")

    # ---- summary.txt
    area = lambda mat, th: sum(p.L * p.W * p.qty for p in parts if p.mat == mat and abs(p.t - th) < 0.01)
    sheet = C["sheet_w"] * C["sheet_l"]
    verify = [l.strip() for l in open(sys.argv[2]) if "[verify]" in l and not l.strip().startswith("//")]
    with open(os.path.join(out, "summary.txt"), "w") as f:
        f.write("parts: %d lines, %d pieces\n" % (len(parts), sum(p.qty for p in parts)))
        f.write("3/4 ply: %.1f sq ft, about %d sheets at 80%% yield (not a nesting result)\n" % (area("ply", C["ply_t"]) / 144, math.ceil(area("ply", C["ply_t"]) / sheet / 0.8)))
        f.write("5/8 Baltic birch: %.1f sq ft, about %d sheets\n" % (area("bb", C["drawer_t"]) / 144, math.ceil(area("bb", C["drawer_t"]) / sheet / 0.8)))
        f.write("1/2 Baltic birch (bottoms): %.1f sq ft, about %d sheets\n" % (area("bb", C["drawer_bot_t"]) / 144, math.ceil(area("bb", C["drawer_bot_t"]) / sheet / 0.8)))
        f.write("\nDrawer schedule (box width = cabinet inside - 42 mm + 2 x %.4f; box height = front - %g):\n" % (C["drawer_t"], C["box_h_minus"]))
        for cid, fr in fronts.items():
            if fr[1] != "drawers": continue
            W = byid[cid][3]; inner = W - 2 * C["ply_t"]; inside = inner - 42 * MM
            z = K["toe_h"]
            for i, h in enumerate(reversed(fr[2])):
                f.write("  %-8s front %d from the bottom: z %.3f to %.3f, box %.4f wide x %g high, inside width %.1f mm\n" % (cid, i + 1, z, z + h, inside + 2 * C["drawer_t"], max(4, h - C["box_h_minus"]), inside / MM))
                z += h
        f.write("\nlayout checks (draw.py) are about positions; this file is about parts. Neither is a physical test.\n")
        f.write("fridge bay: built to the LG spec sheet cabinet figure. Ladder cross pieces under end panels and divider only.\n")
        f.write("oven cabinet: open back, floor at %.3f on a toe board and a rear ledger, no top (front rail + rear stretcher), clamp relief on the sides.\n" % C["ov_floor"])
        if sink_drain:
            drop = sink_drain[5] - K["counter_t"]
            f.write("drainboard: drop %.3f below the counter, slab %.3f: %s\n" % (sink_drain[5], K["counter_t"],
                    "relief generated in the S_B24 top slab and in the two side panels under it (sink base west, S_B24 east) [verify the drop and the depression footprint]" if drop > 0 else "no relief needed"))
        f.write("\n[verify] in construction.scad, measure before cutting:\n")
        for v in verify: f.write("  " + v + "\n")
    print(open(os.path.join(out, "summary.txt")).read())

if __name__ == "__main__":
    main()
