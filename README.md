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

- construction.scad: how every box is built. Stock thicknesses, dado depths,
  the IKEA front hole rows, Blum Tandem numbers, and which fronts each cabinet
  gets. Lines tagged [verify] are to be measured before cutting.
- cutlist.py: reads kitchen_data.scad and construction.scad, writes into out/:
  cutlist.csv (every part), fronts.csv (the Bofronts order), summary.txt
  (sheet count and the [verify] list), one DXF per cabinet with all its parts
  flat: OUTLINE, DADO (pockets), HOLE layers.

  python3 cutlist.py kitchen_data.scad construction.scad out

Construction: 3/4 prefinished ply carcass, bottom and back in 3/8 dados, top
rabbeted and dowelled, separate 4 1/2 ladder base per run. Sink base has two
stretchers instead of a top. Oven cabinet sides run to the floor with the
opening floor at the height the oven manual asks. Drawer boxes 1/2 Baltic birch
with a lock joint, 1/4 bottom, on Blum Tandem 21 runners. Fronts from Bofronts,
drawer fronts undrilled.
