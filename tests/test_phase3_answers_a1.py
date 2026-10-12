"""Phase 3 owner answers, package a1 (owner rulings 12.10.2026): Ch 10 smoke control,
Ch 11 LPG, Ch 19 EAP, Ch 15 accessibility. One test per answer coded.

Code text in the asserts was read off the rendered pages: Table 10.21 p.858,
Table 10.25 p.862, Table 10.27 p.866, Ch 2 #2.9.4.a p.220, Ch 11 #2.2.4-#2.2.5 p.884,
Table 11.5 p.906, Table 11.7 p.909, #3.2.2 / Table 11.12 p.923, Ch 15 #5.2.8 p.1119,
Table 19.1 item 8 p.1243, Table 19.2 p.1246.
Run with `python -m pytest tests/test_phase3_answers_a1.py`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import engine  # noqa: E402
from flsc_schema import Building  # noqa: E402
from test_phase1_findings import items, report  # noqa: E402
from test_phase3_app import _GEO, _app_test, _guard, _occ, _save_keys  # noqa: E402

BASE = dict(ground_floor_bua_m2=1000, plot_area_m2=3000)
SC_YAML = (ROOT / "rules" / "ch10_smoke_control.yaml").read_text(encoding="utf-8")
CYL = "Gas cylinders (villa / domestic / small commercial)"


def get(r, code, prefix):
    out = [it for it in items(r, code) if it.system.startswith(prefix)]
    assert len(out) == 1, [(x.system, x.status) for x in items(r, code)]
    return out[0]


def names(r, code="LPG"):
    return [it.system for it in items(r, code)]


# ------------------------------------------------------------------ Ch 10
def test_P3_Ch10_Q1_mall_assembly_stair_inference_cites_the_ruling():
    for occ in ("mall_covered", "assembly_b"):
        r = report(occupancy=occ, height_m=15, **BASE)
        st = get(r, "SC", "Stair Pressurization (malls / assembly")
        assert st.status == "required"
        assert "inference" in st.detail and "owner ruling 12.10.2026, P3 Ch10 Q1" in st.detail
        assert "pending" not in st.detail


def test_P3_Ch10_Q2_road_tunnel_exactly_90_m_takes_the_jet_fan_band():
    kw = dict(occupancy="business", height_m=10, has_tunnel=True, **BASE)
    at90 = get(report(tunnel_length_m=90, **kw), "SC", "Tunnel Smoke Management")
    assert at90.status == "required" and "more than 90 m" in at90.system
    assert "Section 2.14" in at90.spec
    assert "exactly 90 m" in at90.detail and "P3 Ch10 Q2" in at90.detail
    below = get(report(tunnel_length_m=89.9, **kw), "SC", "Tunnel Smoke Management")
    assert "less than 90 m" in below.system
    assert "tier to be confirmed" not in SC_YAML and "sc_aux_tunnel_road_rail_90" not in SC_YAML


def test_P3_Ch10_Q3_long_corridor_such_as_list_cites_the_ruling():
    for occ in ("hotel_a", "business"):
        r = report(occupancy=occ, height_m=20, corridor_length_m=80, **BASE)
        cor = get(r, "SC", "Enclosed Corridor Natural Ventilation")
        assert cor.status == "required" and "P3 Ch10 Q3" in cor.detail


def test_P3_Ch10_Q4_high_depth_underground_fire_lift_with_no_basement_count():
    kw = dict(occupancy="high_depth_underground", height_m=6, floors_above_grade=1,
              floors_below_grade=0, **BASE)
    b = Building(**kw)
    assert b.requires_fire_lift_2_9_4
    assert any("high depth underground" in why for why in b.fire_lift_2_9_4_reasons)
    r = report(**kw)
    lift = get(r, "FSA", "Fire Lift")
    assert lift.status == "required" and "high depth underground" in lift.detail
    # Ch 10 prints its #2.9.4.a lift line for the same building
    assert get(r, "SC", "Firefighting Lift (more than 2 basements)").status == "required"
    # one reason only when basements are also entered
    deep = Building(**{**kw, "floors_below_grade": 3, "depth_below_grade_m": 6})
    assert len(deep.fire_lift_2_9_4_reasons) == 1
    # a low-depth underground building is unchanged
    assert not Building(**{**kw, "occupancy": "low_depth_underground"}).requires_fire_lift_2_9_4


# ------------------------------------------------------------------ Ch 19 / Ch 15
def test_P3_Ch11_Q1_written_eap_required_for_every_non_villa_building():
    for occ in ("business", "residential", "mercantile_a", "storage_industrial"):
        r = report(occupancy=occ, height_m=10, hazard_class="OH1", sum_gf_bua_m2=1000, **BASE)
        eap = get(r, "EAP", "Written Emergency Action Plan")
        assert eap.status == "required", occ
        assert "Table 19.2 #3.1.i" in eap.detail and "P3 Ch11 Q1" in eap.detail
        assert not [it for it in items(r, "EAP") if it.status == "recommended"]
    villa = report(occupancy="villa_private", height_m=6, ground_floor_bua_m2=300)
    assert get(villa, "EAP", "Emergency Action Plan").status == "not_required"


def test_P3_Ch11_Q2_villa_assembly_point_drills_and_wheelchairs_conditional():
    for occ in ("villa_private", "villa_commercial"):
        r = report(occupancy=occ, height_m=6, ground_floor_bua_m2=300)
        for prefix in ("Assembly point", "Drills and training"):
            it = get(r, "EAP", prefix)
            assert it.status == "conditional", (occ, prefix)
            assert "p.1233" in it.detail and "P3 Ch11 Q2" in it.detail
        wc = get(r, "ACC", "Foldable wheelchairs")
        assert wc.status == "conditional" and wc.code_ref == "Ch 15, #5.2.8"
        assert "p.1090" in wc.detail and "all occupancies" in wc.detail
        assert items(r, "ACC")[0].page_ref == "p.1090"
    # non-villa buildings unchanged: required
    biz = report(occupancy="business", height_m=12, **BASE)
    assert get(biz, "EAP", "Assembly point").status == "required"
    assert get(biz, "ACC", "Foldable wheelchairs").status == "required"


# ------------------------------------------------------------------ Ch 11
def test_P3_Ch11_Q3_cylinders_in_new_or_modified_building_stop_unless_cd_approval():
    kw = dict(occupancy="residential", height_m=12, has_gas_cylinders_villa=True, **BASE)
    new = Building(**kw)
    assert new.is_new_or_modified_building is True and new.has_cd_cylinder_approval is False
    stops = engine.lpg_input_stops(new)
    assert len(stops) == 1 and "#2.2.4" in stops[0] and "p.884" in stops[0]
    ban = get(report(**kw), "LPG", "Cylinder Installations Not Allowed")
    assert "NOT allowed (#2.2.4)" in ban.detail and "P3 Ch11 Q3" in ban.detail
    ok = dict(kw, has_cd_cylinder_approval=True)
    assert engine.lpg_input_stops(Building(**ok)) == []
    assert "approval recorded (#2.2.5)" in get(report(**ok), "LPG", "Cylinder Installations").detail
    old = dict(kw, is_new_or_modified_building=False)
    assert engine.lpg_input_stops(Building(**old)) == []
    assert "Existing building" in get(report(**old), "LPG", "Cylinder Installations").detail
    # no cylinders: no stop whatever the inputs
    assert engine.lpg_input_stops(Building(occupancy="residential", height_m=12, **BASE)) == []
    # app: inputs saved, Load type-checked, and the app stops
    keys = _save_keys()
    assert "is_new_or_modified_building" in keys and "has_cd_cylinder_approval" in keys
    bad = _guard()({"is_new_or_modified_building": "yes", "has_cd_cylinder_approval": 1})
    assert len(bad) == 2
    state = {**_GEO, **_occ("Residential", "residential"), "gas_system_radio": CYL}
    at = _app_test(state)
    assert any("#2.2.4" in e.value and "p.884" in e.value for e in at.error)
    at = _app_test({**state, "has_cd_cylinder_approval": True})
    assert not [e for e in at.error if "#2.2.4" in e.value]
    at = _app_test({**state, "is_new_or_modified_building": False})
    assert not [e for e in at.error if "#2.2.4" in e.value]


def test_P3_Ch11_Q4_at_grade_items_only_when_ticked_beside_roof_or_underground():
    kw = dict(occupancy="residential", height_m=40, has_lpg_tanks=True, **BASE)
    at_grade_items = ("Maximum Quantity (72,000 Gal per location)", "Aboveground LPG Tank Installation",
                      "Tank Fire Protection - Fixed Water Spray System")
    for variant in ("has_lpg_tank_roof_mounted", "has_lpg_tank_underground_mounded"):
        r = report(**kw, **{variant: True})
        assert not [n for n in at_grade_items if n in names(r)], variant
        none = get(r, "LPG", "Aboveground (at-grade) LPG Tanks")
        assert none.status == "not_required" and "P3 Ch11 Q4" in none.detail
        both = report(**kw, **{variant: True}, has_lpg_tank_at_grade=True)
        for n in at_grade_items:
            assert get(both, "LPG", n).status == "required", (variant, n)
        assert not [n for n in names(both) if n.startswith("Aboveground (at-grade)")]
    # plain "LPG tanks" with neither roof nor underground: at grade, unchanged
    plain = report(**kw)
    assert plain.chapter("LPG").selected_branch == "lpg_aboveground_tank"
    assert get(plain, "LPG", "Maximum Quantity (72,000 Gal per location)").status == "required"
    ticked = report(**kw, has_lpg_tank_at_grade=True)
    assert ticked.chapter("LPG").model_dump() == plain.chapter("LPG").model_dump()
    assert "has_lpg_tank_at_grade" in _save_keys()
    assert _guard()({"has_lpg_tank_at_grade": "true"})


def test_P3_Ch11_Q5_mall_4000_gal_cites_gfa_or_plot_ruling():
    r = report(occupancy="business", height_m=20, has_lpg_tanks=True,
               has_lpg_tank_roof_mounted=True, ground_floor_bua_m2=2000,
               gross_floor_area_m2=8000, plot_area_m2=25000)
    m = get(r, "LPG", "Mall 4,000 Gal Allowance")
    assert m.status == "conditional"
    assert "GFA or a plot area above 20,000 m2" in m.detail and "P3 Ch11 Q5" in m.detail


def test_P3_Ch11_Q6_indoor_flame_effect_show_in_unsprinklered_building_stops():
    kw = dict(occupancy="business", height_m=12, has_lpg_flame_effect=True, **BASE)
    assert not engine.building_sprinklered(Building(**kw))
    assert Building(**kw).lpg_flame_effect_show is None
    indoor = dict(kw, lpg_flame_effect_show="indoor")
    stops = engine.lpg_input_stops(Building(**indoor))
    assert len(stops) == 1 and "#3.2.2" in stops[0] and "p.923" in stops[0]
    line = get(report(**indoor), "LPG", "Indoor Flame Effect Shows")
    assert line.status == "required" and "NOT allowed (#3.2.2" in line.detail
    assert engine.lpg_input_stops(Building(**dict(kw, lpg_flame_effect_show="both")))
    out = dict(kw, lpg_flame_effect_show="outdoor")
    assert engine.lpg_input_stops(Building(**out)) == []
    assert get(report(**out), "LPG", "Indoor Flame Effect Shows").status == "not_required"
    # sprinklered building: an indoor show is allowed, no stop
    spr = dict(indoor, height_m=40)
    assert engine.building_sprinklered(Building(**spr)) and engine.lpg_input_stops(Building(**spr)) == []
    # app: saved, Load choice-checked, and the app stops
    assert "lpg_flame_effect_show_input" in _save_keys()
    assert _guard()({"lpg_flame_effect_show_input": "inside"})
    assert not _guard()({"lpg_flame_effect_show_input": "outdoor"})
    state = {**_GEO, **_occ("Business", "business"), "has_lpg_flame_effect": True,
             "lpg_flame_effect_show_input": "indoor"}
    at = _app_test(state)
    assert any("#3.2.2" in e.value and "p.923" in e.value for e in at.error)
    at = _app_test({**state, "lpg_flame_effect_show_input": "outdoor"})
    assert not [e for e in at.error if "#3.2.2" in e.value]
