#!/usr/bin/env python3
"""cutlist.py -- part list, DXF per cabinet and order sheets for every box in kitchen_data.scad,
built per construction.scad.

usage: python3 cutlist.py kitchen_data.scad construction.scad out_dir

Writes into out_dir (stale .dxf files there are deleted first):
  cutlist.csv      one row per part: cabinet, part, qty, length, width, thickness, material, features
  fronts.csv       the Bofronts order: nominal module and finished size per door, drawer front, panel, filler
  hardware.csv     runners, locking devices, hinges, plates, shelf pins, kick clips, per cabinet
  services.csv     every hole for a cord, hose or gas line: cabinet, side, position, size, purpose
  countertop.csv   the two countertop cutouts for the counter fabricator, with explicit origins
  ops.txt          layer legend (face, tool, depth), handed parts, hand operations
  summary.txt      sheet estimate, drawer and runner schedule, the [verify] list from both data files
  <CABINET>.dxf    all parts of that cabinet laid flat

Conventions
  Every part is drawn with its FEATURE FACE up. Side: inside face up, front edge at x = 0, bottom edge
  at y = 0. Slab (top, bottom, floor, shelf): inside face up, front at x = 0, low-pos end at y = 0 (east
  end on the window wall, south end on the oven wall). Drawer parts: inside face up, bottom at y = 0.
  The drawer back and the drawer bottom need a second face (hook bores from the rear; the bottom's
  rabbet is on its top face): see ops.txt.
  Layers: OUTLINE (closed polyline, tool outside), THRU (through pocket, tool inside), POCKET_<mils>
  (pocket to that depth, thousandths of an inch), HOLE_<dia mils>_<depth mils>, HOLE_<dia mils>_THRU,
  DOGBONE_<depth mils|THRU> (bit-diameter relief circles at inside corners that a square part must enter),
  NOTE (text).
  Validation runs before any DXF is written: closed simple outlines, no backtracking, every hole in
  material, blind bores not breaking into the opposite face's pockets, every part within the sheet.
"""
import csv, math, os, re, sys, glob

MM = 1 / 25.4

# ---------------------------------------------------------------- scad data reader
def read_scad(path, ns=None):
    ns = {} if ns is None else dict(ns)
    src = re.sub(r"//[^\n]*", "", open(path).read())
    # scalar: one per line, value runs to the last ';' on the line (strings may contain ';')
    for m in re.finditer(r"^\s*([A-Za-z_]\w*)\s*=\s*(?!\[)(.+?)\s*;\s*$", src, re.M):
        ns[m.group(1)] = eval(m.group(2), {}, ns)
    for m in re.finditer(r"^\s*([A-Za-z_]\w*)\s*=\s*(\[.*?\])\s*;", src, re.M | re.S):
        ns[m.group(1)] = eval(re.sub(r",\s*\]", "]", m.group(2)), {}, ns)
    return ns

# ---------------------------------------------------------------- tiny DXF writer (R12, closed POLYLINE)
class DXF:
    def __init__(self):
        self.e = []
    def poly(self, pts, layer):
        self.e.append("0\nPOLYLINE\n8\n%s\n66\n1\n70\n1\n" % layer)
        for (x, y) in pts:
            self.e.append("0\nVERTEX\n8\n%s\n10\n%.4f\n20\n%.4f\n" % (layer, x, y))
        self.e.append("0\nSEQEND\n8\n%s\n" % layer)
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

# ---------------------------------------------------------------- geometry
def finger_profile(length, depth, fw, start_tab):
    n = max(2, int(round(length / fw)))
    f = length / n
    pts, corners, tab, x = [], [], start_tab, 0.0
    for i in range(n):
        y0 = 0.0 if tab else -depth
        pts += [(x, y0), (x + f, y0)]
        if not tab:
            corners.append((x, x + f))
        x += f
        tab = not tab
    return pts, corners

def fingered_outline(L, W, edges, bit_d):
    """Counterclockwise outline of an L x W envelope. edges maps bottom|right|top|left to
    (depth, finger_w, start_tab); start_tab is "tab at x = 0" (bottom/top) or "tab at y = 0" (left/right).
    A straight edge after a fingered one starts where that one ended (no backtracking)."""
    r = bit_d / 2
    poly, bones = [], []
    spec = [("bottom", (0, 0), (L, 0), (0, 1)), ("right", (L, 0), (L, W), (-1, 0)),
            ("top", (L, W), (0, W), (0, -1)), ("left", (0, W), (0, 0), (1, 0))]
    fingered = [bool(edges.get(n_)) for (n_, _, _, _) in spec]
    for idx, (name, p0, p1, inward) in enumerate(spec):
        e = edges.get(name)
        if not e:
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
            for a, s in ((a1, +1), (a2, -1)):
                cx = q0[0] + ux * a + inward[0] * depth
                cy = q0[1] + uy * a + inward[1] * depth
                bones.append((cx + ux * k * s - inward[0] * k, cy + uy * k * s - inward[1] * k))
    return dedupe(poly), bones

def dedupe(poly):
    out = []
    for q in poly:
        if not out or abs(out[-1][0] - q[0]) > 1e-9 or abs(out[-1][1] - q[1]) > 1e-9:
            out.append(q)
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-9 and abs(out[0][1] - out[-1][1]) < 1e-9:
        out.pop()
    return out

def clip_band(poly, axis, lo, hi, limit, keep_below):
    """Subtract from a rectilinear outline the half-strip {lo < a < hi, b > limit} (keep_below=True) or
    {lo < a < hi, b < limit} (keep_below=False); a is the coordinate on `axis` (0 = x, 1 = y), b the other.
    Used to merge notches and reliefs that touch an edge into the outline itself."""
    o = 1 - axis
    def A(p): return p[axis]
    def B(p): return p[o]
    def mk(a, b): return (a, b) if axis == 0 else (b, a)
    pts = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        pts.append(p)
        cross = [a for a in (lo, hi) if (A(p) - a) * (A(q) - a) < 0]
        cross.sort(key=lambda a: abs(a - A(p)))
        for a in cross:
            tt = (a - A(p)) / (A(q) - A(p))
            pts.append(mk(a, B(p) + tt * (B(q) - B(p))))
    out = []
    for p in pts:
        if lo - 1e-9 < A(p) < hi + 1e-9:
            b = B(p)
            b = min(b, limit) if keep_below else max(b, limit)
            out.append(mk(A(p), b))
        else:
            out.append(p)
    return dedupe(out)

