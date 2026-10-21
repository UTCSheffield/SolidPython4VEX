"""Joining parts at holes, with the fasteners chosen automatically.

attach(a, hole_a, b, hole_b) moves `b` so its hole lines up with `hole_a` (walls in contact),
then adds a screw and nut at every paired hole. Screw length comes from the stack thickness.
Fasteners are drawn as plain smooth shapes and every nut looks the same; the BOM and
instructions carry the real SKUs (default nut: nylock).
"""
import math
import re
from collections import namedtuple

from solid2 import cylinder, import_stl, multmatrix

from .assembly import VEXAssembly
from .holes import columns, mat_mul, mat_vec, transpose, INCH
from .parts import CATALOG, PARTS_DIR, part_info

SCREW_D = 0.164 * INCH
HEAD_D, HEAD_H = 6.3, 2.0
THREAD_PROTRUSION = 0.8  # mm of screw that should show past the nut

Nut = namedtuple("Nut", "sku thickness")
NUTS = {
    "hex": Nut("275-1028", 3.2),
    "nylock": Nut("275-1027", 6.35),
    "keps": Nut("275-1026", 3.4),
    "low_profile": Nut("276-7767", 2.4),
}
RETAINER_SKU = "276-6482"  # 1-post hex nut retainer, holds a hex nut

_SCREW_NAME = re.compile(r"8_32_x_([\d_]+)_Star_Drive_Screw$")


def _inches(text):
    a, *b = text.split("_")
    if not b:
        return float(a)
    return float(f"{a}.{b[0]}") if len(b[0]) == 3 else int(a) / int(b[0])


def _by_sku(sku):
    return next(p for p in CATALOG.values() if p.sku == sku)


def screw_table():
    """{length_in: PartInfo} for the 8-32 star drive screws in the catalog."""
    table = {}
    for info in CATALOG.values():
        m = _SCREW_NAME.search(info.name)
        if m:
            table[_inches(m.group(1))] = info
    return table


def choose_screw(stack_mm, nut_mm):
    need = (stack_mm + nut_mm + THREAD_PROTRUSION) / INCH
    table = screw_table()
    fits = [length for length in table if length >= need - 1e-6]
    if not fits:
        raise ValueError(f"No 8-32 screw long enough for a {stack_mm:.1f} mm stack")
    length = min(fits)
    return length, table[length]


def _place(shape, origin, z_axis):
    """Move shape built along +z so +z points along z_axis, at origin."""
    ref = (1.0, 0.0, 0.0) if abs(z_axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    x = _norm(_cross(ref, z_axis))
    y = _cross(z_axis, x)
    R = columns(x, y, z_axis)
    return multmatrix([[*R[i], origin[i]] for i in range(3)] + [[0, 0, 0, 1]])(shape)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(v):
    n = math.sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def _tag(shape, info):
    shape.part_info = info
    return shape


def screw_shape(info, length_mm, z_from, z_to):
    """Screw along +z: head on z_to, tip at z_from."""
    body = cylinder(d=SCREW_D, h=length_mm, _fn=16).translate(0, 0, z_to - length_mm)
    head = cylinder(d=HEAD_D, h=HEAD_H, _fn=20).translate(0, 0, z_to)
    return _tag(body + head, info)


NUT_DRAWN_H = 3.2  # every nut is drawn the same, whatever the real type


def nut_shape(info, z_top):
    return _tag(cylinder(r=5.0, h=NUT_DRAWN_H, _fn=6).translate(0, 0, z_top - NUT_DRAWN_H), info)


def _rotation_about(axis, quarter_turns):
    c, s = [(1, 0), (0, 1), (-1, 0), (0, -1)][quarter_turns % 4]
    x, y, z = axis
    return (
        (c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s),
        (y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s),
        (z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)),
    )


