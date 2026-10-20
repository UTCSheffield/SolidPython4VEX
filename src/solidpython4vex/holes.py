"""Integer hole lattice for VEX structure parts.

Hole positions are integer (u, v) coordinates on a face, in UNIT steps. UNIT is half the
0.5" hole pitch, so the half-pitch-staggered rows of channels are plain integers
(a 0.5" pitch is a step of 2 in u).
"""
from dataclasses import dataclass

from solid2 import cube, cylinder

INCH = 25.4
UNIT = 0.25 * INCH
PITCH = 2 * UNIT
SQUARE_HOLE = 0.182 * INCH
ROUND_HOLE = 4.2  # mounting holes in gears and sprockets


def mat_vec(R, v):
    return tuple(sum(R[i][j] * v[j] for j in range(3)) for i in range(3))


def mat_mul(A, B):
    return tuple(tuple(sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def columns(c0, c1, c2):
    """3x3 matrix whose columns are the given vectors."""
    return tuple(tuple(c[i] for c in (c0, c1, c2)) for i in range(3))


def transpose(R):
    return tuple(tuple(R[j][i] for j in range(3)) for i in range(3))


@dataclass(frozen=True)
class Face:
    """A planar face with a local frame; `origin` is the (u, v) = (0, 0) point in part space.

    (u_axis, v_axis, -normal) is a right-handed frame; `normal` points out of the material.
    """

    name: str
    origin: tuple
    u_axis: tuple
    v_axis: tuple
    normal: tuple
    thickness: float = 1.6  # wall thickness; the origin lies on the wall's mid-plane

    def transformed(self, R, t):
        """This face after the rigid transform p -> R p + t."""
        return Face(
            self.name,
            tuple(a + b for a, b in zip(mat_vec(R, self.origin), t)),
            mat_vec(R, self.u_axis),
            mat_vec(R, self.v_axis),
            mat_vec(R, self.normal),
            self.thickness,
        )

    def point(self, u, v):
        return tuple(
            o + u * UNIT * a + v * UNIT * b
            for o, a, b in zip(self.origin, self.u_axis, self.v_axis)
        )


@dataclass(frozen=True)
class Hole:
    face: Face
    u: float  # integer on channels; gears and sprockets may use fractions of UNIT
    v: float
    kind: str = "square"  # or "round"

    @property
    def position(self):
        return self.face.point(self.u, self.v)

    @property
    def normal(self):
        return self.face.normal

    def transformed(self, R, t):
        return Hole(self.face.transformed(R, t), self.u, self.v, self.kind)

    def cutter(self, depth=10, size=None):
        """Cube (square hole) or cylinder (round hole) centred on the hole, long along the face normal."""
        if self.kind == "round":
            axis = max(range(3), key=lambda i: abs(self.normal[i]))
            rot = {0: (0, 90, 0), 1: (-90, 0, 0), 2: (0, 0, 0)}[axis]
            return cylinder(d=size or ROUND_HOLE, h=depth, center=True, _fn=24).rotate(rot).translate(self.position)
        size = size or SQUARE_HOLE
        dims = [size if abs(n) == 0 else depth for n in self.normal]
        return cube(dims, center=True).translate(self.position)


def row(face, v, first_u, count, step=2):
    """`count` holes along u on line v, `step` lattice units apart (2 = one 0.5" pitch)."""
    return [Hole(face, first_u + i * step, v) for i in range(count)]


def staggered_row(face, v, pitches):
    """Holes on lattice line v of a face `pitches` long: only u + v even exist,
    so odd lines start half a pitch in and even lines are offset by half a pitch."""
    return [Hole(face, u, v) for u in range(2 - v % 2, 2 * pitches, 2)]
