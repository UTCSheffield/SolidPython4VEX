from pathlib import Path

from examples.test_chassis import build_test_chassis


def test_render_writes_relative_retainers_import_paths(tmp_path):
    output = tmp_path / "build" / "test_chassis.scad"
    output.parent.mkdir()
    build_test_chassis().render(output)

    scad = output.read_text()
    imports = [
        line.split('file = "')[1].split('"')[0]
        for line in scad.splitlines()
        if "276_6483_4_Post_Hex_Nut_Retainer.stl" in line
    ]
    assert len(imports) == 4
    for imported in imports:
        path = Path(imported)
        assert not path.is_absolute()
        assert (output.parent / path).is_file()


def test_test_chassis_builds_with_expected_bom():
    chassis = build_test_chassis()
    quantities = {part.sku: quantity for part, quantity in chassis.bom()}
    assert quantities["276-2289"] == 2
    assert quantities["276-7285"] == 2
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


def test_35_hole_channel_crosspieces_attach_to_35_hole_rails():
    from solidpython4vex.structure import C_Channel_1x2x1x35_Aluminum, ChannelFrame

    channel = C_Channel_1x2x1x35_Aluminum()
    frame = ChannelFrame(channel)
    frame.attach(C_Channel_1x2x1x35_Aluminum(), at="front", hardware="4-post")
    frame.attach(C_Channel_1x2x1x35_Aluminum(), at="rear", hardware="4-post")

    quantities = {part.sku: quantity for part, quantity in frame.bom()}
    assert quantities["276-2289"] == 4
    assert quantities["276-6483"] == 4


def test_u_channel_crosspieces_set_rail_spacing_and_attach():
    from solidpython4vex.structure import (
        C_Channel_1x2x1x35_Aluminum,
        ChannelFrame,
        U_Channel_2x2x2x20_Aluminum,
    )

    rail = C_Channel_1x2x1x35_Aluminum()
    crosspiece = U_Channel_2x2x2x20_Aluminum()
    frame = ChannelFrame(rail)
    frame.attach(crosspiece, at="front", hardware="4-post")
    frame.attach(crosspiece, at="rear", hardware="4-post")

    left_web = frame.left.hole("web", 2, 0)
    right_web = frame.right.hole("web", 2, 0)
    assert abs(left_web.position[2] - right_web.position[2]) == 228.6
    quantities = {part.sku: quantity for part, quantity in frame.bom()}
    assert quantities["276-2289"] == 2
    assert quantities["276-7285"] == 2
    assert quantities["276-6483"] == 4


def test_u_channel_side_rails_lay_web_on_top_and_open_side_down():
    from solidpython4vex.structure import ChannelFrame, U_Channel_2x2x2x20_Aluminum

    rail = U_Channel_2x2x2x20_Aluminum()
    flat = ChannelFrame(rail).lay_flat()
    web_holes = [hole for hole in flat.holes if hole.face.name == "web"]

    assert web_holes
    assert all(abs(hole.position[2] - (rail.flange_len + rail.T / 2)) < 1e-9
               for hole in web_holes)
    assert rail.flange_len == 24.23


def test_automatic_frame_rejects_different_front_and_rear_spans():
    import pytest

    from solidpython4vex.structure import (
        C_Channel_1x2x1x35_Aluminum,
        ChannelFrame,
        U_Channel_2x2x2x20_Aluminum,
    )

    frame = ChannelFrame(C_Channel_1x2x1x35_Aluminum())
    frame.attach(U_Channel_2x2x2x20_Aluminum(), at="front")
    with pytest.raises(ValueError, match="matching lengths"):
        frame.attach(C_Channel_1x2x1x35_Aluminum(), at="rear")


def test_u_rails_accept_longer_c_channel_crosspieces():
    from solidpython4vex.structure import (
        C_Channel_1x2x1x35_Aluminum,
        ChannelFrame,
        U_Channel_2x2x2x20_Aluminum,
    )

    rail = U_Channel_2x2x2x20_Aluminum()
    crosspiece = C_Channel_1x2x1x35_Aluminum()
    frame = ChannelFrame(rail)
    frame.attach(crosspiece, at="front", hardware="4-post")
    frame.attach(crosspiece, at="rear", hardware="4-post")

    left_web = frame.left.hole("web", 2, 0)
    right_web = frame.right.hole("web", 2, 0)
    assert abs(left_web.position[2] - right_web.position[2]) == 419.1
    quantities = {part.sku: quantity for part, quantity in frame.bom()}
    assert quantities["276-7285"] == 2
    assert quantities["276-2289"] == 2
    assert quantities["276-6483"] == 4


def test_chassis_footprint_is_square():
    from solidpython4vex.structure import C_Channel_1x2x1x25_Aluminum, ChannelFrame

    channel = C_Channel_1x2x1x25_Aluminum()
    frame = ChannelFrame(channel)
    left_web = frame.left.hole("web", 2, 0)
    right_web = frame.right.hole("web", 2, 0)
    rail_spacing = abs(left_web.position[2] - right_web.position[2])
    width = rail_spacing + channel.outer_width
    assert abs(channel.length - width) < 1e-9
    assert channel.length == 317.5


def test_named_channel_type_provides_catalog_metadata_and_frame_dimensions():
    from solidpython4vex.structure import C_Channel_1x2x1x25_Aluminum, ChannelFrame

    channel = C_Channel_1x2x1x25_Aluminum()
    frame = ChannelFrame(channel)
    (info, quantity), = channel.bom()

    assert info.sku == "276-2288"
    assert quantity == 1
    assert channel.hole_count == 25
    assert channel.length == 317.5
    left_web = frame.left.hole("web", 2, 0)
    right_web = frame.right.hole("web", 2, 0)
    assert abs(left_web.position[2] - right_web.position[2]) == 292.1


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

    from solidpython4vex.structure import C_Channel_1x2x1x25_Aluminum, ChannelFrame

    left = C_Channel_1x2x1x25_Aluminum()
    frame = ChannelFrame(left, left.mirror(axis="z", at=-23 * 6.35))
    with pytest.raises(ValueError, match="90 degrees"):
        frame.attach(C_Channel_1x2x1x25_Aluminum(), at="front", angle=45)