def attach(a, hole_a, b, hole_b, *, also=(), side="outer", roll=0, nut="nylock", retainer=False,
           screw=None, fasteners=True):
    """Return a new assembly: `b` joined to `a` at hole_a/hole_b.

    side    "outer": b sits on the outward face of hole_a's wall; "inner": inside it.
    roll    quarter turns of b about the hole normal.
    also    more (hole_on_a, hole_on_b) pairs; they must line up with the first pair.
    nut     key of NUTS, or None for no nut. retainer=True adds a nut retainer per hole.
    screw   a catalog screw length in inches; default is chosen from the stack thickness.
    fasteners  False places the parts only, so you can add hardware yourself.
    """
    fa, fb = hole_a.face, hole_b.face
    for ha, hb in [(hole_a, hole_b), *also]:
        if ha.size_class != hb.size_class:
            raise ValueError(f"cannot join a {ha.kind} hole to a {hb.kind} hole ({ha.size_class} vs {hb.size_class})")
    # axle holes are coaxial: no wall contact and no screws; the shaft station sets the position
    axle = hole_a.is_axle
    if axle:
        fasteners = False
    s = 1 if side == "outer" else -1
    n = tuple(s * c for c in fa.normal)
    # right-handed target frame for b's (u, v, -normal) frame
    t_u, t_v = fa.u_axis, tuple(-s * c for c in fa.v_axis)
    for _ in range(roll % 4):
        R90 = _rotation_about(n, 1)
        t_u, t_v = mat_vec(R90, t_u), mat_vec(R90, t_v)
    target = columns(t_u, t_v, n)
    source = columns(fb.u_axis, fb.v_axis, tuple(-c for c in fb.normal))
    R = mat_mul(target, transpose(source))
    gap = 0 if axle else (fa.thickness + fb.thickness) / 2
    pb = mat_vec(R, hole_b.position)
    t = tuple(pa + gap * nc - c for pa, nc, c in zip(hole_a.position, n, pb))

    pairs = [(hole_a, hole_b), *also]
    moved = {hb: hb.transformed(R, t) for _, hb in pairs}
    for ha, hb in pairs:
        if ha in a.taken or hb in b.taken:
            raise ValueError(f"hole already used: {ha if ha in a.taken else hb}")
        d = [x - y for x, y in zip(ha.position, moved[hb].position)]
        along = sum(x * c for x, c in zip(d, n))
        err = math.dist(d, [along * c for c in n])  # in-plane error; the wall gap is expected
        if err > 0.3:
            raise ValueError(f"holes do not line up ({err:.2f} mm apart): {ha} / {hb}")

    parts = [a.shape, multmatrix([[*R[i], t[i]] for i in range(3)] + [[0, 0, 0, 1]])(b.shape)]
    if fasteners:
        stack = fa.thickness + fb.thickness
        nut_t = NUTS[nut].thickness if nut else 0
        length_in, screw_info = choose_screw(stack, nut_t) if screw is None else (screw, screw_table()[screw])
        length = length_in * INCH
        for ha, _ in pairs:
            parts += _hardware(ha, n, stack, fa.thickness, length, screw_info, nut, retainer)

    shape = parts[0]
    for p in parts[1:]:
        shape = shape + p
    out = VEXAssembly()
    out.shape = shape
    out.holes = list(a.holes) + [h.transformed(R, t) for h in b.holes]
    used = {ha for ha, _ in pairs} | {moved[hb] for _, hb in pairs}
    out.taken = set(a.taken) | {h.transformed(R, t) for h in b.taken} | used
    return out


def _hardware(hole, n, stack, wall_a, length, screw_info, nut, retainer):
    """Screw head on the far side of b, nut on the far side of a. z runs along n from a's mid-plane."""
    base = tuple(hole.position)
    head_z = wall_a / 2 + (stack - wall_a)
    nut_info = part_info_for(NUTS[nut].sku) if nut else None
    items = [_place(screw_shape(screw_info, length, head_z - length, head_z), base, n)]
    if nut:
        items.append(_place(nut_shape(nut_info, -wall_a / 2), base, n))
    if retainer:
        items.append(_place(_tag(cylinder(d=9, h=1, _fn=6).translate(0, 0, -wall_a / 2 - 1), _by_sku(RETAINER_SKU)), base, n))
    return items


def four_post_hardware(hole):
    """One screw, one hex nut, and a catalog four-post retainer for a 2-1-2 joint."""
    stack = 2 * hole.face.thickness
    length_in, screw_info = choose_screw(stack, NUTS["hex"].thickness)
    n = hole.normal
    items = _hardware(
        hole, n, stack, hole.face.thickness, length_in * INCH, screw_info, "hex", False
    )

    retainer_info = _by_sku("276-6483")
    retainer = import_stl(str(PARTS_DIR / "stl" / f"{retainer_info.name}.stl"))
    retainer.part_info = retainer_info
    frame = columns(hole.face.u_axis, n, hole.face.v_axis)
    # the retainer's plate sits against the metal and its 3.17 mm posts go up into the holes
    offset = tuple(
        p + axis * (-hole.face.thickness / 2)
        for p, axis in zip(hole.position, n)
    )
    matrix = [[*frame[i], offset[i]] for i in range(3)] + [[0, 0, 0, 1]]
    items.append(multmatrix(matrix)(retainer))
    return items


def part_info_for(sku):
    return _by_sku(sku)
