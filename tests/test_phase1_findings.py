"""Phase 1 audit fixes (audit 12.10.2026): one test per finding.

Each test names the audit finding it pins. Code values quoted in the asserts
come from UAE FLSC 2018 (CDGH-OP-25) as read off the printed pages listed in
the rule YAML. Run with `python -m pytest tests/test_phase1_findings.py`.
"""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import engine  # noqa: E402
from flsc_schema import Building  # noqa: E402


# ---------------------------------------------------------------- helpers
def report(**kw):
    kw.setdefault("floors_above_grade", max(1, int(kw.get("height_m", 3) // 3.5)))
    return engine.evaluate(Building(**kw))


def items(r, code, required_only=False):
    ch = r.chapter(code)
    out = [it for b in ch.blocks for it in b.items] if ch else []
    return [it for it in out if it.status == "required"] if required_only else out


def fp(r, **kw):
    return items(r, "FP", **kw)


def lines(r, code, prefix, status="required"):
    return [it for it in items(r, code) if it.system.startswith(prefix) and it.status == status]


def pump(r):
    p = lines(r, "FP", "Fire Pump")
    assert len(p) == 1, [(x.system, x.spec) for x in p]
    return p[0]


def tank(r):
    t = lines(r, "FP", "Fire Water Tank")
    assert len(t) == 1, [(x.system, x.spec) for x in t]
    return t[0]


def refs(r, code="FP"):
    return " | ".join(it.code_ref or "" for it in items(r, code))


# ------------------------------------------------- ALTA case (12.10 ruling)
def test_alta_midrise_3_basements_routes_to_9_20_a_row_h():
    """Ruling 12.10.2026: midrise with 3+ basements -> Table 9.20.a row H."""
    r = report(occupancy="business", height_m=21, floors_above_grade=6, floors_below_grade=3,
               depth_below_grade_m=10.5, ground_floor_bua_m2=1000, plot_area_m2=5000)
    p = pump(r)
    assert p.spec.startswith("750 gpm @ 6.9 bar")
    assert "Table 9.20.a.1" in p.code_ref
    assert tank(r).spec.startswith("45 minutes")
    assert r.requires_wet_riser


# ---------------------------------------------------------------- engine
def test_CH9D_01_each_aux_room_keeps_its_own_row():
    r = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000,
               has_main_electrical_room=True, has_main_telephone_room=True,
               has_main_server_room=True, has_rmu_idf_mdf_room=True, has_gsm_room=True)
    names = [it.system for it in items(r, "FP")]
    for room in ("Main Telephone Room", "Main Server Room", "GSM Room"):
        assert any(n.startswith(room) for n in names), room


def test_ENG_09_one_pump_and_one_tank_line_when_two_tables_apply():
    r = report(occupancy="storage_industrial", height_m=24, ground_floor_bua_m2=1000,
               gross_floor_area_m2=1000, storage_tenancy="multi")  # Q-4, 28.10.2026
    p, t = pump(r), tank(r)
    assert "not governing" in p.detail or "also required by" in p.detail
    assert t is not None


def test_CH9A_08_depth_over_7m_routes_midrise_to_row_h():
    r = report(occupancy="residential", height_m=20, floors_below_grade=2,
               depth_below_grade_m=8, ground_floor_bua_m2=800)
    assert "Table 9.20.a.1" in pump(r).code_ref
    assert pump(r).spec.startswith("750 gpm")


def test_CH9A_10_single_exit_midrise_has_one_pump():
    r = report(occupancy="residential", height_m=20, ground_floor_bua_m2=400,
               has_single_exit_stair=True)
    assert pump(r).spec.startswith("500 gpm @ 6.9 bar")
    assert "Table 9.20.c" in pump(r).code_ref


def test_CH9A_11_healthcare_b_single_exit_uses_9_20_b_row_1():
    r = report(occupancy="healthcare_b", height_m=20, ground_floor_bua_m2=400,
               has_single_exit_stair=True)
    assert pump(r).spec.startswith("50 gpm @ 4.5 bar")
    assert "Table 9.20.b.1" in pump(r).code_ref


def test_ENG_24_height_must_be_stated_and_areas_non_negative():
    with pytest.raises(ValueError):
        Building(occupancy="residential", height_m=0)
    with pytest.raises(ValueError):
        Building(occupancy="residential", height_m=10, ground_floor_bua_m2=-5)
    with pytest.raises(ValueError):
        Building(occupancy="residential", height_m=-5)
    Building(occupancy="infrastructure", height_m=0)  # no building height


def test_ENG_24_app_refuses_impossible_loaded_values_by_name():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    keep = [n for n in tree.body
            if (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_SCENARIO_LIMITS"
                                                 for t in n.targets))
            or (isinstance(n, ast.FunctionDef) and n.name == "_invalid_scenario_values")]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "app_guard", "exec"), ns)
    bad = ns["_invalid_scenario_values"]({"height_m_input": -5, "floors_above_input": 2.5,
                                          "plot_area_input": "big"})
    text = " ".join(bad)
    assert "Building height = -5" in text
    assert "Floors above grade = 2.5" in text
    assert "Plot area = 'big'" in text
    assert ns["_invalid_scenario_values"]({"height_m_input": 30.0}) == []


