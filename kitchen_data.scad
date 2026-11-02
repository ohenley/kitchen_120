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
ceiling_h   = 94;             // [label] measured, planner had 96
south_len   = 170.5;          // [label] 82 + 36 + 52 1/2
west_len    = 288;            // [label] 120 + 36 + 132
counter_h   = 36;             // [choice] planner shows 4 1/2 + 30 + 1 1/8 = 35 5/8. Both satisfy the appliances, see notes.
counter_t   = 1.125;          // [label]
counter_oh  = 1.5;            // [choice] countertop overhang past the box front, window wall (counter 25 1/2)
west_counter_oh = 1.5;        // [choice] oven wall counter 25 1/2, same as the window wall. Cooktop minimum is 25 3/8. Its 2 7/8 rear rule is to a COMBUSTIBLE surface; tile over drywall is not one.
toe_h       = 4.875;          // [choice] ladder base height. 4 7/8 + 30 box + 1 1/8 slab = 36 counter. The planner had 4 1/2 legs, which gives 35 5/8.
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
// Countertop receptacles already in the oven wall. With the standard 12 beside the corner
// the oven cabinet centre is 74; the receptacles land 13 and 11 1/2 from the cooktop edges.
// Oven 240 V on a separate 20 A circuit [mfr: KitchenAid manual, models 4.8 kW and below] and cooktop 120 V are in the adjacent cabinets, not listed.
// z = 0 until the box height above the counter is measured. Nothing renders it yet.
electrical = [
  ["OUT_W1", "west",  46.0, 0, "[label] countertop receptacle, 13 south of the cooktop edge (59), toward the window wall"],
  ["OUT_W2", "west", 100.5, 0, "[label] countertop receptacle, 11 1/2 north of the cooktop edge (89), toward the corridor"],
];

// ---- cabinets: [id, wall, pos, width, height, depth, z_bottom, kind, note] -
// kind: base | wall | tall | filler | zone. "zone" = an opening an appliance fills.
// Fridge bay [mfr, LG spec sheet p.2 cabinet figure]: 3 wall filler | end panel 3/4 | FR1 opening 570 mm = 22 7/16 | divider 3/4 | FR2 opening 22 7/16 | end panel 3/4 = ends at 50 1/8.
// Clear height 1802 mm = 70 15/16 (71 used) above a raised floor; 50 mm channel behind the unit; floor notch, toe grille and top slot sizes in construction.scad.
// Bay depth 25 1/4 = 2 channel + 22 1/2 body + 3/4 panel, panel face flush with the bay front, 1/2 proud of the drawer fronts.
cabinets = [
  // window wall (south in this file), east to west
  ["S_WALLFILL",   "south",   0.0,    3.0,  ceiling_h, 24, 0,      "filler", "[choice] 3 off the east wall, full height, scribed"],
  ["S_FRIDGE_BAY", "south",   3.0,   47.125, 77.375, 25.25, 0,     "tall",   "[mfr] box: 2 end panels, floor slab on the ladder, 1 divider, shelf. Openings 22 7/16 x 71, floor at 5 5/8. Toe grilles, floor notches, shelf slots per LG, see construction.scad"],
  ["S_FRIDGE_TOP", "south",   3.0,   47.125, ceiling_h - 77.375 - 1.5, 23.25, 77.375, "wall", "[choice] cabinet over the fridges, 23 1/4 deep: the 2 channel continues behind it to a 1 1/2 vented strip at the ceiling"],
  ["S_B8",         "south",  50.125,  7.875, 30, 24, toe_h,        "base",   "[choice] custom pullout, what is left between the bay and the DW. DW outlet here"],
  ["S_DW",         "south",  58.0,   24.0,  30, 24, toe_h,         "zone",   "dishwasher opening, see DW"],
  ["S_SB36",       "south",  82.0,   36.0,  30, 24, toe_h,         "base",   "[label] 36 sink base, centred on WIN_S2 at 100, bowls 85 to 115 inside. No top drawer"],
  ["S_B24",        "south", 118.0,   24.0,  30, 24, toe_h,         "base",   "[label] 24 drawer base. Drainboard rides over 118 to 132 1/4"],
  ["S_GAP",        "south", 142.0,    4.5,  30, 24, toe_h,         "zone",   "[label] pull-away gap of the blind corner, under the counter. Planner: 2 3/4 + frame"],
  // oven wall (west), from the window wall
  ["W_CORNER47",   "west",    0.0,   47.0,  30, 24, toe_h,         "base",   "[choice] custom-cut blind corner box, 47 wide, built like the others. NOT the IKEA article (505.967.57 is 50 wide and would push the run past 120). Door section 24 (Bofronts standard 24 x 30), fixed blind panel 23 toward the window wall. Its side is what the window wall sees at 146 1/2 to 170 1/2"],
  ["W_B12",        "west",   47.0,   12.0,  30, 24, toe_h,         "base",   "[label] standard 12. Oven centre lands at 74, receptacles 13 and 11 1/2 from the cooktop edges"],
  ["W_OVEN30",     "west",   59.0,   30.0,  30, 24, toe_h,         "zone",   "[label] oven cabinet, centre 74. Sides notched 3/16 in the top 3 1/4 for the cooktop cutout. Floor at 4 5/8 from the finished floor, sides run to the floor, see OV"],
  ["W_D30",        "west",   89.0,   30.0,  30, 24, toe_h,         "base",   "[choice] 3 drawers, finished end toward the corridor"],
  ["W_END",        "west",  119.0,    0.75, 30, 24, toe_h,         "filler", "[choice] applied finished end panel on W_D30, Bofronts matching. Set width 0 if the prefinished ply side is the finish"],
  ["W_FILL2",      "west",  119.75,   0.25, 30, 24, toe_h,         "filler", "[choice] reveal to the opening at 120"],
  ["W_HOOD30",     "west",   59.0,   30.0,  18, 20, 66,            "zone",   "[choice] 30 hood centred on the oven cabinet at 74. Height/depth placeholders"],
];

