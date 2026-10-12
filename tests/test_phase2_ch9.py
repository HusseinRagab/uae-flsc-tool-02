"""Phase 2 package ch9 (audit 12.10.2026): one test per fixed finding.

Ch 9 storage (Table 9.27), special hazards (Tables 9.25, 9.26, 9.28), Table 9.29
rows, Tables 9.30 / 9.31 and the #1.1.13 hazard defaults. Code values in the
asserts are read off the rendered pages named in each rule's `page:` field.
Run with `python -m pytest tests/test_phase2_ch9.py`.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import yaml  # noqa: E402

import engine  # noqa: E402
from flsc_schema import default_hazard, Building  # noqa: E402
from test_phase1_findings import report, items, lines, pump, tank  # noqa: E402


def store(**kw):
    kw.setdefault("occupancy", "storage_industrial")
    kw.setdefault("height_m", 8)
    kw.setdefault("plot_area_m2", 20000)
    return report(**kw)


def branch(r):
    return r.chapter("FP").selected_branch


def names(r, code="FP", status=None):
    return [it.system for it in items(r, code) if status is None or it.status == status]


def block(r, word):
    return [it for b in r.chapter("FP").blocks if word in b.title for it in b.items]


RULES = yaml.safe_load((ROOT / "rules" / "ch9_fire_protection.yaml").read_text(encoding="utf-8"))
BRANCH_PAGE = {br["id"]: br.get("page") for br in RULES["branches"]}


# ------------------------------------------------------------ Table 9.27
def test_CH9C_01_extra_hazard_group_2_reaches_groups_E_and_J():
    multi = store(ground_floor_bua_m2=3000, hazard_class="HH", is_extra_hazard_2=True)
    assert branch(multi) == "storage_industrial_eh2_tier1"
    assert pump(multi).spec.startswith("1000 gpm @ 4.5 bar")
    assert any("0.40 gpm / 232 m2" in (it.spec or "") for it in items(multi, "FP"))
    big = store(ground_floor_bua_m2=5000, hazard_class="HH", is_extra_hazard_2=True)
    assert pump(big).spec.startswith("1500 gpm @ 6.9 bar")
    assert tank(big).spec.startswith("120 minutes")
    single = store(ground_floor_bua_m2=2000, hazard_class="HH", is_extra_hazard_2=True,
                   is_single_tenant_storage=True)
    assert branch(single) == "storage_single_tenant_eh2_tier1"


def test_CH9C_02_single_tenant_LH_density_is_0_15_gpm_140_m2():
    for gf in (2000, 5000):
        r = store(ground_floor_bua_m2=gf, hazard_class="LH", is_single_tenant_storage=True)
        spr = lines(r, "FP", "Automatic Sprinkler System")
        assert spr and "0.15 gpm / 140 m2" in spr[0].spec, gf
        assert "0.10" not in spr[0].spec


def test_CH9C_03_hangar_group_I_3000_gpm_groups_II_III_and_IV_1500_gpm():
    g1 = store(ground_floor_bua_m2=4000, hazard_class="OH2", is_aircraft_hanger=True)
    assert pump(g1).spec.startswith("3000 gpm @ 6.9 bar")
    assert "Foam-Water Hand Hose System" in names(g1, status="required")
    g2 = store(ground_floor_bua_m2=4000, hazard_class="OH2", is_aircraft_hanger=True,
               hangar_group="II_III")
    assert branch(g2) == "storage_aircraft_hanger_ii_iii"
    assert pump(g2).spec.startswith("1500 gpm @ 6.9 bar")
    assert "465 m2" in lines(g2, "FP", "Foam-Water Deluge System")[0].spec
    g4 = store(ground_floor_bua_m2=4000, hazard_class="OH2", is_aircraft_hanger=True,
               hangar_group="IV")
    assert branch(g4) == "storage_aircraft_hanger_iv"
    assert pump(g4).spec.startswith("1500 gpm")


def test_CH9C_04_commodity_groups_L_to_O_reachable():
    tires = store(ground_floor_bua_m2=2000, hazard_class="HH", storage_commodity="tires")
    assert branch(tires) == "storage_commodity_tires_r3"
    assert "Table 9.7.FF" in pump(tires).spec and "4.5 bar" in pump(tires).spec
    assert tank(tires).spec.startswith("90 minutes") and "breeching" in tank(tires).spec
    plastics = store(ground_floor_bua_m2=150, hazard_class="HH", storage_commodity="plastics_rubber")
    assert branch(plastics) == "storage_commodity_plastics_r1"
    assert pump(plastics).spec.startswith("50 gpm @ 4.5 bar")
    assert tank(plastics).spec.startswith("60 minutes")
    for comm, bid in (("class_i_iv", "storage_commodity_class_i_iv_r4"),
                      ("rolled_paper", "storage_commodity_paper_r4")):
        assert branch(store(ground_floor_bua_m2=5000, hazard_class="OH2",
                            storage_commodity=comm)) == bid


def test_CH9C_05_group_T_aboveground_tank_storage():
    big = store(ground_floor_bua_m2=1000, hazard_class="HH", is_aboveground_tank_storage=True,
                ast_storage_area_m2=1000, ast_tank_capacity_m3=500)
    assert branch(big) == "storage_aboveground_tanks_r2"
    req = names(big, status="required")
    assert any(n.startswith("Fixed Low Expansion Foam System") for n in req)
    assert any(n.startswith("Yard Fire Hydrants") for n in req)
    assert lines(big, "FP", "Cooling Deluge Water Spray System", status="conditional")
    assert tank(big).spec.startswith("120 minutes")
    p = [it for it in items(big, "FP") if it.system.startswith("Fire Pump")]
    assert "additional 1000 gpm" in p[0].spec
    small = store(ground_floor_bua_m2=100, hazard_class="HH", is_aboveground_tank_storage=True,
                  ast_storage_area_m2=100, ast_tank_capacity_m3=50)
    assert branch(small) == "storage_aboveground_tanks_r1"
    assert pump(small).spec.startswith("100 gpm @ 4.5 bar")
    # Not stated (0) never takes the small row.
    assert branch(store(ground_floor_bua_m2=100, hazard_class="HH",
                        is_aboveground_tank_storage=True)) == "storage_aboveground_tanks_r2"


def test_CH9C_06_cold_storage_has_a_fire_pump_at_every_row():
    for gf, bar in ((150, "4.5 bar"), (500, "4.5 bar"), (2000, "6.9 bar"), (5000, "6.9 bar")):
        r = store(ground_floor_bua_m2=gf, hazard_class="OH1", is_cold_storage=True)
        assert bar in pump(r).spec, gf


def test_CH9C_07_CH9D_03_exterior_balcony_sprinklers():
    r = report(occupancy="residential", height_m=55, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_exterior_balconies=True)
    bal = lines(r, "FP", "Exterior Balcony Sprinklers")
    assert bal and "12 m2 per sprinkler head" in bal[0].spec and "79 deg C" in bal[0].spec
    assert "Table 9.29 row B" in bal[0].code_ref


def test_CH9C_08_public_washrooms_without_heater_flag():
    r = report(occupancy="mall_covered", height_m=20, ground_floor_bua_m2=5000, plot_area_m2=20000)
    wc = lines(r, "FP", "Public Washrooms and Bathrooms")
    assert wc and "Table 9.29 row G.ii" in wc[0].code_ref


def test_CH9C_09_hotels_OH1_stables_OH2():
    assert {default_hazard(o) for o in ("hotel_a", "hotel_b", "hotel_c")} == {"OH1"}
    assert default_hazard("animal_housing") == "OH2"


def test_CH9C_10_groups_R_and_S_foam_in_hose_reels_and_hydrants():
    s = store(ground_floor_bua_m2=1000, hazard_class="HH", is_flammable_liquid_industrial=True)
    assert lines(s, "FP", "Hose Reel System (incorporating foam application)")
    r4 = store(ground_floor_bua_m2=5000, hazard_class="HH", is_flammable_liquid_warehouse=True)
    hyd = lines(r4, "FP", "Yard Fire Hydrants")
    assert hyd and "foam" in (hyd[0].detail or "").lower()


def test_CH9C_11_open_yard_over_3600_trolley_foam_and_no_hose_reel():
    r = store(ground_floor_bua_m2=5000, hazard_class="OH2", is_open_yard_storage=True)
    assert branch(r) == "storage_open_yard_r4"
    assert lines(r, "FP", "Trolley Type Foam Extinguishers")
    assert lines(r, "FP", "Hose Reel System", status="not_required")
    assert pump(r).spec.startswith("500 gpm @ 6.9 bar")
    assert tank(r).spec.startswith("60 minutes")


def test_CH9C_12_group_A_tiers_use_unit_compartment_area():
    t1 = store(ground_floor_bua_m2=800, max_unit_area_m2=100, hazard_class="LH")
    assert branch(t1) == "storage_industrial_tier1_lh"
    assert pump(t1).spec.startswith("50 gpm @ 4.5 bar") and tank(t1).spec.startswith("30 minutes")
    t2 = store(ground_floor_bua_m2=1200, max_unit_area_m2=100, hazard_class="LH")
    assert branch(t2) == "storage_industrial_tier2_lh"
    assert pump(t2).spec.startswith("250 gpm") and tank(t2).spec.startswith("45 minutes")
    # Unit area not stated: the whole ground floor is one unit (never the smaller tier).
    assert branch(store(ground_floor_bua_m2=1200, hazard_class="LH")) == "storage_industrial_tier3_lh"


def test_CH9C_13_hangar_hose_reel_not_required():
    r = store(ground_floor_bua_m2=4000, hazard_class="OH2", is_aircraft_hanger=True)
    assert lines(r, "FP", "Dry Riser, Wet Riser and Hose Reel System", status="not_required")
    assert not [n for n in names(r, status="required") if n.startswith("Hose Reel")]


def test_CH9C_14_idle_pallets_tiered():
    small = store(ground_floor_bua_m2=500, hazard_class="OH2", is_idle_pallet_storage=True)
    assert pump(small).spec.startswith("50 gpm @ 4.5 bar")
    assert tank(small).spec.startswith("45 minutes")
    assert not lines(small, "FP", "Automatic Sprinkler")
    mid = store(ground_floor_bua_m2=2000, hazard_class="OH2", is_idle_pallet_storage=True)
    assert "9.7.G" in pump(mid).spec and "4.5 bar" in pump(mid).spec
    assert tank(mid).spec.startswith("60 minutes") and "breeching" in tank(mid).spec


def test_CH9C_15_groups_R_and_S_row_1_and_R_hydrants_only_in_row_4():
    for flag in ("is_flammable_liquid_warehouse", "is_flammable_liquid_industrial"):
        r = store(ground_floor_bua_m2=150, hazard_class="HH", **{flag: True})
        assert pump(r).spec.startswith("50 gpm @ 4.5 bar"), flag
        assert tank(r).spec.startswith("45 minutes"), flag
        assert not lines(r, "FP", "Foam Solution Reserve"), flag
    r3 = store(ground_floor_bua_m2=2000, hazard_class="HH", is_flammable_liquid_warehouse=True)
    assert not lines(r3, "FP", "Yard Fire Hydrants")


def test_CH9C_16_cold_storage_under_230_m2_hose_reel_only():
    r = store(ground_floor_bua_m2=150, hazard_class="OH1", is_cold_storage=True)
    assert not [n for n in names(r, status="required") if "Sprinkler" in n]
    assert tank(r).spec.startswith("30 minutes")


def test_CH9C_17_cold_storage_is_below_4_deg_C():
    r = store(ground_floor_bua_m2=2000, hazard_class="OH1", is_cold_storage=True)
    assert "below 4 deg C" in r.chapter("FP").selected_branch_section
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "below 4 deg C - Group P" in src and "< 40 deg C" not in src


def test_CH9C_18_hazard_defaults_follow_1_1_13():
    assert default_hazard("mercantile_b") == "OH1"
    assert default_hazard("parking_enclosed") == "OH1"
    for occ in ("assembly_b", "assembly_c", "labour_accommodation",
                "detention_a", "detention_b", "detention_c"):
        assert default_hazard(occ) == "LH", occ
    # Attached enclosed parking sub-evaluation no longer forces OH2.
    r = report(occupancy="hotel_a", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_parking_area=True, attached_parking_kind="enclosed", parking_area_m2=2000)
    src = (ROOT / "engine.py").read_text(encoding="utf-8")
    assert 'hazard_class="OH2" if synth_occ' not in src
    assert r is not None


def test_CH9C_19_high_ceiling_design_starts_above_10_m():
    kw = dict(occupancy="business", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
              has_high_ceiling=True)
    at10 = engine.evaluate(Building(ceiling_height_m=10.0, floors_above_grade=8, **kw))
    assert at10.high_ceiling.not_required and at10.high_ceiling.k_factor is None
    assert "exceeds 10 m" in at10.high_ceiling.note
    above = engine.evaluate(Building(ceiling_height_m=10.1, floors_above_grade=8, **kw))
    assert above.high_ceiling.height_range == "10 m to 13.5 m"


def test_CH9C_20_CH9D_12_table_9_29_rows_cited_as_rows():
    r = report(occupancy="mall_covered", height_m=20, ground_floor_bua_m2=5000,
               plot_area_m2=20000, has_atrium=True)
    atr = lines(r, "FP", "Atrium Sprinklers", status="recommended")
    assert atr and atr[0].code_ref.endswith("Table 9.29 row A")
    for rule in RULES["various_locations"]:
        for e in rule["systems"]:
            assert "Table 9.29." not in (e.get("code_ref") or ""), rule["id"]


def test_CH9C_21_page_citations():
    assert BRANCH_PAGE["storage_industrial_tier3_lh"] == "p.724"
    assert BRANCH_PAGE["storage_industrial_tier4_lh"] == "p.724"
    assert BRANCH_PAGE["tunnel_road_rail_medium"] == "p.747"
    assert BRANCH_PAGE["storage_open_yard"] == "p.746"
    assert BRANCH_PAGE["storage_single_tenant_eh2_tier1"] == "p.733"
    for g, p in (("class_i_iv", "p.735"), ("plastics", "p.736"), ("tires", "p.737"),
                 ("paper", "p.738")):
        assert BRANCH_PAGE[f"storage_commodity_{g}_r1"] == p
    assert "storage_industrial_tier_hh" not in BRANCH_PAGE


def test_CH9C_22_motor_fuel_tank_item_not_required_by_table_9_25():
    r = report(occupancy="motor_fuel_dispensing", motor_fuel_group="C", height_m=5,
               ground_floor_bua_m2=200, plot_area_m2=2000)
    tanks = [it for it in items(r, "FP") if it.system.startswith("Fuel Storage Tanks")]
    assert tanks and all(it.status == "recommended" for it in tanks)
    assert "Table 9.25" in tanks[0].detail


def test_CH9C_23_marina_cites_ch_20_table_20_5():
    r = report(occupancy="infrastructure", height_m=0, ground_floor_bua_m2=0, plot_area_m2=50000)
    m = [it for it in items(r, "FP") if it.system.startswith("Marina")]
    assert m and "Ch 20, Table 20.5" in m[0].code_ref and "p.1268" in m[0].page_ref


def test_CH9C_24_groups_G_H_density_area_140_m2():
    for hz, dens in (("OH1", "0.15 gpm / 140 m2"), ("OH2", "0.20 gpm / 140 m2")):
        r = store(ground_floor_bua_m2=2000, hazard_class=hz, is_single_tenant_storage=True)
        spr = lines(r, "FP", "Automatic Sprinkler System")[0]
        assert dens in spr.spec and "139" not in spr.spec and "9.7.F" not in spr.spec


def test_CH9C_25_groups_I_and_J_separate_J_breeching_and_hydrants():
    j1 = store(ground_floor_bua_m2=2000, hazard_class="HH", is_extra_hazard_2=True,
               is_single_tenant_storage=True)
    assert pump(j1).spec.startswith("1000 gpm @ 4.5 bar")
    assert tank(j1).spec.startswith("60 minutes") and "breeching" in tank(j1).spec
    j2 = store(ground_floor_bua_m2=5000, hazard_class="HH", is_extra_hazard_2=True,
               is_single_tenant_storage=True)
    assert lines(j2, "FP", "Yard Fire Hydrants")
    i = store(ground_floor_bua_m2=2000, hazard_class="HH", is_single_tenant_storage=True)
    assert branch(i) == "storage_single_tenant_extra_hazard"
    assert "EH2" not in " ".join(it.spec or "" for it in items(i, "FP") if it.duty)


def test_CH9C_27_tunnel_length_0_is_a_missing_input():
    r = report(occupancy="business", height_m=20, ground_floor_bua_m2=1000, plot_area_m2=2000,
               has_tunnel=True, tunnel_kind="road_rail", tunnel_length_m=0)
    assert lines(r, "FP", "Tunnel Length Required", status="conditional")
    assert not lines(r, "FP", "No Tunnel Fire Protection System Required", status="not_required")
    short = report(occupancy="business", height_m=20, ground_floor_bua_m2=1000, plot_area_m2=2000,
                   has_tunnel=True, tunnel_kind="road_rail", tunnel_length_m=50)
    none = lines(short, "FP", "No Tunnel Fire Protection System Required", status="not_required")
    assert none and "Chapter 4" not in none[0].detail


def test_CH9C_28_storage_hazard_forced_and_plot_sum_input():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and any(k.arg == "key" and getattr(k.value, "value", None) == "storage_hazard_input"
                     for k in n.keywords)]
    assert calls, "storage hazard selector missing"
    idx = [k.value for k in calls[0].keywords if k.arg == "index"]
    assert idx and isinstance(idx[0], ast.Constant) and idx[0].value is None
    # Tier 4 reads the sum of GF BUAs of every building on the plot (#4.1.13).
    r = store(ground_floor_bua_m2=800, max_unit_area_m2=100, sum_gf_bua_m2=4000, hazard_class="LH")
    assert branch(r) == "storage_industrial_tier4_lh"


# ------------------------------------------------------- Tables 9.29-9.31
def test_CH9D_02_heater_bathrooms_protect_the_above_false_ceiling_space():
    r = report(occupancy="residential", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_bathrooms_with_heaters=True)
    it = lines(r, "FP", "Above-False-Ceiling Space of Bathrooms with Heaters")
    assert it and "electric" not in (it[0].detail or "").lower()
    assert not lines(r, "FP", "Public Washrooms")             # residential: row G.iii
    assert lines(r, "FP", "Residential / Hotel / Apartment Washrooms", status="not_required")


def test_CH9D_04_control_room_exemption_keeps_critical_systems_condition():
    r = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_control_room=True)
    cr = lines(r, "FP", "Control Room / Fire Command Centre")[0]
    assert "not with critical life or building monitoring and control systems" in cr.detail
    assert "preferred" not in cr.detail


def test_CH9D_05_atrium_draft_stops_required():
    r = report(occupancy="mall_covered", height_m=20, ground_floor_bua_m2=5000,
               plot_area_m2=20000, has_atrium=True)
    assert lines(r, "FP", "Atrium Draft Stops - non-combustible, 450 mm deep", status="required")


def test_CH9D_06_kitchen_hood_shuts_fuel_and_electric_power():
    r = report(occupancy="hotel_a", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_commercial_kitchen=True)
    k = lines(r, "FP", "Commercial Kitchen Hood")[0]
    assert "electric power" in k.detail and "manual resetting" in k.detail
    assert "UL-300" not in k.detail


def test_CH9D_07_above_false_ceiling_note_row_F():
    r = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000)
    f = lines(r, "FP", "Above False Ceiling Spaces", status="not_required")
    assert f and "fire stopping" in f[0].detail
    assert not [it for it in items(r, "FP") if "concealed" in (it.detail or "").lower()]
    # Unsprinklered building: the standing notes stay silent (no #4.13.1 echo).
    villa = report(occupancy="villa_private", height_m=8, ground_floor_bua_m2=300)
    assert not lines(villa, "FP", "Above False Ceiling Spaces", status="not_required")
    assert not lines(villa, "FP", "Public Washrooms", status="not_required")


def test_CH9D_09_lpg_underground_mounded_not_given_aboveground_spray():
    r = report(occupancy="residential", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_lpg_tanks=True, has_lpg_tank_underground_mounded=True)
    lpg = [it for it in items(r, "FP") if it.system.startswith("LPG Tanks")]
    assert len(lpg) == 1 and lpg[0].status == "conditional"
    assert "aboveground or on roofs or podiums" in lpg[0].detail


def test_CH9D_10_diesel_generator_foam_sprinkler_listed_once():
    r = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_diesel_generator_room=True)
    dg = [it for it in items(r, "FP") if it.system.startswith("Diesel Generator")]
    assert len(dg) == 1 and "Table 9.31.E" in dg[0].code_ref
    assert "de-duplication" not in (dg[0].detail or "")
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '("has_diesel_generator_room", False)' in src


def test_CH9D_11_no_added_preferences_and_msds_note():
    for sec in ("auxiliary_rooms", "equipment"):
        for rule in RULES[sec]:
            for e in rule["systems"]:
                text = (e.get("detail") or "") + (e.get("name") or "")
                for word in ("preferred", "NFPA 1 ", "VESDA", "UL-300", "FRP", "typical for"):
                    assert word not in text, (rule["id"], word)
    r = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_main_server_room=True)
    note = lines(r, "FP", "Auxiliary Room System Selection")
    assert note and "MSDS" in note[0].detail and "#4.1.16" in note[0].code_ref


def test_CH9D_13_table_9_30_exemption_text_complete():
    r = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_rmu_idf_mdf_room=True, has_gsm_room=True, has_lv_mv_room=True,
               has_transformer_room_private=True)
    for room in ("RMU / IDF", "GSM Room", "LV / MV Room", "Transformer Room (private)"):
        it = lines(r, "FP", room)[0]
        assert "separated service blocks" in it.detail, room
    for room in ("RMU / IDF", "GSM Room"):
        assert "less than 10 m2" in lines(r, "FP", room)[0].detail
    assert "podium floor" in lines(r, "FP", "LV / MV Room")[0].detail


def test_CH9D_14_wet_chemical_states_3_burner_condition():
    r = report(occupancy="hotel_a", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_commercial_kitchen=True)
    assert "3 or more burners" in lines(r, "FP", "Commercial Kitchen Hood")[0].spec
