from solid2 import cube

from .assembly import VEXAssembly
from .holes import Face, row, staggered_row, PITCH, UNIT
from .parts import part_info


class Angle(VEXAssembly):
    """1x1 angle with `holes` square holes per leg at 0.5" pitch.

    Axes match the VEX STEP: x along the length (centred), outer corner at
    (y, z) = (CORNER_Y, CORNER_Z). The "web" leg extends along +z, the "flange" along -y.
    """

    LEG = 12.7
    T = 1.6
    CORNER_Y, CORNER_Z = 1.6, -7.56
    HOLE_LINE = 7.55  # hole line distance from the outer corner, measured from the STEP

    def __init__(self, holes=35, name="217_6484_1x1x35_Aluminum_Angle"):
        self.info = part_info(name)
        length = holes * PITCH
        x0 = -length / 2
        # first hole centre is one lattice unit (half a pitch) from the end
        web = Face("web", (x0, self.CORNER_Y - self.T / 2, self.CORNER_Z + self.HOLE_LINE),
                   (1, 0, 0), (0, 0, 1), (0, 1, 0))
        flange = Face("flange", (x0, self.CORNER_Y - self.HOLE_LINE, self.CORNER_Z + self.T / 2),
                      (1, 0, 0), (0, 1, 0), (0, 0, -1))
        self.faces = {"web": web, "flange": flange}
        self.holes = row(web, 0, 1, holes) + row(flange, 0, 1, holes)

        y_lo, z_hi = self.CORNER_Y - self.LEG, self.CORNER_Z + self.LEG
        body = (
            cube([length, self.T, self.LEG]).translate(x0, self.CORNER_Y - self.T, self.CORNER_Z)
            + cube([length, self.LEG, self.T]).translate(x0, y_lo, self.CORNER_Z)
        )
        for h in self.holes:
            body -= h.cutter(depth=self.T * 3)
        self.shape = body
        self.shape.part_info = self.info


class Channel(VEXAssembly):
    """C or U channel. Frame: x along the length (centred), web in y in [0, T] (outer face +y),
    flanges at z = +-outer_width/2 extending toward -y.

    Lattice (see holes.py): web v is the row across the web (0 = centreline); flange v = k is
    the row k half-pitches below the web's inner face. Holes exist where u + v is even.
    `web`/`flange` are the part's (w, h) in the VEX name, e.g. 1x2x1x25 C -> w=2, h=1.
    """

    T = 1.6
    # measured from the VEX STEP files; other sizes use the nominal fallback below
    PROFILES = {
        ("C", 2, 1): dict(outer_width=25.4, flange_len=12.4, line=6.04),
        ("U", 2, 2): dict(outer_width=29.0, flange_len=24.23, line=6.3),
    }

    def __init__(self, kind, w, h, holes, name=None):
        prof = self.PROFILES.get((kind, w, h), dict(outer_width=w * 12.7, flange_len=h * 12.7 - 0.3, line=6.04))
        self.info = part_info(name or "")
        self.kind, self.w, self.h = kind, w, h
        length = holes * PITCH
        x0 = -length / 2
        half = prof["outer_width"] / 2
        line = prof["line"]
        T = self.T

        web = Face("web", (x0, T / 2, 0), (1, 0, 0), (0, 0, 1), (0, 1, 0))
        # flange v = k puts the row at y = -(line + (k - 1) * UNIT)
        flange_y0 = UNIT - line
        flanges = {
            "flange_pos": Face("flange_pos", (x0, flange_y0, half - T / 2), (1, 0, 0), (0, -1, 0), (0, 0, 1)),
            "flange_neg": Face("flange_neg", (x0, flange_y0, -half + T / 2), (1, 0, 0), (0, -1, 0), (0, 0, -1)),
        }
        self.faces = {"web": web, **flanges}
        web_rows = range(-(w - 1), w)
        flange_rows = range(1, 2 * h)
        self.holes = [hh for v in web_rows for hh in staggered_row(web, v, holes)]
        for f in flanges.values():
            self.holes += [hh for k in flange_rows for hh in staggered_row(f, k, holes)]

        L = prof["flange_len"]
        self.flange_len = L
        body = cube([length, T, 2 * half]).translate(x0, 0, -half)
        for z0 in (-half, half - T):
            body += cube([length, L, T]).translate(x0, -L, z0)
        for hh in self.holes:
            body -= hh.cutter(depth=T * 3)
        self.shape = body
        self.shape.part_info = self.info


