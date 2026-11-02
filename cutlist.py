#!/usr/bin/env python3
"""cutlist.py -- part list and DXF for every box in kitchen_data.scad, built per construction.scad.

usage: python3 cutlist.py kitchen_data.scad construction.scad out_dir

Writes, into out_dir:
  cutlist.csv        one row per part: cabinet, part, qty, length, width, thickness, material, features
  fronts.csv         the Bofronts order: one row per door or drawer front, nominal size
  summary.txt        sheet estimate and the [verify] list
  <CABINET>.dxf      all parts of that cabinet laid flat: OUTLINE (with finger joints), DADO (pockets),
                     HOLE, DOGBONE (relief circles at notch corners, bit diameter; keep or let the CAM redo them)
Everything is a flat 2D cut. Carcass top and bottom are finger-jointed to the sides, the back sits in
dados. Drawer boxes are finger-jointed at all four corners. No part stands on edge.
"""
import csv, math, os, re, sys

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
        self.e += ["0\nLINE\n8\n%s\n10\n%.4f\n20\n%.4f\n11\n%.4f\n21\n%.4f\n" % (layer, x1, y1, x2, y2)]
    def rect(self, x, y, w, h, layer):
        self.line(x, y, x + w, y, layer); self.line(x + w, y, x + w, y + h, layer)
        self.line(x + w, y + h, x, y + h, layer); self.line(x, y + h, x, y, layer)
    def circle(self, x, y, d, layer):
        self.e += ["0\nCIRCLE\n8\n%s\n10\n%.4f\n20\n%.4f\n40\n%.4f\n" % (layer, x, y, d / 2)]
    def text(self, x, y, s, layer="NOTE", h=0.5):
        self.e += ["0\nTEXT\n8\n%s\n10\n%.4f\n20\n%.4f\n40\n%.3f\n1\n%s\n" % (layer, x, y, h, s)]
    def save(self, path):
        with open(path, "w") as f:
            f.write("0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n9\n$INSUNITS\n70\n1\n0\nENDSEC\n"
                    "0\nSECTION\n2\nENTITIES\n" + "".join(self.e) + "0\nENDSEC\n0\nEOF\n")

# ---------------------------------------------------------------- parts
class Part:
    """A flat rectangle L x W of thickness t. Features are drawn in the part's own frame:
    origin bottom-left, L along x, W along y. feats: list of (kind, x, y, w, h | d, note)."""
    def __init__(self, cab, name, L, W, t, mat, qty=1):
        self.cab, self.name, self.L, self.W, self.t, self.mat, self.qty = cab, name, L, W, t, mat, qty
        self.feats = []
        self.poly = [(0, 0), (L, 0), (L, W), (0, W)]   # outline, counterclockwise; fingered edges replace it
        self.dogbones = []                              # (x, y) centres of bit-diameter relief circles
    def fingers(self, edges, bit_d):
        """edges: {"bottom"|"right"|"top"|"left": (depth, finger_w, start_tab)}. The nominal L x W is the
        outer envelope; notches are cut inward by depth. start_tab says whether the first finger at the
        edge's start (bottom-left going counterclockwise) is a tab (full) or a notch."""
        self.poly, self.dogbones = fingered_outline(self.L, self.W, edges, bit_d)
    def pocket(self, x, y, w, h, note):
        self.feats.append(("DADO", x, y, w, h, note))
    def hole(self, x, y, d, note=""):
        self.feats.append(("HOLE", x, y, d, 0, note))
    def note(self, s):
        self.feats.append(("NOTE", 0, 0, 0, 0, s))

def finger_profile(length, depth, fw, start_tab):
    """Points along an edge from 0 to length, y = 0 at the envelope, y = -depth in a notch."""
    n = max(2, int(round(length / fw)))
    if n % 2 == 0 and start_tab is not None:
        n = n  # even count: edge starts and ends with opposite states; fine for mating parts
    f = length / n
    pts, corners = [], []
    tab = start_tab
    x = 0.0
    for i in range(n):
        y0 = 0.0 if tab else -depth
        pts.append((x, y0)); pts.append((x + f, y0))
        if not tab:
            corners.append((x, -depth)); corners.append((x + f, -depth))
        x += f; tab = not tab
    return pts, corners

