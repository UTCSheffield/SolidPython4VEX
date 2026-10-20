"""Shrink the raw STEP->STL meshes into small binary STLs for OpenSCAD.

    pip install .[simplify]
    python scripts/simplify_stl.py /tmp/raw_stl src/solidpython4vex/parts/stl [--max-faces 12000]

Meshes above --max-faces are quadric-decimated; all output is binary STL. Only parts listed
in parts/catalog.json are processed, and existing outputs are skipped (resumable).
Bores and mounting holes are only approximate after decimation; use the hole lattice to
cut exact ones where they matter.
"""
import argparse
import json
from multiprocessing import Pool
from pathlib import Path

CATALOG = Path(__file__).parent.parent / "src" / "solidpython4vex" / "parts" / "catalog.json"


def simplify(job):
    src, dst, max_faces = job
    import fast_simplification as fs
    import trimesh

    mesh = trimesh.load(src, force="mesh")
    mesh.merge_vertices()
    before = len(mesh.faces)
    if before > max_faces:
        v, f = fs.simplify(mesh.vertices, mesh.faces, target_count=max_faces, agg=7)
        mesh = trimesh.Trimesh(v, f)
    mesh.export(dst)
    return src.stem, before, len(mesh.faces), dst.stat().st_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--max-faces", type=int, default=12000)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args()

    wanted = {e["name"] for e in json.loads(CATALOG.read_text())}
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    jobs = [
        (s, out / s.name, args.max_faces)
        for s in sorted(Path(args.src_dir).glob("*.stl"))
        if s.stem in wanted and not (out / s.name).exists()
    ]
    with Pool(args.workers) as pool:
        for name, before, after, size in pool.imap_unordered(simplify, jobs):
            print(f"{name}: {before} -> {after} faces, {size / 1e6:.2f} MB", flush=True)


if __name__ == "__main__":
    main()
