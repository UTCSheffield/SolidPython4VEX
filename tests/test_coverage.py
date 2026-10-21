"""Coverage of the catalog: which parts we model and which of those can attach as expected.

Run `PYTHONPATH=src python3 -m solidpython4vex.coverage` for the full table of what is still to do.
"""

import pytest

from solidpython4vex.coverage import ROLE, category, check, report, role, survey
from solidpython4vex.parts import CATALOG

STATUSES = survey()
BUILT = [s for s in STATUSES if s.state != "missing"]

# Built parts that cannot attach yet, by category. Remove an entry once it is fixed:
# test_known_gaps_are_still_gaps fails when a listed category has no partial parts left.
KNOWN_GAPS = {}


def test_every_catalog_part_has_a_category():
    assert len(STATUSES) == len(CATALOG)
    assert [s.info.sku for s in STATUSES if s.category == "other"] == []


def test_every_role_comes_from_a_known_category():
    assert {role(s.category) for s in STATUSES} <= {"axle", "both", "screw", "host", "hardware"}
    assert set(ROLE) <= {s.category for s in STATUSES}


@pytest.mark.parametrize("status", BUILT, ids=lambda s: s.info.sku)
def test_built_part_attaches_as_its_category_expects(status):
    if status.state == "partial":
        assert status.category in KNOWN_GAPS, f"{status.info.sku}: {status.note}"
    else:
        assert status.state == "ok"


def test_known_gaps_are_still_gaps():
    partial = {s.category for s in STATUSES if s.state == "partial"}
    assert set(KNOWN_GAPS) == partial, "a known gap was fixed (or a new one appeared): update KNOWN_GAPS"


def _built(cat):
    return [s for s in BUILT if s.category == cat]


@pytest.mark.parametrize("cat", ["wheel", "spacer", "collar"])
def test_every_built_wheel_spacer_and_collar_goes_on_a_shaft(cat):
    assert _built(cat), f"no {cat} is built"
    assert all(s.state == "ok" for s in _built(cat))


def test_every_built_channel_and_angle_screws_down():
    parts = _built("channel") + _built("angle")
    assert len(parts) >= 10
    assert all(s.state == "ok" for s in parts)


def test_every_screw_length_and_nut_is_placed_by_attach():
    assert all(s.state == "ok" for s in STATUSES if s.category == "fastener" and "Star Drive Screw" in s.info.description)


def test_report_lists_totals_and_gaps():
    text = report(STATUSES)
    assert "TOTAL" in text and "TO DO" in text and "276-8107" not in text.split("TO DO")[1]

