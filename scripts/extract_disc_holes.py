"""Extract mounting-hole patterns of gears/sprockets from the VEX STEP files.

Run with the OCC env: /opt/conda/envs/occ/bin/python scripts/extract_disc_holes.py cad/step OUT.json
Assumes the disc axis is z (true for the VEX gear/sprocket CAD). For each part writes the
thickness, the centre bore and the off-centre round mounting holes (x, y, radius in mm).
"""
import json
import math
import re
import sys
from pathlib import Path

from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.GeomAbs import GeomAbs_Cylinder
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.TopAbs import TopAbs_FACE
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import topods

NAME = re.compile(r"gear|sprocket", re.I)
SKIP = re.compile(r"bracket|rack|worm|bevel|differential|turntable|2252_007|3880", re.I)


def analyse(path):
    reader = STEPControl_Reader()
    reader.ReadFile(str(path))
    reader.TransferRoots()
    shape = reader.OneShape()
    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    lo, hi = box.CornerMin().Coord(), box.CornerMax().Coord()
    size = [h - l for l, h in zip(lo, hi)]
    ax = size.index(min(size))
    pa, pb = [i for i in range(3) if i != ax]
    centre = [(lo[i] + hi[i]) / 2 for i in range(3)]
    cyls = set()
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        surf = BRepAdaptor_Surface(topods.Face(exp.Current()))
        if surf.GetType() == GeomAbs_Cylinder:
            c = surf.Cylinder()
            d = c.Axis().Direction().Coord()
            if abs(abs(d[ax]) - 1) < 1e-4:
                loc = c.Location().Coord()
                cyls.add((round(loc[pa] - centre[pa], 2), round(loc[pb] - centre[pb], 2), round(c.Radius(), 2)))
        exp.Next()
    holes = sorted(c for c in cyls if 2.0 <= c[2] <= 2.2 and math.hypot(c[0], c[1]) > 1.0)
    bore = sorted(c[2] for c in cyls if math.hypot(c[0], c[1]) < 0.05 and c[2] <= 5)
    return dict(
        axis="xyz"[ax],
        thickness=round(size[ax], 2),
        diameter=round(max(size[pa], size[pb]), 2),
        centre=[round(c, 2) for c in centre],
        round_bore=bore,
        holes=[[x, y] for x, y, _ in holes],
    )


def fit_pattern(holes, grid=12.7):
    """Prefer the 0.5" Cartesian grid (every grid point within some radius); else polar rings."""
    on = {(round(x / grid), round(y / grid)) for x, y in holes
          if abs(x / grid - round(x / grid)) * grid < 0.15 and abs(y / grid - round(y / grid)) * grid < 0.15}
    r2 = max((i * i + j * j for i, j in on), default=0)
    full = {(i, j) for i in range(-8, 9) for j in range(-8, 9) if 0 < i * i + j * j <= r2}
    if on == full:
        return {"grid_r2": r2}
    rings = {}
    for x, y in holes:
        rings.setdefault(round(math.hypot(x, y), 1), []).append(math.degrees(math.atan2(y, x)) % 360)
    return {"polar": [[r, len(a), round(min(a), 1)] for r, a in sorted(rings.items()) if len(a) >= 4]}


def main(step_dir, out):
    catalog = {e["name"] for e in json.load(open(Path(__file__).parent.parent / "src/solidpython4vex/parts/catalog.json"))}
    result = {}
    for p in sorted(Path(step_dir).glob("*.st*p")):
        if p.stem not in catalog or not NAME.search(p.stem) or SKIP.search(p.stem):
            continue
        try:
            r = analyse(p)
            r["pattern"] = fit_pattern(r.pop("holes"))
            result[p.stem] = r
        except Exception as e:
            print("FAIL", p.stem, e, file=sys.stderr)
            continue
        print(p.stem, r["axis"], r["thickness"], r["diameter"], r["round_bore"], r["pattern"])
    json.dump(result, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
