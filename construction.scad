// construction.scad -- how every box is built. Data only, same style as kitchen_data.scad.
// Units: inches. cutlist.py reads this file and kitchen_data.scad.
// Tags: [choice] decision taken here, [blum] from Blum's Tandem chart, [verify] measure
// before cutting: a number taken from the web or from memory, not from a document in hand.

// ---- stock ------------------------------------------------------------
ply_t        = 0.75;    // carcass, "3/4" prefinished maple plywood. [verify] measure the sheet: 18 mm = 0.709, 23/32 = 0.719. Drawer box widths depend on it
back_t       = 0.75;    // full back, same stock
drawer_t     = 0.5;     // drawer box sides/front/back, 1/2 Baltic birch
drawer_bot_t = 0.25;    // drawer bottom, 1/4 Baltic birch
sheet_w      = 48;
sheet_l      = 96;
kerf         = 0.25;    // bit diameter used for nesting estimate

// ---- carcass joinery ----------------------------------------------------
dado_depth   = 0.375;   // [choice] all dados and rabbets 3/8 deep
bot_up       = 0.5;     // [choice] bottom dado starts 1/2 above the side's bottom edge (sits on the ladder)
back_in      = 0.5;     // [choice] back panel's rear face 1/2 in from the side's rear edge
dowel_d      = 8 / 25.4;// 8 mm dowels
dowel_pitch  = 6;       // [choice] one dowel every 6 along a top/side joint
// toe_h comes from kitchen_data.scad (ladder base height, separate part, continuous under a run)
toe_setback  = 3;       // [choice] ladder front set back 3 from the box front

// ---- fridge bay -----------------------------------------------------------
// [verify] from the LG installation manual (MFL67792604): enclosure height, base height and
// load, vent free area per unit, panel thickness and weight. Until then the bay is panels only.
fridge_vent_in2 = 31;      // [verify] reported as "over 200 cm2" per unit; location (base, rear, top) unknown
fridge_base_h   = 0;       // [verify] reported 20 mm supported base; 0 until the manual says where it sits

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
lock_tongue  = 0.25;       // [choice] drawer lock joint: tongue 1/4 thick, dado 1/4 from the end
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