def polygon_area(poly):
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly)))

def point_in_poly(pt, poly):
    x, y = pt; n = len(poly); c = False
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c

def segs_cross(p, q, r, s):
    def o(a, b, c): return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    d1, d2, d3, d4 = o(r, s, p), o(r, s, q), o(p, q, r), o(p, q, s)
    return d1 * d2 < -1e-12 and d3 * d4 < -1e-12

# ---------------------------------------------------------------- parts
class Part:
    """A flat piece L (x) by W (y) of thickness t. Outline self.poly, counterclockwise.
    feats: ("POCKET"|"THRU", x, y, w, h, depth|None, note, mates). holes: (x, y, dia, depth|None, face, note)."""
    def __init__(self, cab, name, L, W, t, mat, qty=1):
        self.cab, self.name, self.L, self.W, self.t, self.mat, self.qty = cab, name, L, W, t, mat, qty
        self.feats, self.holes, self.notes = [], [], []
        self.poly = [(0, 0), (L, 0), (L, W), (0, W)]
        self.dogbones = []
    def pocket(self, x, y, w, h, depth, note, mates=False):
        self.feats.append(("POCKET", x, y, w, h, depth, note, mates))
    def thru(self, x, y, w, h, note, mates=False):
        self.feats.append(("THRU", x, y, w, h, None, note, mates))
    def hole(self, x, y, d, depth, note, face="feature"):
        self.holes.append((x, y, d, depth, face, note))
    def note(self, s):
        self.notes.append(s)
    def fingers(self, edges, bit_d):
        self.poly, bones = fingered_outline(self.L, self.W, edges, bit_d)
        self.dogbones += [(x, y, "DOGBONE_THRU") for (x, y) in bones]
    def corner_notches(self, c):
        L, W = self.L, self.W
        self.poly = [(c, 0), (L - c, 0), (L - c, c), (L, c), (L, W - c), (L - c, W - c), (L - c, W),
                     (c, W), (c, W - c), (0, W - c), (0, c), (c, c)]
    def notch(self, axis, lo, hi, limit, keep_below):
        self.poly = clip_band(self.poly, axis, lo, hi, limit, keep_below)
    def feature_text(self):
        return "; ".join(sorted({f[6] for f in self.feats} | {h[5] for h in self.holes} | set(self.notes)))
    def add_dogbones(self, bit_d):
        r = bit_d / 2; k = r / 2 ** 0.5
        for f in self.feats:
            kind, x, y, w, h, depth, note, mates = f
            if not mates: continue
            layer = "DOGBONE_THRU" if kind == "THRU" else "DOGBONE_" + mils(depth)
            for (cx, cy, sx, sy) in ((x, y, 1, 1), (x + w, y, -1, 1), (x + w, y + h, -1, -1), (x, y + h, 1, -1)):
                self.dogbones.append((cx + sx * k, cy + sy * k, layer))

def holes_row(part, x, z0, zmax, pitch, d, depth, note):
    z = z0
    while z <= zmax:
        part.hole(x, z, d, depth, note)
        z += pitch

# ---------------------------------------------------------------- validation
def validate(parts, C):
    errs = []
    for p in parts:
        poly = p.poly; n = len(poly)
        if n < 4: errs.append((p, "degenerate outline"))
        if polygon_area(poly) <= 0: errs.append((p, "outline not counterclockwise"))
        for i in range(n):
            a, b, c = poly[i - 1], poly[i], poly[(i + 1) % n]
            v1 = (b[0] - a[0], b[1] - a[1]); v2 = (c[0] - b[0], c[1] - b[1])
            if abs(v1[0] * v2[1] - v1[1] * v2[0]) < 1e-9 and v1[0] * v2[0] + v1[1] * v2[1] < 0:
                errs.append((p, "outline backtracks at %s" % (b,))); break
        for i in range(n):
            for j in range(i + 2, n):
                if i == 0 and j == n - 1: continue
                if segs_cross(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]):
                    errs.append((p, "outline self-intersects")); break
        thru = [f for f in p.feats if f[0] == "THRU"]
        for (x, y, d, depth, face, note) in p.holes:
            r = d / 2
            for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
                q = (x + dx, y + dy)
                if not point_in_poly(q, poly) or any(f[1] - 1e-9 < q[0] < f[1] + f[3] + 1e-9 and f[2] - 1e-9 < q[1] < f[2] + f[4] + 1e-9 for f in thru):
                    errs.append((p, "hole '%s' touches a void" % note[:40])); break
            if depth is not None:
                if depth >= p.t - 1e-9:
                    errs.append((p, "blind hole '%s' as deep as the part" % note[:30]))
                for f in p.feats:
                    if f[0] == "POCKET" and f[1] - r <= x <= f[1] + f[3] + r and f[2] - r <= y <= f[2] + f[4] + r and face == "other":
                        if p.t - depth - f[5] < 0.03:
                            errs.append((p, "bore '%s' (%.3f) meets pocket '%s' (%.3f) in %.3f stock" % (note[:30], depth, f[6][:30], f[5], p.t)))
        if min(p.L, p.W) > C["sheet_w"] or max(p.L, p.W) > C["sheet_l"]:
            errs.append((p, "does not fit a %g x %g sheet" % (C["sheet_w"], C["sheet_l"])))
    if errs:
        for p, e in errs:
            print("VALIDATION FAIL %s %s: %s" % (p.cab, p.name, e), file=sys.stderr)
        sys.exit(2)

