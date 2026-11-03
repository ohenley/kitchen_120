// construction.scad -- how every box is built. Data only, same style as kitchen_data.scad.
// Units: inches. cutlist.py reads this file and kitchen_data.scad.
// Tags: [choice] decision taken here, [mfr] from a document in the repo (appliances_ref/) or quoted
// from it, [blum] from Blum's TANDEM documentation, [verify] measure before cutting: a number taken
// from the web or from memory, not from a document in hand.

// ---- stock ------------------------------------------------------------
ply_t        = 0.75;    // carcass, "3/4" prefinished maple plywood. [verify] measure the sheet: 18 mm = 0.709, 23/32 = 0.719. Drawer widths and the S_B8 locking devices depend on it
back_t       = 0.75;    // full back, same stock
drawer_t     = 0.625;   // drawer box sides/front/back, 5/8 Baltic birch. [verify] measure: 15.875 nominal, often 15 or 16 mm
drawer_bot_t = 0.5;     // drawer bottom, 1/2 Baltic birch, captured in a 1/4 deep groove on all four sides
drawer_dado  = 0.25;    // [choice] bottom groove depth in the 5/8 sides
sheet_w      = 48;
sheet_l      = 96;
bit_d        = 0.25;    // [choice] 1/4 compression bit: dogbone size

// ---- carcass joinery ----------------------------------------------------
// Top and bottom are finger-jointed to the sides (glue only). Back sits in 3/8 dados in sides, top and
// bottom, with its corners notched 3/8 so the three joints meet. Stretchers, rails, floors sit in 3/8 dados.
dado_depth   = 0.375;   // [choice] all dados and rabbets 3/8 deep
back_in      = 0.5;     // [choice] back panel's rear face 1/2 in from the side's rear edge
finger_w     = 1.0;     // [choice] carcass finger joints, 1 wide. Drawer fingers = 2 x drawer_t
// toe_h comes from kitchen_data.scad (ladder base height, separate part, continuous under a run)
toe_setback  = 3;       // [choice] ladder front set back 3 from the box front
corner_blind_w = 23.0;  // [choice] fixed panel on the blind corner: 47 - 24 door. Trim on site to the door's real overlay

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
fr_panel_w      = 23.0625;      // [choice] door panel width for two units on a 3/4 divider: opening + divider - 1/8 gap (LG: 592 on a 600 single cabinet)
fr_panel_freezer_h = 701 / 25.4;// [mfr] LG table, 20 mm cabinet sides (19 mm used)
fr_panel_fridge_h  = 1017 / 25.4;// [verify] read off the figure's 1017 mm call-out; confirm in the full LG install manual

// ---- IKEA / Bofronts front interface ------------------------------------
// The front hole row is where Blum plates and Bofronts doors expect them.
row_front    = 37 / 25.4;  // [verify] 37 mm from the side's front edge, 32 mm system
row_rear     = 37 / 25.4;  // [choice] second row 37 mm from the back panel's front face
row_pitch    = 32 / 25.4;
row_hole_d   = 5 / 25.4;   // 5 mm, 13 mm deep (ops.txt)
row_first_z  = 2.5;        // [verify] first hole above the side's bottom edge; measure on a SEKTION frame
// Bofronts nominal sizes already include IKEA's 1/8 gaps; no gap parameter is applied here.

// ---- Blum TANDEM 563H undermount, 21 runner for 24 deep boxes -----------
runner_len   = 21;         // [blum] 21 in / 533 mm
box_depth    = 21;         // [blum] drawer box length equals runner length
// width: inside drawer width = cabinet inside width - 42 mm [blum]; outside = inside + 2 x drawer_t (in cutlist.py)
box_bot_up   = 0.5;        // [blum] bottom recess 1/2 from the lower edge of the sides
rear_notch_w = 35 / 25.4;  // [blum] rear notch in each side, along the side
rear_notch_h = 13 / 25.4;  // [blum] rear notch height
hook_hole_d  = 6 / 25.4;   // [blum] rear hook hole in the back
hook_hole_x  = 11 / 25.4;  // [verify] hook hole centre from the outer end of the back (= outer face of the side)
hook_hole_z  = 24 / 25.4;  // [blum] hook hole centre above the lower edge (11 above the 13 notch shoulder)
box_h_minus  = 4;          // [choice] box height = front height - 4, never under 4
// shorter boxes where a service cavity is needed behind the drawer: [cabinet, front index from the top, box depth]
drawer_depth = [
  ["W_D30", 1, 18],        // [choice] oven junction box and cooktop receptacle sit behind the top drawer (oven manual: adjacent cabinet)
];

// ---- fronts per cabinet: [id, kind, [heights top to bottom] or door count] -
// Front heights are Bofronts/SEKTION modules for a 30 high base. Drawer fronts
// go top to bottom; doors give the count. Fridge bay and fillers have no fronts.
fronts = [
  ["S_B8",       "drawers", [10, 20]],     // [choice] pullout: 2 fronts, one box each. Narrow Blum locking devices, see hardware.csv
  ["S_SB36",     "doors",   2],            // 2 x 18 x 30
  ["S_B24",      "drawers", [10, 10, 10]], // [choice] IKEA's own 24 3-drawer is 5/10/15; 10/10/10 keeps three equal boxes
  ["W_CORNER47", "doors",   1],            // 24 x 30 on the door half
  ["W_B12",      "drawers", [10, 20]],     // [choice] pullout like S_B8
  ["W_D30",      "drawers", [10, 10, 10]],
  ["S_FRIDGE_TOP", "doors", 2],            // [choice] 2 x 23 9/16, Bofronts custom
];
