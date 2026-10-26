import importlib.util
from pathlib import Path

from solidpython4vex.assembly import _walk_parts
from solidpython4vex.coverage import axle_parts


def test_long_axle_example_carries_every_built_axle_part():
    path = Path(__file__).resolve().parents[1] / "examples" / "axles.py"
    spec = importlib.util.spec_from_file_location("example_test_axles", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    skus = {part.sku for part, _ in module.build_axle_test().bom()}
    assert {info.sku for p in axle_parts() for info in _walk_parts(p.shape)} <= skus
