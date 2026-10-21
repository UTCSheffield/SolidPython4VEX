"""Shafts and the parts that ride on them, with typed axle holes.

Every part is built with its axle along z, centred on the origin. A part's `axle` hole is
"axle_square" (wheel, shaft) or "axle_round" (bearing block, collar, spacer); most here are
standard 1/8" size (class "axle"); `HS_Shaft` and the gears and sprockets in `Disc` use the 1/4" size. `Shaft.at(mm)` is a place on the shaft, measured from its free
end, where `shaft.attach(shaft.at(mm), part, part.axle)` puts a part coaxially.
"""
import re
from .assembly import VEXAssembly
from .holes import Face, Hole, INCH, PITCH
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


class HS_Shaft(Shaft):
    """Uncapped 1/4" high-strength shaft along +z from z=0 (one end) to its other end.

    `HS_Shaft(4)` is the 4" shaft; the catalog has 2", 3", 4" and 24".
    """

    CAP = 0.0
    _NAMES = {
        int(name.split("_")[2]): name for name in CATALOG if re.fullmatch(r"276_\d+_\d+_High_Strength_Shaft", name)
    }

    @classmethod
    def length_of(cls, inches):
        return inches * INCH - (0 if inches == 24 else 1.0)  # the STEP models are 1 mm short, except the 24"

    def __init__(self, inches=4):
        if inches not in self._NAMES:
            raise ValueError(f"no {inches} inch high-strength shaft; choose from {sorted(self._NAMES)}")
        self.inches = inches
        self.info = part_info(self._NAMES[inches])
        self.LENGTH = self.length_of(inches)
        shape = part(self._NAMES[inches])
        self.shape = shape.translate(0, 0, self.LENGTH / 2) if inches == 24 else shape  # the 24" is centred
        self.holes = ()

    def at(self, mm, kind="hs_axle_square"):
        return super().at(mm, kind)


class _AxlePart(VEXAssembly):
    NAME = ""
    WIDTH = 0.0  # along the axle
    KIND = "axle_round"
    AXLE_ALONG_Y = True  # the STEP model has its axle along y
    AXLE_ALONG_X = False  # or along x (when neither is set the axle is along z)
    CENTRE = None  # where the axle crosses the middle of the part in the STEP model, if not the origin

    def __init__(self):
        shape = part(self.NAME)
        if self.CENTRE:
            shape = shape.translate(*(-c for c in self.CENTRE))
        if self.AXLE_ALONG_X:
            shape = shape.rotate((0, -90, 0))
        elif self.AXLE_ALONG_Y:
            shape = shape.rotate((90, 0, 0))
        self.shape = shape
        self.axle = Hole(_axle_face("axle", self.WIDTH), 0, 0, self.KIND)
        self.holes = [self.axle]


class Omni_Wheel_4in(_AxlePart):
    """4" anti-static omni wheel with a square axle hole."""

    NAME = "276_8107_4_320mm_Travel_Omni_Directional_Anti_Static_Wheel"
    WIDTH = 25.04
    KIND = "axle_square"
    DIAMETER = 101.6


class Traction_Wheel_4in(_AxlePart):
    """4" wheel (276-1497) with a square axle hole; its STEP model has the axle along z."""

    NAME = "276_1497_4_Wheel"
    WIDTH = 22.31
    KIND = "axle_square"
    AXLE_ALONG_Y = False
    CENTRE = (-37.63, 24.29, 3.39)
    DIAMETER = 101.6


def _catalog_name(sku):
    return next(info.name for info in CATALOG.values() if info.sku == sku)


