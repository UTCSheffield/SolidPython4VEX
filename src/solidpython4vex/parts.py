import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from solid2 import color, import_stl

PARTS_DIR = Path(__file__).parent / "parts"
STL_DIR = PARTS_DIR / "stl"
CATALOG_FILE = PARTS_DIR / "catalog.json"


@dataclass(frozen=True)
class PartInfo:
    """Catalog metadata for a part; `name` is the STL file stem."""

    name: str
    sku: str = ""
    description: str = ""
    shop_url: str = ""
    step_url: str = ""
    price: Optional[float] = None
    currency: str = "USD"


def load_catalog(path=CATALOG_FILE):
    path = Path(path)
    if not path.exists():
        return {}
    return {e["name"]: PartInfo(**e) for e in json.loads(path.read_text())}


CATALOG = load_catalog()


def part_info(name):
    return CATALOG.get(name) or PartInfo(name=name)


def nominal_inches(name):
    """The size in the catalog description, e.g. '3" Capped Shaft' -> 3.0, '1/4" Nylon Spacer' -> 0.25."""
    match = re.match(r'\s*(\d+(?:\.\d+)?)(?:/(\d+))?"', part_info(name).description)
    if not match:
        raise ValueError(f"{name} has no size in its catalog description")
    whole, denominator = match.groups()
    return float(whole) / float(denominator) if denominator else float(whole)


# first match wins; anything else is bare metal. STL files carry no colour, so it is added in
# the SCAD as a wrapper around the part, which keeps its `.part_info` for the BOM.
COLOURS = (
    (("spacer",), "white"),
    (("wheel",), "green"),
    (("retainer", "bearing"), "black"),
)
METAL = "silver"


def colour_of(info):
    text = f"{info.name} {info.description}".lower()
    return next((c for words, c in COLOURS if any(w in text for w in words)), METAL)


def tint(shape, info, colour=None):
    """Tag `shape` with its catalog info and return it wrapped in the part's colour."""
    shape.part_info = info
    return color(colour or colour_of(info))(shape)


def part(name):
    """Load a part model converted from the VEX STEP library.

    The returned object carries its catalog metadata as `.part_info`.
    """
    return tint(import_stl(str(STL_DIR / f"{name}.stl")), part_info(name))
