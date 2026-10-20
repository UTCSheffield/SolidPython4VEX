"""Batch convert VEX V5 STEP files to STL (requires pythonocc-core).

    python scripts/step_to_stl.py cad/step src/solidpython4vex/parts/stl [--deflection 0.1] [--timeout 120]

Only parts listed in parts/catalog.json (VEX V5) are converted. Each file runs in its own
process with a timeout, and existing STLs are skipped, so the run is resumable.
"""
import argparse
import json
import multiprocessing as mp
from pathlib import Path

CATALOG = Path(__file__).parent.parent / "src" / "solidpython4vex" / "parts" / "catalog.json"


def convert(step_path, stl_path, deflection):
    from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
    from OCC.Core.IFSelect import IFSelect_RetDone
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.StlAPI import StlAPI_Writer

    reader = STEPControl_Reader()
    if reader.ReadFile(str(step_path)) != IFSelect_RetDone:
        raise RuntimeError(f"Could not read {step_path}")
    reader.TransferRoots()
    shape = reader.OneShape()
    BRepMesh_IncrementalMesh(shape, deflection)
    if not StlAPI_Writer().Write(shape, str(stl_path)):
        raise RuntimeError(f"Could not write {stl_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--deflection", type=float, default=0.1)
    ap.add_argument("--timeout", type=float, default=120)
    ap.add_argument("--catalog", default=str(CATALOG))
    args = ap.parse_args()

    wanted = {e["name"] for e in json.loads(Path(args.catalog).read_text())}
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    failed = []
    for step in sorted(Path(args.src_dir).rglob("*")):
        if step.suffix.lower() not in (".step", ".stp") or step.stem not in wanted:
            continue
        stl = out / f"{step.stem}.stl"
        if stl.exists():
            continue
        tmp = stl.with_suffix(".tmp")
        proc = mp.Process(target=convert, args=(step, tmp, args.deflection))
        proc.start()
        proc.join(args.timeout)
        if proc.is_alive():
            proc.kill()
            proc.join()
        if proc.exitcode == 0 and tmp.exists():
            tmp.rename(stl)
            print("ok  ", step.name, flush=True)
        else:
            tmp.unlink(missing_ok=True)
            failed.append(step.name)
            print("FAIL", step.name, flush=True)
    print(f"{len(failed)} failed:", *failed, sep="\n  ")


if __name__ == "__main__":
    main()
