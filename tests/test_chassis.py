from examples.test_chassis import build_test_chassis


def test_test_chassis_builds_with_expected_bom():
    chassis = build_test_chassis()
    quantities = {part.sku: quantity for part, quantity in chassis.bom()}
    assert quantities["276-2288"] == 4
    assert quantities["276-4991"] == 4
    assert quantities["275-1028"] == 4
    assert quantities["276-6483"] == 4
    assert len(chassis.taken) == 40
    scad = chassis.shape.as_scad()
    assert scad.startswith("multmatrix")
    assert "12.4" in scad  # the lowest channel flange is on the ground plane
    assert scad.count("276_6483_4_Post_Hex_Nut_Retainer.stl") == 4


def test_front_and_rear_crosspieces_attach_at_90_degrees():
    chassis = build_test_chassis()
    assert all(
        abs(h.face.normal[2]) > 0.99
        for h in chassis.holes
        if h.face.name == "web"
    )


def test_chassis_footprint_is_square():
    from examples.test_chassis import CHANNEL_HOLES, RAIL_SPACING
    from solidpython4vex.holes import PITCH

    length = CHANNEL_HOLES * PITCH
    width = RAIL_SPACING + 2 * PITCH
    assert abs(length - width) < 1e-9
    assert length == 317.5


def test_mirror_moves_holes_with_the_part():
    import pytest

    from solidpython4vex.structure import C_Channel

    rail = C_Channel(2, 1, 25)
    reflected = rail.mirror(axis="z", at=-23 * 6.35)
    original = rail.hole("web", 2, 0)
    mirrored = reflected.hole("web", 2, 0)
    assert mirrored.position[:2] == pytest.approx(original.position[:2])
    assert mirrored.position[2] == pytest.approx(original.position[2] - 292.1)


def test_channel_frame_rejects_non_perpendicular_crosspiece():
    import pytest

    from examples.test_chassis import CHANNEL, CHANNEL_HOLES
    from solidpython4vex.structure import C_Channel, ChannelFrame

    left = C_Channel(2, 1, CHANNEL_HOLES, CHANNEL)
    frame = ChannelFrame(left, left.mirror(axis="z", at=-23 * 6.35))
    with pytest.raises(ValueError, match="90 degrees"):
        frame.attach(C_Channel(2, 1, CHANNEL_HOLES, CHANNEL), at="front", angle=45)