# ------------------------------------------------- Tables 9.18 / 9.19
def test_CH9A_01_zoning_measured_from_lowest_pump_level():
    r = report(occupancy="residential", height_m=40, floors_below_grade=4,
               depth_below_grade_m=14, ground_floor_bua_m2=2000)
    assert "Table 9.19.B" in refs(r)
    assert any("Each Zone" in it.system for it in fp(r))
    r = report(occupancy="business", height_m=85, floors_below_grade=3,
               depth_below_grade_m=10, ground_floor_bua_m2=2000)
    assert lines(r, "FP", "Second Fire Pump Set")
    r = report(occupancy="residential", height_m=40, floors_below_grade=4,
               depth_below_grade_m=14, ground_floor_bua_m2=2000, pump_room_at_grade=True)
    assert "Table 9.19.D" in refs(r)


def test_CH9A_02_9_19_c_large_plot_1000_gpm():
    r = report(occupancy="residential", height_m=40, ground_floor_bua_m2=2000, plot_area_m2=25000)
    assert pump(r).spec.startswith("1000 gpm @ 6.9 bar")
    assert "Table 9.19.C" in pump(r).code_ref


def test_CH9A_03_9_20_b_row_4_large_plot():
    r = report(occupancy="residential", height_m=20, ground_floor_bua_m2=2000, plot_area_m2=25000)
    assert pump(r).spec.startswith("1000 gpm")
    assert tank(r).spec.startswith("60 minutes")


def test_CH9A_04_super_highrise_first_pump_17_bar_and_upper_sets():
    r = report(occupancy="business", height_m=120, ground_floor_bua_m2=2000, plot_area_m2=5000,
               wet_riser_standpipes=3)
    assert pump(r).spec.startswith("1000 gpm @ 17 bar")
    up = lines(r, "FP", "Upper-level Pump Sets")
    assert up and up[0].spec.startswith("1000 gpm @ 6.9 bar")
    assert lines(r, "FP", "Upper-level Fire Water Tanks")[0].spec.startswith("30 minutes")


def test_CH9A_05_super_highrise_large_plot_upper_sets():
    r = report(occupancy="business", height_m=120, ground_floor_bua_m2=2000, plot_area_m2=30000)
    assert lines(r, "FP", "Upper-level Pump Sets")[0].spec.startswith("750 gpm @ 6.9 bar")
    assert lines(r, "FP", "Upper-level Fire Water Tanks")


def test_CH9A_06_interconnect_lowest_and_highest():
    r = report(occupancy="residential", height_m=30, ground_floor_bua_m2=2000)
    assert any("Lowest + Highest Level of Each Zone" in it.system for it in fp(r))


def test_CH9A_07_storage_more_than_100m_from_hydrant():
    r = report(occupancy="storage_industrial", height_m=12, ground_floor_bua_m2=2000,
               gross_floor_area_m2=2000, gf_beyond_100m_from_hydrant=True)
    assert lines(r, "FP", "Yard Fire Hydrant")


