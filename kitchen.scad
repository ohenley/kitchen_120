// kitchen.scad -- renders kitchen_data.scad. Do not put numbers here.
// F5 to preview. Views: set `show_*` flags below.
// Frame: X east, Y north, Z up. Origin = inside SW corner (the L corner).
// Window wall = south wall along y = 0. Oven wall = west wall along x = 0.
include <kitchen_data.scad>

show_walls      = true;
show_cabinets   = true;
show_appliances = true;
show_openings   = true;
show_labels     = true;
wall_t = 4;   // drawn wall thickness, cosmetic

// ---- helpers ----------------------------------------------------------
// Place a box of size [w, d, h] with its back along a wall. Children are drawn
// with x along the wall, y going into the room, back face at y = 0.
// south: pos from the east wall, x = south_len - pos - w .. south_len - pos, y = off .. off + d
// west:  pos from the south wall, y = pos .. pos + w,                       x = off .. off + d
module on_wall(wall, pos, w, d, z, off = 0) {
  if (wall == "south")
    translate([south_len - pos - w, off, z]) children();
  else if (wall == "west")
    translate([off, pos + w, z]) rotate([0, 0, -90]) children();
}

module box(w, d, h) { cube([w, d, h]); }

// label sits just behind the back face, readable from outside the wall (walls off)
module label(txt, w) {
  if (show_labels)
    translate([w / 2, -0.2, 2]) rotate([90, 0, 0])
      linear_extrude(0.2) text(txt, size = min(2.5, w / 4), halign = "center");
}

function kind_color(k) =
  k == "base"   ? [0.80, 0.65, 0.45] :
  k == "wall"   ? [0.85, 0.72, 0.50] :
  k == "tall"   ? [0.75, 0.60, 0.40] :
  k == "filler" ? [0.50, 0.50, 0.50] :
                  [0.90, 0.90, 0.90, 0.35];   // zone: translucent

// ---- walls and openings ---------------------------------------------
module walls() {
  color([0.92, 0.92, 0.92])
  difference() {
    union() {
      translate([-wall_t, -wall_t, 0]) cube([south_len + 2 * wall_t, wall_t, ceiling_h]);  // south
      translate([-wall_t, -wall_t, 0]) cube([wall_t, west_len + 2 * wall_t, ceiling_h]);   // west
    }
    if (show_openings)
      for (o = openings) {
        wall = o[1]; pos = o[2]; w = o[3]; sill = o[4]; head = o[5];
        if (wall == "south")
          translate([south_len - pos - w, -wall_t - 1, sill]) cube([w, wall_t + 2, head - sill]);
        else
          translate([-wall_t - 1, pos, sill]) cube([wall_t + 2, w, head - sill]);
      }
  }
  // floor
  color([0.95, 0.90, 0.80]) translate([0, 0, -1]) cube([south_len, west_len, 1]);
}

// ---- cabinets ---------------------------------------------------------
module cabinets_all() {
  for (c = cabinets) {
    id = c[0]; wall = c[1]; pos = c[2]; w = c[3]; h = c[4]; d = c[5]; z = c[6]; kind = c[7];
    off = (wall == "west" && kind != "wall") ? west_offset : 0;
    color(kind_color(kind))
    on_wall(wall, pos, w, d, z, off) {
      box(w, d, h);
      label(id, w);
    }
    // Countertop over counter-height items. It runs back to the wall over any offset,
    // and the piece in the corner runs out to the counter front of the perpendicular run.
    if ((kind == "base" || kind == "zone" || kind == "filler") && z + h <= counter_h + 0.01) {
      at_corner = (wall == "south" && abs(pos + w - south_len) < 0.01);
      cw   = at_corner ? max(w, west_offset + base_d + counter_oh) : w;
      cpos = at_corner ? south_len - cw : pos;
      cd   = off + d + counter_oh;
      color([0.95, 0.95, 0.95])
      on_wall(wall, cpos, cw, cd, z + h, 0) box(cw, cd, counter_t);
    }
  }
}

// ---- appliances: cutout volumes, translucent so collisions show -------
module appliances_all() {
  for (a = appliances) {
    id = a[0]; wall = a[2]; pos = a[3]; w = a[4]; h = a[5]; d = a[6]; z = a[7]; off = a[8];
    color([0.20, 0.45, 0.90, 0.45])
    on_wall(wall, pos, w, d, z, off) {
      box(w, d, h);
      label(id, w);
    }
  }
  // fridge doors open 90 deg, both hinged right: footprint 24 4/5 along the wall, 45 3/10 deep,
  // anchored on the opening edge toward the oven corner (west), overhanging 2 2/5 toward the east wall.
  color([0.9, 0.2, 0.2, 0.15]) {
    on_wall("south",  3.75 + 22.375 - 24.8, 24.8, 45.3, 0, 0.75) cube([24.8, 45.3, 1]);
    on_wall("south", 26.875 + 22.375 - 24.8, 24.8, 45.3, 0, 0.75) cube([24.8, 45.3, 1]);
  }
}

// ---- scene ------------------------------------------------------------
if (show_walls)      walls();
if (show_cabinets)   cabinets_all();
if (show_appliances) appliances_all();
