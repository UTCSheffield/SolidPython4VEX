"""V5 electronics: brain, radio, and battery clip with battery."""
from itertools import product

from solid2 import multmatrix

from .assembly import VEXAssembly
from .holes import Face, Hole, PITCH, UNIT, mat_vec
from .joints import _rotation_about, attach
from .parts import part, part_info


class V5_Robot_Brain(VEXAssembly):
    """V5 brain (276-4810). Only the inner four mounting holes (3" x 1.5") are used.

    They are blind pockets in the flat back; "brain_mount" is that back face and the
    body extends away from it, so with the face on a plate the screen faces up.
    """

    NAME = "276_4810_V5_Robot_Brain"
    POCKET = 6.0
    MOUNT_FACE = "brain_mount"
    MOUNT_EXTENT = (-69.0, 69.0, -49.9, 49.9)  # body extent in mm along the mount face's (u, v) axes

    def __init__(self):
        self.info = part_info(self.NAME)
        self.shape = part(self.NAME)
        mount = Face("brain_mount", (0, 0, 8), (1, 0, 0), (0, -1, 0), (0, 0, 1), 0.0)
        self.faces = {"brain_mount": mount}
        self.holes = [Hole(mount, u, v, "round") for u in (-6, 6) for v in (-3, 3)]


class V5_Robot_Radio(VEXAssembly):
    """V5 radio (276-4831), screwed into two blind pockets 0.5" apart in its back (the y = 16 face).

    "radio_mount" is that face, centred between the pockets, so the radio body sits 12.65 mm to one side.
    """

    NAME = "276_4831_V5_Robot_Radio"
    POCKET = 11.0
    MOUNT_FACE = "radio_mount"
    MOUNT_EXTENT = (-54.85, 29.55, -12.7, 12.7)

    def __init__(self):
        self.info = part_info(self.NAME)
        self.shape = part(self.NAME)
        mount = Face("radio_mount", (12.65, 16, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0), 0.0)
        self.faces = {"radio_mount": mount}
        self.holes = [Hole(mount, u, 0, "round") for u in (-1, 1)]


class V5_Battery(VEXAssembly):
    """V5 battery (276-4811) held by two battery clips (276-6020).

    The clips are fixed through their central holes and sit square across the battery, so the
    battery lies along the line joining the two screws. `spacing` is the distance between the
    screws in pitches (0.5") and must be even. "battery_mount" is the clips' base, with the two
    screw holes at u = -spacing and +spacing (lattice units), on the battery's centre line.
    """

    CLIP = "276_6020_V5_Battery_Clip"
    BATTERY = "276_4811_V5_Robot_Battery"
    POCKET = None
    LIFT = 0.25 * 25.4  # the battery sits this far further up out of the clips than the raw CAD
    MOUNT_FACE = "battery_mount"
    MOUNT_EXTENT = (-82.1, 81.3, -23.2, 23.2)

    def __init__(self, spacing=8):
        if spacing % 2 or spacing < 2:
            raise ValueError("spacing must be an even number of pitches")
        self.info = part_info(self.BATTERY)
        self.shape = part(self.BATTERY).translate(0, self.LIFT, 0)
        for side in (-1, 1):
            clip = multmatrix([[0, 0, 1, side * spacing * PITCH / 2], [0, 1, 0, 0], [-1, 0, 0, 0], [0, 0, 0, 1]])(
                part(self.CLIP)
            )
            self.shape += clip
        base = Face("battery_mount", (0, -8, 0), (1, 0, 0), (0, 0, -1), (0, -1, 0), 2.0)
        self.faces = {"battery_mount": base}
        self.holes = [Hole(base, u, 0, "round") for u in (-spacing, spacing)]


def placed(assembly, part_, *, x=0, y=0, z=0, up_axis="y", along_y=False):
    """Add `part_` to `assembly` unattached, rotated so the part's `up_axis` points along world +z.

    along_y turns the part a further quarter turn so its long x side runs along world y."""
    rot = {"z": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "y": [[1, 0, 0], [0, 0, -1], [0, 1, 0]]}[up_axis]
    if along_y:
        rot = [[-rot[1][j] for j in range(3)], list(rot[0]), list(rot[2])]
    moved = multmatrix([[*rot[i], t] for i, t in enumerate((x, y, z))] + [[0, 0, 0, 1]])(part_.shape)
    out = VEXAssembly()
    out.shape = assembly.shape + moved
    out.holes = list(assembly.holes)
    out.taken = set(assembly.taken)
    return out


