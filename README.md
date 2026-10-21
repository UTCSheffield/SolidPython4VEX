# SolidPython4VEX
A python DSL for designing VEX competition robots, built on [SolidPython2](https://github.com/jeff-dh/SolidPython).

## Approach
- Part models come from the VEX V5 STEP CAD libraries, batch converted to STL and imported into OpenSCAD.
- Assemblies are Python classes with a chainable API (`attach`, `mirror`) and can later provide BOM and weight estimates.

```python
channel = C_Channel_1x2x1x25_Aluminum()
frame = ChannelFrame(channel)
frame.attach(C_Channel_1x2x1x25_Aluminum(), at="front", angle=90, hardware="4-post")
frame.attach(C_Channel_1x2x1x25_Aluminum(), at="rear", angle=90, hardware="4-post")
chassis = frame.lay_flat()
wheeled = chassis.dead_wheel(at="rear", side="right")
```

## Layout
- `src/solidpython4vex/` - library (`VEXAssembly`, `part()` STL loader)
- `src/solidpython4vex/holes.py` - integer hole lattice (`UNIT` = 0.25"; holes exist where `u + v` is even, which gives the half-pitch stagger)
- `src/solidpython4vex/structure.py` - parametric `Angle`, `C_Channel`, `U_Channel` and `ChannelFrame`; named catalogued channel classes cover the C-channel and U-channel STL parts. `ChannelFrame(channel)` mirrors the rail; the first crosspiece sets the rail spacing based on its length, and front/rear crosspieces must have matching lengths. `.attach(..., at="front"|"rear", angle=90)` adds a perpendicular crosspiece using a five-hole joint
- `src/solidpython4vex/drive.py` - `Disc(name)` for gears and sprockets: decimated STL blank with the real mounting holes (0.5" grid, or polar rings on the old 84T) and bore cut exactly, `.holes` on both faces for `attach`; patterns in `parts/discs.json` from `scripts/extract_disc_holes.py`. Also `dead_wheel_stack(span, wall)` and `place_dead_wheel_near_rear(...)` for a rear dead wheel through a U-channel rail (`channel.dead_wheel(side="outboard")` on a single channel before it goes into a `ChannelFrame`, which mirrors it onto the other rail, or `frame.lay_flat().dead_wheel(side="right")` for one wheel): a flat bearing bolted to the inside of each flange (bore on the middle hole row, a screw and hex nut in each neighbouring hole), with a 3" capped shaft, a collar at the inboard end, a 1/2" nylon spacer, and the 4" omni wheel outboard of the rail with its face against the shaft cap (parts are positioned from the cap end). `channel.motor_wheel(at="front", side="outboard", motor_gearing="blue")` does the same with a `V5_Smart_Motor` (276-4840, coloured red/green/blue by cartridge for identification only) against the frame side of the inner flange: a `Bearing_Flat(bore="end")` inside the U carries the shaft and its screws go through the flange into the motor's two posts, and a 4" traction wheel (276-1497) sits outboard. The shaft insertion depth into the motor is assumed. SCAD output is coloured by part type (metal silver, spacers white, wheels green, retainers and bearings black).
- `src/solidpython4vex/axles.py` - `Shaft(inches)` (capped, with `.at(mm)` stations), `Omni_Wheel_4in`, `Shaft_Collar`, `Nylon_Spacer_1_8in` `Bearing_Flat` (276-1209, used by the dead wheel; its raised rings go against the structure) and `Bearing_Block` (pillow block), each with typed axle holes. Hole kinds are `square`/`round` (the 0.5" grid), `axle_square`/`axle_round` (1/8") and `hs_axle_square`/`hs_axle_round` (1/4" high strength); `attach` only joins holes of the same size class, and axle holes join coaxially with no fasteners.
- `src/solidpython4vex/joints.py` - `attach(hole, other, other_hole, ...)` moves a part onto a hole and adds screws/nuts automatically (default nylock; length from the stack thickness; drawn as plain smooth shapes, real SKUs only in the BOM); `fasteners=False` to place hardware yourself
- `scripts/scrape_vex_catalog.py`, `scripts/download_steps.js` - build `parts/catalog.json` (VEX V5 only: SKU, shop and STEP links)
- `scripts/step_to_stl.py` - batch STEP to STL converter (`pip install .[convert]`)

Named C-channel classes are available for `1x2x1x25` aluminum, `1x2x1x35`
aluminum and steel, `1x3x1x35` aluminum, and `1x5x1x25`/`1x5x1x35` aluminum
and steel. `U_Channel_2x2x2x20_Aluminum` represents the catalogued U-channel.
These classes supply catalog metadata internally, so designs do not need SKU
strings. The C-channel coupler gusset STL is an accessory rather than a channel
profile, and the `2x2x1x35` C-channel requested in the local example is not in
the available STL/catalog set.

## Test chassis

Build a rectangular frame with 1x2x1x35 aluminum C-channel side rails and
2x2x2x20 aluminum U-channel crosspieces:

```sh
PYTHONPATH=src python examples/test_chassis.py
```

The example mirrors the side rail and uses the crosspiece length to set the rail spacing, so
shorter U-channel crosspieces produce a rectangular rather than square frame. Each corner uses a
five-hole 2-1-2 joint, one four-post nut retainer, one hex nut, and one screw. `.lay_flat()` puts
the chassis in the XY ground plane with its lowest flange at z=0. `build_test_wheeled_chassis()` adds
a 4" omni dead wheel (`.dead_wheel(...)`) near the rear crosspiece. The example writes
`build/test_chassis.scad` and `build/test_wheeled_chassis.scad` and prints each BOM. Imported STL assets use paths relative to the SCAD
file, so keep the repository's `src/solidpython4vex/parts/stl/` directory alongside it.

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
