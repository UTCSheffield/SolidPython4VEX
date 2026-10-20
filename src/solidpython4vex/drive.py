"""Gears and sprockets with attachable mounting holes.

Hole patterns come from the VEX STEP files (scripts/extract_disc_holes.py -> parts/discs.json).
Most discs have a 0.5" Cartesian grid of round holes around the bore, so on the lattice they are
at even (u, v) like any channel hole; the old 84T gear uses polar rings instead.
The decimated STL is only a blank: the real holes and bore are cut exactly on top of it.
"""
import json
import math

from solid2 import cube, cylinder, import_stl

from .assembly import VEXAssembly
from .holes import Face, Hole, ROUND_HOLE, UNIT, PITCH
from .parts import PARTS_DIR, STL_DIR, part_info

SPECS = json.load(open(PARTS_DIR / "discs.json"))
BORE_SQUARE = 6.35

# rotation taking the disc axis onto z, per source axis
_AXIS_ROTATION = {"x": (0, -90, 0), "y": (90, 0, 0), "z": (0, 0, 0)}


def _pattern_points(pattern):
    """Hole centres (x, y) in mm around the disc centre."""
    if "grid_r2" in pattern:
        r2 = pattern["grid_r2"]
        return [(i * PITCH, j * PITCH) for i in range(-6, 7) for j in range(-6, 7) if 0 < i * i + j * j <= r2]
    pts = []
    for r, n, phase in pattern.get("polar", []):
        pts += [(r * math.cos(math.radians(phase + 360 * k / n)), r * math.sin(math.radians(phase + 360 * k / n)))
                for k in range(n)]
    return pts


class Disc(VEXAssembly):
    """A gear or sprocket (catalog `name`), axis along z, centred on the origin.

    `.holes` are the round mounting holes on both faces ("front" normal +z, "back" normal -z);
    the centre bore is cut but not attachable.
    """

    def __init__(self, name):
        if name not in SPECS:
            raise KeyError(f"no hole spec for {name}; known: {sorted(SPECS)}")
        spec = SPECS[name]
        self.info = part_info(name)
        t = spec["thickness"]
        self.thickness = t
        self.faces = {
            "front": Face("front", (0, 0, 0), (1, 0, 0), (0, -1, 0), (0, 0, 1), t),
            "back": Face("back", (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, -1), t),
        }
        pts = _pattern_points(spec["pattern"])
        self.holes = [Hole(self.faces["front"], x / UNIT, -y / UNIT, "round") for x, y in pts] + [
            Hole(self.faces["back"], x / UNIT, y / UNIT, "round") for x, y in pts
        ]

        blank = import_stl(str(STL_DIR / f"{name}.stl")).translate([-c for c in spec["centre"]])
        rot = _AXIS_ROTATION[spec["axis"]]
        if any(rot):
            blank = blank.rotate(rot)

        depth = t * 3
        for x, y in pts:
            blank -= cylinder(d=ROUND_HOLE, h=depth, center=True, _fn=24).translate(x, y, 0)
        if spec["round_bore"]:
            blank -= cylinder(r=spec["round_bore"][0], h=depth, center=True, _fn=32)
        else:
            blank -= cube([BORE_SQUARE, BORE_SQUARE, depth], center=True)
        self.shape = blank
        self.shape.part_info = self.info


def disc_names():
    return sorted(SPECS)
