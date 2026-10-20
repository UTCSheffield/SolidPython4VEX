# SolidPython4VEX
A python DSL for designing VEX competition robots, built on [SolidPython2](https://github.com/jeff-dh/SolidPython).

## Approach
- Part models come from the VEX V5 STEP CAD libraries, batch converted to STL and imported into OpenSCAD.
- Assemblies are Python classes with a chainable API (`attach`, `mirror`) and can later provide BOM and weight estimates.

```python
left = C_Channel(2, 1, 25, CHANNEL)
frame = ChannelFrame(left, left.mirror(axis="z", at=-23 * UNIT))
frame.attach(C_Channel(2, 1, 25, CHANNEL), at="front", angle=90, hardware="4-post")
frame.attach(C_Channel(2, 1, 25, CHANNEL), at="rear", angle=90, hardware="4-post")
chassis = frame.lay_flat()
```

## Layout
- `src/solidpython4vex/` - library (`VEXAssembly`, `part()` STL loader)
- `src/solidpython4vex/holes.py` - integer hole lattice (`UNIT` = 0.25"; holes exist where `u + v` is even, which gives the half-pitch stagger)
- `src/solidpython4vex/structure.py` - parametric `Angle`, `C_Channel`, `U_Channel` and `ChannelFrame`; `.attach(..., at="front"|"rear", angle=90)` adds a perpendicular crosspiece using a five-hole joint
- `src/solidpython4vex/drive.py` - `Disc(name)` for gears and sprockets: decimated STL blank with the real mounting holes (0.5" grid, or polar rings on the old 84T) and bore cut exactly, `.holes` on both faces for `attach`; patterns in `parts/discs.json` from `scripts/extract_disc_holes.py`
- `src/solidpython4vex/joints.py` - `attach(hole, other, other_hole, ...)` moves a part onto a hole and adds screws/nuts automatically (default nylock; length from the stack thickness; drawn as plain smooth shapes, real SKUs only in the BOM); `fasteners=False` to place hardware yourself
- `scripts/scrape_vex_catalog.py`, `scripts/download_steps.js` - build `parts/catalog.json` (VEX V5 only: SKU, shop and STEP links)
- `scripts/step_to_stl.py` - batch STEP to STL converter (`pip install .[convert]`)

## Test chassis

Build a simple rectangular frame from four 1x2x1x25 aluminum C-channels:

```sh
PYTHONPATH=src python examples/test_chassis.py
```

The example mirrors the left rail to make the right rail and attaches each cross-piece once at
90 degrees. The five-hole 2-1-2 joint at each corner uses a four-post nut retainer, one hex nut,
and one screw. `.lay_flat()` puts the chassis in the XY ground plane with its lowest flange at
z=0. The 12.5-inch square outside footprint is ready for adding wheels and motors. The script
writes `build/test_chassis.scad` and prints the BOM. Imported STL assets use paths relative to the
SCAD file, so keep the repository's `src/solidpython4vex/parts/stl/` directory alongside it.

```
python scripts/step_to_stl.py <step_dir> src/solidpython4vex/parts/stl
```

## References
- [Designing a V5 Chassis](https://kb.vex.com/hc/en-us/articles/360035953131-Designing-a-V5-Chassis)
- [Simplified VRC CAD library](https://www.vexforum.com/t/simplified-vrc-cad-library-step-file-4-3mb-zipped-yet-to-add-new-hs-gears-and-pneumatics/120454)
- [VEX aluminum kit CAD](https://www.vexrobotics.com/aluminum-kits.html#cad)
- [pythonocc STEP to STL](https://pythonocc-doc.readthedocs.io/en/latest/convert/#stp-to-stl)
- [openscad-step-reader](https://github.com/agordon/openscad-step-reader)
- [openscad-vex-library](https://github.com/UTCSheffield/openscad-vex-library)
- SolidPython2 extensions (as used for BOSL) are the integration path; XRP support may fit too.