def test_CH9A_12_9_20_a_2_states_the_60m_fallback():
    r = report(occupancy="hotel_a", height_m=20, ground_floor_bua_m2=2000, plot_area_m2=25000)
    y = " ".join(it.detail or "" for it in lines(r, "FP", "Yard Fire Hydrant"))
    assert "within 60 m" in y and "Table 9.20.a.1" in y


def test_CH9A_13_plot_exactly_20000_is_row_1():
    r = report(occupancy="hotel_a", height_m=20, ground_floor_bua_m2=2000, plot_area_m2=20000)
    assert "Table 9.20.a.1" in pump(r).code_ref
    assert tank(r).spec.startswith("45 minutes")


def test_CH9A_14_outlet_sizes_25_40_65():
    r = report(occupancy="business", height_m=120, ground_floor_bua_m2=2000, plot_area_m2=30000)
    text = " ".join(it.detail or "" for it in fp(r))
    assert "25 mm" in text and "65 mm" in text
    assert "38 mm" not in text and "64 mm" not in text


def test_CH9A_16_pump_source_cites_uae_tables_not_nfpa():
    r = report(occupancy="residential", height_m=30, ground_floor_bua_m2=2000)
    d = pump(r).detail
    assert "Table 9.6 item" in d and "NFPA 14" not in d
    assert "250 gpm at 7 bar" in d


# ------------------------------------------------- Tables 9.20 / 9.21
@pytest.mark.parametrize("gf, gpm, bar", [(800, "50 gpm", "4.5 bar"), (2000, "300 gpm", "4.5 bar"),
                                          (5000, "750 gpm", "6.9 bar")])
def test_9_20_b_tiers(gf, gpm, bar):
    r = report(occupancy="residential", height_m=20, ground_floor_bua_m2=gf)
    assert pump(r).spec.startswith(f"{gpm} @ {bar}")
    assert tank(r).spec.startswith("45 minutes")


def test_CH9B_05_lowrise_public_large_plot():
    r = report(occupancy="assembly_b", height_m=12, ground_floor_bua_m2=4000, plot_area_m2=25000)
    assert pump(r).spec.startswith("1000 gpm @ 6.9 bar")
    assert tank(r).spec.startswith("60 minutes")
    assert lines(r, "FP", "Wet Riser")
    assert lines(r, "FP", "Yard Fire Hydrant")


def test_CH9B_06_lowrise_residential_large_plot_keeps_tier_systems():
    r = report(occupancy="residential", height_m=12, ground_floor_bua_m2=4000, plot_area_m2=25000)
    assert lines(r, "FP", "Automatic Sprinkler System")
    assert lines(r, "FP", "Wet Riser")
    assert r.requires_wet_riser
    assert "1000 gpm @ 6.9 bar" in pump(r).spec
    assert tank(r).spec.startswith("60 minutes")


def test_CH9B_09_converted_villa_tiers():
    r = report(occupancy="assembly_c", height_m=7, floors_above_grade=2, ground_floor_bua_m2=600,
               villa_converted_use=True)
    assert not [it for it in fp(r) if it.status == "required"
                and ("Sprinkler" in it.system or it.system.startswith("Fire Pump"))]
    r = report(occupancy="business", height_m=7, floors_above_grade=2, ground_floor_bua_m2=1000,
               villa_converted_use=True, has_single_exit_stair=True)
    cond = lines(r, "FP", "Fire Pump", status="conditional")
    assert cond and cond[0].spec.startswith("250 gpm @ 4.5 bar")
    assert lines(r, "FP", "Second Exit Stair", status="recommended")


def test_9_21_c_single_exit_replaces_hose_reel_tier():
    r = report(occupancy="residential", height_m=12, ground_floor_bua_m2=2000,
               has_single_exit_stair=True)
    assert pump(r).spec.startswith("300 gpm @ 4.5 bar")
    assert "Table 9.21.c.2" in pump(r).code_ref


# ------------------------------------------------- Tables 9.22 / 9.23
def test_CH9B_08_open_mall_tenant_item():
    r = report(occupancy="mall_open", height_m=7, ground_floor_bua_m2=500, plot_area_m2=800)
    t = lines(r, "FP", "Tenant Buildings")
    assert t and "Table 9.22.B" in t[0].detail and "combined" in t[0].detail


