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
from .axles import Bearing_Flat, Nylon_Spacer_1_2in, Omni_Wheel_4in, Shaft, Shaft_Collar
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


def dead_wheel_stack(span, wall):
    """A 4" omni wheel on a 3" capped shaft that passes through both flanges of a U channel.

    The parts are positioned from the cap end: the wheel's face is against the cap, then a 1/2"
    spacer (enough to clear the screws and nuts on the outer flange), then the outer flange, `span`
    mm of channel, the inner flange and a collar. The free end sticks out beyond the collar.
    `span` is the distance between the outer faces of the two flanges and `wall` the flange
    thickness. Returns `(stack, station)`: `station` is the shaft position of the inner flange's
    inner face, for `chassis.attach(inner_bearing.axle, stack, station)`.
    """
    shaft = Shaft(3)
    collar, wheel, spacer = Shaft_Collar(), Omni_Wheel_4in(), Nylon_Spacer_1_2in()
    wheel_at = shaft.LENGTH - shaft.CAP - wheel.WIDTH / 2
    spacer_at = wheel_at - wheel.WIDTH / 2 - spacer.WIDTH / 2
    outer_face = spacer_at - spacer.WIDTH / 2
    inner_face = outer_face - span
    collar_at = inner_face - collar.WIDTH / 2
    if collar_at < collar.WIDTH / 2:
        raise ValueError("the 3 inch shaft is too short to span this channel")
    stack = shaft
    for at, item in ((collar_at, collar), (spacer_at, spacer), (wheel_at, wheel)):
        stack = stack.attach(shaft.at(at), item, item.axle)
    return stack, shaft.at(inner_face + wall)


def place_dead_wheel_near_rear(chassis, inset=1, side="right"):
    """Mount a dead wheel through the two flanges of a U-channel rail, near its rear end.

    `chassis` is either a single U channel (the left rail of a `ChannelFrame`, before it is laid
    flat) or a laid-flat frame with two U-channel rails. Rails run along x with the rear at +x, and
    the axle runs across the rail. A flat bearing is bolted to the inside of each flange with the
    bore in the middle hole row and a screw and hex nut in each neighbouring hole; the shaft goes
    through both with a collar at the inboard end and a spacer before the wheel, which sits outboard
    of the rail with its outer face against the shaft's cap. `inset` is how many 0.5" pitches the axle
    is in front of the last flange hole (1 uses the last hole as a screw hole).

    side  for a laid-flat frame, the "left" or "right" rail. For a single channel, which way the
          wheel hangs: "outboard"/"left" (away from the frame the channel is the left rail of) or
          "inboard"/"right".
    """
    flange = [h for h in chassis.holes if h.face.name.startswith("flange") and h.v == 2]
    if not flange:
        raise ValueError("a dead wheel needs a U channel rail with a middle row of flange holes")
    axis = max(range(3), key=lambda i: abs(flange[0].normal[i]))  # the axle runs along the flange normal
    levels = sorted({round(h.position[axis], 3) for h in flange})
    if len(levels) == 2:
        if side not in ("outboard", "left", "inboard", "right"):
            raise ValueError("side must be 'outboard' or 'inboard' for a single channel")
        sign = 1 if side in ("outboard", "left") else -1
        rail = levels
    elif len(levels) == 4:
        if side not in ("left", "right"):
            raise ValueError("side must be 'left' or 'right'")
        sign = 1 if side == "right" else -1
        rail = levels[2:] if sign > 0 else levels[:2]
    else:
        raise ValueError("a dead wheel needs a U channel rail with a middle row of flange holes")
    inner_y, outer_y = rail if sign > 0 else rail[::-1]
    flange = [h for h in flange if round(h.position[axis], 3) in rail]
    thickness = flange[0].face.thickness

    def row(y):
        return {round(h.position[0], 3): h for h in flange if abs(h.position[axis] - y) < 0.5}

    inner_row, outer_row = row(inner_y), row(outer_y)
    wanted = max(outer_row) - inset * PITCH
    centre = min(outer_row, key=lambda x: abs(x - wanted))
    pitch = round(PITCH, 3)
    holes = []
    for flange_row in (inner_row, outer_row):
        pair = [flange_row.get(round(centre + dx, 3)) for dx in (-pitch, pitch)]
        if None in pair:
            raise ValueError("not enough flange holes at that position; try a smaller inset")
        holes.append(pair)

    def bolt(assembly, left, right):
        for roll in range(4):
            block = Bearing_Flat()
            try:
                return assembly.attach(left, block, block.hole("base", -2, 0), nut="hex", roll=roll, side="inner",
                                       also=[(right, block.hole("base", 2, 0))])
            except ValueError:
                continue
        raise ValueError("could not bolt a bearing block onto the rail")

    assembled = chassis
    for left, right in holes:
        assembled = bolt(assembled, left, right)

    inner_axle = next(h for h in assembled.holes if h.kind == "axle_round" and h.normal[axis] * sign > 0.99)
    stack, station = dead_wheel_stack(abs(outer_y - inner_y) + thickness, thickness)
    return assembled.attach(inner_axle, stack, station)
