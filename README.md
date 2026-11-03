# kitchen_120

- kitchen_data.scad: the kitchen. Room, openings, one line per cabinet,
  one line per appliance opening. Units are inches, origin is the inside
  SW corner at floor level: window wall south, oven wall west, X east,
  Y north. Edit this file only.
- kitchen.scad: OpenSCAD renderer. Includes kitchen_data.scad. F5 to preview.
- draw.py: plan and two elevations as PNG from the same data file.
  python3 draw.py kitchen_data.scad out

Tags on each data line: [label] IKEA planner figure, [px] read from planner
pixels, [mfr] manufacturer document, [choice] a decision to confirm.

## Cut list

- construction.scad: how every box is built. Stock, joinery, the IKEA front hole rows, the Blum
  TANDEM numbers, the LG fridge bay numbers, which fronts each cabinet gets. Lines tagged [verify]
  are to be measured before cutting.
- cutlist.py: reads kitchen_data.scad and construction.scad, writes into out/:
  cutlist.csv (every part), fronts.csv (the Bofronts order), hardware.csv (runners, locking devices,
  hinges), countertop.csv (the two cutouts), ops.txt (DXF layer legend and setup rules), summary.txt
  (sheet estimate, drawer schedule, [verify] list), one DXF per cabinet with all its parts flat.

  python3 cutlist.py kitchen_data.scad construction.scad out

Construction: 3/4 prefinished ply carcass. Top and bottom finger-jointed to the sides (1 in fingers,
glue only). Back in 3/8 dados in sides, top and bottom, corners notched so the three joints meet.
Separate 4 7/8 ladder base per run. Sink base: two vertical stretchers instead of a top, Bosch hose
opening in the dishwasher-side panel. Oven cabinet: sides to the floor, open back, floor panel at the
height the oven manual asks on a toe board and a rear ledger, no top (front rail and rear stretcher),
clamp relief on the sides under the cooktop cutout, cable hole to W_D30 whose top drawer is 18 deep
to leave the junction box and receptacle room. Fridge bay: end panels, floor, shelf and divider
built to the LG cabinet figure with its toe grilles, floor notches, shelf slots and 2 in channel.
Drawer boxes: 5/8 Baltic birch, finger-jointed at all four corners, 1/4 bottom in a dado, on Blum
TANDEM runners; width from Blum's 42 mm rule and the measured stock. Fronts from Bofronts, drawer
fronts undrilled.

Every cut is flat. The DXF layers say what each feature is (ops.txt). draw.py's PASS is about
positions; it says nothing about whether parts assemble. The generator validates its own outlines
(simple, no backtracking) and that every hole lies in material.