def test_CH9B_10_commercial_villa_one_pump_fed_from_yard_set():
    r = report(occupancy="villa_commercial", height_m=7, floors_above_grade=2,
               ground_floor_bua_m2=2000, plot_area_m2=25000)
    p = pump(r)
    assert p.spec.startswith("1000 gpm") and "9.23.B.3 vii" in p.detail


def test_CH9B_12_open_mall_120m_and_hydrant_alternative():
    r = report(occupancy="mall_open", height_m=7, ground_floor_bua_m2=500, plot_area_m2=1500)
    text = " ".join(it.detail or "" for it in fp(r))
    assert "120 m of every exterior part of the tenant buildings" in text
    assert lines(r, "FP", "Fire Pump (where yard hydrants", status="conditional")


# ------------------------------------------------- Table 9.24 parking
@pytest.mark.parametrize("gf, h, plot, gpm, mins", [
    (800, 9, 5000, "50 gpm @ 4.5 bar", "30"),
    (3000, 12, 5000, "300 gpm @ 4.5 bar", "30"),
    (5000, 12, 5000, "750 gpm @ 6.9 bar", "60"),
    (5000, 12, 25000, "1000 gpm @ 6.9 bar", "60"),
])
def test_CH9B_01_enclosed_parking_rows(gf, h, plot, gpm, mins):
    r = report(occupancy="parking_enclosed", height_m=h, ground_floor_bua_m2=gf, plot_area_m2=plot)
    assert pump(r).spec.startswith(gpm)
    assert tank(r).spec.startswith(mins)
    names = " ".join(it.system for it in fp(r))
    assert "Class I" not in names and "Smoke Control" not in names


def test_CH9B_02_open_parking_rows():
    r = report(occupancy="parking_open", height_m=12, ground_floor_bua_m2=3000)
    assert lines(r, "FP", "Automatic Sprinkler System")
    assert pump(r).spec.startswith("1000 gpm @ 6.9 bar") and tank(r).spec.startswith("60")
    r = report(occupancy="parking_open", height_m=20, ground_floor_bua_m2=1500, exit_stairs=2)
    assert pump(r).spec.startswith("750 gpm @ 6.9 bar") and tank(r).spec.startswith("60")
    r = report(occupancy="parking_open", height_m=20, ground_floor_bua_m2=1500, exit_stairs=3)
    assert pump(r).spec.startswith("1000 gpm @ 6.9 bar")
    r = report(occupancy="parking_open", height_m=9, ground_floor_bua_m2=1500)
    assert pump(r).spec.startswith("50 gpm @ 4.5 bar") and tank(r).spec.startswith("45")
    text = " ".join(it.detail or "" for it in fp(r))
    assert "standalone open parking does not require sprinklers" not in text


def test_CH9B_03_robotic_parking_deluge():
    r = report(occupancy="parking_enclosed", height_m=12, ground_floor_bua_m2=3000,
               has_robotic_parking=True)
    assert lines(r, "FP", "Deluge Water Spray System")
    assert "2 adjacent deluge" in pump(r).spec
    assert tank(r).spec.startswith("60")


def test_CH9B_04_covered_shaded_parking():
    r = report(occupancy="parking_open", height_m=4, floors_above_grade=1, ground_floor_bua_m2=5000,
               is_covered_shaded_parking=True)
    assert pump(r).spec.startswith("50 gpm @ 4.5 bar") and tank(r).spec.startswith("60")
    r = report(occupancy="parking_open", height_m=4, floors_above_grade=1, ground_floor_bua_m2=25000,
               plot_area_m2=30000, is_covered_shaded_parking=True)
    assert pump(r).spec.startswith("1000 gpm") and lines(r, "FP", "Yard Fire Hydrant")
    r = report(occupancy="parking_open", height_m=4, floors_above_grade=1, ground_floor_bua_m2=2000,
               is_covered_shaded_parking=True)
    assert lines(r, "FP", "Table 9.24.D - no printed requirement", status="conditional")


