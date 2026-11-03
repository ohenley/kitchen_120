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
shade_modules   = true;   // each cabinet row gets its own brightness step so neighbours read apart
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

// brightness step per row index, cycling so adjacent rows always differ; alpha untouched
function shade(i) = shade_modules ? [1.00, 0.72, 0.88, 0.58][i % 4] : 1;
function tint(c, f) = len(c) == 4 ? [c[0] * f, c[1] * f, c[2] * f, c[3]] : c * f;

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
  for (i = [0 : len(cabinets) - 1]) {
    c = cabinets[i];
    id = c[0]; wall = c[1]; pos = c[2]; w = c[3]; h = c[4]; d = c[5]; z = c[6]; kind = c[7];
    off = (wall == "west" && kind != "wall") ? west_offset : 0;
    color(tint(kind_color(kind), shade(i)))
    on_wall(wall, pos, w, d, z, off) {
      box(w, d, h);
      label(id, w);
    }
    // Countertop over counter-height items, running back to the wall over any offset.
    if ((kind == "base" || kind == "zone" || kind == "filler") && z + h <= counter_h + 0.01) {
      cd = off + d + (wall == "west" ? west_counter_oh : counter_oh);
      color([0.95, 0.95, 0.95])
      on_wall(wall, pos, w, cd, z + h, 0) box(w, cd, counter_t);
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
  // fridge doors open 90 deg, handles at the centre: FR1 hinged on the east (wall side), FR2 hinged on the
  // west. Each sweep: the 22 7/16 door in front of its own opening plus 3 past the hinge side
  // (LG: 24 4/5 wide open), 45 3/10 deep from the back of the bay.
  fr1 = [for (a = appliances) if (a[0] == "FR1") a][0];
  fr2 = [for (a = appliances) if (a[0] == "FR2") a][0];
  color([0.9, 0.2, 0.2, 0.15]) {
    on_wall("south", fr1[3] - 3,          fr1[4] + 3, 45.3, 0, fr1[8]) cube([fr1[4] + 3, 45.3, 1]);   // sweep toward the east wall
    on_wall("south", fr2[3],              fr2[4] + 3, 45.3, 0, fr2[8]) cube([fr2[4] + 3, 45.3, 1]);   // sweep over S_B8
  }
}
}

// ---- scene ------------------------------------------------------------
if (show_walls)      walls();
if (show_cabinets)   cabinets_all();
if (show_appliances) appliances_all();
