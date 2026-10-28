"""Phase 4 owner rulings 13.10.2026, P4 Q1-Q6: Business Groups A / B / C and Mercantile
Group C (kiosks, food trucks, mercantile trucks). One test per ruling coded.

Code text in the asserts was read off the rendered pages (UAE FLSC 2018, CDGH-OP-25):
Table 1.1 rows 2 and 11 p.48 / p.50, Table 1.9 item 48 p.98, Table 6.5 p.419, Table 8.14
items 31, 34, 35 p.511, #1.1.13.3.c p.529, Table 9.20.b row C p.701, Table 9.21.b p.707,
Table 11.3 p.899.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import engine  # noqa: E402
from flsc_schema import Building, default_hazard  # noqa: E402
from test_phase1_findings import items, report  # noqa: E402
from test_phase3_app import APP_SRC, _GEO, _app_test, _guard, _occ, _save_keys  # noqa: E402

STAND = "Stand-alone Self-Contained EL (Section 3.4)"
KIOSK = dict(occupancy="mercantile_c", mercantile_c_type="kiosk_permanent",
             ground_floor_bua_m2=15)
MERC = ("Mercantile", "mercantile_c")


def named(r, code, prefix):
    return [it for it in items(r, code) if it.system.startswith(prefix)]


def all_items(r):
    return [(c.chapter_code, it) for c in r.chapters for b in c.blocks for it in b.items]


# ------------------------------------------------------------------ Q1
def test_P4_Q1_business_group_required_no_default():
    """Table 1.1 row 2 p.48: Business Groups A, B, C; Table 6.5 p.419 item 11 BUSINESS,
    GROUP C: stand alone self contained. No group: Ch 6 system type NOT EVALUATED."""
    assert Building.model_fields["business_group"].default is None
    r = report(occupancy="business", height_m=10, ground_floor_bua_m2=500)
    ne = named(r, "EL", "Emergency Lighting System Type (Business) - NOT EVALUATED")
    assert len(ne) == 1 and ne[0].status == "not_evaluated" and "P4 Q1" in ne[0].detail
    assert not named(r, "EL", "Monitored") and not named(r, "EL", STAND)
    c = report(occupancy="business", business_group="C", height_m=10, ground_floor_bua_m2=500)
    assert [it.status for it in named(c, "EL", STAND)] == ["required"]
    b = report(occupancy="business", business_group="B", height_m=10, ground_floor_bua_m2=500)
    assert named(b, "EL", "Monitored") and not named(b, "EL", STAND)
    # At 23 m or more the group does not change Ch 6 (items 1-2 govern): no NOT EVALUATED.
    hi = report(occupancy="business", height_m=40)
    assert not named(hi, "EL", "Emergency Lighting System Type (Business)")
    # Groups A, B, C are printed together everywhere else: the same Ch 9 row.
    fps = {g: report(occupancy="business", business_group=g, height_m=18,
                     ground_floor_bua_m2=1500).chapter("FP").selected_branch for g in "ABC"}
    assert len(set(fps.values())) == 1, fps


def test_P4_Q1_listed_other_business_keeps_the_height_row():
    """A Business occupancy listed under R13 has no group input: Table 6.5 items 5-6 (the
    more onerous of items 5-6 and 11) are kept, with the ruling named."""
    for main in ("hotel_a", "villa_commercial"):
        r = report(occupancy=main, secondary_occupancies=["business"],
                   mixed_occupancy_mode="most_restrictive", height_m=10, ground_floor_bua_m2=500)
        assert not named(r, "EL", "Emergency Lighting System Type (Business)"), main
        assert named(r, "EL", "Monitored"), main
    # Where only the Business occupancy brings the line, the ruling is named on it.
    assert any("P4 Q1" in (it.detail or "") for it in named(r, "EL", "Monitored"))


def test_P4_Q1_app_selector_stop_and_legacy_hint():
    keys = _save_keys()
    assert "business_group_input" in keys and "is_post_office" in keys
    assert 'key="business_group_input"' in APP_SRC
    guard = _guard()
    assert guard({"business_group_input": None}) == []
    assert "Business group = 'D' (not a listed option)" in " ".join(
        guard({"business_group_input": "D"}))
    base = {**_GEO, **_occ("Business / Office", "business")}
    at = _app_test(base)
    assert any("Select the Business group" in e.value and "P4 Q1" in e.value for e in at.error)
    at = _app_test({**base, "_legacy_business_group_c": True})
    assert any("old 'Business Group C (stand-alone)' box ticked" in e.value for e in at.error)
    at = _app_test({**base, "business_group_input": "C"})
    assert not at.error
    assert json.loads(at.session_state["_building_json"])["business_group"] == "C"


# ------------------------------------------------------------------ Q2
def test_P4_Q2_post_office_is_OH2_other_business_LH():
    """#1.1.13.3.c p.529 lists post offices under Ordinary Hazard Group 2; #1.1.13 does not
    list Business (LH, owner ruling P4 Q2)."""
    assert default_hazard("business") == "LH"
    assert default_hazard("business", is_post_office=True) == "OH2"
    assert default_hazard("residential", is_post_office=True) == "LH"
    po = Building(occupancy="business", business_group="B", is_post_office=True)
    assert po.hazard_class == "OH2"
    # An explicit override is respected.
    assert Building(occupancy="business", business_group="B", is_post_office=True,
                    hazard_class="LH").hazard_class == "LH"
    with pytest.raises(ValueError, match="Group B only"):
        Building(occupancy="business", business_group="A", is_post_office=True)
    with pytest.raises(ValueError, match="Group B only"):
        Building(occupancy="residential", is_post_office=True)
    # The app passes the post office (Group B only) and derives OH2.
    at = _app_test({**_GEO, **_occ("Business / Office", "business"),
                    "business_group_input": "B", "is_post_office": True})
    b = json.loads(at.session_state["_building_json"])
    assert b["is_post_office"] is True and b["hazard_class"] == "OH2"
    at = _app_test({**_GEO, **_occ("Business / Office", "business"),
                    "business_group_input": "A", "is_post_office": True})
    b = json.loads(at.session_state["_building_json"])
    assert b["is_post_office"] is False and b["hazard_class"] == "LH"


# ------------------------------------------------------------------ Q3
def test_P4_Q3_mercantile_c_is_OH1():
    assert default_hazard("mercantile_c") == "OH1"
    assert Building(**KIOSK).hazard_class == "OH1"


# ------------------------------------------------------------------ Q4
def test_P4_Q4_midrise_kiosk_takes_table_9_20_b_row_C():
    """Table 9.20.b p.701 lists 'C. MERCANTILE GROUP C (KIOSKS)' with residential and
    business: up to 900 m2 dry riser + hose reel, 50 gpm, 45 minutes."""
    r = report(height_m=18, kiosk_in_sprinklered_area_or_mall=False, **KIOSK)
    fp = r.chapter("FP")
    assert fp.selected_branch == "midrise_residential_upto_900"
    assert "Table 9.20.b" in fp.selected_branch_section
    pump = named(r, "FP", "Fire Pump")[0]
    assert pump.spec.startswith("50 gpm")
    assert not any("P4 Q4" in (it.detail or "") for it in items(r, "FP"))


def test_P4_Q4_lowrise_kiosk_takes_table_9_21_b_by_inference():
    """Table 9.21.b p.707 does not list Mercantile Group C: applied by inference (owner
    ruling P4 Q4), never Table 9.21.a (public)."""
    # Audit F9A-03 (28.10.2026): Table 9.21.b rows 1-2 need the plot area (row 3 is a plot
    # of more than 20,000 m2); a blank plot is NOT EVALUATED, so the plot is entered here.
    r = report(height_m=4, kiosk_in_sprinklered_area_or_mall=False, plot_area_m2=500, **KIOSK)
    fp = r.chapter("FP")
    assert fp.selected_branch == "lowrise_residential_upto_3600"
    assert "P4 Q4" in fp.selected_branch_section
    hr = named(r, "FP", "Hose Reel System")[0]
    assert "Table 9.20.b row C" in hr.detail and "P4 Q4" in hr.detail
    assert not fp.selected_branch.startswith("lowrise_public")
    # Mercantile A at the same size takes Table 9.21.a, so the routing really changed.
    a = report(occupancy="mercantile_a", height_m=4, ground_floor_bua_m2=15)
    assert a.chapter("FP").selected_branch.startswith("lowrise_public")


# ------------------------------------------------------------------ Q5
def test_P4_Q5_type_required_every_chapter_not_evaluated():
    r = report(occupancy="mercantile_c", height_m=4, ground_floor_bua_m2=15)
    for c in r.chapters:
        its = [it for b in c.blocks for it in b.items]
        assert [it.system for it in its] == ["Mercantile Group C Type - NOT EVALUATED"], c.chapter_code
        assert its[0].status == "not_evaluated" and "P4 Q5" in its[0].detail
    assert r.occupant_load is None and r.fire_access is None


def test_P4_Q5_food_truck_takes_only_its_own_items():
    """Table 8.14 item 34 FOOD TRUCKS p.511 heat detector #4.7; Table 6.5 item 12 p.419;
    Table 11.3 p.899 with LPG cylinders; Ch 4 extinguishers as mercantile."""
    r = report(occupancy="mercantile_c", mercantile_c_type="food_truck", height_m=3,
               ground_floor_bua_m2=15, has_lpg_cylinders_food_truck=True)
    codes = {c.chapter_code for c in r.chapters}
    assert {"FSA", "MOE", "FE", "ES", "EL", "EVC", "FA", "FP", "SC", "LPG", "ACC", "EAP"} <= codes
    na = {c.chapter_code for c in r.chapters for b in c.blocks for it in b.items
          if it.source_rule == "p4_q5_truck_not_applicable"}
    assert na == {"FSA", "MOE", "ES", "EVC", "FP", "SC", "ACC", "EAP"}
    for c in r.chapters:
        if c.chapter_code in na:
            it = c.blocks[0].items[0]
            assert it.status == "not_required" and "Not Applicable to a Food truck" in it.system
    assert [it.system for it in items(r, "FA")] == ["Heat Detector (Food Truck)"]
    assert "Table 8.14 item 34" in items(r, "FA")[0].code_ref
    assert [it.system for it in items(r, "EL")] == [STAND]
    assert "Table 6.5 item 12" in items(r, "EL")[0].code_ref
    assert named(r, "FE", "Class A Fire Extinguisher (Multi-purpose Dry Powder OR Clean Agent)")
    assert named(r, "LPG", "Food Truck LPG Cylinder Installation (Table 11.3)")
    assert not r.attached_parking_chapters and r.occupant_load is None


def test_P4_Q5_mercantile_truck_heat_detector_item_35():
    r = report(occupancy="mercantile_c", mercantile_c_type="mercantile_truck", height_m=3,
               ground_floor_bua_m2=15)
    fa = items(r, "FA")
    assert [(it.system, it.status) for it in fa] == [("Heat Detector (Mercantile Truck)", "required")]
    assert "Table 8.14 item 35" in fa[0].code_ref
    # Elsewhere item 35 stays a conditional reminder only.
    o = report(occupancy="mercantile_b", height_m=8)
    assert [it.status for it in named(o, "FA", "Heat Detector (Mercantile Truck)")] == ["conditional"]


def test_P4_Q5_kiosk_table_1_9_item_48_and_temporary_item_31():
    """Table 1.9 item 48 KIOSKS p.98 i-v; Table 8.14 item 31 TEMPORARY KIOSKS p.511."""
    r = report(height_m=4, kiosk_in_sprinklered_area_or_mall=False, **KIOSK)
    k = [it for it in items(r, "FP") if (it.code_ref or "").startswith("Ch 1, Table 1.9 item 48")]
    specs = " | ".join(it.spec or "" for it in k)
    assert "Not less than 1.5 m" in specs and "Not less than 6 m" in specs
    assert "not more than 18 m2" in specs and "0 Hour" in specs
    assert named(r, "FP", "Automatic Fire Detection and Alarm System (Kiosk")
    assert not named(r, "FA", "Battery Operated Smoke Detectors (Temporary Kiosk)")
    t = report(occupancy="mercantile_c", mercantile_c_type="kiosk_temporary", height_m=4,
               ground_floor_bua_m2=15, kiosk_in_sprinklered_area_or_mall=False)
    item31 = named(t, "FA", "Battery Operated Smoke Detectors (Temporary Kiosk)")
    assert len(item31) == 1 and item31[0].status == "required"
    assert "Table 8.14 item 31" in item31[0].code_ref


def test_P4_Q5_kiosk_item_48_iii_three_states():
    """Item 48 iii p.98: kiosks at sprinkler protected areas and mall buildings shall be
    provided with automatic sprinkler system. Blank = NOT EVALUATED, never a pass."""
    name = "Automatic Sprinkler System (Kiosk, Table 1.9 item 48 iii)"
    yes = report(height_m=4, kiosk_in_sprinklered_area_or_mall=True, **KIOSK)
    assert [it.status for it in named(yes, "FP", name)] == ["required"]
    assert engine.building_sprinklered(yes.building)
    no = report(height_m=4, kiosk_in_sprinklered_area_or_mall=False, **KIOSK)
    assert [it.status for it in named(no, "FP", name)] == ["not_required"]
    assert not engine.building_sprinklered(no.building)
    blank = report(height_m=4, **KIOSK)
    ne = named(blank, "FP", "Kiosk Location (Table 1.9 item 48 iii) - NOT EVALUATED")
    assert len(ne) == 1 and ne[0].status == "not_evaluated"
    assert not named(blank, "FP", name)
    assert not engine.building_sprinklered(blank.building)   # blank never counts as protected


def test_P4_Q5_mercantile_c_is_its_own_building():
    with pytest.raises(ValueError, match="cannot be a listed other occupancy"):
        Building(occupancy="residential", secondary_occupancies=["mercantile_c"],
                 mixed_occupancy_mode="most_restrictive")
    with pytest.raises(ValueError, match="clear the listed other occupancies"):
        Building(occupancy="mercantile_c", mercantile_c_type="kiosk_permanent",
                 secondary_occupancies=["residential"], mixed_occupancy_mode="most_restrictive")


def test_P4_Q5_mercantile_rows_in_chapters_3_4_5_7_and_occupant_load():
    """Mercantile rows printed without a group (Table 3.13 / 3.16 item 13, Table 4.3 item 9,
    Table 5.3 item 14, Table 7.3) cover Mercantile Group C kiosks."""
    r = report(height_m=4, kiosk_in_sprinklered_area_or_mall=False, **KIOSK)
    assert r.chapter("MOE").selected_branch == "moe_mercantile"
    assert r.chapter("ES").selected_branch == "es_mercantile"
    assert named(r, "FE", "Class B Fire Extinguisher (Foam + Dry Powder) - Mercantile Areas")
    assert named(r, "EVC", "Emergency Voice Evacuation (EVC) - mercantile under highrise")
    assert r.occupant_load is not None and r.occupant_load.evaluated


def test_P4_Q5_app_type_location_area_and_secondary_stops():
    keys = _save_keys()
    assert "mercantile_c_type_input" in keys and "kiosk_location_input" in keys
    guard = _guard()
    assert guard({"mercantile_c_type_input": "food_truck", "kiosk_location_input": "other"}) == []
    bad = " ".join(guard({"mercantile_c_type_input": "cart", "kiosk_location_input": True}))
    assert "Mercantile Group C type = 'cart'" in bad and "Kiosk location" in bad
    base = {**_GEO, **_occ(*MERC), "ground_bua_input": 15.0, "gfa_input": 15.0,
            "height_m_input": 4.0, "floors_above_input": 1}
    at = _app_test(base)
    assert any("Select the Mercantile Group C type" in e.value for e in at.error)
    at = _app_test({**base, "mercantile_c_type_input": "kiosk_permanent",
                    "ground_bua_input": 20.0, "gfa_input": 20.0})
    assert any("not have an area more than 18 m2" in e.value for e in at.error)
    at = _app_test({**base, "mercantile_c_type_input": "kiosk_permanent",
                    "mixed_occupancy_mode_input": "most_restrictive",
                    "secondary_occupancies_input": ["residential"]})
    assert any("evaluated as its own building" in e.value for e in at.error)
    at = _app_test({**base, "mercantile_c_type_input": "kiosk_temporary",
                    "kiosk_location_input": "sprinklered_or_mall"})
    assert not at.error
    b = json.loads(at.session_state["_building_json"])
    assert b["mercantile_c_type"] == "kiosk_temporary"
    assert b["kiosk_in_sprinklered_area_or_mall"] is True


# ------------------------------------------------------------------ Q6
def test_P4_Q6_old_mercantile_group_c_tick_loads_then_stops():
    """An older file's 'Mercantile Group C (stand-alone)' tick loads, then stops by name until
    the occupancy is set to Mercantile Group C or the tick is cleared."""
    assert "is_mercantile_group_c" in _save_keys()
    base = {**_GEO, **_occ("Mercantile", "mercantile_a"), "_last_occupancy": "mercantile_a",
            "is_mercantile_group_c": True}
    at = _app_test(base)
    assert any("P4 Q6" in e.value and "untick" in e.value for e in at.error)
    at = _app_test({**base, "is_mercantile_group_c": False})
    assert not at.error
    # Changing the occupancy to Mercantile Group C clears the tick; the type is then asked.
    at = _app_test(base)
    at.selectbox(key="occupancy_sub_select").set_value("mercantile_c").run()
    assert not at.exception
    assert not any("P4 Q6" in e.value for e in at.error)
    assert any("Select the Mercantile Group C type" in e.value for e in at.error)
