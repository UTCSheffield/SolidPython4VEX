from collections import Counter
import math
import os
from pathlib import Path
import re


_SCAD_IMPORT = re.compile(r'(?P<prefix>\bimport\s*\(\s*file\s*=\s*")(?P<path>[^"]+)(?P<suffix>")')


def _walk_parts(node):
    """Yield part_info for every part occurrence (shared nodes count each use)."""
    if node.__dict__.get("part_info") is not None:
        yield node.__dict__["part_info"]
    for child in getattr(node, "_children", ()):
        yield from _walk_parts(child)


class VEXAssembly:
    """Base class for assemblies; subclasses set self.shape."""

    shape = None
    holes = ()
    _taken = None

    @property
    def taken(self):
        if self._taken is None:
            self._taken = set()
        return self._taken

    @taken.setter
    def taken(self, value):
        self._taken = value

    def hole(self, face, u, v):
        return next(h for h in self.holes if h.face.name == face and h.u == u and h.v == v)

    mount_faces = {}

    def attach(self, *args, at=None, **kwargs):
        """Join `other` to this assembly with fasteners.

        `attach(hole, other, other_hole, ...)` is the hole-to-hole form (see joints.attach);
        `attach(part, at="middle", inset=0, hardware="screw")` finds the holes itself
        (see electronics.mount).
        """
        if len(args) == 1:
            from .electronics import mount

            return mount(self, args[0], at=at or "middle", **kwargs)
        from .joints import attach

        return attach(self, *args, **kwargs)

    def dead_wheel(self, at="rear", side="outboard", rail=None, inset=1):
        """Return this U channel or laid-flat frame with a 4" omni dead wheel on a rail (see motion.py)."""
        from .motion import place_dead_wheel_near_rear

        if at != "rear":
            raise ValueError("dead wheels can currently only be placed at the 'rear'")
        wheeled = place_dead_wheel_near_rear(self, inset=inset, side=side, rail=rail)
        # keep the channel's size attributes so the result can still go into a ChannelFrame
        for name in ("kind", "w", "h", "hole_count", "length", "outer_width", "flange_len"):
            if hasattr(self, name):
                setattr(wheeled, name, getattr(self, name))
        return wheeled

    def motor_wheel(self, at="front", side="outboard", rail=None, motor_gearing="blue", inset=0):
        """Return this U channel or laid-flat frame with a motor-driven 4" wheel on a rail (see motion.py)."""
        from .motion import place_motor_wheel

        wheeled = place_motor_wheel(self, at=at, side=side, rail=rail, motor_gearing=motor_gearing, inset=inset)
        for name in ("kind", "w", "h", "hole_count", "length", "outer_width", "flange_len"):
            if hasattr(self, name):
                setattr(wheeled, name, getattr(self, name))
        return wheeled

    def add(self, other):
        """Return a new assembly containing this assembly and `other`."""
        combined = VEXAssembly()
        combined.shape = self.shape + other.shape
        combined.holes = list(self.holes) + list(other.holes)
        combined.taken = set(self.taken) | set(other.taken)
        return combined

    def mirror(self, axis="x", at=0):
        """Return this assembly reflected across the plane `axis = at`, including its holes."""
        from solid2 import multmatrix

        if axis not in ("x", "y", "z"):
            raise ValueError("axis must be 'x', 'y', or 'z'")
        index = "xyz".index(axis)
        reflection = tuple(
            tuple(-1 if i == j == index else int(i == j) for j in range(3))
            for i in range(3)
        )
        offset = tuple(2 * at if i == index else 0 for i in range(3))
        transform = multmatrix(
            [[*reflection[i], offset[i]] for i in range(3)] + [[0, 0, 0, 1]]
        )(self.shape)

        mirrored = VEXAssembly()
        mirrored.shape = transform
        mirrored.holes = [hole.transformed(reflection, offset) for hole in self.holes]
        mirrored.taken = {hole.transformed(reflection, offset) for hole in self.taken}
        return mirrored

    def translate(self, x=0, y=0, z=0):
        """Return this assembly shifted by `(x, y, z)`, including its holes."""
        from solid2 import multmatrix

        offset = (x, y, z)
        identity = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        moved = VEXAssembly()
        moved.shape = multmatrix(
            [[*identity[i], offset[i]] for i in range(3)] + [[0, 0, 0, 1]]
        )(self.shape)
        moved.holes = [hole.transformed(identity, offset) for hole in self.holes]
        moved.taken = {hole.transformed(identity, offset) for hole in self.taken}
        return moved

    def rotate(self, axis="z", degrees=90, around=(0, 0, 0)):
        """Return this assembly rotated about an axis through `around`, including its holes."""
        from solid2 import multmatrix

        from .holes import mat_vec

        if axis not in ("x", "y", "z"):
            raise ValueError("axis must be 'x', 'y', or 'z'")
        angle = math.radians(degrees)
        c, s = math.cos(angle), math.sin(angle)
        rotations = {
            "x": ((1, 0, 0), (0, c, -s), (0, s, c)),
            "y": ((c, 0, s), (0, 1, 0), (-s, 0, c)),
            "z": ((c, -s, 0), (s, c, 0), (0, 0, 1)),
        }
        rotation = rotations[axis]
        rotated_origin = mat_vec(rotation, around)
        offset = tuple(a - b for a, b in zip(around, rotated_origin))
        moved = VEXAssembly()
        moved.shape = multmatrix(
            [[*rotation[i], offset[i]] for i in range(3)] + [[0, 0, 0, 1]]
        )(self.shape)
        moved.holes = [hole.transformed(rotation, offset) for hole in self.holes]
        moved.taken = {hole.transformed(rotation, offset) for hole in self.taken}
        return moved

    def render(self, path):
        target = Path(path)
        scad = self.shape.as_scad()

        def relative_import(match):
            source = Path(match.group("path"))
            if not source.is_absolute():
                return match.group(0)
            if not source.is_file():
                raise FileNotFoundError(f"SCAD import file does not exist: {source}")
            relative = os.path.relpath(source, target.parent.resolve()).replace(os.sep, "/")
            return f'{match.group("prefix")}{relative}{match.group("suffix")}'

        target.write_text(_SCAD_IMPORT.sub(relative_import, scad))

    def bom(self):
        """Return [(PartInfo, quantity)] sorted by part name."""
        counts = Counter(_walk_parts(self.shape))
        return sorted(counts.items(), key=lambda kv: kv[0].name)

    def bom_total(self):
        """Total price of priced parts; unpriced parts are ignored."""
        return sum(p.price * q for p, q in self.bom() if p.price is not None)

    def bom_csv(self):
        rows = ["sku,name,quantity,unit_price,line_total"]
        for p, q in self.bom():
            unit = "" if p.price is None else f"{p.price:.2f}"
            total = "" if p.price is None else f"{p.price * q:.2f}"
            rows.append(f"{p.sku},{p.name},{q},{unit},{total}")
        return "\n".join(rows)
