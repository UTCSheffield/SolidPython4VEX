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
from .axles import (
    Bearing_Flat,
    Nylon_Spacer_1_2in,
    Omni_Wheel_4in,
    Shaft,
    Shaft_Collar,
    Traction_Wheel_4in,
    V5_Smart_Motor,
)
from .holes import Face, Hole, ROUND_HOLE, UNIT, PITCH
from .parts import PARTS_DIR, STL_DIR, part_info, tint

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
        self.shape = tint(self.shape, self.info)

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


class _Rail:
    """The two flanges of a U-channel rail and their middle rows of holes, found from a chassis."""

    def __init__(self, chassis, side, what):
        flange = [h for h in chassis.holes if h.face.name.startswith("flange") and h.v == 2]
        if not flange:
            raise ValueError(f"a {what} needs a U channel rail with a middle row of flange holes")
        self.axis = max(range(3), key=lambda i: abs(flange[0].normal[i]))  # the axle runs along the flange normal
        levels = sorted({round(h.position[self.axis], 3) for h in flange})
        if len(levels) == 2:
            if side not in ("outboard", "left", "inboard", "right"):
                raise ValueError("side must be 'outboard' or 'inboard' for a single channel")
            self.sign = 1 if side in ("outboard", "left") else -1
            rail = levels
        elif len(levels) == 4:
            if side not in ("left", "right"):
                raise ValueError("side must be 'left' or 'right'")
            self.sign = 1 if side == "right" else -1
            rail = levels[2:] if self.sign > 0 else levels[:2]
        else:
            raise ValueError(f"a {what} needs a U channel rail with a middle row of flange holes")
        inner_y, outer_y = rail if self.sign > 0 else rail[::-1]
        flange = [h for h in flange if round(h.position[self.axis], 3) in rail]
        self.thickness = flange[0].face.thickness
        self.span = abs(outer_y - inner_y) + self.thickness  # between the outer faces of the flanges

        def row(y):
            return {round(h.position[0], 3): h for h in flange if abs(h.position[self.axis] - y) < 0.5}

        self.inner_row, self.outer_row = row(inner_y), row(outer_y)

    def holes_at(self, row, centre, *steps):
        """The flange holes `steps` pitches from `centre` along x."""
        found = [row.get(round(centre + n * round(PITCH, 3), 3)) for n in steps]
        if None in found:
            raise ValueError("not enough flange holes at that position; try a different inset")
        return found

    def axle_hole(self, assembly, kind, x=None):
        """The free `kind` axle hole facing out of the rail (nearest `x` along the rail, if given)."""
        found = [h for h in assembly.holes if h.kind == kind and h.normal[self.axis] * self.sign > 0.99
                 and h not in assembly.taken]
        return min(found, key=lambda h: abs(h.position[0] - x)) if x is not None else found[0]


def _bolt_bearing(assembly, hole_pairs, bore, side, **kwargs):
    """Bolt a Bearing_Flat onto `hole_pairs` (flange hole, bearing screw-hole u), trying each roll."""
    for roll in range(4):
        bearing = Bearing_Flat(bore)
        (first, u), *others = hole_pairs
        try:
            return assembly.attach(first, bearing, bearing.hole("base", u, 0), roll=roll, side=side,
                                   also=[(h, bearing.hole("base", n, 0)) for h, n in others], **kwargs)
        except ValueError:
            continue
    raise ValueError("could not bolt a bearing onto the rail")


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
    rail = _Rail(chassis, side, "dead wheel")
    centre = min(rail.outer_row, key=lambda x: abs(x - (max(rail.outer_row) - inset * PITCH)))
    assembled = chassis
    for row in (rail.inner_row, rail.outer_row):
        left, right = rail.holes_at(row, centre, -1, 1)
        assembled = _bolt_bearing(assembled, [(left, -2), (right, 2)], "middle", "inner", nut="hex")
    stack, station = dead_wheel_stack(rail.span, rail.thickness)
    return assembled.attach(rail.axle_hole(assembled, "axle_round"), stack, station)


MOTOR_SCREW = 0.75  # inches: through the bearing and flange and into the motor's posts


def motor_wheel_stack(span):
    """A 4" wheel on a 3" capped shaft that is driven by a motor against the inner flange.

    Along the shaft from its free end (which sits inside the motor): the motor's boss against the
    frame side of the inner flange, the two flanges and `span` mm of channel, a 1/2" spacer that
    clears the screws and nuts on the outer flange, then the wheel against the shaft's cap.
    Returns `(stack, station)`: `station` is where the motor's boss is on the shaft.
    """
    shaft = Shaft(3)
    wheel, spacer = Traction_Wheel_4in(), Nylon_Spacer_1_2in()
    wheel_at = shaft.LENGTH - shaft.CAP - wheel.WIDTH / 2
    spacer_at = wheel_at - wheel.WIDTH / 2 - spacer.WIDTH / 2
    boss_at = spacer_at - spacer.WIDTH / 2 - span
    if boss_at < 0:
        raise ValueError("the 3 inch shaft is too short to reach the motor from this channel")
    stack = shaft
    for at, item in ((spacer_at, spacer), (wheel_at, wheel)):
        stack = stack.attach(shaft.at(at), item, item.axle)
    return stack, shaft.at(boss_at)


def place_motor_wheel(chassis, at="front", side="outboard", motor_gearing="blue", inset=0):
    """Mount a motor-driven 4" wheel through a U-channel rail, at its front or rear end.

    The rails are as for `place_dead_wheel_near_rear`. The motor sits against the frame side of the
    inner flange with its shaft along the middle row of flange holes. A flat bearing inside the U
    carries the shaft: its bore is at the shaft and its two screws go through the flange into the
    motor's two posts. A second flat bearing and a hex-nut joint carry the shaft at the outer
    flange, then a spacer and the wheel. `inset` is how many 0.5" pitches the shaft is in from the
    end hole of the flange row; the motor's posts are on the side of the shaft toward the middle
    of the rail.
    """
    if at not in ("front", "rear"):
        raise ValueError("at must be 'front' or 'rear'")
    rail = _Rail(chassis, side, "motor wheel")
    toward_middle = -1 if at == "rear" else 1
    end = max(rail.outer_row) if at == "rear" else min(rail.outer_row)
    centre = min(rail.outer_row, key=lambda x: abs(x - (end + toward_middle * inset * PITCH)))
    motor = V5_Smart_Motor(motor_gearing)

    inner_posts = rail.holes_at(rail.inner_row, centre, toward_middle, 2 * toward_middle)
    assembled = _bolt_bearing(
        chassis, [(inner_posts[0], -2), (inner_posts[1], -4)], "end", "inner", nut=None, screw=MOTOR_SCREW
    )
    assembled.taken = assembled.taken - set(inner_posts)  # the motor's posts use the same flange holes
    for roll in range(4):
        try:
            assembled = assembled.attach(
                inner_posts[0], motor, motor.hole("boss", -2, 0), roll=roll, side="outer", fasteners=False,
                also=[(inner_posts[1], motor.hole("boss", -4, 0))],
            )
            break
        except ValueError:
            continue
    else:
        raise ValueError("could not place the motor against the rail")

    outer_posts = rail.holes_at(rail.outer_row, centre, toward_middle, 2 * toward_middle)
    assembled = _bolt_bearing(assembled, [(outer_posts[0], -2), (outer_posts[1], -4)], "end", "inner", nut="hex")
    stack, station = motor_wheel_stack(rail.span)
    return assembled.attach(rail.axle_hole(assembled, "axle_square", centre), stack, station)