# ------------------------------------------------- Ch 5 / 6 / 7 / 8
def test_CH47_02_converted_villa_and_multistorey_fuel_get_sign_items():
    for kw in (dict(occupancy="villa_private", villa_converted_use=True),
               dict(occupancy="motor_fuel_dispensing", fuel_dispensing_multistorey=True)):
        r = report(height_m=7, floors_above_grade=2, ground_floor_bua_m2=500, **kw)
        names = [it.system for it in items(r, "ES", required_only=True)]
        assert "Exit Signs at Exit Doors" in names and "Exit Signs at Exit Stairs" in names
        assert not [it for it in items(r, "ES") if it.status == "not_required"]


def test_CH47_10_unconverted_commercial_villa_only_not_required():
    r = report(occupancy="villa_commercial", height_m=8, floors_above_grade=2, ground_floor_bua_m2=500)
    assert [it.status for it in items(r, "ES")] == ["not_required"]


def test_CH47_06_one_el_system_type_line_for_malls():
    r = report(occupancy="mall_covered", height_m=12, ground_floor_bua_m2=5000)
    el = [it for it in items(r, "EL") if "Central Battery" in it.system or "Monitored" in it.system]
    assert len(el) == 1 and "OR" in el[0].system and el[0].status == "required"


def test_ENG_08_highrise_parking_gets_evc():
    r = report(occupancy="parking_enclosed", height_m=24, ground_floor_bua_m2=3000)
    assert not [it for it in items(r, "EVC") if it.status == "not_required"]
    assert items(r, "EVC", required_only=True)


def test_CH8_09_plant_nursery_only_not_required():
    r = report(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000,
               is_plant_nursery=True)
    assert "fa_storage_industrial" not in [b["id"] for b in engine._select_branches(
        engine.load_rules("ch8_fire_alarm.yaml")["branches"], r.building)]


def test_CH8_10_cold_storage_no_whole_building_smoke():
    r = report(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000,
               is_cold_storage=True)
    assert not [it for it in items(r, "FA") if "(entire building)" in it.system]


def test_CH8_15_fa_height_text_cites_ch1():
    r = report(occupancy="residential", height_m=20, ground_floor_bua_m2=800)
    text = " ".join((it.detail or "") + (it.spec or "") for it in items(r, "FA"))
    assert "<= 15 m" not in text


# ------------------------------------------------- Ch 10
def test_CH10_01_any_basement_gets_table_10_22_items_2_and_4():
    r = report(occupancy="residential", height_m=14, floors_below_grade=1,
               depth_below_grade_m=4, ground_floor_bua_m2=1000)
    req = [it.system for it in items(r, "SC", required_only=True)]
    assert any(s.startswith("Passenger Elevator Lobby at Underground") for s in req)
    assert any(s.startswith("Corridor and Open Circulation Smoke Management") for s in req)
    assert any("Section 2.13" in s for s in req)


def test_CH10_02_known_case_no_contradictions():
    r = report(occupancy="business", height_m=20, floors_below_grade=3,
               depth_below_grade_m=10.5, ground_floor_bua_m2=1000)
    sc = items(r, "SC")
    names = [it.system for it in sc]
    assert names.count("Stair Pressurization (basement stairs, depth more than 7 m)") == 1
    assert "Firefighting Lift (NOT mandatory)" not in names
    assert "Stair Pressurization (open-plan office in highrise)" not in names


def test_CH10_04_high_depth_occupancy_without_numbers():
    r = report(occupancy="high_depth_underground", height_m=6, ground_floor_bua_m2=1000)
    req = [it.system for it in items(r, "SC", required_only=True)]
    # Re-pointed in phase 3 (CH10-27): with no depth entered the rows are
    # FAQ #29.i (more than 2 levels) and Ch 2 #2.9.4.a, not the Table 10.22
    # depth rows, which are named NOT EVALUATED.
    assert "Stair Pressurization (basement stairs, more than 2 basement levels)" in req
    assert "Firefighting Lift (more than 2 basements)" in req


def test_CH10_37_one_tunnel_line():
    r = report(occupancy="business", height_m=10, ground_floor_bua_m2=2000, has_tunnel=True)
    assert len([it for it in items(r, "SC") if it.system.startswith("Tunnel Smoke Management")]) == 1