def fingered_outline(L, W, edges, bit_d):
    """Counterclockwise outline of an L x W envelope with fingered edges. Dogbone relief circles at
    every inside corner of every notch, centred so the circle passes through the corner."""
    r = bit_d / 2
    poly, bones = [], []
    def edge(name, p0, p1, inward):
        # p0 -> p1 is the outline direction. The finger pattern is always generated from the end with
        # the smaller x (or y), so start_tab means "tab at x = 0" / "tab at y = 0" on every edge and the
        # same pattern on the top and bottom edges of a part lines up.
        e = edges.get(name)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        length = (dx * dx + dy * dy) ** 0.5
        if not e:
            poly.append(p0); return
        depth, fw, start_tab = e
        reverse = name in ("top", "left")
        q0, q1 = (p1, p0) if reverse else (p0, p1)
        ux, uy = (q1[0] - q0[0]) / length, (q1[1] - q0[1]) / length
        pts, corners = finger_profile(length, depth, fw, start_tab)
        seq = [(q0[0] + ux * a + inward[0] * (-b), q0[1] + uy * a + inward[1] * (-b)) for (a, b) in pts]
        poly.extend(reversed(seq) if reverse else seq)
        p0 = q0
        # inside corners: pairs (left corner, right corner) of each notch bottom
        for i in range(0, len(corners), 2):
            (a1, _), (a2, _) = corners[i], corners[i + 1]
            cx1 = p0[0] + ux * a1 + inward[0] * depth; cy1 = p0[1] + uy * a1 + inward[1] * depth
            cx2 = p0[0] + ux * a2 + inward[0] * depth; cy2 = p0[1] + uy * a2 + inward[1] * depth
            k = r / 2 ** 0.5
            # push the circle into the notch: along the edge toward the notch interior, and outward (-inward)
            bones.append((cx1 + ux * k - inward[0] * k, cy1 + uy * k - inward[1] * k))
            bones.append((cx2 - ux * k - inward[0] * k, cy2 - uy * k - inward[1] * k))
    edge("bottom", (0, 0), (L, 0), (0, 1))
    edge("right",  (L, 0), (L, W), (-1, 0))
    edge("top",    (L, W), (0, W), (0, -1))
    edge("left",   (0, W), (0, 0), (1, 0))
    # drop consecutive duplicates
    out = []
    for q in poly:
        if not out or abs(out[-1][0] - q[0]) > 1e-9 or abs(out[-1][1] - q[1]) > 1e-9:
            out.append(q)
    return out, bones

def holes_row(part, x, z0, zmax, pitch, d, note):
    z = z0
    while z <= zmax:
        part.hole(x, z, d, note); z += pitch

def carcass(C, cab, W, H, D, kind, variant, parts):
    """Standard box: 2 sides, bottom, top (or 2 stretchers), full back. Side frame: x = depth
    (0 = front edge), y = height (0 = bottom edge)."""
    t, bt, dd = C["ply_t"], C["back_t"], C["dado_depth"]
    side_h = H
    bot_z = C["bot_up"]                       # bottom dado lower edge above the side's bottom edge
    if variant == "oven":
        # sides run to the floor, no ladder under this box; floor of the opening at ov_floor
        side_h = H + C["toe_h"]
        bot_z = C["ov_floor"] - t
    # sides: top and bottom edges fingered (tabs first at the front), back in a dado
    fw, bit = C["finger_w"], C["bit_d"]
    s = Part(cab, "side", D, side_h, t, "ply", 2)
    edges = {"bottom": (t, fw, True)} if variant != "oven" else {}
    if variant != "sink":
        edges["top"] = (t, fw, True)
    s.fingers(edges, bit)
    if variant == "oven":
        # sides run to the floor; the opening floor is a captured panel in a dado, not a corner joint
        s.pocket(0, bot_z, D - C["back_in"], t, "floor dado, %.3f deep" % dd)
    s.pocket(D - C["back_in"] - bt, (0 if variant == "oven" else t), bt, side_h - (0 if variant == "oven" else 2 * t) - (0 if variant != "sink" else -t), "back dado, %.3f deep" % dd)
    if variant == "sink":
        s.pocket(0, side_h - 4, t, 4, "front stretcher dado"); s.pocket(D - C["back_in"] - bt - t, side_h - 4, t, 4, "rear stretcher dado")
    holes_row(s, C["row_front"], C["row_first_z"], side_h - 1, C["row_pitch"], C["row_hole_d"], "front 32 mm row")
    holes_row(s, D - C["back_in"] - bt - C["row_rear"], C["row_first_z"], side_h - 1, C["row_pitch"], C["row_hole_d"], "rear 32 mm row")
    if variant == "oven":
        s.pocket(0, side_h - 3.25, 3.25, 3.25, "cooktop notch 3/16 deep from the INSIDE face, top front")
        s.note("sides run to the floor: toe board in front, floor of the opening at %.3f" % C["ov_floor"])
    if variant == "corner":
        s.note("blind corner: a 23 fixed panel closes the half toward the window wall")
    parts.append(s)
    # top and bottom: full width W (fingers through the sides), full depth D, back dado near the rear
    def slab(name):
        q = Part(cab, name, D, W, t, "ply")
        q.fingers({"bottom": (t, fw, False), "top": (t, fw, False)}, bit)   # ends at y = 0 and y = W
        q.pocket(D - C["back_in"] - bt, t, bt, W - 2 * t, "back dado, %.3f deep" % dd)
        return q
    if variant == "oven":
        parts.append(Part(cab, "floor", D - C["back_in"] - bt + dd, W - 2 * t + 2 * dd, t, "ply"))
    else:
        parts.append(slab("bottom"))
    inner = W - 2 * t
    if variant == "sink":
        parts.append(Part(cab, "stretcher", inner + 2 * dd, 4, t, "ply", 2))
        back_h = side_h - t - dd        # from the bottom slab's dado to the top edge
    else:
        parts.append(slab("top"))
        back_h = side_h - 2 * t + 2 * dd
    parts.append(Part(cab, "back", inner + 2 * dd, back_h, bt, "ply"))
    if variant == "corner":
        parts.append(Part(cab, "blind_panel", 23.625, H, t, "ply"))

