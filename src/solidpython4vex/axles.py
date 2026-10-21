"""Shafts and the parts that ride on them, with typed axle holes.

Every part is built with its axle along z, centred on the origin. A part's `axle` hole is
"axle_square" (wheel, shaft) or "axle_round" (bearing block, collar, spacer); all of these here are
standard 1/8" size (class "axle"). `Shaft.at(mm)` is a place on the shaft, measured from its free
end, where `shaft.attach(shaft.at(mm), part, part.axle)` puts a part coaxially.
"""
from .assembly import VEXAssembly
from .holes import Face, Hole, INCH
from .parts import CATALOG, nominal_inches, part, part_info


def _axle_face(name, width):
    # (u, v, -normal) = (x, y, z) is right-handed
    return Face(name, (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, -1), width)


class Shaft(VEXAssembly):
    """Capped 1/8" shaft along +z from z=0 (free end) to its cap.

    `Shaft(4)` is the 4" shaft; the lengths come from the catalog (1" to 6" in half-inch steps).
    """

    CAP = 0.8
    SHORT = 0.98  # the STEP models are this much shorter than the nominal length
    _NAMES = {
        nominal_inches(name): name for name, info in CATALOG.items() if "Capped Shaft" in info.description
    }

    @classmethod
    def length_of(cls, inches):
        """Length in mm from the free end to the outside of the cap."""
        return inches * INCH - cls.SHORT

    def __init__(self, inches=4):
        if inches not in self._NAMES:
            raise ValueError(f"no {inches} inch capped shaft; choose from {sorted(self._NAMES)}")
        self.inches = inches
        self.info = part_info(self._NAMES[inches])
        self.LENGTH = self.length_of(inches)
        self.shape = part(self._NAMES[inches]).translate(0, 0, self.LENGTH - self.CAP)  # STEP origin is at the cap end
        self.holes = ()

    def at(self, mm, kind="axle_square"):
        """A coaxial mounting position `mm` from the free end of the shaft."""
        if not 0 <= mm <= self.LENGTH:
            raise ValueError(f"{mm} mm is off the end of the {self.LENGTH} mm shaft")
        face = Face(f"axle@{mm:g}", (0, 0, mm), (1, 0, 0), (0, 1, 0), (0, 0, -1), 0)
        return Hole(face, 0, 0, kind)


class _AxlePart(VEXAssembly):
    NAME = ""
    WIDTH = 0.0  # along the axle
    KIND = "axle_round"
    AXLE_ALONG_Y = True  # the STEP model has its axle along y

    def __init__(self):
        shape = part(self.NAME)
        self.shape = shape.rotate((90, 0, 0)) if self.AXLE_ALONG_Y else shape
        self.axle = Hole(_axle_face("axle", self.WIDTH), 0, 0, self.KIND)
        self.holes = [self.axle]


class Omni_Wheel_4in(_AxlePart):
    """4" anti-static omni wheel with a square axle hole."""

    NAME = "276_8107_4_320mm_Travel_Omni_Directional_Anti_Static_Wheel"
    WIDTH = 25.04
    KIND = "axle_square"
    DIAMETER = 101.6


class Shaft_Collar(_AxlePart):
    NAME = "228_3510_Rubber_Shaft_Collar"
    WIDTH = 6.35


class Nylon_Spacer_1_8in(_AxlePart):
    NAME = "275_1066_001_1_8_Nylon_Spacer"
    WIDTH = nominal_inches(NAME) * INCH


class Nylon_Spacer_1_4in(Nylon_Spacer_1_8in):
    NAME = "275_1066_002_1_4_Nylon_Spacer"
    WIDTH = nominal_inches(NAME) * INCH


class Nylon_Spacer_3_8in(Nylon_Spacer_1_8in):
    NAME = "275_1066_003_3_8_Nylon_Spacer"
    WIDTH = nominal_inches(NAME) * INCH


class Nylon_Spacer_1_2in(Nylon_Spacer_1_8in):
    NAME = "275_1066_004_1_2_Nylon_Spacer"
    WIDTH = nominal_inches(NAME) * INCH


class Bearing_Block(VEXAssembly):
    """Pillow block bearing: a 35.6 x 10.2 mm plate with a hub, axle along the hub (+z).

    The plate's flat base lies on z=0 and the hub sticks up 12.7 mm. Two base holes sit one grid
    pitch either side of the bore: `hole("base", -2, 0)` and `hole("base", 2, 0)`, so the block
    bolts flat onto any row of three adjacent holes (a U-channel flange's middle row, or a web).
    `.axle` is the round axle hole at the bore, normal pointing out along the hub.
    """

    NAME = "276_2016_001_Bearing_Blocks"
    HUB = 12.7  # base plane to the top of the hub
    THICKNESS = 3.17  # the plate
    KIND = "axle_round"

    def __init__(self):
        self.info = part_info(self.NAME)
        self.shape = part(self.NAME).translate(76.25, 0.73, 0)  # bore on the z axis, base on z=0
        self.axle = Hole(Face("axle", (0, 0, 0), (1, 0, 0), (0, -1, 0), (0, 0, 1), 0), 0, 0, self.KIND)
        base = Face("base", (0, 0, self.THICKNESS / 2), (1, 0, 0), (0, 1, 0), (0, 0, -1), self.THICKNESS)
        self.holes = [self.axle, Hole(base, -2, 0, "round"), Hole(base, 2, 0, "round")]


class Bearing_Flat(VEXAssembly):
    """Flat bearing (276-1209): a 35.6 x 10.2 mm plate with three holes on the 0.5" grid.

    The middle hole is the round axle bore and the outer two are mounting holes. A raised ring
    around each hole stands 2 mm proud of the plate and goes against the structure, so the flat
    plate is on the far side. The ring tops lie on z=0 and the plate's far face is at z=6.35.
    The holes are `hole("base", -2, 0)` and `hole("base", 2, 0)` (mounting) and `.axle` (bore,
    normal +z, away from the structure), the same layout as `Bearing_Block`, so either can be
    bolted on a row of three adjacent holes.
    """

    NAME = "276_1209_Flat_Bearing"
    THICKNESS = 6.35  # ring tops to the far face of the plate
    KIND = "axle_round"

    def __init__(self):
        from solid2 import multmatrix

        self.info = part_info(self.NAME)
        # STEP axis is x, long side y: re-axis so the bore is the z axis and the ring tops are z=0
        shape = part(self.NAME).translate(-82.626, -26.416, 12.7)
        self.shape = multmatrix([[0, 1, 0, 0], [0, 0, -1, 0], [-1, 0, 0, self.THICKNESS], [0, 0, 0, 1]])(shape)
        self.axle = Hole(Face("axle", (0, 0, 0), (1, 0, 0), (0, -1, 0), (0, 0, 1), 0), 0, 0, self.KIND)
        base = Face("base", (0, 0, self.THICKNESS / 2), (1, 0, 0), (0, 1, 0), (0, 0, -1), self.THICKNESS)
        self.holes = [self.axle, Hole(base, -2, 0, "round"), Hole(base, 2, 0, "round")]
