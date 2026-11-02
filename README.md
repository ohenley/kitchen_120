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