def drawer_boxes(C, cab, W, heights, parts):
    t, bt, bit = C["drawer_t"], C["drawer_bot_t"], C["bit_d"]
    inner = W - 2 * C["ply_t"]
    bw = inner - C["box_w_minus"]
    for i, fh in enumerate(heights):
        bh = max(4, fh - C["box_h_minus"])
        tag = "drawer%d" % (i + 1)
        # sides: fingers on both vertical ends (front and back), tabs first at the bottom
        side = Part(cab, tag + "_side", C["box_depth"], bh, t, "bb", 2)
        side.fingers({"left": (t, t, True), "right": (t, t, True)}, bit)
        side.pocket(0, C["box_bot_up"], C["box_depth"], bt, "bottom dado 1/4 deep")
        side.pocket(C["box_depth"] - C["rear_notch_w"], 0, C["rear_notch_w"], C["rear_notch_h"], "Tandem rear notch [verify]")
        parts.append(side)
        # front and back: full outer width, notches first at the bottom so they mate with the sides
        fb = Part(cab, tag + "_front_back", bw, bh, t, "bb", 2)
        fb.fingers({"left": (t, t, False), "right": (t, t, False)}, bit)
        fb.pocket(0, C["box_bot_up"], bw, bt, "bottom dado 1/4 deep")
        fb.hole(C["hook_hole_x"], C["hook_hole_z"], C["hook_hole_d"], "Tandem hook hole, back panel only [verify]")
        fb.hole(bw - C["hook_hole_x"], C["hook_hole_z"], C["hook_hole_d"], "Tandem hook hole [verify]")
        parts.append(fb)
        parts.append(Part(cab, tag + "_bottom", C["box_depth"] - 2 * t + 2 * 0.25, bw - 2 * t + 2 * 0.25, bt, "bb"))

def fridge_bay(C, cab, W, H, D, parts):
    t = C["ply_t"]
    parts.append(Part(cab, "end_panel", D, H, t, "ply", 2))
    parts.append(Part(cab, "divider", D, H - t, t, "ply"))
    parts.append(Part(cab, "shelf", D, W - 2 * t + 2 * C["dado_depth"], t, "ply"))

