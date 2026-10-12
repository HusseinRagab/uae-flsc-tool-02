"""Phase 3 follow-up answers, package a4 (owner rulings 12.10.2026, 17:07Z): one test per
answer. Cite form "owner ruling 12.10.2026, P3 follow-up <card>".

Code text in the asserts was read off the rendered pages: Table 6.5 p.419, Ch 11
#2.2.4-#2.2.5 p.884, #3.2.2 / Table 11.12 p.923, Table 8.13 items 19-23 p.506, Table 19.2
p.1246; #1.7.45 p.45 from the audit slice quote (CH9A-08 / ENG).
Run with `python -m pytest tests/test_phase3_followups.py`.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import engine  # noqa: E402
from flsc_schema import Building  # noqa: E402
from test_phase1_findings import items, report  # noqa: E402
from test_phase3_app import _GEO, _app_test, _guard, _loader, _occ, _save_keys  # noqa: E402

BASE = dict(ground_floor_bua_m2=1000, plot_area_m2=3000)
CYL = "Gas cylinders (villa / domestic / small commercial)"
CB = "Central Battery (Section 3.2) OR Monitored Self-Contained (Section 3.3) Emergency Lighting"


def get(r, code, prefix):
    out = [it for it in items(r, code) if it.system.startswith(prefix)]
    assert len(out) == 1, [(x.system, x.status) for x in items(r, code)]
    return out[0]


# ------------------------------------------------------------------ F-a2
def test_F_a2_amusement_with_group_c_keeps_table_6_5_item_4():
    """Table 6.5 p.419: item 4 AMUSEMENT BUILDINGS (Central Battery OR Monitored) governs over
    item 11 / 12 (stand-alone) when both boxes are ticked. The governing row was already coded
    by package a2; the ruling citation is new."""
    for occ, flag, item in (("business", "is_business_group_c", "item 11"),
                            ("mercantile_a", "is_mercantile_group_c", "item 12"),
                            ("mercantile_b", "is_mercantile_group_c", "item 12")):
        r = report(occupancy=occ, height_m=10, ground_floor_bua_m2=200,
                   has_amusement_confounding=True, **{flag: True})
        cb = get(r, "EL", CB)
        assert cb.status == "required" and "Table 6.5 item 4" in cb.code_ref
        assert "P3 follow-up F-a2" in cb.detail and item in cb.detail, (occ, cb.detail)
        assert not [it for it in items(r, "EL") if it.system.startswith("Stand-alone")], occ
        # Group C without amusement: item 11 / 12 governs, no F-a2 citation
        plain = report(occupancy=occ, height_m=10, ground_floor_bua_m2=200, **{flag: True})
        assert get(plain, "EL", "Stand-alone").status == "required"
        assert not [it for it in items(plain, "EL") if "F-a2" in (it.detail or "")]
    # amusement without Group C: item 4, no F-a2 citation
    r = report(occupancy="business", height_m=10, ground_floor_bua_m2=200,
               has_amusement_confounding=True)
    assert "F-a2" not in get(r, "EL", CB).detail


# ------------------------------------------------------------------ F-a1-1
def test_F_a1_1_new_or_modified_building_is_a_required_choice_with_no_prefill():
    assert Building.model_fields["is_new_or_modified_building"].default is None
    kw = dict(occupancy="residential", height_m=12, has_gas_cylinders_villa=True, **BASE)
    blank = Building(**kw)
    assert blank.is_new_or_modified_building is None
    stops = engine.lpg_input_stops(blank)
    assert len(stops) == 1 and "#2.2.4" in stops[0] and "p.884" in stops[0]
    assert "'New or modified building'" in stops[0] and "'Existing building'" in stops[0]
    line = get(report(**kw), "LPG", "Cylinder Installations Not Allowed")
    assert line.detail.startswith("NOT EVALUATED") and "P3 follow-up F-a1-1" in line.detail
    # the two choices keep the P3 Ch11 Q3 behaviour
    new = dict(kw, is_new_or_modified_building=True)
    assert "#2.2.4" in engine.lpg_input_stops(Building(**new))[0]
    assert engine.lpg_input_stops(Building(**dict(new, has_cd_cylinder_approval=True))) == []
    old = dict(kw, is_new_or_modified_building=False)
    assert engine.lpg_input_stops(Building(**old)) == []
    assert "Existing building" in get(report(**old), "LPG", "Cylinder Installations").detail
    # no cylinders: no stop
    assert engine.lpg_input_stops(Building(occupancy="residential", height_m=12, **BASE)) == []
    # app: a choice, saved, Load-checked, no pre-fill
    keys = _save_keys()
    assert "new_or_modified_building_input" in keys and "is_new_or_modified_building" not in keys
    apply, defaults = _loader()
    assert "is_new_or_modified_building" not in defaults
    assert "new_or_modified_building_input" not in defaults
    guard = _guard()
    assert guard({"new_or_modified_building_input": "yes"})
    assert guard({"new_or_modified_building_input": True})
    for ok in (None, "new", "existing"):
        assert guard({"new_or_modified_building_input": ok}) == []
    # an old file without the key loads, then stops until the choice is made
    state = {}
    apply(state, {"gas_system_radio": CYL, **_occ("Residential / Lodging", "residential")}, keys)
    assert state.get("new_or_modified_building_input") is None
    base = {**_GEO, **_occ("Residential / Lodging", "residential"), "gas_system_radio": CYL}
    at = _app_test(base)
    assert any("#2.2.4" in e.value and "F-a1-1" in e.value for e in at.error)
    assert json.loads(at.session_state["_building_json"])["is_new_or_modified_building"] is None
    at = _app_test({**base, "new_or_modified_building_input": "existing"})
    assert not [e for e in at.error if "#2.2.4" in e.value]
    assert json.loads(at.session_state["_building_json"])["is_new_or_modified_building"] is False
    at = _app_test({**base, "new_or_modified_building_input": "new"})
    assert any("#2.2.4" in e.value and "P3 Ch11 Q3" in e.value for e in at.error)
    at = _app_test({**base, "new_or_modified_building_input": "new",
                    "has_cd_cylinder_approval": True})
    assert not [e for e in at.error if "#2.2.4" in e.value]


# ------------------------------------------------------------------ F-a1-2
def test_F_a1_2_villa_written_eap_conditional_pending_p1233():
    for occ in ("villa_private", "villa_commercial"):
        r = report(occupancy=occ, height_m=6, ground_floor_bua_m2=300)
        eap = get(r, "EAP", "Written Emergency Action Plan")
        assert eap.status == "conditional", occ
        assert "p.1233" in eap.detail and "not yet read" in eap.detail
        assert "Table 19.2 #3.1.i (p.1246)" in eap.detail and "P3 follow-up F-a1-2" in eap.detail
        assert not [it for it in items(r, "EAP") if it.status == "not_required"]
        for prefix in ("Assembly point", "Drills and training"):
            assert get(r, "EAP", prefix).status == "conditional"
    # non-villa buildings unchanged: required
    biz = report(occupancy="business", height_m=10, **BASE)
    assert get(biz, "EAP", "Written Emergency Action Plan").status == "required"


# ------------------------------------------------------------------ F-a1-3
def test_F_a1_3_indoor_flame_show_also_needs_automatic_detection_and_alarm():
    """#3.2.2 p.923: 'No indoor flame effect shows shall be allowed if the building is not fully
    sprinkler protected and provided with automatic fire detection and alarm system.' Table
    8.13 item 22 p.506: (i) no fire detectors if the enclosed parking is fully sprinklered,
    (ii) Manual Fire Detection and Alarm System, (iii) unsprinklered: Heat Detection."""
    show = dict(has_lpg_flame_effect=True, lpg_flame_effect_show="indoor", **BASE)
    # sprinklered enclosed parking: sprinklers yes, automatic detection no -> stop
    park = Building(occupancy="parking_enclosed", height_m=10, **show)
    assert engine.building_sprinklered(park)
    assert not engine.fa_automatic_detection_required(park)
    stops = engine.lpg_input_stops(park)
    assert len(stops) == 1 and "#3.2.2" in stops[0] and "p.923" in stops[0]
    assert "automatic fire detection and alarm" in stops[0] and "item 22" in stops[0]
    assert "not fully sprinkler protected per its Ch 9" not in stops[0]
    line = get(report(occupancy="parking_enclosed", height_m=10, **show), "LPG",
               "Indoor Flame Effect Shows")
    assert "NOT allowed (#3.2.2" in line.detail and "Ch 8 result" in line.detail
    # open parking at 40 m (sprinklered): by analogy with item 22, named
    op = engine.lpg_input_stops(Building(occupancy="parking_open", height_m=40, **show))
    assert op and "R10" in op[0]
    # plant nursery: both conditions missing, both named
    nur = Building(occupancy="storage_industrial", height_m=8, hazard_class="OH1",
                   is_plant_nursery=True, sum_gf_bua_m2=1000, **show)
    msg = engine.lpg_input_stops(nur)[0]
    assert "not fully sprinkler protected" in msg and "item 28" in msg
    # unsprinklered lowrise business: only the sprinkler condition is named
    biz = engine.lpg_input_stops(Building(occupancy="business", height_m=12, **show))[0]
    assert "not fully sprinkler protected" in biz and "Ch 8 result" not in biz
    # sprinklered and detection required: no stop
    tall = Building(occupancy="business", height_m=40, **show)
    assert engine.fa_automatic_detection_required(tall) and engine.lpg_input_stops(tall) == []
    # R13 most restrictive: a listed occupancy that requires detection counts
    mixed = Building(occupancy="parking_enclosed", height_m=40, mixed_occupancy_mode="most_restrictive",
                     secondary_occupancies=["business"], **show)
    assert engine.fa_automatic_detection_required(mixed)
    # outdoor-only shows are unaffected
    out = dict(show, lpg_flame_effect_show="outdoor")
    assert engine.lpg_input_stops(Building(occupancy="parking_enclosed", height_m=10, **out)) == []
    assert get(report(occupancy="parking_enclosed", height_m=10, **out), "LPG",
               "Indoor Flame Effect Shows").status == "not_required"
    # the FA chapter itself does not change
    kw = dict(occupancy="parking_enclosed", height_m=10, **BASE)
    assert report(**kw).chapter("FA").model_dump() == \
        report(**kw, **{k: v for k, v in show.items() if k not in BASE}).chapter("FA").model_dump()
    # app stops by name
    at = _app_test({**_GEO, **_occ("Parking", "parking_enclosed"), "has_lpg_flame_effect": True,
                    "lpg_flame_effect_show_input": "indoor"})
    assert any("#3.2.2" in e.value and "Ch 8 result" in e.value for e in at.error)


# ------------------------------------------------------------------ F-a3
def test_F_a3_attached_parking_own_depth_below_the_fire_access_level():
    """#1.7.45 p.45 (slice quote): high depth = more than 7 m below or more than two basements
    below the level of exit discharge."""
    assert Building.model_fields["parking_depth_m"].default is None
    kw = dict(occupancy="residential", height_m=40, floors_above_grade=12, floors_below_grade=3,
              depth_below_grade_m=12, ground_floor_bua_m2=1000, plot_area_m2=3000,
              has_parking_area=True, parking_area_m2=2000, parking_height_m=0,
              parking_basement_levels=1)
    deep = "Stair Pressurization (basement parking stairs, more than 2 levels or more than 7 m below)"

    def park(**extra):
        return {(ch.chapter_code, it.system): it for ch in report(**{**kw, **extra}).attached_parking_chapters
                for blk in ch.blocks for it in blk.items}

    blank = park()
    note = blank[("PARK", "Parking depth not entered: building depth used")]
    assert "12 m" in note.spec and "P3 follow-up F-a3" in note.detail and note.code_ref == "Ch 1, #1.7.45"
    assert blank[("SC", deep)].status == "required"           # building depth 12 m used
    own = park(parking_depth_m=5)
    assert ("SC", deep) not in own and not [k for k in own if k[0] == "PARK"]
    assert park(parking_depth_m=8)[("SC", deep)].status == "required"
    # no parking basements: the depth is not used and no note is printed
    assert not [k for k in park(parking_basement_levels=0) if k[0] == "PARK"]
    # nor in a building with no basements (its depth is 0 m, nothing to take)
    assert not [k for k in park(floors_below_grade=0, depth_below_grade_m=0,
                                parking_basement_levels=None) if k[0] == "PARK"]
    # never deeper than the building
    with pytest.raises(ValueError, match="cannot exceed the building's depth"):
        Building(**kw, parking_depth_m=12.5)
    with pytest.raises(ValueError):
        Building(**kw, parking_depth_m=-1)
    # app: limits, saved, Load-checked, stops when deeper than the building
    assert "parking_depth_m_input" in _save_keys()
    guard = _guard()
    assert guard({"parking_depth_m_input": -1}) and guard({"parking_depth_m_input": "5"})
    assert guard({"parking_depth_m_input": None}) == [] and guard({"parking_depth_m_input": 5.0}) == []
    state = {**_GEO, **_occ("Residential / Lodging", "residential"), "floors_below_input": 2,
             "depth_below_grade_input": 6.0, "has_parking_area": True,
             "parking_area_m2_input": 1500.0, "parking_height_m_input": 0.0,
             "parking_basement_levels_input": 1}
    at = _app_test({**state, "parking_depth_m_input": 7.0})
    assert any("cannot exceed the building's depth" in e.value and "F-a3" in e.value for e in at.error)
    at = _app_test({**state, "parking_depth_m_input": 4.0})
    assert not [e for e in at.error if "F-a3" in e.value]
    assert json.loads(at.session_state["_building_json"])["parking_depth_m"] == 4.0
