"""Which catalog parts we have modelled, and whether each one can actually be attached.

Every catalog part is put in a category (from its description) and every category says how its
parts are expected to join the rest of a robot:

    axle      goes on a shaft through its axle hole (wheels, gears, sprockets, spacers, collars)
    both      goes on a shaft and screws down (bearings, motors)
    screw     screws onto a channel through its grid holes (channels, plates, gussets, sensors, ...)
    host      carries axle parts (shafts)
    hardware  screws and nuts, added automatically by `attach`

A part's status is one of
    missing   no class builds it yet
    partial   a class builds it but it cannot do the attachment its category expects (see `note`)
    ok        it attached to a reference part

Run `python src/solidpython4vex/coverage.py` (or `python -m solidpython4vex.coverage`) for the report; tests/test_coverage.py checks it.
"""

import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

if not __package__:  # run as a file: python src/solidpython4vex/coverage.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from solidpython4vex.axles import Bearing_Block, Bearing_Flat, HS_Shaft, Shaft, V5_Smart_Motor, _AxlePart
from solidpython4vex.motion import Disc, disc_names
from solidpython4vex.joints import NUTS, RETAINER_SKU, screw_table
from solidpython4vex.parts import CATALOG, nominal_inches
from solidpython4vex.structure import Angle, C_Channel_1x2x1x25_Aluminum, _CatalogChannel

# (category, words in the lower-cased description); the first match wins
_RULES = [
    ("gusset", ("gusset",)),
    ("retainer", ("retainer",)),
    ("fastener", ("screw", " nut", "star drive coupler", "standoff", "washer")),
    ("electronics", ("controller", "brain", "battery", "sensor", "switch", "servo", "expander", "radio", "cable",
                     "light", "flashlight", "potentiometer", "accelerometer", "tracker", "gps", "wire retaining",
                     "motor 393", "motor controller")),
    ("pneumatics", ("pneumatic", "fitting", "valve", "regulator", "manifold", "reservoir", "gauge", "schrader",
                    "air ")),
    ("track", ("chain", "tread", "conveyor", "rubber link")),
    ("collar", ("collar",)),
    ("spacer", ("spacer", "bushing")),
    ("bearing", ("bearing", "pillow block")),
    ("shaft insert", ("adapter", "insert", "coupler")),
    ("shaft", ("capped shaft", " shaft", "shifter shaft")),
    ("bracket", ("bracket", "flange", "hinge", "clip", "strap", "motor post", "turntable", "bumper")),
    ("sprocket", ("sprocket",)),
    ("gear", ("gear", "pinion", "rack", "clutch", "cam", "lead screw", "crank", "u-joint", "universal")),
    ("wheel", ("wheel", "roller")),
    ("motor", ("v5 smart motor",)),
    ("channel", ("channel", "chassis rail")),
    ("angle", ("angle",)),
    ("plate", ("plate", " bar")),
]

ROLE = {
    "wheel": "axle", "gear": "axle", "sprocket": "axle", "spacer": "axle", "collar": "axle",
    "shaft insert": "axle", "bearing": "both", "motor": "both", "shaft": "host",
    "fastener": "hardware", "retainer": "hardware",
}  # everything else (channels, plates, brackets, electronics, ...) is "screw"


def category(info):
    text = f" {info.description.lower()} "
    for name, words in _RULES:
        if any(w in text for w in words):
            return name
    return "other"


def role(cat):
    return ROLE.get(cat, "screw")


def _all_subclasses(cls):
    for sub in cls.__subclasses__():
        yield sub
        yield from _all_subclasses(sub)


def _factories():
    """{catalog name: callable that builds the part}, from the classes and tables we have."""
    made = {}
    for info in CATALOG.values():
        if "Capped Shaft" in info.description:
            made[info.name] = lambda inches=nominal_inches(info.name): Shaft(inches)
    for inches, name in HS_Shaft._NAMES.items():
        made[name] = lambda inches=inches: HS_Shaft(inches)
    for cls in _all_subclasses(_AxlePart):
        if getattr(cls, "NAME", None):
            made[cls.NAME] = cls
    for cls in (Bearing_Block, Bearing_Flat, V5_Smart_Motor):
        made[cls.NAME] = cls
    for cls in _CatalogChannel.__subclasses__():
        made[cls.part_name] = cls
    made["217_6484_1x1x35_Aluminum_Angle"] = Angle
    for name in disc_names():
        made[name] = lambda name=name: Disc(name)
    return made


def _hardware_skus():
    return {info.sku for info in screw_table().values()} | {n.sku for n in NUTS.values()} | {RETAINER_SKU, "276-6483"}


def axle_parts():
    """A new instance of every built part that rides on a shaft (wheels, gears, sprockets, spacers,
    collars, ...), in category order. Parts that are built later turn up here automatically."""
    factories, found = _factories(), []
    for info in CATALOG.values():
        cat = category(info)
        if role(cat) == "axle" and info.name in factories:
            found.append((cat, info.sku, factories[info.name]()))
    order = ["wheel", "gear", "sprocket", "spacer", "collar", "shaft insert"]
    found.sort(key=lambda f: (order.index(f[0]), f[1]))
    return [part for _, _, part in found]


@dataclass
class Status:
    info: object
    category: str
    state: str  # missing | partial | ok
    note: str = ""


def _on_shaft(part):
    holes = [h for h in part.holes if h.is_axle]
    if not holes:
        return "no axle hole to put on a shaft"
    hole = holes[0]
    shaft = HS_Shaft(4) if hole.size_class == "hs_axle" else Shaft(6)
    try:
        shaft.attach(shaft.at(30, hole.kind), part, hole)
    except ValueError as err:
        return f"does not go on a shaft: {err}"
    return ""