def ladders(C, cabs, parts):
    """One ladder per contiguous run of ladder-kind boxes on a wall."""
    runs = {}
    for c in cabs:
        if c["ladder"]:
            runs.setdefault(c["wall"], []).append(c)
    n = 0
    for wall, cs in runs.items():
        cs.sort(key=lambda c: c["pos"])
        start, end = cs[0]["pos"], cs[0]["pos"] + cs[0]["W"]
        segs = []
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
    C["base_d"] = K["base_d"]
    # oven opening floor above the finished floor, from the OV appliance line
    ov = [a for a in K["appliances"] if a[0] == "OV"][0]
    C["ov_floor"] = ov[7]
    fronts = {f[0]: f for f in C["fronts"]}

    parts, cabs = [], []
    for c in K["cabinets"]:
        cid, wall, pos, W, H, D, z, kind = c[:8]
        rec = {"id": cid, "wall": wall, "pos": pos, "W": W, "ladder": False}
        if kind == "filler" or kind == "zone" and cid not in ("W_OVEN30",):
            continue
        if cid == "W_OVEN30":
            carcass(C, cid, W, H, D, kind, "oven", parts)
        elif kind == "tall":
            fridge_bay(C, cid, W, H, D, parts)
        elif kind == "wall":
            carcass(C, cid, W, H, D, kind, "wall", parts)
        elif kind == "base":
            variant = "sink" if cid.startswith("S_SB") else "corner" if "CORNER" in cid else "base"
            carcass(C, cid, W, H, D, kind, variant, parts)
            rec["ladder"] = True
        if cid in fronts and fronts[cid][1] == "drawers":
            drawer_boxes(C, cid, W, fronts[cid][2], parts)
        cabs.append(rec)
    ladders(C, cabs, parts)

    # cutlist.csv
    with open(os.path.join(out, "cutlist.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cabinet", "part", "qty", "length", "width", "thickness", "material", "features"])
        for p in parts:
            feats = "; ".join(sorted({x[5] for x in p.feats if x[5]}))
            w.writerow([p.cab, p.name, p.qty, "%.4f" % p.L, "%.4f" % p.W, "%.3f" % p.t, p.mat, feats])

    # fronts.csv (Bofronts order, nominal SEKTION sizes)
    with open(os.path.join(out, "fronts.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cabinet", "front", "qty", "nominal_w", "nominal_h", "note"])
        for c in K["cabinets"]:
            cid, W, H = c[0], c[3], c[4]
            if cid not in fronts: continue
            fr = fronts[cid]
            if fr[1] == "doors":
                n = fr[2]; dw = 24 if "CORNER" in cid else W / n
                w.writerow([cid, "door", n, "%g" % dw, "%g" % H, "standard" if dw in (12, 15, 18, 24, 30, 36) else "Bofronts custom"])
            else:
                for i, h in enumerate(fr[2]):
                    w.writerow([cid, "drawer front %d" % (i + 1), 1, "%g" % W, "%g" % h, "order undrilled; " + ("standard" if W in (12, 15, 18, 24, 30, 36) else "Bofronts custom")])
        for c in K["cabinets"]:
            if c[7] == "filler" and "END" in c[0] and c[3] > 0:
                w.writerow([c[0], "cover panel", 1, "25", "35", "Bofronts base cover panel, trim to %g x %g on site (box depth + front, box + ladder)" % (c[5] + 0.75, c[4] + K["toe_h"])])
        w.writerow(["S_DW", "dishwasher panel", 1, "24", "30", "Bofronts custom, Bosch 7 to 18 lb"])
        w.writerow(["S_FRIDGE_BAY", "fridge door panel", 2, "22", "70", "Bofronts custom, LG panel spec"])

    # DXF per cabinet
    by_cab = {}
    C_bit = C["bit_d"]
    for p in parts: by_cab.setdefault(p.cab, []).append(p)
    for cab, ps in by_cab.items():
        d = DXF(); x = 0
        for p in ps:
            for q in range(p.qty):
                pts = p.poly
                for (ax_, ay_), (bx_, by_) in zip(pts, pts[1:] + pts[:1]):
                    d.line(x + ax_, ay_, x + bx_, by_, "OUTLINE")
                for (cx_, cy_) in p.dogbones:
                    d.circle(x + cx_, cy_, C_bit, "DOGBONE")
                d.text(x + 0.5, p.W + 0.6, "%s %s %.3fx%.3fx%.3f" % (cab, p.name, p.L, p.W, p.t))
                for k, fx, fy, fw, fh, note in p.feats:
                    if k == "DADO": d.rect(x + fx, fy, fw, fh, "DADO")
                    elif k == "HOLE": d.circle(x + fx, fy, fw, "HOLE")
                x += p.L + 2
        d.save(os.path.join(out, cab + ".dxf"))

    # summary
    area = sum(p.L * p.W * p.qty for p in parts if p.mat == "ply")
    area_bb = sum(p.L * p.W * p.qty for p in parts if p.mat == "bb" and p.t == C["drawer_t"])
    area_bot = sum(p.L * p.W * p.qty for p in parts if p.t == C["drawer_bot_t"])
    sheet = C["sheet_w"] * C["sheet_l"]
    verify = [l.strip() for l in open(sys.argv[2]) if "[verify]" in l]
    with open(os.path.join(out, "summary.txt"), "w") as f:
        f.write("parts: %d lines, %d pieces\n" % (len(parts), sum(p.qty for p in parts)))
        f.write("3/4 ply: %.1f sq ft, about %d sheets at 80%% yield\n" % (area / 144, math.ceil(area / sheet / 0.8)))
        f.write("5/8 Baltic birch: %.1f sq ft, about %d sheets\n" % (area_bb / 144, math.ceil(area_bb / sheet / 0.8)))
        f.write("1/4 Baltic birch: %.1f sq ft, about %d sheets\n" % (area_bot / 144, math.ceil(area_bot / sheet / 0.8)))
        f.write("\nfridge bay: panels only. Base, vent openings and panel fixing wait for the LG installation manual.\n")
        f.write("set ply_t in construction.scad to the measured sheet thickness (18 mm or 23/32 is usual); drawer box widths depend on it.\n")
        f.write("\nNumbers tagged [verify] in construction.scad, measure before cutting:\n")
        for v in verify: f.write("  " + v + "\n")
    print(open(os.path.join(out, "summary.txt")).read())

if __name__ == "__main__":
    main()
