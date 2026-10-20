"""Batch convert VEX STEP files to STL (requires pythonocc-core)."""
import sys
from pathlib import Path

from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.StlAPI import StlAPI_Writer


def convert(step_path, stl_path, deflection=0.1):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(step_path)) != IFSelect_RetDone:
        raise RuntimeError(f"Could not read {step_path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    BRepMesh_IncrementalMesh(shape, deflection)
    if not StlAPI_Writer().Write(shape, str(stl_path)):
        raise RuntimeError(f"Could not write {stl_path}")


def main(src_dir, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for step in sorted(Path(src_dir).rglob("*")):
        if step.suffix.lower() in (".step", ".stp"):
            convert(step, out / f"{step.stem}.stl")
            print(step.name)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
