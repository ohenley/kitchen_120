// construction.scad -- how every box is built. Data only, same style as kitchen_data.scad.
// Units: inches. cutlist.py reads this file and kitchen_data.scad.
// Tags: [choice] decision taken here, [mfr] from a document in appliances_ref/ or quoted from it,
// [blum] from Blum's TANDEM documentation, [verify] measure or confirm before cutting.

// ---- stock ------------------------------------------------------------
ply_t        = 0.75;    // carcass, "3/4" prefinished maple plywood. [verify] measure the sheet: 18 mm = 0.709, 23/32 = 0.719. Drawer widths and the S_B8 locking devices depend on it
back_t       = 0.75;    // full back, same stock
drawer_t     = 0.625;   // drawer box sides/front/back, 5/8 Baltic birch. [verify] measure: 15.875 nominal, often 15 or 16 mm
drawer_bot_t = 0.5;     // drawer bottom, 1/2 Baltic birch, rabbeted to a 1/4 tongue that sits in the groove
drawer_groove_w = 0.25; // [choice] groove width = tongue thickness
drawer_groove_d = 0.1875; // [choice] groove depth 3/16: leaves 1.1 mm between the groove and the 10 mm hook bore
sheet_w      = 48;
sheet_l      = 96;
bit_d        = 0.25;    // [choice] 1/4 compression bit: dogbone size

// ---- carcass joinery ----------------------------------------------------
// Top and bottom are finger-jointed to the sides (glue only). Back sits in 3/8 dados in sides, top and
// bottom, with its corners notched 3/8 so the three joints meet. Stretchers, rails, floors sit in 3/8 dados.
dado_depth   = 0.375;   // [choice] all dados and rabbets 3/8 deep
back_in      = 0.5;     // [choice] back panel's rear face 1/2 in from the side's rear edge
back_in_override = [    // cabinets whose back sits further from the wall (service void behind it)
  ["S_B8", 2.0],        // [choice] fridge cords run in the 2 void behind S_B8's back, up to the receptacle on that back
];
finger_w     = 1.0;     // [choice] carcass finger joints, 1 wide. Drawer fingers = 2 x drawer_t
// toe_h comes from kitchen_data.scad (ladder base height, separate part, continuous under a run)
toe_setback  = 3;       // [choice] ladder front rail 3 behind the CARCASS front, 3 3/4 behind the fronts
corner_blind_w = 24.875;// [choice] fixed panel on the blind corner: the door must start past the window-wall fronts' plane (24 3/4) + 1/8, so door = 47 - 24 7/8 = 22 1/8 nominal, Bofronts custom
glue_note    = "PVA on raw plywood only: the prefinished faces are not glue surfaces; fingers, dados and tongues are bare";

// ---- fridge column, from the LG spec sheet p.2 cabinet figure (15 mm cabinet basis) ------
// One column from the ladder to the ceiling: end panels, floor, divider, shelf, upper section with
// doors, vented strip. Air: in through the toe grille, under the floor slab (ladder cavity), up through
// the floor notch at the rear, up the 50 mm channel behind the unit, through the slot in the shelf, up
// the channel behind the upper section's back, over its top slab, out through the vented strip.
fr_toe_grille_w = 404 / 25.4;   // [mfr] toe board opening, centred on each unit
fr_toe_grille_h = 51 / 25.4;    // [mfr]
fr_notch_w      = 190 / 25.4;   // [mfr] floor slab notch at the rear, width along the bay
fr_notch_d      = 220 / 25.4;   // [mfr] notch depth, front to back, from the rear edge
fr_notch_from   = 300 / 25.4;   // [mfr] notch starts 300 from the east side of each opening
fr_top_slot_w   = 400 / 25.4;   // [mfr] shelf slot, centred on each unit, at the rear
fr_top_slot_d   = 50 / 25.4;    // [mfr]
fr_channel      = 2.0;          // [mfr] 50 mm behind the unit, carried up behind the upper section's back
fr_top_vent     = 3.0;          // [choice] vented strip at the ceiling, 3 high, two slots of 420 x 55 mm (230 cm2 each, LG asks over 200 net)
fr_vent_slot_w  = 420 / 25.4;
fr_vent_slot_h  = 55 / 25.4;
fr_tab_w        = 3.0;          // [choice] divider tabs into through slots in floor and shelf, 3 per edge
fr_panel_w      = 23.0625;      // [verify] door panel width for two units on a 3/4 divider: opening + divider - 1/8 gap (LG: 592 on a 600 single cabinet); confirm with LG's hinge bracket geometry
fr_panel_freezer_h = 701 / 25.4;// [mfr] LG table, 20 mm cabinet sides (19 mm used)
fr_panel_fridge_h  = 1017 / 25.4;// [verify] read off the figure's 1017 mm call-out; confirm in the full LG install manual before ordering

// ---- IKEA / Bofronts front interface ------------------------------------
// Bofronts doors come bored for IKEA UTRUSTA hinges (Blum-made clip hinges). The carcass rows are
// where the UTRUSTA plates and the Blum runners screw in.
row_front    = 37 / 25.4;  // [verify] 37 mm from the side's front edge, 32 mm system
row_rear     = 37 / 25.4;  // [choice] second row 37 mm from the back panel's front face
row_pitch    = 32 / 25.4;
row_hole_d   = 5 / 25.4;   // 5 mm
row_hole_depth = 13 / 25.4;// 13 mm deep
row_first_z  = 2.5;        // [verify] first hole above the side's bottom edge; measure on a SEKTION frame
front_reveal = 0.125;      // Bofronts: a nominal 24 x 30 door is 23 7/8 x 29 7/8 finished; nominal = module, finished = nominal - 1/8

