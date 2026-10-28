"""Audit 28.10.2026, lead-session fixes: mixed most-restrictive mode (owner ruling R-F).

R-F: one Table 6.5 emergency lighting package that meets every row (#4.2, p.419) and one
Table 8.13 alarm protocol per building (extending R7)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine import evaluate  # noqa: E402
from flsc_schema import Building  # noqa: E402

_MIX = dict(mixed_occupancy_mode="most_restrictive", floors_above_grade=4,
            ground_floor_bua_m2=2000, gross_floor_area_m2=8000,
            secondary_storage_hazard="OH1", sum_gf_bua_m2=2000)


def _block(kw, chap, prefix):
    r = evaluate(Building(**{**_MIX, **kw}))
    ch = next(c for c in r.chapters if c.chapter_code == chap)
    return [it for bl in ch.blocks if bl.title.startswith(prefix) for it in bl.items]


def _el_types(items):
    return [it.system for it in items if it.status == "required" and (
        it.system.startswith(("Monitored Self-Contained EL", "Central Battery",
                              "Stand-alone Self-Contained EL")))]


def test_RF_el_mall_plus_lowrise_keeps_monitored_only():
    # Table 6.5 item 3 (mall: Central Battery OR Monitored) + item 6 (low rise: Monitored)
    items = _block(dict(occupancy="assembly_a", secondary_occupancies=["mall_covered"],
                        height_m=12), "EL", "EL - System")
    types = _el_types(items)
    assert types == ["Monitored Self-Contained EL (Section 3.3)"]
    line = next(it for it in items if it.system == types[0])
    assert "items 3 and 6" in line.code_ref and "R-F" in line.detail


def test_RF_el_highrise_plus_fuel_drops_stand_alone():
    # item 2 (Central Battery OR Monitored) + item 13 fuel station (stand-alone): #4.2
    items = _block(dict(occupancy="residential", secondary_occupancies=["motor_fuel_dispensing"],
                        height_m=30), "EL", "EL - System")
    types = _el_types(items)
    assert len(types) == 1 and types[0].startswith("Central Battery")
    assert any("#4.2" in (it.system or "") for it in items)


def test_RF_el_single_occupancy_unchanged():
    items = _block(dict(occupancy="mall_covered", secondary_occupancies=[],
                        mixed_occupancy_mode="none", height_m=12), "EL", "EL - System")
    assert len(_el_types(items)) == 1


def _protocols(items):
    return [(it.source_rule, it.system) for it in items if it.status == "required" and (
        "Phased Evacuation Alarm" in it.system or it.system.startswith(
            ("Positive Alarm Sequence", "General Fire Alarm")))]


def test_RF_fa_residential_plus_hotel_one_protocol():
    # Table 8.13 item 2 (5-floor phased, PAS 15/180/240 s) vs item 18 hotel (no evacuation
    # on general alarm, PAS 120 s): the hotel row governs (R7), the height protocol is named.
    items = _block(dict(occupancy="residential", secondary_occupancies=["hotel_a"],
                        height_m=30), "FA", "FA - Detection")
    p = _protocols(items)
    assert {r for r, _ in p} == {"fa_hotel"}
    assert any("5-Floor Phased Evacuation Alarm" in (it.detail or "") for it in items)


def test_RF_fa_residential_plus_storage_one_protocol():
    # items 3-4 PAS 180 s vs items 19-20 (vii) general alarm = evacuation alarm
    items = _block(dict(occupancy="residential", secondary_occupancies=["storage_industrial"],
                        height_m=10), "FA", "FA - Detection")
    p = _protocols(items)
    assert {r for r, _ in p} == {"fa_storage_industrial"}


def test_RF_fa_single_highrise_keeps_height_protocol():
    items = _block(dict(occupancy="residential", secondary_occupancies=[],
                        mixed_occupancy_mode="none", height_m=30), "FA", "FA - Detection")
    names = [s for _, s in _protocols(items)]
    assert "5-Floor Phased Evacuation Alarm" in names
