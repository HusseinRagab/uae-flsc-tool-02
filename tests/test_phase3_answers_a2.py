"""Phase 3 owner answers 12.10.2026, package a2 (Ch 4 extinguishers, Ch 5 exit signs,
Ch 6 emergency lighting): one test per answer coded, questions P3 Ch47 Q1-Q3.
Code text in the asserts is read off the rendered pages named in each test
(UAE FLSC 2018, CDGH-OP-25).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flsc_schema import Building  # noqa: E402
from test_phase1_findings import report, items  # noqa: E402
from test_phase3_app import (APP_SRC, _GEO, _app_test, _guard, _occ,  # noqa: E402
                             _save_keys, _state)


def named(r, code, name):
    return [it for it in items(r, code) if it.system == name]


# ------------------------------------------------------------------ Q1 (Ch 5)
def test_P3_Ch47_Q1_nursery_strips_cite_the_owner_ruling():
    """Table 5.3 item 8.ii p.398: Nurseries shall be provided with Photoluminescent Exit
    Marking strips; owner ruling: conditional for Group A, required when Nursery ticked."""
    name = "Photoluminescent Exit Marking Strips (Nurseries)"
    r = report(occupancy="education_a", height_m=8, ground_floor_bua_m2=800)
    s = named(r, "ES", name)
    assert [x.status for x in s] == ["conditional"]
    assert "Owner ruling 12.10.2026, P3 Ch47 Q1" in s[0].detail
    t = report(occupancy="education_a", height_m=8, ground_floor_bua_m2=800,
               has_nursery_within=True)
    s = named(t, "ES", name)
    assert [x.status for x in s] == ["required"]
    assert "owner ruling 12.10.2026, P3 Ch47 Q1" in s[0].detail
    assert "Table 5.3 item 8.ii (p.398)" in s[0].detail


# ------------------------------------------------------------------ Q2 (Ch 4)
P374 = ("Multi-purpose Dry Powder 2-A, 20-B, C 4 kg (ONE) OR Clean Agent Type 4 kg (ONE), "
        "AND CO2 Type 5 kg (ONE)")


def class_a(r):
    return [it for it in items(r, "FE") if it.system.startswith("Class A")]


def test_P3_Ch47_Q2_class_a_for_occupancies_row_1_does_not_list():
    """Table 4.3 row 1 p.373-374 lists items 1-12 only; owner ruling: parking and
    underground take the p.374 types as a tool decision, infrastructure no line,
    mixed_multiple follows its listed occupancies (R13)."""
    for occ, kw in (("parking_enclosed", {}), ("parking_open", {}),
                    ("high_depth_underground", {"floors_below_grade": 2}),
                    ("low_depth_underground", {"floors_below_grade": 1})):
        r = report(occupancy=occ, height_m=10, ground_floor_bua_m2=1000, **kw)
        a = class_a(r)
        assert len(a) == 1 and a[0].status == "required", (occ, a)
        assert P374 in a[0].spec, occ
        assert "owner ruling 12.10.2026" in a[0].code_ref and "tool decision" in a[0].code_ref
        assert a[0].detail.startswith("Tool decision, owner ruling 12.10.2026 (P3 Ch47 Q2): "
                                      "Table 4.3 row 1 does not list this occupancy")
        assert "pending an owner ruling" not in a[0].detail
    assert class_a(report(occupancy="infrastructure", height_m=6, ground_floor_bua_m2=500)) == []
    assert class_a(report(occupancy="mixed_multiple", height_m=10, ground_floor_bua_m2=1000)) == []
    # R13: the listed occupancies bring their own Class A lines (p.373 and p.374 types).
    m = report(occupancy="mixed_multiple", height_m=10, ground_floor_bua_m2=1000,
               mixed_occupancy_mode="most_restrictive",
               secondary_occupancies=["residential", "mall_covered"])
    got = {it.system: it for it in class_a(m)}
    assert set(got) == {"Class A Fire Extinguisher (Multi-purpose Dry Powder AND CO2)",
                        "Class A Fire Extinguisher (Multi-purpose Dry Powder OR Clean Agent) + CO2"}
    assert all(it.status == "required" for it in got.values())
    assert "from residential" in got["Class A Fire Extinguisher (Multi-purpose Dry Powder AND CO2)"].detail
    # A p.374 occupancy with parking keeps one line (same spec).
    mp = report(occupancy="mall_covered", height_m=10, ground_floor_bua_m2=1000,
                mixed_occupancy_mode="most_restrictive", secondary_occupancies=["parking_enclosed"])
    assert len(class_a(mp)) == 1


# ------------------------------------------------------------------ Q3 (Ch 6)
STAND = "Stand-alone Self-Contained EL (Section 3.4)"


def el_types(r):
    return [(it.system, it.status) for it in items(r, "EL")
            if "Central Battery" in it.system or it.system.startswith(("Monitored", "Stand-alone"))
            or it.system.startswith("One Centralized")]


def test_P3_Ch47_Q3_group_c_takes_table_6_5_item_11_12_below_23_m():
    """Table 6.5 p.419 items 11 BUSINESS, GROUP C / 12 MERCANTILE, GROUP C: 'Stand alone Self
    Contained Emergency Lighting System as per Section 3.4., shall be provided and
    permitted'; items 1-2 super highrise / highrise. Table 1.1 p.48 / p.50; #1.7.9.2 p.41."""
    assert Building.model_fields["is_business_group_c"].default is False
    assert Building.model_fields["is_mercantile_group_c"].default is False
    for occ, flag, h, item in (("business", "is_business_group_c", 10, "item 11"),
                               ("business", "is_business_group_c", 22.9, "item 11"),
                               ("mercantile_a", "is_mercantile_group_c", 4, "item 12"),
                               ("mercantile_b", "is_mercantile_group_c", 18, "item 12")):
        r = report(occupancy=occ, height_m=h, ground_floor_bua_m2=200, **{flag: True})
        assert el_types(r) == [(STAND, "required")], (occ, h, el_types(r))
        s = named(r, "EL", STAND)[0]
        assert f"Table 6.5 {item}" in s.code_ref and "P3 Ch47 Q3" in s.detail
    # 23 m or more: the height rows govern, no item 11 / 12 line.
    for occ, flag in (("business", "is_business_group_c"), ("mercantile_b", "is_mercantile_group_c")):
        r = report(occupancy=occ, height_m=23, ground_floor_bua_m2=200, **{flag: True})
        assert [n for n, _ in el_types(r)] == [
            "Central Battery (Section 3.2) OR Monitored Self-Contained (Section 3.3) Emergency Lighting",
            "One Centralized Emergency Lighting System for the Entire Facility (#4.2)"], el_types(r)
        assert not [it for it in items(r, "EL") if it.system.startswith("Stand-alone")]
    # Unticked: height row required, item 11 / 12 a conditional prompt.
    r = report(occupancy="mercantile_b", height_m=8, ground_floor_bua_m2=200)
    assert el_types(r) == [
        ("Monitored Self-Contained EL (Section 3.3)", "required"),
        ("One Centralized Emergency Lighting System for the Entire Facility (#4.2)", "required"),
        ("Stand-alone Self-Contained EL (Section 3.4) - Mercantile Group C only", "conditional")]
    # A flag on another occupancy changes nothing.
    assert el_types(report(occupancy="residential", height_m=10, is_business_group_c=True,
                           is_mercantile_group_c=True)) == el_types(
        report(occupancy="residential", height_m=10))