# ---------------------------------------------------------------- carcass
def carcass(C, cab, W, H, D, variant, parts, extra=None):
    """variant: base | sink | corner | oven. Two handed sides (A low-pos end, B high-pos end), slabs, back."""
    t, bt, dd = C["ply_t"], C["back_t"], C["dado_depth"]
    fw, bit = C["finger_w"], C["bit_d"]
    extra = extra or {}
    back_in = extra.get("back_in", C["back_in"])
    inner = W - 2 * t
    side_h = H + (C["toe_h"] if variant == "oven" else 0)
    sides = {}
    for name in ("side_A", "side_B"):
        s = Part(cab, name, D, side_h, t, "ply", 1)
        edges = {}
        if variant != "oven":
            edges["bottom"] = (t, fw, True)
            if variant != "sink":
                edges["top"] = (t, fw, True)
        s.fingers(edges, bit)
        if variant == "oven":
            fz = C["ov_floor"] - t
            s.pocket(0, fz, D, t, dd, "floor dado 3/8 deep, floor top face at %.3f" % C["ov_floor"])
            s.pocket(D - 3, side_h - t, 3, t, dd, "rear top stretcher dado 3/8 deep", mates=True)
            s.pocket(0, side_h - 2.5, t, 2.5, dd, "front top rail dado 3/8 deep", mates=True)
            s.pocket(D - t, 0, t, fz, dd, "rear ledger dado 3/8 deep", mates=True)
            s.pocket(C["toe_setback"], 0, t, fz, dd, "toe board dado 3/8 deep, set back like the ladder", mates=True)
            s.pocket(1.25, side_h - 3.5, 21.0625 - 1.25, 3.5, 3 / 16, "cooktop clamp relief 3/16 deep, inside face, under the countertop cutout zone")
            s.note("open back: gas and cords come through the open back; the cooktop guide's right-rear relief is satisfied")
        else:
            s.pocket(D - back_in - bt, t, bt, side_h - 2 * t + (t if variant == "sink" else 0), dd, "back dado 3/8 deep", mates=True)
            holes_row(s, C["row_front"], C["row_first_z"], side_h - 1, C["row_pitch"], C["row_hole_d"], C["row_hole_depth"], "front 32 mm row, 5 x 13 mm")
            holes_row(s, D - back_in - bt - C["row_rear"], C["row_first_z"], side_h - 1, C["row_pitch"], C["row_hole_d"], C["row_hole_depth"], "rear 32 mm row, 5 x 13 mm")
        if variant == "sink":
            s.pocket(0, side_h - 4, t, 4, dd, "front stretcher dado 3/8 deep", mates=True)
            s.pocket(D - back_in - bt - t, side_h - 4, t, 4, dd, "rear stretcher dado 3/8 deep", mates=True)
        sides[name[-1]] = s
    for (which, x, zloc, dia, depth, note) in extra.get("holes", []):
        sides[which].hole(x, zloc, dia, depth, note)
    for (which, x, y, w_, h_, note) in extra.get("thru", []):
        sides[which].thru(x, y, w_, h_, note)
    for (which, x0, x1, dep) in extra.get("side_relief", []):
        s = sides[which]
        s.notch(0, x0, x1, s.W - dep, True)
        s.note("drainboard relief: top edge lowered %.3f over x %.2f to %.2f, fingers removed there" % (dep, x0, x1))
    if variant == "corner":
        sides["A"].note("blind corner: the %g fixed panel closes the half toward the window wall" % C["corner_blind_w"])
    parts += [sides["A"], sides["B"]]
    def slab(name):
        q = Part(cab, name, D, W, t, "ply")
        q.fingers({"bottom": (t, fw, False), "top": (t, fw, False)}, bit)
        q.pocket(D - back_in - bt, t, bt, W - 2 * t, dd, "back dado 3/8 deep", mates=True)
        return q
    if variant == "oven":
        floor = Part(cab, "floor", D, inner + 2 * dd, t, "ply")
        floor.note("in the side dados, on the toe board and the rear ledger; the oven manual asks for a solid level support, 200 lb")
        parts.append(floor)
        parts.append(Part(cab, "toe_board", inner + 2 * dd, C["ov_floor"] - t, t, "ply"))
        parts.append(Part(cab, "rear_ledger", inner + 2 * dd, C["ov_floor"] - t, t, "ply"))
        parts.append(Part(cab, "rear_top_stretcher", inner + 2 * dd, 3, t, "ply"))
        parts.append(Part(cab, "front_top_rail", inner + 2 * dd, 2.5, t, "ply"))
    else:
        parts.append(slab("bottom"))
        if variant == "sink":
            parts.append(Part(cab, "front_stretcher", inner + 2 * dd, 4, t, "ply"))
            parts.append(Part(cab, "rear_stretcher", inner + 2 * dd, 4, t, "ply"))
        else:
            top = slab("top")
            for (x0, x1, y0, y1) in extra.get("top_relief", []):
                top.notch(0, x0, x1, y1, False)
                top.note("drainboard relief: slab cut away over x %.2f to %.2f from the sink end to %.2f, fingers included" % (x0, x1, y1))
            parts.append(top)
        back_h = (H - 2 * t + 2 * dd) if variant != "sink" else (H - t + dd)
        back = Part(cab, "back", inner + 2 * dd, back_h, bt, "ply")
        back.corner_notches(dd)
        if variant == "sink":
            back.note("sits in the bottom dado and the side dados; top edge free behind the rear stretcher")
        for (x, y, dia, note) in extra.get("back_holes", []):
            back.hole(x, y, dia, None, note)
        parts.append(back)
    if variant == "corner":
        parts.append(Part(cab, "blind_panel", C["corner_blind_w"], H, t, "ply"))
    for n in range(extra.get("shelves", 0)):
        parts.append(Part(cab, "shelf", D - back_in - bt - 0.25, inner - 0.125, t, "ply"))

