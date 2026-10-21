import importlib.util
from pathlib import Path

import pytest

from solidpython4vex.electronics import Plate_5x25_Steel, V5_Robot_Brain, free_holes


def _robot():
    path = Path(__file__).resolve().parents[1] / "examples" / "test_robot.py"
    spec = importlib.util.spec_from_file_location("example_test_robot", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_test_robot()


def test_robot_bom_has_electronics_and_plate():
    bom = {part.sku: qty for part, qty in _robot().bom()}
    for sku in ("275-1140", "276-4810", "276-4811", "276-4831"):
        assert bom[sku] == 1
    assert bom["276-6020"] == 2  # one clip at each screw of the battery
    # the brain's four pockets take 1/4" screws driven from under the plate
    assert bom["276-4990"] == 4


def test_brain_sits_on_top_of_the_plate_with_its_body_above():
    robot = _robot()
    mounts = [h for h in robot.holes if h.face.name == "brain_mount"]
    assert len(mounts) == 4 and all(h in robot.taken for h in mounts)
    assert all(round(h.normal[2]) == -1 for h in mounts)
    plate_z = next(h for h in robot.holes if h.face.name == "plate_top").position[2]
    assert all(h.position[2] > plate_z for h in mounts)


def test_plate_holes_are_on_the_half_pitch_lattice():
    plate = Plate_5x25_Steel()
    assert len(free_holes(plate, "plate_top")) == 125
    assert V5_Robot_Brain().hole("brain_mount", 6, 3).position[0] == pytest.approx(38.1)
