import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from solid2 import import_stl

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


def part(name):
    """Load a part model converted from the VEX STEP library.

    The returned object carries its catalog metadata as `.part_info`.
    """
    shape = import_stl(str(STL_DIR / f"{name}.stl"))
    shape.part_info = part_info(name)
    return shape
