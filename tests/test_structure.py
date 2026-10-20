from solidpython4vex.structure import Angle, C_Channel, U_Channel


def test_hole_counts_match_vex_step():
    assert len(Angle().holes) == 70
    assert len(C_Channel(2, 1, 25).holes) == 124
    assert len(U_Channel(2, 2, 20).holes) == 177


def test_stagger_rule():
    ch = C_Channel(2, 1, 25)
    for h in ch.holes:
        assert (h.u + h.v) % 2 == 0
    web_mid = [h for h in ch.holes if h.face.name == "web" and h.v == 0]
    assert len(web_mid) == 24 and web_mid[0].u == 2


def test_bom_carries_sku():
    ch = C_Channel(2, 1, 25, "276_2288_1x2x1x25_Aluminum_C_Channel")
    (info, qty), = ch.bom()
    assert info.sku == "276-2288" and qty == 1


def test_named_channel_types_cover_catalogued_channel_stls():
    from pathlib import Path

    from solidpython4vex.parts import STL_DIR
    from solidpython4vex.structure import (
        C_Channel_1x2x1x25_Aluminum,
        C_Channel_1x2x1x35_Aluminum,
        C_Channel_1x2x1x35_Steel,
        C_Channel_1x3x1x35_Aluminum,
        C_Channel_1x5x1x25_Aluminum,
        C_Channel_1x5x1x25_Steel,
        C_Channel_1x5x1x35_Aluminum,
        C_Channel_1x5x1x35_Steel,
        U_Channel_2x2x2x20_Aluminum,
    )

    channel_types = (
        C_Channel_1x2x1x25_Aluminum,
        C_Channel_1x2x1x35_Aluminum,
        C_Channel_1x2x1x35_Steel,
        C_Channel_1x3x1x35_Aluminum,
        C_Channel_1x5x1x25_Aluminum,
        C_Channel_1x5x1x25_Steel,
        C_Channel_1x5x1x35_Aluminum,
        C_Channel_1x5x1x35_Steel,
        U_Channel_2x2x2x20_Aluminum,
    )
    assert len(channel_types) == 9

    for channel_type in channel_types:
        channel = channel_type()
        (info, quantity), = channel.bom()
        assert quantity == 1
        assert info.sku
        assert (Path(STL_DIR) / f"{info.name}.stl").is_file()
        assert channel.length == channel.hole_count * 12.7


def test_attach_adds_fasteners_and_aligns_holes():
    name = "276_2288_1x2x1x25_Aluminum_C_Channel"
    a, b = C_Channel(2, 1, 25, name), C_Channel(2, 1, 25, name)
    joint = a.attach(
        a.hole("web", 2, 0), b, b.hole("web", 2, 0),
        also=[(a.hole("web", 6, 0), b.hole("web", 6, 0))],
    )
    skus = {}
    for info, qty in joint.bom():
        skus[info.sku] = qty
    assert skus["276-4992"] == 2  # default nylock: 3.2 mm stack + 6.35 mm nut + thread -> 1/2"
    assert skus["275-1027"] == 2
    assert skus["276-2288"] == 2
    assert len(joint.taken) == 4


def test_attach_rejects_reused_hole():
    import pytest

    a, b, c = C_Channel(2, 1, 25), C_Channel(2, 1, 25), C_Channel(2, 1, 25)
    joint = a.attach(a.hole("web", 2, 0), b, b.hole("web", 2, 0))
    with pytest.raises(ValueError):
        joint.attach(a.hole("web", 2, 0), c, c.hole("web", 2, 0))


def test_hex_nut_allows_shorter_screw():
    a, b = C_Channel(2, 1, 25), C_Channel(2, 1, 25)
    joint = a.attach(a.hole("web", 2, 0), b, b.hole("web", 2, 0), nut="hex")
    assert {i.sku for i, _ in joint.bom() if i.sku} == {"275-1028", "276-4991"}  # 3/8" screw
