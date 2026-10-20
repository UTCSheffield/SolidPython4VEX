"""Build a square, four-channel VEX chassis frame."""
from pathlib import Path

from solidpython4vex.holes import UNIT
from solidpython4vex.structure import C_Channel, ChannelFrame

CHANNEL = "276_2288_1x2x1x25_Aluminum_C_Channel"
CHANNEL_HOLES = 25
RAIL_SPACING = 46 * UNIT


def build_test_chassis():
    left = C_Channel(2, 1, CHANNEL_HOLES, CHANNEL)
    right = left.mirror(axis="z", at=-RAIL_SPACING / 2)
    frame = ChannelFrame(left, right)
    frame.attach(C_Channel(2, 1, CHANNEL_HOLES, CHANNEL), at="front", hardware="4-post")
    frame.attach(C_Channel(2, 1, CHANNEL_HOLES, CHANNEL), at="rear", hardware="4-post")
    return frame.lay_flat()


if __name__ == "__main__":
    chassis = build_test_chassis()
    output = Path("build/test_chassis.scad")
    output.parent.mkdir(parents=True, exist_ok=True)
    chassis.render(output)
    print(f"Wrote {output}")
    print(chassis.bom_csv())