def try_attach(assembly, part_, candidates, **kwargs):
    """Attach `part_` using the first candidate list of (assembly_hole, part_hole) pairs that lines up.

    Each candidate is tried at all four quarter-turn rolls; the hole geometry decides which fit.
    """
    for pairs in candidates:
        for roll in range(4):
            try:
                return attach(assembly, pairs[0][0], part_, pairs[0][1], also=pairs[1:], roll=roll, **kwargs)
            except ValueError:
                continue
    raise ValueError(f"could not line up {type(part_).__name__} with the holes offered")


def orientations(part_uvs, centre):
    """Candidate (plate_uv, part_uv) pairings of a symmetric hole pattern about `centre`.

    The pattern may be mirrored or turned, since the roll of the attach is searched separately.
    """
    cu, cv = centre
    for swap in (False, True):
        for su in (1, -1):
            for sv in (1, -1):
                pairs = []
                for u, v in part_uvs:
                    a, b = (v, u) if swap else (u, v)
                    pairs.append(((cu + su * a, cv + sv * b), (u, v)))
                yield pairs


def free_holes(assembly, face):
    """{(u, v): hole} for the unused holes of the faces called `face`."""
    return {(h.u, h.v): h for h in assembly.holes if h.face.name == face and h not in assembly.taken}


_END = {"left": -1, "front": -1, "right": 1, "rear": 1}


def mount(base, part_, *, at="middle", inset=0, hardware="screw", face=None, spin=0, **kwargs):
    """Screw `part_` onto a free face of `base` and return the joined assembly.

    at       "middle", or "left"/"front" / "right"/"rear" for the low / high end of the face's long (u) axis
    inset    pitches (0.5") in from that end; for "middle" it slides the part along u
    face     the base face to use; default is the first of `base.mount_faces` where the part fits
    spin     degrees (0, 90, 180 or 270) the part is turned about the face normal, as in BOSL2.
             At 0 the part's u axis, the line of its mounting holes, runs along the base's long axis.
    """
    if hardware not in ("screw", "individual"):
        raise ValueError("hardware must be 'screw'")
    if at != "middle" and at not in _END:
        raise ValueError("at must be 'middle', 'left', 'right', 'front' or 'rear'")
    if spin % 90:
        raise ValueError("spin must be a multiple of 90 degrees")
    roll = (spin // 90) % 4
    pattern = [(h.u, h.v) for h in part_.holes if h.face.name == part_.MOUNT_FACE]
    lo_u, hi_u, lo_v, hi_v = (c / UNIT for c in part_.MOUNT_EXTENT)
    names = [face] if face else list(base.mount_faces)
    for name in names:
        length, v_centre = base.mount_faces[name]
        free = free_holes(base, name)
        fa = next(iter(free.values())).face
        # the part's (u, v) in the base face's (u, v) after `roll` quarter turns (see joints.attach)
        n = fa.normal
        t_u, t_v = fa.u_axis, tuple(-c for c in fa.v_axis)
        for _ in range(roll):
            R90 = _rotation_about(n, 1)
            t_u, t_v = mat_vec(R90, t_u), mat_vec(R90, t_v)

        def move(u, v):
            return tuple(round(u * sum(x * y for x, y in zip(t_u, ax)) + v * sum(x * y for x, y in zip(t_v, ax)))
                         for ax in (fa.u_axis, fa.v_axis))

        xs = [move(u, v)[0] for u in (lo_u, hi_u) for v in (lo_v, hi_v)]
        lo_x, hi_x = min(xs), max(xs)
        if at == "middle":
            target = length / 2 - (lo_x + hi_x) / 2 + 2 * inset
        elif _END[at] < 0:
            target = -lo_x + 2 * inset
        else:
            target = length - hi_x - 2 * inset
        found = []
        for cu, cv in product(range(int(length) + 1), range(int(2 * v_centre) + 1)):
            pairs = [((cu + move(u, v)[0], cv + move(u, v)[1]), (u, v)) for u, v in pattern]
            if all(a in free for a, _ in pairs):
                found.append((abs(cu - target) + 4 * abs(cv - v_centre), cu, cv, pairs))
        found.sort(key=lambda f: f[:3])
        for *_, pairs in found:
            pair_holes = [(free[a], part_.hole(part_.MOUNT_FACE, *b)) for a, b in pairs]
            try:
                out = attach(base, pair_holes[0][0], part_, pair_holes[0][1], also=pair_holes[1:],
                             roll=roll, pocket=part_.POCKET, **kwargs)
            except ValueError:
                continue
            out.mount_faces = base.mount_faces
            for attr in ("kind", "w", "h", "hole_count", "length", "outer_width", "flange_len"):
                if hasattr(base, attr):
                    setattr(out, attr, getattr(base, attr))
            return out
    raise ValueError(f"no free spot for {type(part_).__name__} at {at!r} on {names}")