# ---------------------------------------------------------------- drawers
def drawer_boxes(C, cab, W, heights, parts, hw, sched):
    """Blum TANDEM. inside width = cabinet inside - 42 mm; outside = inside + 2 t. Fingers 2 t tall at all
    four corners. Back: 35 x 13 mm notches at both lower corners (in the outline), hook bores 6 x 10 from the
    rear face, 7 mm inboard of the side's inside face, 24 mm up. Bottom: 1/2 rabbeted to a 1/4 tongue in a
    3/16 groove. Front: four 1/4 holes for the Bofronts front screws."""
    t, bt, bit = C["drawer_t"], C["drawer_bot_t"], C["bit_d"]
    gw, gd = C["drawer_groove_w"], C["drawer_groove_d"]
    inner = W - 2 * C["ply_t"]
    inside_w = inner - 42 * MM
    bw = inside_w + 2 * t
    fwd = 2 * t
    narrow = inside_w < 124 * MM
    overrides = {(o[0], o[1]): o[2] for o in C.get("drawer_depth", [])}
    z_front_top = C["toe_h"] + 30
    for i, fh in enumerate(heights):
        bh = max(4, fh - C["box_h_minus"])
        depth = overrides.get((cab, i + 1), C["box_depth"])
        tag = "drawer%d" % (i + 1)
        side = Part(cab, tag + "_side", depth, bh, t, "bb", 2)
        side.fingers({"left": (t, fwd, False), "right": (t, fwd, False)}, bit)
        side.pocket(0, C["box_bot_up"], depth, gw, gd, "bottom groove 1/4 wide x 3/16 deep")
        side.note("two identical parts; the pair is made by turning one over about its vertical axis")
        parts.append(side)
        front = Part(cab, tag + "_front", bw, bh, t, "bb", 1)
        front.fingers({"left": (t, fwd, True), "right": (t, fwd, True)}, bit)
        front.pocket(0, C["box_bot_up"], bw, gw, gd, "bottom groove 1/4 wide x 3/16 deep")
        for x in (1.5, bw - 1.5):
            for y in (max(1.5, C["box_bot_up"] + gw + 0.5), bh - 1.0):
                front.hole(x, y, 0.25, None, "1/4 through, #8 screw + washer into the Bofronts front, 1/16 play")
        parts.append(front)
        back = Part(cab, tag + "_back", bw, bh, t, "bb", 1)
        back.fingers({"left": (t, fwd, True), "right": (t, fwd, True)}, bit)
        back.notch(0, 0, C["back_notch_w"], C["back_notch_h"], False)
        back.notch(0, bw - C["back_notch_w"], bw, C["back_notch_h"], False)
        back.pocket(0, C["box_bot_up"], bw, gw, gd, "bottom groove 1/4 wide x 3/16 deep")
        hx = t + C["hook_hole_in"]
        for x in (hx, bw - hx):
            back.hole(x, C["hook_hole_z"], C["hook_hole_d"], C["hook_hole_depth"], "Tandem hook bore 6 x 10 mm from the REAR face", face="other")
        back.note("Tandem notches 35 x 13 mm at both lower corners, in the outline")
        parts.append(back)
        bottom = Part(cab, tag + "_bottom", depth - 2 * t + 2 * gd, bw - 2 * t + 2 * gd, bt, "bb")
        rb = gd + 1 / 32
        for (x, y, w_, h_) in ((0, 0, bottom.L, rb), (0, bottom.W - rb, bottom.L, rb), (0, 0, rb, bottom.W), (bottom.L - rb, 0, rb, bottom.W)):
            bottom.pocket(x, y, w_, h_, bt - gw, "rabbet on the TOP face: 1/4 tongue all round")
        bottom.note("drawn top face up; the rabbets are the only feature")
        parts.append(bottom)
        z_top = z_front_top - sum(heights[:i])
        z_bot = z_top - fh
        side_low = z_bot + C["box_front_up"]
        screw = side_low + C["runner_fix_dz"]
        cab_z = C["toe_h"]
        k = round((screw - cab_z - C["row_first_z"]) / C["row_pitch"])
        row_z = cab_z + C["row_first_z"] + k * C["row_pitch"]
        sched.append((cab, i + 1, z_bot, z_top, bw, bh, depth, inside_w / MM, side_low, screw, row_z))
        hw.append([cab, tag, "Blum TANDEM 563H %d in pair, BLUMOTION" % depth, 1, "inside drawer width %.1f mm; euro screws into the 32 mm rows, front and rear" % (inside_w / MM)])
        hw.append([cab, tag, "Blum locking devices L+R, %s" % ("narrow T51.0801.20 (95 to 124 mm inside) [verify part no.]" if narrow else "standard T51.1901 (170 mm min inside) [verify part no.]"), 1,
                   "inside width %.1f mm; screwed under the drawer front's lower edge, device as jig (hand pilots)" % (inside_w / MM)])
    return bw

