// construction.scad -- how every box is built. Data only, same style as kitchen_data.scad.
// Units: inches. cutlist.py reads this file and kitchen_data.scad.
// Tags: [choice] decision taken here, [blum] from Blum's Tandem chart, [verify] measure
// before cutting: a number taken from the web or from memory, not from a document in hand.

// ---- stock ------------------------------------------------------------
ply_t        = 0.75;    // carcass, "3/4" prefinished maple plywood. [verify] measure the sheet: 18 mm = 0.709, 23/32 = 0.719. Drawer box widths depend on it
back_t       = 0.75;    // full back, same stock
drawer_t     = 0.625;   // drawer box sides/front/back, 5/8 Baltic birch, the dovetail-box standard
drawer_bot_t = 0.25;    // drawer bottom, 1/4 Baltic birch
sheet_w      = 48;
sheet_l      = 96;
bit_d        = 0.25;    // [choice] 1/4 compression bit: dogbone size and nesting gap

// ---- carcass joinery ----------------------------------------------------
dado_depth   = 0.375;   // [choice] all dados and rabbets 3/8 deep
bot_up       = 0.5;     // [choice] bottom dado starts 1/2 above the side's bottom edge (sits on the ladder)
back_in      = 0.5;     // [choice] back panel's rear face 1/2 in from the side's rear edge
finger_w     = 1.0;     // [choice] carcass finger joints, 1 wide, top and bottom to sides. Drawer fingers = drawer_t
// toe_h comes from kitchen_data.scad (ladder base height, separate part, continuous under a run)
toe_setback  = 3;       // [choice] ladder front set back 3 from the box front

// ---- fridge bay, from the LG spec sheet p.2 cabinet figure (15 mm cabinet basis) --------
// Air: in through the toe grille, under the floor slab, up through the floor notch at the rear,
// up the 50 mm channel behind the unit, out through the slot in the shelf, up the channel behind
// the top cabinet to the vented strip at the ceiling.
fr_toe_grille_w = 404 / 25.4;   // [mfr] toe board opening, centred on each unit
fr_toe_grille_h = 51 / 25.4;    // [mfr]
fr_notch_w      = 190 / 25.4;   // [mfr] floor slab notch at the rear, width along the bay
fr_notch_d      = 220 / 25.4;   // [mfr] notch depth, front to back, from the rear edge
fr_notch_from   = 300 / 25.4;   // [mfr] notch starts 300 from the east side of each opening
fr_top_slot_w   = 400 / 25.4;   // [mfr] shelf slot, centred on each unit, at the rear
fr_top_slot_d   = 50 / 25.4;    // [mfr]
fr_channel      = 2.0;          // [mfr] 50 mm behind the unit, carried up behind the top cabinet
fr_top_vent     = 1.5;          // [choice] vented strip at the ceiling, continuous grille over the bay
fr_tab_w        = 3.0;          // [choice] divider tabs into through slots in floor and shelf, 3 per edge

// ---- IKEA / Bofronts front interface ------------------------------------
// The front hole row is where Blum plates and Bofronts doors expect them.
row_front    = 37 / 25.4;  // [verify] 37 mm from the side's front edge, 32 mm system
row_rear     = 37 / 25.4;  // [choice] second row 37 mm from the back panel's front face
row_pitch    = 32 / 25.4;
row_hole_d   = 5 / 25.4;
row_first_z  = 2.5;        // [verify] first hole above the side's bottom edge; measure on a SEKTION frame
front_gap    = 0.125;      // [verify] gap between neighbouring Bofronts fronts

// ---- Blum Tandem 563H undermount, 21 runner for 24 deep boxes -----------
runner_len   = 21;         // [blum] 21 in / 533 mm
box_depth    = 21;         // [blum] drawer box length equals runner length
box_w_minus  = 0.5;        // [verify] box outside width = cabinet inside width - 1/2 (Blum 563H)
box_bot_up   = 0.5;        // [blum] bottom recess 1/2 from the lower edge of the sides
rear_notch_w = 0.5;        // [verify] notch at the rear bottom corner of each side, width along the side
rear_notch_h = 0.5;        // [verify] notch height
hook_hole_d  = 6 / 25.4;   // [verify] rear hook hole in the back panel, 6 mm
hook_hole_x  = 0.4375;     // [verify] hook hole centre from the outside face of the side, 7/16
hook_hole_z  = 0.3125;     // [verify] hook hole centre above the side's bottom edge, 5/16
box_h_minus  = 4;          // [choice] box height = front height - 4, never under 4

// ---- fronts per cabinet: [id, kind, [heights top to bottom] or door count] -
// Front heights are Bofronts/SEKTION modules for a 30 high base. Drawer fronts
// go top to bottom; doors give the count. Fridge bay and fillers have no fronts.
fronts = [
  ["S_B8",       "drawers", [10, 20]],     // [choice] pullout: 2 fronts, one box each
  ["S_SB36",     "doors",   2],            // 2 x 18 x 30, false front behind the sink not modelled
  ["S_B24",      "drawers", [10, 10, 10]],  // [choice] IKEA's own 24 3-drawer is 5/10/15; 10/10/10 keeps three equal boxes
  ["W_CORNER47", "doors",   1],            // 24 x 30 on the door half
  ["W_B12",      "drawers", [10, 20]],     // [choice] pullout like S_B8
  ["W_D30",      "drawers", [10, 10, 10]],
  ["S_FRIDGE_TOP", "doors", 2],            // [choice] 2 x 23 1/2, Bofronts custom
];