# ------------------------------------------------- attached parking
def test_attached_parking_carries_routing_inputs():
    r = report(occupancy="hotel_a", height_m=18, ground_floor_bua_m2=1000, plot_area_m2=2000,
               has_parking_area=True, attached_parking_kind="open", exit_stairs=3,
               parking_area_m2=1000,  # phase 3 (ENG-11): the parking area is required
               # P3 App Q2 (owner ruling 12.10.2026): the parking's own height and levels
               parking_height_m=18, parking_basement_levels=0)
    # Owner ruling Q-3 (28.10.2026): one governing pump for host + parking, kept in the
    # host's Ch 9 chapter; the parking's Table 9.24.C.2 pump (3 stairs: 1000 gpm) governs.
    ch = next(c for c in r.attached_parking_chapters if c.chapter_code == "FP")
    assert not [it for b in ch.blocks for it in b.items
                if it.system.startswith("Fire Pump") and it.status == "required"]
    p = pump(r)
    assert p.spec.startswith("1000 gpm") and "Table 9.24.C.2" in p.code_ref


# ------------------------------------------- R14 / CH9A-09 (#4.1.5, p.694)
def test_R14_lift_machine_room_sprinkler_only_in_sprinklered_buildings():
    """Ruling R14 12.10.2026: Table 9.30.M only when the building is sprinklered."""
    r = report(occupancy="assembly_c", height_m=7, floors_above_grade=2, ground_floor_bua_m2=600,
               villa_converted_use=True)
    assert not lines(r, "FP", "Lift Machine Room")
    lmr = lines(r, "FP", "Lift Machine Room", status="not_required")
    assert lmr
    assert "#4.1.5" in lmr[0].code_ref and lmr[0].page_ref == "p.694"
    r = report(occupancy="business", height_m=21, floors_above_grade=6, floors_below_grade=3,
               depth_below_grade_m=10.5, ground_floor_bua_m2=1000, plot_area_m2=5000)
    lmr = lines(r, "FP", "Lift Machine Room")
    assert lmr and lmr[0].status == "required" and "Table 9.30.M" in lmr[0].code_ref


def test_R14b_every_table_9_30_room_gated_by_4_1_5():
    """Ruling R14b 12.10.2026: #4.1.5 applies to every Table 9.30 room."""
    kw = dict(has_main_electrical_room=True, has_diesel_generator_room=True,
              has_main_server_room=True, has_battery_room=True)
    # plot area entered: with it blank the Table 9.21.b row, and the sprinkler test, is
    # NOT EVALUATED (verifier 28.10.2026, blank-input residual).
    r = report(occupancy="residential", height_m=10, ground_floor_bua_m2=300, plot_area_m2=1000, **kw)
    # Owner ruling R-E (28.10.2026): the diesel generator room takes Table 9.31.E regardless
    # of sprinklers (citing Table 9.30.G too), so it has no #4.1.5 note.
    assert not [it for it in items(r, "FP")
                if "Table 9.30" in (it.code_ref or "") and it.status != "not_required"
                and not it.system.startswith("Diesel Generator Room")]
    notes = [it for it in items(r, "FP") if "#4.1.5" in (it.code_ref or "")]
    assert {n.system.split(" - ")[0] for n in notes} >= {"Main Electrical Room", "Main Server Room"}
    assert "Diesel Generator Room" not in {n.system.split(" - ")[0] for n in notes}
    assert lines(r, "FP", "Diesel Generator Room")[0].source_rule == "eq_E_diesel_generator"
    assert lines(r, "FP", "Battery Room", status="not_required")      # 9.30.D "None", ungated
    r = report(occupancy="business", height_m=21, floors_above_grade=6, floors_below_grade=3,
               depth_below_grade_m=10.5, ground_floor_bua_m2=1000, plot_area_m2=5000, **kw)
    for room in ("Main Electrical Room", "Diesel Generator Room", "Main Server Room"):
        assert lines(r, "FP", room), room
    assert not [it for it in items(r, "FP") if "#4.1.5" in (it.code_ref or "")]
