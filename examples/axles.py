"""Put every wheel, gear, sprocket, spacer and collar we have built onto long axles.

Standard 1/8" parts go on 6" capped shafts and high-strength 1/4" parts on a 24" high-strength shaft.
Parts are picked up from the catalog classes automatically, so new ones appear here as they are built.
The axles lie side by side along x, and the BOM lists everything on them.
"""
from pathlib import Path

from solidpython4vex.axles import HS_Shaft, Shaft
from solidpython4vex.coverage import axle_parts

GAP = 130  # mm between axles, enough for a 4" wheel


def width(part):
    return getattr(part, "WIDTH", None) or part.thickness


def fill(make_shaft, parts, start=3.0, end_clear=1.0):
    """Threads `parts` onto as many shafts as needed; returns a list of assembled axles."""
    axles, queue = [], list(parts)
    while queue:
        shaft = make_shaft()
        stack, at = shaft, start
        room = shaft.LENGTH - shaft.CAP - end_clear
        while queue and at + width(queue[0]) <= room:
            part = queue.pop(0)
            at += width(part) / 2
            stack = stack.attach(shaft.at(at, part.axle.kind), part, part.axle)
            at += width(part) / 2
        if stack is shaft:
            raise ValueError(f"{width(queue[0]):.1f} mm part does not fit on the shaft")
        axles.append(stack)
    return axles


def build_axle_test():
    standard = [p for p in axle_parts() if p.axle.size_class == "axle"]
    strong = [p for p in axle_parts() if p.axle.size_class == "hs_axle"]
    axles = fill(lambda: Shaft(6), standard) + fill(lambda: HS_Shaft(24), strong)
    test = None
    for row, axle in enumerate(axles):
        laid = axle.rotate("y", 90).translate(0, row * GAP, 0)
        test = laid if test is None else test.add(laid)
    return test


if __name__ == "__main__":
    build = Path(__file__).resolve().parents[1] / "build"
    build.mkdir(parents=True, exist_ok=True)
    axles = build_axle_test()
    output = build / "test_axles.scad"
    axles.render(output)
    print(f"Wrote {output}")
    print(axles.bom_csv())