def _screwed_down(part):
    grid = [h for h in part.holes if not h.is_axle]
    if not grid:
        return "no grid holes to screw down with"
    for hole in grid[:8]:
        for side in ("outer", "inner"):
            for roll in range(4):
                channel = C_Channel_1x2x1x25_Aluminum()
                try:
                    channel.attach(channel.hole("web", 2, 0), part, hole, side=side, roll=roll)
                    return ""
                except ValueError:
                    continue
    return "could not be screwed to a channel"


def check(info, factories=None, hardware=None):
    cat = category(info)
    what = role(cat)
    if what == "hardware":
        ok = info.sku in (hardware or _hardware_skus())
        return Status(info, cat, "ok" if ok else "missing", "" if ok else "not placed by attach")
    build = (factories or _factories()).get(info.name)
    if build is None:
        return Status(info, cat, "missing")
    part = build()
    if what == "host":
        return Status(info, cat, "ok")
    notes = []
    if what in ("axle", "both"):
        notes.append(_on_shaft(part))
    if what in ("screw", "both"):
        notes.append(_screwed_down(part))
    notes = [n for n in notes if n]
    return Status(info, cat, "partial" if notes else "ok", "; ".join(notes))


def survey():
    factories, hardware = _factories(), _hardware_skus()
    return [check(info, factories, hardware) for info in sorted(CATALOG.values(), key=lambda i: str(i.sku))]


# What to do for each category: (how to fix it, an existing class to copy)
ACTIONS = {
    "gear": ("Add Disc specs for the unbuilt gears with scripts/extract_disc_holes.py (racks, bevels, "
             "worms, cams and joints need their own classes)", "motion.Disc"),
    "sprocket": ("Add Disc specs for the unbuilt sprockets with scripts/extract_disc_holes.py", "motion.Disc"),
    "wheel": ("One _AxlePart subclass each: NAME, WIDTH, KIND (axle_square, or hs_axle_square for the "
              "high-strength bore), and AXLE_ALONG_Y/CENTRE from the mesh", "axles.Traction_Wheel_4in"),
    "spacer": ("One _AxlePart subclass each (WIDTH from the name); high-strength ones use an hs_axle_square KIND",
               "axles.Nylon_Spacer_1_8in"),
    "collar": ("One _AxlePart subclass each (WIDTH measured from the mesh)", "axles.Shaft_Collar"),
    "shaft insert": ("_AxlePart subclasses that join a standard axle hole to a high-strength one (needs a "
                     "bridging joint kind)", "axles._AxlePart"),
    "shaft": ("Capped and high-strength shafts are built; the rest need their own classes", "axles.HS_Shaft"),
    "bearing": ("Class with an axle_round bore and a row of grid holes, like Bearing_Flat", "axles.Bearing_Flat"),
    "motor": ("Add the 5.5W motor as another V5_Smart_Motor name", "axles.V5_Smart_Motor"),
    "channel": ("A _CatalogChannel subclass each (kind, width, height, holes_count, part_name)",
                "structure.C_Channel_1x2x1x35_Aluminum"),
    "angle": ("Angle(holes, name) already takes a name: just add the sizes (2x2, 3x3 need a wider LEG)",
              "structure.Angle"),
    "plate": ("A Plate class: a grid of square holes on one face, like a channel web", "structure.Channel"),
    "gusset": ("Flat and bent gusset classes with their hole patterns", "structure.Angle"),
    "bracket": ("One class each with its mounting holes", "structure.Angle"),
    "retainer": ("A retainer-with-bearing class for the other retainer kinds", "joints.four_post_hardware"),
    "fastener": ("Standoffs, washers and couplers need an `attach` hardware option; screws and nuts are done",
                 "joints.attach"),
    "electronics": ("Sensors and electronics: one class each with its mounting holes (low priority)",
                    "axles.V5_Smart_Motor"),
    "pneumatics": ("Cylinders and fittings: one class each with its mounting holes (low priority)",
                   "structure.Angle"),
    "track": ("Chains, treads and conveyor links need a track/loop model (low priority)", ""),
}


def report(statuses=None):
    statuses = statuses or survey()
    by_cat = defaultdict(Counter)
    for s in statuses:
        by_cat[s.category][s.state] += 1
    lines = [f"{'category':<14}{'role':<10}{'total':>6}{'ok':>5}{'partial':>9}{'missing':>9}"]
    for cat, c in sorted(by_cat.items()):
        lines.append(f"{cat:<14}{role(cat):<10}{sum(c.values()):>6}{c['ok']:>5}{c['partial']:>9}{c['missing']:>9}")
    totals = Counter(s.state for s in statuses)
    lines.append(f"{'TOTAL':<24}{len(statuses):>6}{totals['ok']:>5}{totals['partial']:>9}{totals['missing']:>9}")

    todo = sorted(
        (cat for cat, c in by_cat.items() if c["partial"] or c["missing"]),
        key=lambda cat: list(ACTIONS).index(cat) if cat in ACTIONS else len(ACTIONS),
    )
    lines += ["", "TO DO, in suggested order (every part has its STL; what is missing is the class)"]
    for cat in todo:
        c = by_cat[cat]
        action, example = ACTIONS.get(cat, ("add a class", ""))
        lines.append(f"\n{cat}: {c['partial']} cannot attach, {c['missing']} not built")
        lines.append(f"  fix: {action}")
        if example:
            lines.append(f"  copy: {example}")
        notes = sorted({s.note for s in statuses if s.category == cat and s.state == "partial"})
        lines += [f"  why it fails: {n}" for n in notes]
        for s in statuses:
            if s.category == cat and s.state != "ok":
                tag = "FAILS " if s.state == "partial" else "missing"
                lines.append(f"    {tag} {s.info.sku:<14}{s.info.description[:50]}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
