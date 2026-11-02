// kitchen_data.scad  -- single source of truth. Edit here only.
// Units: inches. Origin: inside SW corner of the kitchen (the L corner), floor level.
//   X runs east along the south wall, Y runs north along the west wall, Z is up.
//   Right-handed, so the OpenSCAD top view is a plan with north up.
// "pos" is the distance from the corner along the wall the item sits on
// (south wall: from the east wall; west wall: from the south wall).
// Tags on each line:
//   [label]   a number printed by the IKEA planner
//   [px]      read from planner pixels, +/- 1/4"
//   [mfr]     manufacturer install document (the four PDFs)
//   [choice]  a design decision taken here, to be confirmed

// ---- room ------------------------------------------------------------
ceiling_h   = 96;             // [label]
south_len   = 170.5;          // [label] 82 + 36 + 52 1/2
west_len    = 288;            // [label] 120 + 36 + 132
counter_h   = 36;             // [choice] planner shows 4 1/2 + 30 + 1 1/8 = 35 5/8. Both satisfy the appliances, see notes.
counter_t   = 1.125;          // [label]
counter_oh  = 1.5;            // [choice] countertop overhang past the box front
toe_h       = 4.5;            // [label]
base_d      = 24;
wall_d      = 15;
west_offset = 0;              // [choice] west base run sits against the wall, 24 deep, counter 25 1/2 like the south run.
                              //   The planner label showed 2 7/8 off the wall (28 3/8 counter); rejected, not wanted.

// ---- openings: [id, wall, pos, width, sill_z, head_z] ------------------
// No window on the west wall. The 51 1/4 x 16 white box at the ceiling over the oven in the
// planner elevation is not a window (it was read as one in v1); unidentified, left out.
// south wall, east to west: 57 1/2 | 24 | 6 1/2 | 24 | 6 | 24 | 28 1/2  [label]
// sill 42, head 78 [label]. Faucet centre = 100 = centre of WIN_S2 = centre of S_SB36.
openings = [
  ["WIN_S1", "south",  57.5,  24,    42, 78],
  ["WIN_S2", "south",  88.0,  24,    42, 78],
  ["WIN_S3", "south", 118.0,  24,    42, 78],
  ["CORR_W", "west",  120.0,  36,     0, 80],   // [label] 120 | 36 | 132. Corridor opening, no door, no casing: cabinets may run to 120
];

// ---- electrical: [id, wall, pos_centre, z, note] -------------------------
// Countertop receptacles already in the oven wall. The cooktop centre 73 1/4
// comes from them: 12 1/4 beyond each edge of the 30 cooktop.
// Oven 240 V 30 A and cooktop 120 V are in the adjacent cabinets, not listed.
// z = 0 until the box height above the counter is measured. Nothing renders it yet.
electrical = [
  ["OUT_W1", "west",  46.0, 0, "[label] countertop receptacle, 12 1/4 south of the cooktop edge (58 1/4), toward the window wall"],
  ["OUT_W2", "west", 100.5, 0, "[label] countertop receptacle, 12 1/4 north of the cooktop edge (88 1/4), toward the corridor"],
];

// ---- cabinets: [id, wall, pos, width, height, depth, z_bottom, kind, note] -
// kind: base | wall | tall | filler | zone. "zone" = an opening an appliance fills.
// Fridge bay: 3 wall filler | end panel 3/4 | FR1 opening 22 3/8 | divider 3/4 | FR2 opening 22 3/8 | end panel 3/4 = ends at 50 [label].
// Opening 22 3/8 = 21 4/5 body + 0.2875 per side (mfr asks 3/10 per side, short by 1/64, fine). Opening height 71 = 70 case + 1 top [mfr].
cabinets = [
  // window wall (south in this file), east to west
  ["S_WALLFILL",   "south",   0.0,    3.0,  ceiling_h, 24, 0,      "filler", "[choice] 3 off the east wall, full height, scribed"],
  ["S_FRIDGE_BAY", "south",   3.0,   47.0,  71.75, 24, 0,          "tall",   "[label] bay ends at 50. 2 openings 22 3/8 x 71 x 24, 3/4 panels, 3/4 shelf on top"],
  ["S_FRIDGE_TOP", "south",   3.0,   47.0,  ceiling_h - 71.75, 24, 71.75, "wall", "[choice] cabinet over the fridges, 24 deep"],
  ["S_B8",         "south",  50.0,    8.0,  30, 24, toe_h,         "base",   "[choice] custom pullout, what is left between the bay and the DW. DW outlet here"],
  ["S_DW",         "south",  58.0,   24.0,  30, 24, toe_h,         "zone",   "dishwasher opening, see DW"],
  ["S_SB36",       "south",  82.0,   36.0,  30, 24, toe_h,         "base",   "[label] 36 sink base, centred on WIN_S2 at 100, bowls 85 to 115 inside. No top drawer"],
  ["S_B24",        "south", 118.0,   24.0,  30, 24, toe_h,         "base",   "[label] 24 drawer base. Drainboard rides over 118 to 132 1/4"],
  ["S_GAP",        "south", 142.0,    4.5,  30, 24, toe_h,         "zone",   "[label] pull-away gap of the blind corner, under the counter. Planner: 2 3/4 + frame"],
  // oven wall (west), from the window wall
  ["W_CORNER47",   "west",    0.0,   47.0,  30, 24, toe_h,         "base",   "[label] SECBBP1D blind corner base, system width 50. Blind panel 0 to 23 5/8 toward the window wall, door 24 to 47. Its side is what the window wall sees at 146 1/2 to 170 1/2"],
  ["W_B11",        "west",   47.0,   11.25, 30, 24, toe_h,         "base",   "[choice] custom 11 1/4, lands the oven centre at 73 1/4. Planner shows 10 1/4 + 1 3/4 here"],
  ["W_OVEN30",     "west",   58.25,  30.0,  30, 24, toe_h,         "zone",   "[label] oven cabinet, centre 73 1/4 between the two countertop receptacles. Sides notched 3/16 in the top 3 1/4 for the cooktop cutout. Floor at 4 5/8 from the finished floor, see OV"],
  ["W_D30",        "west",   88.25,  30.0,  30, 24, toe_h,         "base",   "[choice] 3 drawers, finished end toward the corridor"],
  ["W_FILL2",      "west",  118.25,   1.75, 30, 24, toe_h,         "filler", "[choice] reveal to the opening at 120"],
  ["W_HOOD30",     "west",   58.25,  30.0,  18, 20, 66,            "zone",   "[choice] 30 hood centred on the oven cabinet at 73 1/4. Height/depth placeholders"],
];