# ---------------------------------------------------------------- fridge column
def fridge_column(C, cab, W, Hcol, D, parts, openings, H_upper, extra):
    """From the ladder to the vented strip: end panels, floor (fingered), divider (tabs), shelf (captured),
    upper back 2 off the wall (captured), top slab (fingered, stops at the back), toe board, vent strip."""
    t, fw, bit, dd = C["ply_t"], C["finger_w"], C["bit_d"], C["dado_depth"]
    ch = C["fr_channel"]
    z_shelf = Hcol - H_upper - t
    top_d = D - ch
    ends = {}
    for nm in ("A", "B"):
        end = Part(cab, "end_panel_" + nm, D, Hcol, t, "ply", 1)
        end.fingers({"bottom": (t, fw, True), "top": (t, fw, True)}, bit)
        end.notch(0, top_d, D, Hcol - t, True)
        end.pocket(0, z_shelf, D, t, dd, "shelf dado 3/8 deep, full depth", mates=True)
        end.pocket(D - ch - t, z_shelf + t, t, Hcol - z_shelf - 2 * t, dd, "upper back dado 3/8 deep, back 2 off the wall", mates=True)
        holes_row(end, C["row_front"], z_shelf + t + 1.5, Hcol - 1.5, C["row_pitch"], C["row_hole_d"], C["row_hole_depth"], "front 32 mm row (upper section), 5 x 13 mm")
        end.note("to the wall; closes the air channel at the side; lower section open-backed, upper back 2 off the wall")
        ends[nm] = end
    for (which, x, zloc, dia, depth, note) in extra.get("holes", []):
        ends[which].hole(x, zloc, dia, depth, note)
    parts += [ends["A"], ends["B"]]
    floor = Part(cab, "floor", D, W, t, "ply"); floor.fingers({"bottom": (t, fw, False), "top": (t, fw, False)}, bit)
    shelf = Part(cab, "shelf", D, W - 2 * t + 2 * dd, t, "ply")
    shelf.pocket(D - ch - t, 0, t, shelf.W, dd, "upper back dado 3/8 deep, on the TOP face", mates=True)
    shelf.note("drawn top face up: the back dado is on top, the slots go through")
    top = Part(cab, "top", top_d, W, t, "ply"); top.fingers({"bottom": (t, fw, False), "top": (t, fw, False)}, bit)
    top.pocket(top_d - t, t, t, W - 2 * t, dd, "upper back dado 3/8 deep", mates=True)
    toe = Part(cab, "toe_board", W, C["toe_h"], t, "ply")
    for (o, ow) in openings:
        floor.thru(D - C["fr_notch_d"], o + C["fr_notch_from"], C["fr_notch_d"], C["fr_notch_w"], "air notch, through [LG 190 x 220 mm]")
        shelf.thru(D - C["fr_top_slot_d"], o - t + dd + ow / 2 - C["fr_top_slot_w"] / 2, C["fr_top_slot_d"], C["fr_top_slot_w"], "exhaust slot, through [LG 400 x 50 mm], in the channel")
        toe.thru(o + ow / 2 - C["fr_toe_grille_w"] / 2, (C["toe_h"] - C["fr_toe_grille_h"]) / 2, C["fr_toe_grille_w"], C["fr_toe_grille_h"], "grille opening, through [LG 404 x 51 mm]; open grille, not a louvre")
    div_y = openings[0][0] + openings[0][1]
    n, tw = 3, C["fr_tab_w"]
    for i in range(n):
        x = (i + 0.5) * D / n - tw / 2
        floor.thru(x, div_y, tw, t, "divider tab slot, through", mates=True)
        shelf.thru(x, div_y - t + dd, tw, t, "divider tab slot, through", mates=True)
    Hdiv = z_shelf - t
    div = Part(cab, "divider", D, Hdiv + 2 * t, t, "ply")
    xs = [((i + 0.5) * D / n - tw / 2, (i + 0.5) * D / n + tw / 2) for i in range(n)]
    def tabbed(ybase, sgn):
        out, x = [], 0.0
        for (a, b) in xs:
            out += [(x, ybase + sgn * t), (a, ybase + sgn * t), (a, ybase), (b, ybase), (b, ybase + sgn * t)]
            x = b
        out.append((D, ybase + sgn * t))
        return out
    bottom = tabbed(0, +1)
    topp = [(x, div.W - y) for (x, y) in tabbed(0, +1)]
    div.poly = dedupe(bottom + list(reversed(topp)))
    div.note("tabs %g x 3/4 into the floor and shelf slots, glued; the slots carry dogbones" % tw)
    for (x, zloc, dia, note) in extra.get("divider_holes", []):
        div.hole(x, zloc + t, dia, None, note)
    parts.append(div)
    uback = Part(cab, "upper_back", W - 2 * t + 2 * dd, H_upper - t + 2 * dd, t, "ply")
    uback.corner_notches(dd)
    parts += [floor, shelf, top, toe, uback]
    strip = Part(cab, "ceiling_vent_strip", W, C["fr_top_vent"], t, "ply")
    for (o, ow) in openings:
        strip.thru(o + ow / 2 - C["fr_vent_slot_w"] / 2, (C["fr_top_vent"] - C["fr_vent_slot_h"]) / 2, C["fr_vent_slot_w"], C["fr_vent_slot_h"], "exhaust opening [choice 420 x 55 mm], open grille")
    parts.append(strip)
    parts.append(Part(cab, "upper_shelf", top_d - t - 0.25, W - 2 * t - 0.125, t, "ply"))