def C_Channel(w, h, holes, name=None):
    return Channel("C", w, h, holes, name)


def U_Channel(w, h, holes, name=None):
    return Channel("U", w, h, holes, name)


class ChannelFrame(VEXAssembly):
    """A pair of side rails to which front/rear C-channel crosspieces can be attached."""

    def __init__(self, left, right):
        self.left, self.right = left, right
        self.shape = left.shape + right.shape
        self.holes = list(left.holes) + list(right.holes)

    def lay_flat(self):
        """Orient the frame in the XY ground plane, with its lowest flange at z=0."""
        return self.rotate(axis="x", degrees=90).translate(z=self.left.flange_len)

    def attach(self, *args, at=None, angle=90, hardware="individual", **kwargs):
        """Attach a crosspiece by name, or use the base hole-to-hole attach API.

        `frame.attach(member, at="front", angle=90)` uses the five-hole corner pattern.
        `hardware="individual"` uses a screw and nut per hole; `"4-post"` uses one
        four-post retainer, screw, and hex nut per corner. The three-positional-argument
        form remains the low-level `VEXAssembly.attach` API.
        """
        if len(args) == 3:
            return VEXAssembly.attach(self, *args, **kwargs)
        if len(args) != 1 or at is None:
            raise TypeError("attach expects (hole, other, other_hole) or (member, at='front'|'rear')")
        if angle != 90:
            raise ValueError("C-channel crosspieces currently attach at 90 degrees")
        return self.attach_crosspiece(args[0], end=at, hardware=hardware)

    def attach_crosspiece(self, crosspiece, end, hardware="individual"):
        """Attach a front/rear crosspiece with five holes at each corner."""
        if end not in ("front", "rear"):
            raise ValueError("end must be 'front' or 'rear'")
        if hardware not in ("individual", "4-post"):
            raise ValueError("hardware must be 'individual' or '4-post'")

        left_holes = {(h.face.name, h.u, h.v): h for h in self.left.holes}
        right_holes = {(h.face.name, h.u, h.v): h for h in self.right.holes}
        rail_rows = [h.u for h in self.left.holes if h.face.name == "web" and h.v == 0]
        beam_rows = [h.u for h in crosspiece.holes if h.face.name == "web"]
        rail_end = min(rail_rows) if end == "front" else max(rail_rows)
        beam_low, beam_high = min(beam_rows), max(beam_rows)

        left_pairs = (
            ((rail_end - 1, -1), (beam_low + 2, 1)),
            ((rail_end - 1, 1), (beam_low, 1)),
            ((rail_end, 0), (beam_low + 1, 0)),
            ((rail_end + 1, -1), (beam_low + 2, -1)),
            ((rail_end + 1, 1), (beam_low, -1)),
        )
        right_pairs = (
            ((rail_end - 1, -1), (beam_high - 2, 1)),
            ((rail_end - 1, 1), (beam_high, 1)),
            ((rail_end, 0), (beam_high - 1, 0)),
            ((rail_end + 1, -1), (beam_high - 2, -1)),
            ((rail_end + 1, 1), (beam_high, -1)),
        )

        def rail_hole(holes, uv):
            return holes[("web", *uv)]

        left_anchor = rail_hole(left_holes, (rail_end, 0))
        right_anchor = rail_hole(right_holes, (rail_end, 0))
        joined = VEXAssembly.attach(
            self,
            left_anchor,
            crosspiece,
            crosspiece.hole("web", beam_low + 1, 0),
            roll=1,
            also=[
                (rail_hole(left_holes, rail_uv), crosspiece.hole("web", *beam_uv))
                for rail_uv, beam_uv in left_pairs
                if rail_uv != (rail_end, 0)
            ] + [
                (rail_hole(right_holes, rail_uv), crosspiece.hole("web", *beam_uv))
                for rail_uv, beam_uv in right_pairs
            ],
            fasteners=hardware == "individual",
        )
        if hardware == "4-post":
            from .joints import four_post_hardware

            for anchor in (left_anchor, right_anchor):
                for item in four_post_hardware(anchor):
                    joined.shape += item
        self.shape, self.holes, self.taken = joined.shape, joined.holes, joined.taken
        return self
