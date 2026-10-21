from solidpython4vex.drive import Disc
from solidpython4vex.structure import C_Channel


def _mounting(disc):
    return [h for h in disc.holes if not h.is_axle]


def test_hole_counts():
    assert len(_mounting(Disc("276_7749_84T_High_Strength_Gear_v2_4_pack"))) == 2 * 28
    assert len(_mounting(Disc("276_8330_32T_Sprocket_6P"))) == 2 * 8
    assert len(_mounting(Disc("276_3438_84T_High_Strength_Gear"))) == 2 * 24
    assert len(_mounting(Disc("276_7572_24T_High_Strength_Gear_v2"))) == 0


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


def test_every_disc_has_one_axle_hole_that_takes_a_shaft():
    from solidpython4vex.axles import HS_Shaft, Shaft
    from solidpython4vex.drive import disc_names

    for name in disc_names():
        disc = Disc(name)
        assert sum(h.is_axle for h in disc.holes) == 1
        shaft = HS_Shaft(3) if disc.axle.size_class == "hs_axle" else Shaft(3)
        joined = shaft.attach(shaft.at(30, disc.axle.kind), disc, disc.axle)
        assert disc.info.sku in [p.sku for p, _ in joined.bom()]


def test_gear_bore_kinds():
    assert Disc("276_5034_36T_High_Strength_Gear").axle.kind == "hs_axle_square"
    assert Disc("276_2169_001_12T_Gear").axle.kind == "axle_round"