// ---- appliances: [id, model, wall, pos, w, h, d, z_bottom, off, note] ---
// Each box is the OPENING the cabinet must provide, placed like a cabinet.
// "off" is the distance from the wall to the back of the opening.
cutout_rear = west_counter_oh + base_d - 2.75 - 19.8125;   // cooktop cutout rear edge from the cabinet back
appliances = [
  ["DW",  "Bosch SHV53D73UC",      "south",  58.0,    24.0,    34.0625, 24.0,    0,     0,
     "[mfr, install manual p.9] opening 23 5/8 to 24 1/4 W, 34 1/16 H min, 21 5/8 D min. 120 V outlet in an ADJACENT cabinet (S_B8). Drain hose max 92 with a high loop at 33 min above the floor (p.9). Panel: Bofronts dishwasher panel for SEKTION, Bosch accepts 7 to 18 lb from the factory."],
  ["FR1", "LG LSBNC1021P",         "south",   3.75,   22.4375, 71.0,    22.5,    5.625, 2.0,
     "[mfr] body 554 W x 1775 H x 565 D (mm), door panels 592 wide for a 600 cabinet; freezer panel 696/699/701 mm for 15/18/20 mm sides, fridge panel height from the full install manual [verify]. Hinge right from factory, reversible. Open 90: 24 4/5 wide, 45 3/10 deep. Two units side by side: panel width = opening + divider - gap = 23 1/16, Bofronts custom"],
  ["FR2", "LG LSBNC1021P",         "south",  26.9375, 22.4375, 71.0,    22.5,    5.625, 2.0,
     "[mfr] same. [choice] handles at the centre: FR1 hinged on the east (factory right, door needs 2 1/4 past its opening toward the east wall, covered by the 3/4 panel + 3 filler), FR2 reversed to hinge on the west, its door swings over S_B8. Door panels: Bofronts custom, LG panel spec, under LG's weight limit"],
  ["SINK",       "Segong SG-12050D2", "south",  85.0,  30.0, 8.5, 19.6875, counter_h - 8.5, base_d + counter_oh - 2 - 19.6875,
     "[mfr] 1200 x 500 mm top mount (rim 85 to 132 1/4), 0.8 mm 304, sound pad underneath. This box is the 30 wide bowl region only; the drainboard is SINK_DRAIN. [choice] bowl region centred at 100 = faucet on WIN_S2, assumes the holes are centred behind the bowls. Bowl depth 8 1/2 is a GUESS, measure. Front rim 2 behind the counter front."],
  ["SINK_DRAIN", "drainboard of SINK", "south", 115.0, 17.25, 1.5, 19.6875, counter_h - 1.5, base_d + counter_oh - 2 - 19.6875,
     "[choice] drainboard depression below the rim: 1 1/2 is a GUESS, measure. If it is deeper than the slab (1 1/8) the top drawer of S_B24 loses that much"],
  ["FAUCET", "Kingston Brass KS413", "south", 94.625, 10.75, 9.25, 10.3125, 37.625, -0.5,
     "[mfr] wall mount, 8 centres, union axis 39 1/2 above the SUBFLOOR (as roughed in), about 39 above the finished floor. Centred on WIN_S2 at 100. Body 10 3/4 wide incl. 2 3/4 escutcheons, 7 7/8 above axis to spout top, tip 10 5/16 from the tile face. off -0.5: the tile face above the counter sits about 1/2 in front of the cabinet-level wall. Stubs to be cut after tile (3/8 drywall + thinset + 1/4 to 1/2 tile)."],
  ["CT",  "KitchenAid KCGG530PBL", "west",   59.5625, 28.875,  3.25,    19.8125, counter_h - 3.25, west_offset + cutout_rear,
     "[mfr] countertop cutout 28 7/8 W x 19 13/16 D, front edge 2 3/4 behind the counter front. Burner box 28 1/4 x 19 1/4 x 3 1/4 (4 1/4 at the gas inlet, right rear). Counter >= 25 3/8 deep. 120 V outlet within 24 of the right rear corner. 34 to an uncovered cabinet above, 18 to upper cabinets within 12 3/4 either side."],
  ["OV",  "KitchenAid KOES730SBE", "west",   59.75,  28.5,    27.75,   24.0,    counter_h - 31.375, west_offset,
     "[mfr] under-cooktop install: cutout 28 1/2 W min x 27 3/4 H min x 24 D, bottom of cutout 31 3/8 below the countertop surface and at most 4 5/8 above the floor. 240 V, separate 20 A circuit (manual p.12, models 4.8 kW and below), junction box in an ADJACENT cabinet. Centre the cooktop cutout over the oven cutout."],
];
