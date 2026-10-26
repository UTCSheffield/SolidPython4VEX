from solid2 import cube

from .assembly import VEXAssembly
from .holes import Face, Hole, row, staggered_row, PITCH, UNIT
from .parts import part_info, tint


class Plate_5x25_Steel(VEXAssembly):
    """5x25 steel plate (275-1140): 25 holes long (x), 5 wide (z), 1.2 mm thick (y in [0, T]).

    Holes sit at odd (u, v) on both faces: "plate_top" (normal +y) and "plate_bottom" (normal -y).
    The same physical hole is (u, v) on the top face and (u, 10 - v) on the bottom face.
    """

    T = 1.2
    NAME = "275_1140_5x25_Steel_Plate"
    LENGTH_HOLES, WIDTH_HOLES = 25, 5

    def __init__(self):
        self.info = part_info(self.NAME)
        length, width = self.LENGTH_HOLES * 2 * UNIT, self.WIDTH_HOLES * 2 * UNIT
        self.length, self.width = length, width
        x0, z0 = -length / 2, -width / 2
        top = Face("plate_top", (x0, self.T / 2, z0), (1, 0, 0), (0, 0, 1), (0, 1, 0), self.T)
        bottom = Face("plate_bottom", (x0, self.T / 2, -z0), (1, 0, 0), (0, 0, -1), (0, -1, 0), self.T)
        self.faces = {"plate_top": top, "plate_bottom": bottom}
        self.mount_faces = {"plate_top": (2 * self.LENGTH_HOLES, self.WIDTH_HOLES)}
        us = range(1, 2 * self.LENGTH_HOLES, 2)
        vs = range(1, 2 * self.WIDTH_HOLES, 2)
        self.holes = [Hole(f, u, v) for f in (top, bottom) for u in us for v in vs]
        body = cube([length, self.T, width]).translate(x0, 0, z0)
        for h in self.holes[: len(us) * len(vs)]:
            body -= h.cutter(depth=self.T * 3)
        self.shape = tint(body, self.info)


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
        self.shape = tint(self.shape, self.info)


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
        self.hole_count = holes
        self.length = length
        x0 = -length / 2
        half = prof["outer_width"] / 2
        self.outer_width = prof["outer_width"]
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
        self.shape = tint(self.shape, self.info)


def C_Channel(w, h, holes, name=None):
    return Channel("C", w, h, holes, name)


def U_Channel(w, h, holes, name=None):
    return Channel("U", w, h, holes, name)


class _CatalogChannel(Channel):
    kind = ""
    width = 0
    height = 0
    holes_count = 0
    part_name = ""

    def __init__(self):
        super().__init__(
            self.kind, self.width, self.height, self.holes_count, self.part_name
        )


class C_Channel_1x2x1x25_Aluminum(_CatalogChannel):
    kind, width, height, holes_count = "C", 2, 1, 25
    part_name = "276_2288_1x2x1x25_Aluminum_C_Channel"


class C_Channel_1x2x1x35_Aluminum(_CatalogChannel):
    kind, width, height, holes_count = "C", 2, 1, 35
    part_name = "276_2289_1x2x1x35_Aluminum_C_Channel"


class C_Channel_1x2x1x35_Steel(_CatalogChannel):
    kind, width, height, holes_count = "C", 2, 1, 35
    part_name = "276_2906_1x2x1x35_Steel_C_Channel"


class C_Channel_1x3x1x35_Aluminum(_CatalogChannel):
    kind, width, height, holes_count = "C", 3, 1, 35
    part_name = "276_4359_1x3x1x35_Aluminum_C_Channel"


class C_Channel_1x5x1x25_Aluminum(_CatalogChannel):
    kind, width, height, holes_count = "C", 5, 1, 25
    part_name = "276_2290_1x5x1x25_Aluminum_C_Channel"


class C_Channel_1x5x1x25_Steel(_CatalogChannel):
    kind, width, height, holes_count = "C", 5, 1, 25
    part_name = "275_1138_1x5x1x25_Steel_C_Channel"


class C_Channel_1x5x1x35_Aluminum(_CatalogChannel):
    kind, width, height, holes_count = "C", 5, 1, 35
    part_name = "276_2298_1x5x1x35_Aluminum_C_Channel"


class C_Channel_1x5x1x35_Steel(_CatalogChannel):
    kind, width, height, holes_count = "C", 5, 1, 35
    part_name = "275_1139_1x5x1x35_Steel_C_Channel"


class U_Channel_2x2x2x20_Aluminum(_CatalogChannel):
    kind, width, height, holes_count = "U", 2, 2, 20
    part_name = "276_7285_U_Channel_2x2x2x20"


