"""Build a square, four-channel VEX chassis frame."""
from pathlib import Path

from solidpython4vex.structure import C_Channel_1x2x1x25_Aluminum, ChannelFrame, U_Channel_2x2x2x20_Aluminum


def build_test_chassis():
    channel = U_Channel_2x2x2x20_Aluminum()
    frame = ChannelFrame(channel)
    frame.attach(C_Channel_1x2x1x25_Aluminum(), at="front", hardware="4-post")
    frame.attach(C_Channel_1x2x1x25_Aluminum(), at="rear", hardware="4-post")
    return frame.lay_flat()


def build_test_wheeled_chassis():
    channel = U_Channel_2x2x2x20_Aluminum()
    channel = channel.dead_wheel(at="rear", side="outboard")
    channel = channel.motor_wheel(at="front", side="outboard", motor_gearing="green", inset=2)
    frame = ChannelFrame(channel)
    frame.attach(C_Channel_1x2x1x25_Aluminum(), at="front", hardware="4-post")
    frame.attach(C_Channel_1x2x1x25_Aluminum(), at="rear", hardware="4-post")
    return frame.lay_flat()


if __name__ == "__main__":
    build = Path(__file__).resolve().parents[1] / "build"
    build.mkdir(parents=True, exist_ok=True)
    for name, make in (("test_chassis", build_test_chassis), ("test_wheeled_chassis", build_test_wheeled_chassis)):
        chassis = make()
        output = build / f"{name}.scad"
        chassis.render(output)
        print(f"Wrote {output}")
        print(chassis.bom_csv())
