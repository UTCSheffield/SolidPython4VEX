"""A wheeled chassis with a plate deck carrying the V5 brain, radio and battery."""
from pathlib import Path

from solidpython4vex.electronics import Plate_5x25_Steel, V5_Battery, V5_Robot_Brain, V5_Robot_Radio
from solidpython4vex.structure import C_Channel_1x2x1x25_Aluminum, ChannelFrame, U_Channel_2x2x2x20_Aluminum


def build_test_robot():
    channel = U_Channel_2x2x2x20_Aluminum()
    channel = channel.dead_wheel(at="rear", side="outboard")
    channel = channel.motor_wheel(at="front", side="outboard", motor_gearing="green", inset=2)

    # Everything is placed where it is stated: `at` is the spot on the plate's long axis, `inset`
    # slides it in by that many 0.5" pitches, `spin` (0/90/180/270) turns it about the plate's normal.
    plate = Plate_5x25_Steel()
    plate = plate.attach(V5_Robot_Brain(), at="middle", hardware="screw")
    plate = plate.attach(V5_Robot_Radio(), at="right", hardware="screw", inset=2, spin=90)
    plate = plate.attach(V5_Battery(spacing=4), at="left", hardware="screw", inset=2, spin=90)

    frame = ChannelFrame(channel)
    frame.attach(C_Channel_1x2x1x25_Aluminum(), at="front", hardware="4-post")
    frame.attach(C_Channel_1x2x1x25_Aluminum(), at="rear", hardware="4-post")
    frame.attach(plate, at="middle", hardware="screw")
    return frame.lay_flat()


if __name__ == "__main__":
    build = Path(__file__).resolve().parents[1] / "build"
    build.mkdir(parents=True, exist_ok=True)
    robot = build_test_robot()
    output = build / "test_robot.scad"
    robot.render(output)
    print(f"Wrote {output}")
    print(robot.bom_csv())