# (class name, sku, STEP axle axis, STEP centre of the wheel, width along the axle in mm, hole kind),
# measured from the meshes. The 4" omni and traction wheels above predate this table.
_WHEELS = [
    ("Traction_Wheel_4in_HS", "276-1497-110", "z", (29.3, 56.94, 68.4), 22.31, "hs_axle_square"),
    ("Traction_Wheel_2_75in", "276-1496", "z", (25.11, 39.07, 36.92), 19.62, "axle_square"),
    ("Anti_Static_Wheel_2_75in", "276-8098", "y", (-0.05, -0.03, -0.02), 25.66, "axle_square"),
    ("Omni_Wheel_2_75in", "276-8106", "y", (-0.23, -0.54, 0.1), 20.14, "axle_square"),
    ("Anti_Static_Wheel_3_25in", "276-7771", "y", (-1.55, 0.06, -0.65), 27.54, "axle_square"),
    ("Omni_Wheel_3_25in", "276-8026", "y", (0, -0.02, 0.01), 24.87, "axle_square"),
    ("Anti_Static_Wheel_4in", "276-8103", "y", (0, 0.14, 0.2), 27.83, "axle_square"),
    ("Omni_Wheel_2in", "276-9044", "x", (0.01, 0, 0), 15.9, "axle_square"),
    ("Mecanum_Wheel_2in_Left", "217-7400-left", "z", (0, 0, 0), 38.67, "axle_square"),
    ("Mecanum_Wheel_2in_Right", "217-7400-right", "z", (0, 0, 0), 38.46, "axle_square"),
    ("Mecanum_Wheel_2in_V2_Left", "276-9041-801", "z", (0, 0, 0), 27.55, "axle_square"),
    ("Mecanum_Wheel_2in_V2_Right", "276-9041-802", "z", (0, 0, 0), 27.54, "axle_square"),
    ("Mecanum_Wheel_4in", "276-1447", "y", (0.08, 0.14, -0.42), 48.36, "axle_square"),
    ("Intake_Rollers", "276-1499", "z", (0, 0, 0), 12.7, "axle_square"),
]
for _cls, _sku, _axis, _centre, _width, _kind in _WHEELS:
    globals()[_cls] = type(_cls, (_AxlePart,), {
        "__doc__": f"{_catalog_name(_sku)} with its axle hole at the origin (axle along z).",
        "__module__": __name__,
        "NAME": _catalog_name(_sku),
        "WIDTH": _width,
        "KIND": _kind,
        "AXLE_ALONG_Y": _axis == "y",
        "AXLE_ALONG_X": _axis == "x",
        "CENTRE": _centre if any(_centre) else None,
    })


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

    Any one of the three holes can be the round axle bore and the other two take screws.
    `Bearing_Flat()` has the bore in the middle (screws at u=-2 and u=2, as on a dead wheel).
    `Bearing_Flat(bore="end")` has it at one end with the screws at u=-2 and u=-4, which is the
    same pattern as the posts on a `V5_Smart_Motor`'s boss, so the bearing carries the motor's shaft.

    A raised ring around each hole stands 2 mm proud of the plate and goes against the structure.
    The ring tops lie on z=0 and the plate's far face is at z=6.35. The mounting holes are
    `hole("base", u, 0)` and `.axle` is the bore, normal +z (away from the structure).
    """

    NAME = "276_1209_Flat_Bearing"
    THICKNESS = 6.35  # ring tops to the far face of the plate
    KIND = "axle_round"

    def __init__(self, bore="middle"):
        from solid2 import multmatrix

        if bore not in ("middle", "end"):
            raise ValueError("bore must be 'middle' or 'end'")
        self.info = part_info(self.NAME)
        # STEP axis is x, long side y: re-axis so the bore is the z axis and the ring tops are z=0
        shape = part(self.NAME).translate(-82.626, -26.416, 12.7)
        shape = multmatrix([[0, 1, 0, 0], [0, 0, -1, 0], [-1, 0, 0, self.THICKNESS], [0, 0, 0, 1]])(shape)
        self.shape = shape if bore == "middle" else shape.translate(-PITCH, 0, 0)
        self.axle = Hole(Face("axle", (0, 0, 0), (1, 0, 0), (0, -1, 0), (0, 0, 1), 0), 0, 0, self.KIND)
        base = Face("base", (0, 0, self.THICKNESS / 2), (1, 0, 0), (0, 1, 0), (0, 0, -1), self.THICKNESS)
        screws = (-2, 2) if bore == "middle" else (-2, -4)
        self.holes = [self.axle] + [Hole(base, u, 0, "round") for u in screws]


class V5_Smart_Motor(VEXAssembly):
    """V5 Smart Motor (276-4840), coloured by its gear cartridge: red, green or blue.

    The output end has a flat boss with three holes on the 0.5" grid: the shaft hole and two
    screw posts, `hole("boss", -2, 0)` and `hole("boss", -4, 0)`. The part's z axis points into
    the motor body; the boss face is on z=0 with its normal -z (toward whatever it is mounted on).
    `.axle` is the shaft hole at the origin. The colour is only to help tell motors apart.
    """

    NAME = "276_4840_V5_Smart_Motor"
    CARTRIDGES = {"red": 100, "green": 200, "blue": 600}  # rpm
    SHAFT_X, BOSS_Z = 12.7, 43.5  # where the shaft and the boss flat are in the STEP model
    KIND = "axle_square"

    def __init__(self, motor_gearing="blue"):
        from dataclasses import replace

        from solid2 import import_stl, multmatrix

        from .parts import STL_DIR, tint

        if motor_gearing not in self.CARTRIDGES:
            raise ValueError(f"motor_gearing must be one of {sorted(self.CARTRIDGES)}")
        self.gearing, self.rpm = motor_gearing, self.CARTRIDGES[motor_gearing]
        self.info = replace(
            part_info(self.NAME), description=f"V5 Smart Motor, {motor_gearing} cartridge ({self.rpm} rpm)"
        )
        raw = tint(import_stl(str(STL_DIR / f"{self.NAME}.stl")), self.info, motor_gearing)
        # shaft on the z axis, boss flat on z=0 and the body toward +z (a half turn about x)
        self.shape = multmatrix(
            [[1, 0, 0, -self.SHAFT_X], [0, -1, 0, 0], [0, 0, -1, self.BOSS_Z], [0, 0, 0, 1]]
        )(raw)
        self.axle = Hole(_axle_face("axle", 0), 0, 0, self.KIND)
        boss = Face("boss", (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, -1), 0)
        self.holes = [self.axle, Hole(boss, -2, 0, "round"), Hole(boss, -4, 0, "round")]
