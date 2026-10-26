import pytest

from pathlib import Path

from examples.test_chassis import build_test_chassis, build_test_wheeled_chassis


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
    assert quantities["276-2288"] == 2
    assert quantities["276-7285"] == 2
    assert quantities["276-4991"] == 4
    assert quantities["275-1028"] == 4
    assert quantities["276-6483"] == 4
    assert "276-8107" not in quantities
    assert len(chassis.taken) == 40
    scad = chassis.shape.as_scad()
    assert "multmatrix" in scad
    assert "12.4" in scad  # the lowest channel flange is on the ground plane
    assert scad.count("276_6483_4_Post_Hex_Nut_Retainer.stl") == 4


def test_wheeled_chassis_has_a_dead_wheel_on_each_outboard_side():
    wheeled = build_test_wheeled_chassis()
    quantities = {part.sku: quantity for part, quantity in wheeled.bom()}
    assert quantities["276-8107"] == 2 and quantities["276-1209"] == 8
    wheels = sorted(h.position[1] for h in wheeled.holes if h.kind == "axle_square" and abs(h.face.thickness - 25.04) < 0.01)
    assert wheels[0] < 0 and wheels[1] > 292.1  # outboard of the left and right rails


def test_dead_wheel_on_a_single_channel_needs_an_outboard_or_inboard_side():
    import pytest

    from solidpython4vex.structure import U_Channel_2x2x2x20_Aluminum

    with pytest.raises(ValueError, match="outboard"):
        U_Channel_2x2x2x20_Aluminum().dead_wheel(side="front")


def test_dead_wheel_side_is_relative_to_the_selected_rail():
    from solidpython4vex.structure import U_Channel_2x2x2x20_Aluminum

    channel = U_Channel_2x2x2x20_Aluminum()
    outboard, = [h for h in channel.dead_wheel(side="outboard").holes if h.kind == "axle_square"]
    inboard, = [h for h in channel.dead_wheel(side="inboard").holes if h.kind == "axle_square"]
    assert outboard.position[2] > 0
    assert inboard.position[2] < 0


def test_laid_flat_frame_uses_rail_and_inboard_outboard_separately():
    chassis = build_test_chassis()
    outboard, = [h for h in chassis.dead_wheel(rail="right", side="outboard").holes if h.kind == "axle_square"]
    inboard, = [h for h in chassis.dead_wheel(rail="right", side="inboard").holes if h.kind == "axle_square"]
    assert outboard.position[1] > 306.6
    assert inboard.position[1] < 278.4


def test_dead_wheel_on_a_laid_flat_frame_adds_the_parts():
    quantities = {part.sku: quantity for part, quantity in build_test_chassis().dead_wheel(rail="right").bom()}
    assert quantities["228-2500-2226"] == 1
    assert quantities["228-3510"] == 1  # the cap holds the wheel, so only the inboard end needs a collar
    assert quantities["276-1209"] == 2
    assert quantities["276-8107"] == 1
    assert quantities["275-1066-004"] == 1  # 1/2" spacer clears the screws and nuts
    assert quantities["276-7285"] == 2
    assert quantities["276-6483"] == 4
    assert quantities["276-4991"] == 4  # corner screws
    assert quantities["276-4992"] == 4  # bearing screws, through the plate and flange
    assert quantities["275-1028"] == 8  # 4 corner nuts + 4 block nuts


def test_dead_wheel_blocks_bolt_to_both_flanges_on_the_middle_row():
    plain = build_test_chassis()
    wheeled = build_test_chassis().dead_wheel(rail="right")
    mounts = {h for h in wheeled.taken - plain.taken if not h.is_axle}
    assert len(mounts) == 8  # per block: two flange holes and two base holes
    flange = {h for h in mounts if h.face.name.startswith("flange")}
    assert len(flange) == 4
    assert {round(h.position[1], 1) for h in flange} == {278.4, 305.8}  # both flanges of the +y rail
    assert {round(h.position[2], 1) for h in mounts} == {11.6}  # middle flange row
    assert {round(h.position[0], 1) for h in flange} == {88.9, 114.3}  # the last flange hole is used


def test_dead_wheel_shaft_runs_across_the_rail_with_the_wheel_outboard():
    wheeled = build_test_chassis().dead_wheel(rail="right")
    axle = sorted((h for h in wheeled.holes if h.is_axle), key=lambda h: h.position[1])
    assert {round(h.position[0], 1) for h in axle} == {101.6}  # one axle line
    assert {round(h.position[2], 1) for h in axle} == {11.6}
    wheel, = [h for h in axle if h.kind == "axle_square"]
    assert wheel.position[1] > 306.6  # beyond the outer flange
    assert {round(h.normal[1]) for h in axle if h.position[1] < 306} == {1, -1}  # bearings face each other
    spacer_gap = wheel.position[1] - 12.52 - 306.6
    assert spacer_gap == pytest.approx(12.7, abs=0.01)  # wheel sits one 1/2" spacer beyond the outer flange
    assert wheel.position[1] == max(h.position[1] for h in axle if h.kind == "axle_square")


def test_left_side_dead_wheel_uses_the_other_rail():
    plain = build_test_chassis()
    wheeled = plain.dead_wheel(rail="left")
    mounts = {h for h in wheeled.taken - plain.taken if not h.is_axle}
    flange = {h for h in mounts if h.face.name.startswith("flange")}
    assert len(flange) == 4
    assert all(abs(h.position[1]) < 15 for h in flange)  # the two flanges of the y=0 rail
    wheel, = [h for h in wheeled.holes if h.kind == "axle_square"]
    assert wheel.position[1] < -14.5


def test_dead_wheel_needs_a_u_channel_rail():
    import pytest

    from solidpython4vex.structure import C_Channel_1x2x1x25_Aluminum, ChannelFrame

    frame = ChannelFrame(C_Channel_1x2x1x25_Aluminum())
    frame.attach(C_Channel_1x2x1x25_Aluminum(), at="front", hardware="4-post")
    frame.attach(C_Channel_1x2x1x25_Aluminum(), at="rear", hardware="4-post")
    with pytest.raises(ValueError, match="U channel"):
        frame.lay_flat().dead_wheel()


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


def test_motor_wheel_bom_and_validation():
    import pytest

    from solidpython4vex.structure import U_Channel_2x2x2x20_Aluminum

    channel = U_Channel_2x2x2x20_Aluminum().motor_wheel(at="front", side="outboard", motor_gearing="red")
    skus = {part.sku: qty for part, qty in channel.bom()}
    assert skus["276-4840"] == 1
    assert skus["276-1497"] == 1
    assert skus["276-1209"] == 2
    assert 'red cartridge' in next(p.description for p, _ in channel.bom() if p.sku == "276-4840")
    with pytest.raises(ValueError, match="motor_gearing"):
        U_Channel_2x2x2x20_Aluminum().motor_wheel(motor_gearing="pink")
    rear = U_Channel_2x2x2x20_Aluminum().motor_wheel(at="rear", side="inboard")
    assert {p.sku for p, _ in rear.bom()} >= {"276-4840", "276-1497"}