// ---- appliances: [id, model, wall, pos, w, h, d, z_bottom, off, note] ---
// Each box is the OPENING the cabinet must provide, placed like a cabinet.
// "off" is the distance from the wall to the back of the opening.
cutout_rear = counter_oh + base_d - 2.75 - 19.8125;   // 2 15/16, cooktop cutout rear edge from the cabinet back
appliances = [
  ["DW",  "Bosch SHV53D73UC",      "south",  58.0,    24.0,    34.0625, 24.0,    0,     0,
     "[mfr] opening 23 5/8 to 24 1/4 W, 34 1/16 H min, 21 5/8 D min. Needs 120 V outlet in an ADJACENT cabinet, drain <= 92 to the sink. Custom panel."],
  ["FR1", "LG LSBNC1021P",         "south",   3.75,   22.375,  71.0,    22.5,    0,     0.75,
     "[mfr] body 21 4/5 W x 70 H (case) x 22 1/2 D no handle, 20 3/5 D without door. Clearance 3/10 sides, 1 top. Hinge right from factory, reversible. Open 90: 24 4/5 wide, 45 3/10 deep"],
  ["FR2", "LG LSBNC1021P",         "south",  26.875,  22.375,  71.0,    22.5,    0,     0.75,
     "[mfr] same. [choice] both hinged RIGHT. With the 3 wall filler FR1 could now be hinged left (needs 2 1/4 past the opening edge)"],
  ["SINK",       "Segong SG-12050D2", "south",  85.0,  30.0, 8.5, 19.6875, counter_h - 8.5, base_d + counter_oh - 2 - 19.6875,
     "[mfr] 1200 x 500 mm top mount (rim 85 to 132 1/4), 0.8 mm 304, sound pad underneath. This box is the 30 wide bowl region only; the drainboard is SINK_DRAIN. [choice] bowl region centred at 100 = faucet on WIN_S2, assumes the holes are centred behind the bowls. Bowl depth 8 1/2 is a GUESS, measure. Front rim 2 behind the counter front."],
  ["SINK_DRAIN", "drainboard of SINK", "south", 115.0, 17.25, 1.5, 19.6875, counter_h - 1.5, base_d + counter_oh - 2 - 19.6875,
     "[choice] drainboard depression below the rim: 1 1/2 is a GUESS, measure. If it is deeper than the slab (1 1/8) the top drawer of S_B24 loses that much"],
  ["FAUCET", "Kingston Brass KS413", "south", 94.625, 10.75, 9.25, 10.3125, 37.625, -0.5,
     "[mfr] wall mount, 8 centres, union axis 39 1/2 above the SUBFLOOR (as roughed in), about 39 above the finished floor. Centred on WIN_S2 at 100. Body 10 3/4 wide incl. 2 3/4 escutcheons, 7 7/8 above axis to spout top, tip 10 5/16 from the tile face. off -0.5: the tile face above the counter sits about 1/2 in front of the cabinet-level wall. Stubs to be cut after tile (3/8 drywall + thinset + 1/4 to 1/2 tile)."],
  ["CT",  "KitchenAid KCGG530PBL", "west",   58.8125, 28.875,  3.25,    19.8125, counter_h - 3.25, west_offset + cutout_rear,
     "[mfr] countertop cutout 28 7/8 W x 19 13/16 D, front edge 2 3/4 behind the counter front. Burner box 28 1/4 x 19 1/4 x 3 1/4 (4 1/4 at the gas inlet, right rear). Counter >= 25 3/8 deep. 120 V outlet within 24 of the right rear corner. 34 to an uncovered cabinet above, 18 to upper cabinets within 12 3/4 either side."],
  ["OV",  "KitchenAid KOES730SBE", "west",   59.0,    28.5,    27.75,   24.0,    counter_h - 31.375, west_offset,
     "[mfr] under-cooktop install: cutout 28 1/2 W min x 27 3/4 H min x 24 D, bottom of cutout 31 3/8 below the countertop surface and at most 4 5/8 above the floor. 240 V 40 A junction box in an ADJACENT cabinet. Centre the cooktop cutout over the oven cutout."],
];