def test_P3_Ch47_Q3_group_c_inputs_saved_checked_on_load_and_reset():
    keys = _save_keys()
    assert "is_business_group_c" in keys and "is_mercantile_group_c" in keys
    assert 'key="is_business_group_c"' in APP_SRC and 'key="is_mercantile_group_c"' in APP_SRC
    assert '"Business Group C (stand-alone)"' in APP_SRC
    assert '"Mercantile Group C (stand-alone)"' in APP_SRC
    guard = _guard()
    bad = " ".join(guard({"is_business_group_c": "true", "is_mercantile_group_c": 1}))
    assert "is_business_group_c = 'true' (not true / false)" in bad
    assert "is_mercantile_group_c = 1 (not true / false)" in bad
    assert guard({"is_business_group_c": True, "is_mercantile_group_c": False}) == []
    # The box reaches the Building, and an occupancy change clears it.
    at = _app_test({**_GEO, **_occ("Business / Office", "business"), "_last_occupancy": "business",
                    "is_business_group_c": True})
    assert json.loads(at.session_state["_building_json"])["is_business_group_c"] is True
    at.selectbox(key="occupancy_category_select").set_value("Residential / Lodging").run()
    assert not at.exception
    assert _state(at, "is_business_group_c", False) is False
    assert json.loads(at.session_state["_building_json"])["is_business_group_c"] is False