# ---------------------------------------------------------------- ladders
def ladders(C, cabs, parts, K):
    t, dd = C["ply_t"], C["dado_depth"]
    runs = {}
    for c in cabs:
        if c["ladder"]:
            runs.setdefault(c["wall"], []).append(c)
    bay = next((c for c in K["cabinets"] if c[7] == "tall"), None)
    frs = sorted([(a[3], a[4]) for a in K["appliances"] if a[0].startswith("FR")])
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
            joints = sorted({c["pos"] for c in cs if a < c["pos"] < b} | {c["pos"] + c["W"] for c in cs if a < c["pos"] + c["W"] < b})
            xs = [a + t / 2] + joints + [b - t / 2]
            if bay and wall == bay[1] and a <= bay[2] < b:
                xs.append(frs[0][0] + frs[0][1] + t / 2)
            xs = sorted(set(xs))
            filled = []
            for x0, x1 in zip(xs, xs[1:]):
                filled.append(x0)
                in_bay = bay and wall == bay[1] and bay[2] - 0.01 <= x0 and x1 <= bay[2] + bay[3] + 0.01
                if not in_bay:
                    k = int(math.ceil((x1 - x0) / 24)) - 1
                    for i in range(1, k + 1):
                        filled.append(x0 + (x1 - x0) * i / (k + 1))
            filled.append(xs[-1])
            for nm in ("front_rail", "rear_rail"):
                r = Part(tag, nm, L, C["toe_h"], t, "ply")
                for x in filled:
                    r.pocket(x - a - t / 2, 0, t, C["toe_h"], dd, "cross dado 3/8 deep", mates=True)
                r.note("front rail 3 behind the carcass fronts; rear rail at the wall, scribed; shim level; boxes screwed down through their bottoms")
                parts.append(r)
            cl = C["base_d"] - C["toe_setback"] - 2 * t + 2 * dd
            cr = Part(tag, "cross", cl, C["toe_h"], t, "ply", len(filled))
            cr.note("seats 3/8 into each rail, glue + 2 screws per end; positions from the run start: " + ", ".join("%.2f" % (x - a) for x in filled))
            parts.append(cr)

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
    back_in_ov = {o[0]: o[1] for o in C.get("back_in_override", [])}
    sink_drain = next((a for a in K["appliances"] if a[0] == "SINK_DRAIN"), None)
    sink = next((a for a in K["appliances"] if a[0] == "SINK"), None)

    svc, svc_rows = {}, []
    for s in C["services"]:
        sid, cabn, side, x, zabs, dia, note = s
        c = byid[cabn]
        zloc = zabs - c[6]
        svc.setdefault(cabn, []).append((side, x, zloc, dia, note))
        svc_rows.append([sid, cabn, side, "%.3f" % x, "%.3f" % zabs, "%.3f" % zloc, ("rect 3.5 x 2.5" if dia == 0 else "%.2f dia" % dia), note])

    parts, cabs, hw, sched = [], [], [], []
    for c in K["cabinets"]:
        cid, wall, pos, W, H, D, z, kind = c[:8]
        rec = {"id": cid, "wall": wall, "pos": pos, "W": W, "ladder": False}
        extra = {"holes": [], "thru": []}
        if cid in back_in_ov: extra["back_in"] = back_in_ov[cid]
        for (side, x, zloc, dia, note) in svc.get(cid, []):
            if dia == 0:
                extra["thru"].append((side, x - 1.75, zloc - 1.25, 3.5, 2.5, note))
            elif side == "D":
                extra.setdefault("divider_holes", []).append((x, zloc, dia, note))
            else:
                extra["holes"].append((side, x, zloc, dia, None, note))
        if sink_drain and wall == sink_drain[2] and kind == "base":
            drop = sink_drain[5] - K["counter_t"]
            if drop > 0:
                d0, d1 = sink_drain[3] + 1, sink_drain[3] + sink_drain[4] - 1
                lo, hi = max(pos, d0), min(pos + W, d1)
                if hi > lo:
                    x0 = K["base_d"] - sink_drain[8] - sink_drain[6] + 1
                    x1 = K["base_d"] - sink_drain[8] - 1
                    y0, y1 = lo - pos, hi - pos
                    extra["top_relief"] = [(x0, x1, y0, y1)]
                    rel = []
                    if lo - pos < 0.01: rel.append(("A", x0, x1, drop))
                    if pos + W - hi < 0.01: rel.append(("B", x0, x1, drop))
                    extra["side_relief"] = rel
        if cid == "W_OVEN30":
            carcass(C, cid, W, H, D, "oven", parts, extra)
        elif kind == "tall":
            frs = sorted([(a[3] - pos, a[4]) for a in K["appliances"] if a[0].startswith("FR")])
            upper = byid["S_FRIDGE_TOP"][4]
            fridge_column(C, cid, W, H, D, parts, frs, upper, extra); rec["ladder"] = True
        elif cid == "S_FRIDGE_TOP":
            continue
        elif kind == "base":
            variant = "sink" if cid.startswith("S_SB") else "corner" if "CORNER" in cid else "base"
            if variant == "corner": extra["shelves"] = 1
            if cid == "S_B8":
                extra["back_holes"] = [(W / 2 - 0.75, 19.875 - K["toe_h"] - 0.75, 1.25, "cords from the void behind the back into the compartment; receptacles on this back at 19 7/8 and 23 3/8")]
            carcass(C, cid, W, H, D, variant, parts, extra); rec["ladder"] = True
        elif kind == "filler" and "WALLFILL" in cid:
            parts.append(Part(cid, "scribe_strip", H, W, C["ply_t"], "ply"))
        else:
            continue
        if cid in fronts and fronts[cid][1] == "drawers":
            drawer_boxes(C, cid, W, fronts[cid][2], parts, hw, sched)
        cabs.append(rec)
    ladders(C, cabs, parts, K)
    for p in parts: p.add_dogbones(C["bit_d"])
    validate(parts, C)

    with open(os.path.join(out, "cutlist.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cabinet", "part", "qty", "length", "width", "thickness", "material", "features"])
        for p in parts:
            w.writerow([p.cab, p.name, p.qty, "%.4f" % p.L, "%.4f" % p.W, "%.3f" % p.t, p.mat, p.feature_text()])

    rv = C["front_reveal"]
    std_w, std_h = (12, 15, 18, 24, 30, 36), (5, 10, 15, 20, 30)
    with open(os.path.join(out, "fronts.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cabinet", "front", "qty", "nominal_w", "nominal_h", "finished_w", "finished_h", "note"])
        def row(cab, kind, qty, nw, nh, note, fw_=None, fh_=None):
            w.writerow([cab, kind, qty, "%g" % nw, "%g" % nh, "%.4f" % (fw_ if fw_ is not None else nw - rv), "%.4f" % (fh_ if fh_ is not None else nh - rv), note])
        for c in K["cabinets"]:
            cid, W, H = c[0], c[3], c[4]
            if cid in fronts:
                fr = fronts[cid]
                if fr[1] == "doors":
                    n = fr[2]
                    dw = (W - C["corner_blind_w"]) if "CORNER" in cid else W / n
                    std = dw in std_w and H in std_h
                    row(cid, "door", n, dw, H, "standard" if std else "Bofronts custom", dw - rv, H - rv)
                    hw.append([cid, "doors", "IKEA UTRUSTA hinge 110 + UTRUSTA plate (the Bofronts boring) [verify part nos.]", 2 * n, "2 per door; plates on the 37 mm row"])
                else:
                    for i, h in enumerate(fr[2]):
                        std = W in std_w and h in std_h
                        row(cid, "drawer front %d" % (i + 1), 1, W, h, "undrilled, screwed from inside the box; " + ("standard" if std else "Bofronts custom"))
            if c[7] == "filler" and "END" in cid and W > 0:
                w.writerow([cid, "cover panel", 1, "25", "35", "24.7500", "%.4f" % (c[4] + K["toe_h"]), "base cover panel, trim on site; thickness per style (3/4 slab, 7/8 Wave) changes the corridor reveal"])
            if cid == "S_GAP":
                row(cid, "filler strip", 1, W, 30, "front filler closing the corner gap, flush with the fronts; stops at the corner door's edge")
            if "CORNER" in cid:
                w.writerow([cid, "blind panel", 1, "%g" % C["corner_blind_w"], "30", "", "", "plywood, prefinished face, flush with the door; no added Bofronts face"])
        w.writerow(["S_DW", "dishwasher panel", 1, "24", "29.625", "23.8750", "29.6250", "Bofronts custom; Bosch p.15: 3 to 10 kg, max 30 1/2 high, panel top at least 1/4 under the counter (hence 29 5/8, bottom aligned with the neighbours)"])
        for u in ("FR1", "FR2"):
            w.writerow([u, "fridge door panel", 1, "", "", "%.4f" % C["fr_panel_w"], "%.4f" % C["fr_panel_fridge_h"], "Bofronts custom, LG jig, under 10 kg [verify height in the LG install manual]"])
            w.writerow([u, "freezer door panel", 1, "", "", "%.4f" % C["fr_panel_w"], "%.4f" % C["fr_panel_freezer_h"], "Bofronts custom, LG jig, under 10 kg [LG table: 701 mm at 20 mm sides]"])
        bay = next((c for c in K["cabinets"] if c[7] == "tall"), None)
        for p in parts:
            if p.name == "front_rail":
                m = re.match(r"LADDER\d+_(\w+)_([\d.]+)_to_([\d.]+)", p.cab)
                a, b = float(m.group(2)), float(m.group(3))
                L = p.L - (bay[3] if (bay and m.group(1) == bay[1] and a <= bay[2] < b) else 0)
                w.writerow([p.cab, "toe kick facing", 1, "", "", "%.3f" % L, "%g" % K["toe_h"], "Bofronts toe kick or prefinished ply strip, on kick clips to the front rail" + ("; fridge segment is its own grilled toe board" if L != p.L else "")])

    with open(os.path.join(out, "hardware.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["cabinet", "item", "part", "qty", "note"])
        for r in hw: w.writerow(r)
        for p in parts:
            if p.name in ("shelf", "upper_shelf") and "LADDER" not in p.cab:
                w.writerow([p.cab, p.name, "5 mm shelf pins", 4, "in the 32 mm rows"])
        w.writerow(["ALL", "toe kick", "plinth clips (Hafele/Richelieu type), screwed to the facing, clip onto the rail", "2 per 24 in", "removable for the DW and fridge toe boards"])
        w.writerow(["ALL", "carcass", "PVA glue", "", C["glue_note"]])
        w.writerow(["ALL", "fronts", "handles", "per fronts.csv", "your choice"])
        w.writerow(["S_FRIDGE_BAY", "doors", "LG door brackets", 4, "LG hardware, not kitchen hinges"])
        w.writerow(["S_FRIDGE_BAY", "upper", "wall anchorage: #10 x 3 into studs through the upper back, 2 per stud", "", "[choice]"])

    with open(os.path.join(out, "services.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["id", "cabinet", "side (A low-pos, B high-pos, D divider)", "x from the front", "z above finished floor", "z on the part", "size", "purpose"])
        for r in svc_rows: w.writerow(r)
        w.writerow(["RECEPT_DW", "S_B8", "back", "", "19.875", "", "duplex", "DW receptacle on the back, compartment behind drawers 1 and 2 (18 deep)"])
        w.writerow(["RECEPT_FR", "S_B8", "back", "", "23.375", "", "duplex", "fridge receptacle, lower quarter of the fridge opening (5 5/8 + 71/4)"])
        w.writerow(["JBOX_OV", "W_D30", "back", "", "19.875", "", "4x4 box", "oven junction box, 240 V 20 A per the oven manual and nameplate [verify], behind drawer 2 (18 deep)"])
        w.writerow(["RECEPT_CT", "W_D30", "back", "", "19.875", "", "single", "cooktop 120 V, within 24 of the cooktop's right rear cutout corner (pos 88 7/16): place within pos 89 to 95"])
        w.writerow(["GAS_VALVE", "W_D30", "compartment", "", "31.25", "", "1/2 shutoff", "behind drawer 1 (15 deep); gas stub through the wall into the compartment per the cooktop guide, 5 below the counter underside"])
        w.writerow(["GAS_STUB", "wall behind W_D30", "", "", "about 30", "", "1/2 NPT", "wall stub lands in W_D30's compartment, not behind the oven"])
        w.writerow(["SINK_SUPPLY", "S_SB36", "back", "", "", "", "", "hot/cold and drain penetrations in the sink back: from the measured rough-ins, not modelled"])

    ct = [a for a in K["appliances"] if a[0] == "CT"][0]
    with open(os.path.join(out, "countertop.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["wall", "item", "origin of 'along the wall'", "along the wall, start", "size along the wall", "from the counter front edge", "depth", "note"])
        w.writerow(["west (oven wall)", "cooktop cutout", "from the south (window) wall", "%.4f" % ct[3], "%.4f" % ct[4], "2.7500", "%.4f" % ct[6], "KitchenAid KCGG530PBL, 28 7/8 x 19 13/16, corner radii per the cooktop template"])
        w.writerow(["south (window wall)", "sink", "from the EAST wall", "%.4f" % sink[3], "47.2500", "%.4f" % sink[8], "19.6875", "integral welded sink, bowls centred at 100 along the wall, centred front to back; NOT a cutout dimension, the fabricator's drawing governs"])
        w.writerow(["south (window wall)", "upstand", "", "", "", "", "", "none, under 1 1/2, or the full 6 to the sill: the faucet escutcheons occupy 37 5/8 to 40 3/8"])
        w.writerow(["both", "material", "", "", "", "", "", "stainless over plywood; counter_t and the apron from the fabricator; dishwasher and corner gap need support strips under the top"])

    by_cab = {}
    for p in parts: by_cab.setdefault(p.cab, []).append(p)
    for cab, ps in by_cab.items():
        d = DXF(); x = 0
        for p in ps:
            for q in range(p.qty):
                d.poly([(x + a, b) for (a, b) in p.poly], "OUTLINE")
                for (cx, cy, layer) in p.dogbones:
                    d.circle(x + cx, cy, C["bit_d"], layer)
                d.text(x + 0.3, p.W + 0.5, "%s %s %.3f x %.3f x %.3f  qty %d" % (cab, p.name, p.L, p.W, p.t, p.qty))
                for ftr in p.feats:
                    kind, fx, fy, fw_, fh, dep, note, mates = ftr
                    d.rect(x + fx, fy, fw_, fh, "THRU" if kind == "THRU" else "POCKET_" + mils(dep))
                    d.text(x + fx, fy + fh + 0.05, note, h=0.2)
                for (hx, hy, dia, dep, face, note) in p.holes:
                    d.circle(x + hx, hy, dia, "HOLE_%s_%s" % (mils(dia), "THRU" if dep is None else mils(dep)) + ("_OTHERFACE" if face == "other" else ""))
                for i, nt in enumerate(p.notes):
                    d.text(x + 0.3, -0.5 - 0.3 * i, nt, h=0.2)
                x += p.L + 2
        d.save(os.path.join(out, cab + ".dxf"))

    with open(os.path.join(out, "ops.txt"), "w") as f:
        f.write("""Layer legend. Every part is drawn with its feature face up (sides: inside face; slabs: inside face; drawer
parts: inside face; drawer bottoms and the fridge shelf: top face; stretchers, rails, strips: the face with features).
  OUTLINE              closed polyline, through cut, tool outside. Finger joints, notches and reliefs are in the outline.
  DOGBONE_THRU         1/4 relief circles at inside corners of finger notches and through slots that a square part enters.
  DOGBONE_<mils>       same, for pockets of that depth (dado ends that receive a square panel end).
  THRU                 through pocket, tool inside the line (vent slots, divider slots, hose opening).
  POCKET_375           0.375 deep: carcass dados (back, floor, shelf, stretchers, rails, ledgers, ladder crosses).
  POCKET_188           0.1875 deep: drawer bottom grooves (1/4 wide), and the cooktop clamp relief on the oven sides.
  POCKET_250           0.250 deep: rabbets on the drawer bottoms' TOP face (1/4 tongue), drawn top face up.
  HOLE_197_512         5 mm x 13 mm deep: the 32 mm rows. Needs a 5 mm drill or a 2 to 4 mm cutter, not the 1/4 bit.
  HOLE_250_THRU        1/4 through: Bofronts front screws in the drawer box fronts.
  HOLE_236_394_OTHERFACE  6 mm x 10 mm deep from the REAR face of the drawer backs: flip the part. The only flipped operation.
  HOLE_1250_THRU       1 1/4 through: cord and gas passages (services.csv).
  NOTE                 text, not geometry.
Handed parts. Carcass sides and drawer sides are cut as identical parts from one drawing (inside face up, front edge
at x = 0, bottom at y = 0). The left/right pair is made by turning one over about its vertical axis: the front edge
stays the front, the bottom stays the bottom, the inside face now faces the other way. Where the two sides differ
(service holes, drainboard relief) they are separate parts: side_A is the low-pos end (east on the window wall,
south on the oven wall), side_B the high-pos end.
Hand operations: pilots for the Blum locking devices under the drawer fronts' lower edge (device as jig); UTRUSTA
plate screws into the rows; kick clips; wall anchors. Nothing else.
Fit: finger widths, tab slots and dados are nominal. Cut one coupon per stock sheet and set the CAM's allowance
from it before cutting cabinets. Glue: PVA on bare plywood; the prefinished faces are not glue surfaces.
""")

    area = lambda mat, th: sum(p.L * p.W * p.qty for p in parts if p.mat == mat and abs(p.t - th) < 0.01)
    sheet = C["sheet_w"] * C["sheet_l"]
    verify = [("construction.scad", l.strip()) for l in open(sys.argv[2]) if "[verify]" in l and not l.strip().startswith("//")]
    verify += [("kitchen_data.scad", l.strip()[:150]) for l in open(sys.argv[1]) if "[verify]" in l or "GUESS" in l]
    with open(os.path.join(out, "summary.txt"), "w") as f:
        f.write("parts: %d lines, %d pieces\n" % (len(parts), sum(p.qty for p in parts)))
        f.write("3/4 ply: %.1f sq ft, about %d sheets at 80%% yield (not a nesting result)\n" % (area("ply", C["ply_t"]) / 144, math.ceil(area("ply", C["ply_t"]) / sheet / 0.8)))
        f.write("5/8 Baltic birch: %.1f sq ft, about %d sheets\n" % (area("bb", C["drawer_t"]) / 144, math.ceil(area("bb", C["drawer_t"]) / sheet / 0.8)))
        f.write("1/2 Baltic birch (bottoms): %.1f sq ft, about %d sheets\n" % (area("bb", C["drawer_bot_t"]) / 144, math.ceil(area("bb", C["drawer_bot_t"]) / sheet / 0.8)))
        f.write("\nDrawer and runner schedule (z above the finished floor):\n")
        for (cab, i, zb, zt, bw, bh, depth, iw, side_low, screw, row_z) in sched:
            f.write("  %-8s front %d (from the top): front %.3f to %.3f; box %.4f x %g x %g deep, inside %.1f mm; side lower edge %.3f; runner screw %.3f -> row hole at %.3f\n" % (cab, i, zb, zt, bw, bh, depth, iw, side_low, screw, row_z))
        f.write("  runner elevations derive from box_front_up and runner_fix_dz in construction.scad, both [verify] against the 563H drawing\n")
        f.write("\nvalidation: outlines simple and counterclockwise, no backtracking, holes in material, bores clear of opposite pockets, parts fit the sheet: PASS\n")
        f.write("layout checks (draw.py) are about positions; this file is about parts. Neither is a physical test.\n")
        f.write("fridge column: one unit on the ladder, to the LG cabinet figure; air: toe grille > ladder cavity > floor notch > channel > shelf slot > behind the upper back > over the top > vent strip.\n")
        f.write("oven cabinet: open back, floor at %.3f on a toe board and a rear ledger, no top (front rail + rear stretcher), clamp relief on the sides.\n" % C["ov_floor"])
        if sink_drain:
            drop = sink_drain[5] - K["counter_t"]
            f.write("drainboard: drop %.3f below the counter, slab %.3f: %s\n" % (sink_drain[5], K["counter_t"],
                    "relief in the S_B24 top and the two side panels under it [verify the drop and footprint; moot with the fabricator's welded bowls]" if drop > 0 else "no relief needed"))
        f.write("\n[verify] items, both data files:\n")
        for src, v in verify: f.write("  %s: %s\n" % (src, v))
    print(open(os.path.join(out, "summary.txt")).read())

if __name__ == "__main__":
    main()