// ---- Blum TANDEM 563H undermount ------------------------------------------
runner_len   = 21;         // [blum] 21 in / 533 mm; shorter runners where a service compartment sits behind the drawer
box_depth    = 21;         // [blum] drawer box length equals runner length
// width: inside drawer width = cabinet inside width - 42 mm [blum]; outside = inside + 2 x drawer_t (in cutlist.py)
box_bot_up   = 0.5;        // [blum] bottom recess: 1/2 from the lower edge of the sides to the underside of the bottom
back_notch_w = 35 / 25.4;  // [blum] notch at each lower corner of the drawer BACK, along the back
back_notch_h = 13 / 25.4;  // [blum] notch height
hook_hole_d  = 6 / 25.4;   // [blum] rear hook hole in the back, from the rear face
hook_hole_depth = 10 / 25.4;// [blum]
hook_hole_in = 7 / 25.4;   // [blum] hook hole centre 7 mm inboard of the drawer side's inside face
hook_hole_z  = 24 / 25.4;  // [blum] hook hole centre above the lower edge (11 above the 13 notch shoulder)
box_h_minus  = 4;          // [choice] box height = front height - 4, never under 4
box_front_up = 0.5;        // [verify] drawer side lower edge sits 1/2 above the front's lower edge
runner_fix_dz = 0.0;       // [verify] runner screw centre relative to the drawer side's lower edge (Blum 563H drawing)
// shorter boxes where a service compartment is needed behind the drawer: [cabinet, front index from the top, box depth]
drawer_depth = [
  ["W_D30", 1, 15],        // [choice] gas flex and cooktop cord pass beside the manifold corner, 16 to 18 behind the front
  ["W_D30", 2, 18],        // [choice] oven junction box and cooktop receptacle at mid-height behind this drawer
  ["S_B8",  1, 18],        // [choice] DW receptacle and fridge receptacle on the back of S_B8, behind both drawers
  ["S_B8",  2, 18],
];

// ---- services: holes through cabinet sides and panels ------------------------
// [id, cabinet, side ("A" low-pos end, "B" high-pos end), x from the front, z above the FINISHED FLOOR, dia, purpose]
// Rule [brief]: plugs in side cabinets, never behind an appliance; receptacles at mid-height, fridge receptacles at the lower quarter.
// Appliance-side passages follow the appliance documents (Bosch rear corner, KitchenAid upper rear), the receptacle sits
// in the side cabinet's service compartment at the rule's height.
services = [
  ["DW_CORD",    "S_B8",        "B", 21.0,  6.875, 1.25, "Bosch cord out of the DW's rear bottom into S_B8's compartment; receptacle at 19 7/8 on S_B8's back"],
  ["DW_HOSES",   "S_SB36",      "A", 20.5,  7.125, 0,    "rect 3.5 x 2.5, Bosch install p.10, hoses and drain to the sink"],
  ["FR_CORD_2",  "S_FRIDGE_BAY","B", 24.25, 23.375, 1.25, "FR2 cord through the end panel, in the channel, to S_B8's void; receptacle at 23 3/8 on S_B8's back [verify LG cord length]"],
  ["FR_CORD_1",  "S_FRIDGE_BAY","D", 24.25, 23.375, 1.25, "FR1 cord through the divider into FR2's channel, then as FR_CORD_2 [verify LG cord length, about 50 in of run]"],
  ["FR_CORD_IN", "S_B8",        "A", 23.0,  23.375, 1.25, "into S_B8's 2 void behind its back; the cords come through S_B8's back to the receptacle"],
  ["OV_CABLE",   "W_OVEN30",    "B", 21.5,  31.875, 1.25, "oven conduit to the junction box, upper rear corner per the oven manual"],
  ["OV_CABLE_IN","W_D30",       "A", 21.5,  31.875, 1.25, "same hole on W_D30's side; junction box at 19 7/8 in the compartment behind drawer 2"],
  ["CT_GAS",     "W_OVEN30",    "B", 17.0,  31.25,  1.25, "gas flex to the cooktop manifold (1 7/16 from the cooktop's right edge, 4 3/8 from its rear), above the oven body"],
  ["CT_GAS_IN",  "W_D30",       "A", 17.0,  31.25,  1.25, "same hole on W_D30; shutoff valve in the compartment behind drawer 1, reached by pulling that drawer"],
  ["CT_CORD",    "W_OVEN30",    "B", 19.5,  31.25,  1.25, "cooktop 120 V cord, right rear corner, to the receptacle at 19 7/8 in W_D30"],
  ["CT_CORD_IN", "W_D30",       "A", 19.5,  31.25,  1.25, "same hole on W_D30"],
];

// ---- fronts per cabinet: [id, kind, [heights top to bottom] or door count] -
fronts = [
  ["S_B8",       "drawers", [10, 20]],     // [choice] pullout: 2 fronts, one box each. Narrow Blum locking devices, see hardware.csv
  ["S_SB36",     "doors",   2],            // 2 x 18 x 30
  ["S_B24",      "drawers", [10, 10, 10]], // [choice] IKEA's own 24 3-drawer is 5/10/15; 10/10/10 keeps three equal boxes
  ["W_CORNER47", "doors",   1],            // 22 1/8 x 30 custom on the door half, see corner_blind_w
  ["W_B12",      "drawers", [10, 20]],     // [choice] pullout like S_B8
  ["W_D30",      "drawers", [10, 10, 10]],
  ["S_FRIDGE_TOP", "doors", 2],            // [choice] upper section of the fridge column, 2 doors
];
