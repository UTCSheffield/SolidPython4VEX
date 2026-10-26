"""Compatibility re-exports for the renamed :mod:`solidpython4vex.motion` module."""

from .motion import (
    Disc,
    dead_wheel_stack,
    disc_names,
    motor_wheel_stack,
    place_dead_wheel_near_rear,
    place_motor_wheel,
)

__all__ = [
    "Disc",
    "dead_wheel_stack",
    "disc_names",
    "motor_wheel_stack",
    "place_dead_wheel_near_rear",
    "place_motor_wheel",
]
