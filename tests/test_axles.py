import pytest

from solidpython4vex.axles import Bearing_Block, Omni_Wheel_4in, Shaft
from solidpython4vex.holes import Face, Hole, KIND_CLASS
from solidpython4vex.structure import C_Channel_1x2x1x25_Aluminum


def test_five_hole_types_plus_gear_round_are_distinct_classes():
    assert KIND_CLASS["square"] == "grid"
    assert KIND_CLASS["axle_square"] == KIND_CLASS["axle_round"] == "axle"
    assert KIND_CLASS["hs_axle_square"] == KIND_CLASS["hs_axle_round"] == "hs_axle"
    with pytest.raises(ValueError, match="unknown hole kind"):
        Hole(Face("f", (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, -1)), 0, 0, "triangle")


def test_wheel_has_square_axle_hole_and_block_has_round_axle_and_grid_holes():
    assert Omni_Wheel_4in().axle.kind == "axle_square"
    block = Bearing_Block()
    assert block.axle.kind == "axle_round"
    assert {h.kind for h in block.holes if h.face.name == "base"} == {"round"}
    assert [h.position for h in block.holes if h.face.name == "base"] == [(-12.7, 0, 1.585), (12.7, 0, 1.585)]


def test_wheel_goes_on_a_shaft_coaxially_without_fasteners():
    shaft = Shaft()
    wheel = Omni_Wheel_4in()
    joined = shaft.attach(shaft.at(40), wheel, wheel.axle)
    placed = next(h for h in joined.holes if h.kind == "axle_square")
    assert placed.position == pytest.approx((0, 0, 40))
    assert [part.sku for part, _ in joined.bom()] == ["228-2500-2228", "276-8107"]


def test_axle_hole_cannot_join_grid_hole():
    channel = C_Channel_1x2x1x25_Aluminum()
    wheel = Omni_Wheel_4in()
    with pytest.raises(ValueError, match="cannot join"):
        channel.attach(channel.hole("web", 2, 0), wheel, wheel.axle)


def test_standard_axle_hole_cannot_join_high_strength_axle_hole():
    shaft = Shaft()
    wheel = Omni_Wheel_4in()
    with pytest.raises(ValueError, match="cannot join"):
        shaft.attach(shaft.at(10, kind="hs_axle_square"), wheel, wheel.axle)


def test_pillow_block_bolts_flat_onto_a_web_with_the_hub_pointing_up():
    channel = C_Channel_1x2x1x25_Aluminum()
    block = Bearing_Block()
    joined = channel.attach(
        channel.hole("web", 4, 0), block, block.hole("base", -2, 0),
        also=[(channel.hole("web", 8, 0), block.hole("base", 2, 0))], nut="hex",
    )
    axle = next(h for h in joined.holes if h.kind == "axle_round")
    assert axle.normal == pytest.approx((0, 1, 0))  # web faces +y, so the hub points away from it
    assert axle.position[0] == pytest.approx(channel.hole("web", 6, 0).position[0])
    quantities = {part.sku: quantity for part, quantity in joined.bom()}
    assert quantities["276-2016-001"] == 1
    assert quantities["275-1028"] == 2


def test_flat_bearing_has_a_round_bore_between_two_mounting_holes():
    from solidpython4vex.axles import Bearing_Flat

    flat = Bearing_Flat()
    assert flat.axle.kind == "axle_round"
    assert [h.position for h in flat.holes if h.face.name == "base"] == [(-12.7, 0, 3.175), (12.7, 0, 3.175)]
    assert [(p.sku) for p, _ in flat.bom()] == ["276-1209"]
