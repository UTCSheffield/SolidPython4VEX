# SolidPython4VEX
A python DSL for designing VEX competition robots, built on [SolidPython2](https://github.com/jeff-dh/SolidPython).

## Approach
- Part models come from the VEX V5 STEP CAD libraries, batch converted to STL and imported into OpenSCAD.
- Assemblies are Python classes with a chainable API (`attach`, `mirror`) and can later provide BOM and weight estimates.

```python
class LightUChassisAssembly(VEXAssembly):
    def __init__(self):
        motor = MotorWheelAssembly(RedMotor, OmniWheel, LEFT)
        dead_wheel = DeadWheelAssembly(RedMotor, OmniWheel, LEFT)

        self.shape = (
            U_Channel_2x2x2x20(FLAT, FORWARD, OPEN_DOWN)
            .attach(FRONT, 3, motor)
            .attach(BACK, 3, dead_wheel)
            .attach(BACK, 6, C_Channel_1x5x1x25)
            .mirror(RIGHT, x=-12.5)
        )
```
(Target API; `attach`/`mirror` are not implemented yet.)

## Layout
- `src/solidpython4vex/` - library (`VEXAssembly`, `part()` STL loader)
- `src/solidpython4vex/holes.py` - integer hole lattice (`UNIT` = 0.25"; holes exist where `u + v` is even, which gives the half-pitch stagger)
- `src/solidpython4vex/structure.py` - parametric `Angle`, `C_Channel`, `U_Channel` with `.holes` for attachment; checked against the VEX STEP files
- `src/solidpython4vex/joints.py` - `attach(hole, other, other_hole, ...)` moves a part onto a hole and adds screws/nuts automatically (default nylock; length from the stack thickness; drawn as plain smooth shapes, real SKUs only in the BOM); `fasteners=False` to place hardware yourself
- `scripts/scrape_vex_catalog.py`, `scripts/download_steps.js` - build `parts/catalog.json` (VEX V5 only: SKU, shop and STEP links)
- `scripts/step_to_stl.py` - batch STEP to STL converter (`pip install .[convert]`)

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