class ChannelFrame(VEXAssembly):
    """A pair of side rails to which front/rear C-channel crosspieces can be attached."""

    def __init__(self, left, right=None):
        self._automatic_spacing = right is None
        self._crosspiece_spacing = None
        if right is None:
            spacing = left.length - left.outer_width
            right = left.mirror(axis="z", at=-spacing / 2)
        self.left, self.right = left, right
        self.shape = left.shape + right.shape
        self.holes = list(left.holes) + list(right.holes)

    def lay_flat(self):
        """Lay the frame on its lowest flange, leaving channel webs facing up.

        For U-channels used as rails, this puts the flat web on top and the open
        side toward the ground.
        """
        return self.rotate(axis="x", degrees=90).translate(z=self.left.flange_len)

    def attach_deck(self, deck, at="middle", inset=0, hardware="screw", rows=3, shift=0):
        """Bolt a plate across both rails, `rows` screws per rail on the rail web's centre row.

        `at` is "middle", "front" or "rear" along the rails and `inset` slides it in pitches.
        `shift` slides the plate along the rails by that many hole columns of one pitch (0.5"), +/-1, the sign picks which edge it moves toward.
        The plate's two long ends meet the rails, so its length must match the rail spacing.
        """
        from .electronics import free_holes

        webs = [h for h in self.holes if h.face.name == "web" and h.normal[1] > 0.9 and h not in self.taken]
        zs = [h.position[2] for h in webs]
        if not webs or max(zs) - min(zs) < 1:
            raise ValueError("expected two rails with free web holes")
        # screw through each rail's outermost hole row so the plate ends sit flush with the rail edges
        edge = {"hi": max(zs), "lo": min(zs)}
        rails = [sorted((h for h in webs if abs(h.position[2] - z) < 0.5), key=lambda h: h.position[0])
                 for z in (edge["hi"], edge["lo"])]
        spacing = round(abs(edge["hi"] - edge["lo"]) / UNIT)
        xs = [h.position[0] for h in rails[0]]
        target = {"front": xs[0], "middle": sum(xs) / 2, "rear": xs[-1]}[at] + inset * PITCH * (1 if at != "rear" else -1)
        start = min(range(len(xs) - rows + 1), key=lambda i: abs(sum(xs[i:i + rows]) / rows - target))
        bottom = free_holes(deck, "plate_bottom")
        mid = max(v for _, v in bottom) // 2 + 1
        v_rows = [mid + 2 * shift + 2 * (k - rows // 2) for k in range(rows)]
        ends = sorted({u for u, _ in bottom})
        u1 = min((u for u in ends if u + spacing in ends), key=lambda u: abs(2 * u + spacing - (ends[-1] + 1)))
        for flip in (False, True):
            for rev in (False, True):
                ra, rb = (rails[1], rails[0]) if flip else (rails[0], rails[1])
                rv = v_rows[::-1] if rev else v_rows
                pairs = [(h, bottom[(u, v)]) for rail, u in ((ra, u1), (rb, u1 + spacing))
                         for h, v in zip(rail[start:start + rows], rv)]
                for roll in range(4):
                    try:
                        joined = VEXAssembly.attach(self, pairs[0][0], deck, pairs[0][1], also=pairs[1:], roll=roll)
                    except ValueError:
                        continue
                    self.shape, self.holes, self.taken = joined.shape, joined.holes, joined.taken
                    return self
        raise ValueError("the plate does not line up with the rail holes")

    def attach(self, *args, at=None, angle=90, hardware="individual", **kwargs):
        """Attach a crosspiece by name, or use the base hole-to-hole attach API.

        `frame.attach(member, at="front", angle=90)` uses the five-hole corner pattern.
        `hardware="individual"` uses a screw and nut per hole; `"4-post"` uses one
        four-post retainer, screw, and hex nut per corner. The three-positional-argument
        form remains the low-level `VEXAssembly.attach` API.
        """
        if len(args) == 3:
            return VEXAssembly.attach(self, *args, **kwargs)
        if len(args) == 1 and any(h.face.name == "plate_bottom" for h in args[0].holes):
            return self.attach_deck(args[0], at=at or "middle", **{"hardware": hardware, **kwargs})
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

        spacing = crosspiece.length - 2 * PITCH
        if spacing <= 0:
            raise ValueError("crosspiece is too short to span the side rails")
        if self._automatic_spacing:
            if self._crosspiece_spacing is not None and abs(spacing - self._crosspiece_spacing) > 0.3:
                raise ValueError("front and rear crosspieces must have matching lengths")
            if self._crosspiece_spacing is None:
                self.right = self.left.mirror(axis="z", at=-spacing / 2)
                self.shape = self.left.shape + self.right.shape
                self.holes = list(self.left.holes) + list(self.right.holes)
                self._crosspiece_spacing = spacing

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
