from solidpython4vex.drive import Disc
from solidpython4vex.structure import C_Channel


def test_hole_counts():
    assert len(Disc("276_7749_84T_High_Strength_Gear_v2_4_pack").holes) == 2 * 28
    assert len(Disc("276_8330_32T_Sprocket_6P").holes) == 2 * 8
    assert len(Disc("276_3438_84T_High_Strength_Gear").holes) == 2 * 24
    assert len(Disc("276_7572_24T_High_Strength_Gear_v2").holes) == 0


def test_grid_holes_are_on_the_lattice():
    for h in Disc("276_8331_40T_Sprocket_6P").holes:
        assert h.u % 2 == 0 and h.v % 2 == 0


def test_gear_attaches_to_channel_and_bom_has_both():
    gear = Disc("276_8330_32T_Sprocket_6P")
    ch = C_Channel(2, 1, 25, "276_2288_1x2x1x25_Aluminum_C_Channel")
    joint = ch.attach(ch.hole("web", 2, 0), gear, gear.hole("front", 2, 0))
    skus = {i.sku for i, _ in joint.bom() if i.sku}
    assert "276-2288" in skus and len(joint.taken) == 2
    joint.shape.as_scad()
