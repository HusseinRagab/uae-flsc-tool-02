"""Fix round 28.10.2026, area ch9: audit ledgers CH09A (F9A-01..13) and CH09B (CH9B2-01..21),
Cursor PRs #26 / #27 / #18 residual, owner rulings R-C, R-E, R-G, R-H, R-J, Q-1, Q-3, Q-4.

Values are read off the code pages named in each test (CDGH-OP-25, September 2018).
"""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from flsc_schema import Building  # noqa: E402
from test_phase1_findings import items, lines, pump, report, tank  # noqa: E402


def fp_all(r):
    return items(r, "FP")


def branches(r):
    """Every FP branch rule id that produced a line (source_rule of the branch block)."""
    ch = r.chapter("FP")
    return {it.source_rule for b in ch.blocks for it in b.items}


def named(r, prefix, status=None, code="FP"):
    return [it for it in items(r, code) if it.system.startswith(prefix)
            and (status is None or it.status == status)]


def pk(r, code="FP"):
    return next((c for c in r.attached_parking_chapters if c.chapter_code == code), None)


def pk_items(r, code="FP"):
    c = pk(r, code)
    return [it for b in c.blocks for it in b.items] if c else []


def store(**kw):
    kw.setdefault("occupancy", "storage_industrial")
    kw.setdefault("height_m", 8)
    kw.setdefault("plot_area_m2", 20000)
    kw.setdefault("storage_tenancy", "multi")
    return report(**kw)


# ------------------------------------------------------------ F9A-01 / ruling R-C
def test_F9A_01_outlet_keeps_host_table_and_most_onerous_pump_governs():
    """p.707 Table 9.21.b.2 (GF > 3600 m2: sprinklers, 750 / 1000 gpm @ 6.9 bar) and p.711
    Table 9.21.e.1 (outlet up to 900 m2: 50 gpm @ 4.5 bar) both apply (ruling R-C)."""
    r = report(occupancy="business", business_group="B", height_m=12, floors_above_grade=3,
               ground_floor_bua_m2=5000, plot_area_m2=5000,
               has_attached_commercial_outlet=True, commercial_outlet_gf_bua_m2=200)
    br = branches(r)
    assert "lowrise_residential_over_3600" in br
    assert "lowrise_commercial_outlet_attached_small" in br
    assert named(r, "Automatic Sprinkler System", "required")
    p = pump(r)
    assert p.spec.startswith("750 gpm @ 6.9 bar")
    assert "Table 9.21.e.1" in p.detail and "50 gpm @ 4.5 bar" in p.detail
    a = report(occupancy="assembly_c", height_m=8, floors_above_grade=2,
               ground_floor_bua_m2=1000, plot_area_m2=5000,
               has_attached_commercial_outlet=True, commercial_outlet_gf_bua_m2=100)
    assert "lowrise_public_501_3600" in branches(a)
    assert pump(a).spec.startswith("300 gpm @ 4.5 bar")


def test_PR26_blank_outlet_area_keeps_host_tier_with_named_line():
    """PR #26 re-checked against R-C: the host Table 9.21.b row stays; Table 9.21.e is named
    NOT EVALUATED (p.711). PR #26 (suppress the host tiers) is not ported."""
    r = report(occupancy="business", business_group="B", height_m=7, floors_above_grade=2,
               ground_floor_bua_m2=2000, plot_area_m2=5000, has_attached_commercial_outlet=True)
    assert "lowrise_residential_upto_3600" in branches(r)
    assert named(r, "Commercial Outlet GF BUA (Table 9.21.e) - NOT EVALUATED", "not_evaluated")


def test_F9A_13_villa_outlet_row_is_G_plus_1_and_mosque_wording():
    """p.711 Table 9.21.e row A 'VILLAS (G+1)', row C 'MOSQUES'."""
    kw = dict(occupancy="villa_private", height_m=10, ground_floor_bua_m2=400, plot_area_m2=2000,
              has_attached_commercial_outlet=True, commercial_outlet_gf_bua_m2=300)
    g1 = report(floors_above_grade=2, **kw)
    assert "lowrise_commercial_outlet_attached_small" in branches(g1)
    g2 = report(floors_above_grade=3, **kw)
    assert "lowrise_commercial_outlet_attached_small" not in branches(g2)
    note = named(g2, "Commercial Outlet (Table 9.21.e) - villa above G+1")
    assert note and note[0].status == "conditional" and "G+1" in note[0].detail
    m = report(occupancy="assembly_c", height_m=8, floors_above_grade=2, ground_floor_bua_m2=400,
               plot_area_m2=2000, has_attached_commercial_outlet=True,
               commercial_outlet_gf_bua_m2=300)
    ex = named(m, "Hose Reel / Dry Landing Valve (exemption)")
    assert ex and "MOSQUES" in ex[0].detail


# ------------------------------------------------------------ F9A-02
def test_F9A_02_attached_covered_parking_reaches_table_9_24_D():
    """p.721 Table 9.24.D 'covered / shaded parking having one level only': the one-level
    test is the parking's, not the 3-floor host's."""
    r = report(occupancy="residential", height_m=10, floors_above_grade=3,
               ground_floor_bua_m2=1000, plot_area_m2=5000, has_parking_area=True,
               attached_parking_kind="open", is_covered_shaded_parking=True,
               parking_area_m2=5000, parking_height_m=4, parking_basement_levels=0)
    assert pk(r).selected_branch == "parking_covered_d1"
    assert not [it for it in pk_items(r) if it.system.startswith("Automatic Sprinkler")
                and it.status == "required"]


# ------------------------------------------------------------ F9A-03 blank areas
def test_F9A_03_blank_gf_bua_never_takes_the_lowest_row():
    mid = report(occupancy="residential", height_m=18, floors_above_grade=5,
                 ground_floor_bua_m2=0, plot_area_m2=5000)
    assert "midrise_residential_upto_900" not in branches(mid)
    assert named(mid, "Built-up Ground Floor Area (Table 9.20.b) - NOT EVALUATED", "not_evaluated")
    low = report(occupancy="hotel_a", height_m=10, floors_above_grade=3,
                 ground_floor_bua_m2=0, plot_area_m2=5000)
    assert "lowrise_public_upto_500" not in branches(low)
    assert named(low, "Built-up Ground Floor Area (Table 9.21.a) - NOT EVALUATED", "not_evaluated")
    res = report(occupancy="residential", height_m=10, floors_above_grade=3,
                 ground_floor_bua_m2=0, plot_area_m2=5000)
    assert "lowrise_residential_upto_3600" not in branches(res)
    assert named(res, "Built-up Ground Floor Area (Table 9.21.b) - NOT EVALUATED", "not_evaluated")
    park = report(occupancy="parking_enclosed", height_m=10, floors_above_grade=3,
                  ground_floor_bua_m2=0, plot_area_m2=5000)
    assert "parking_enclosed_a1" not in branches(park)
    assert named(park, "Built-up Ground Floor Area (Table 9.24) - NOT EVALUATED", "not_evaluated")


def test_F9A_03_blank_plot_never_takes_the_lowest_row():
    mall = report(occupancy="mall_open", height_m=6, floors_above_grade=1,
                  ground_floor_bua_m2=3000, plot_area_m2=0)
    assert "mall_open_small" not in branches(mall)
    assert named(mall, "Plot Area (Table 9.22.B) - NOT EVALUATED", "not_evaluated")
    res = report(occupancy="residential", height_m=10, floors_above_grade=3,
                 ground_floor_bua_m2=2000, plot_area_m2=0)
    assert "lowrise_residential_upto_3600" not in branches(res)
    assert named(res, "Plot Area (Table 9.21.b) - NOT EVALUATED", "not_evaluated")
    pub = report(occupancy="hotel_a", height_m=10, floors_above_grade=3,
                 ground_floor_bua_m2=2000, plot_area_m2=0)
    assert "lowrise_public_501_3600" in branches(pub)
    assert named(pub, "Plot Area more than 20,000 m2 (Table 9.21.a row 4) - NOT EVALUATED",
                 "not_evaluated")


# ------------------------------------------------------------ F9A-04 / PR #18 residual
def test_F9A_04_single_exit_over_3600_takes_table_9_21_c_only():
    """p.709 #4.5.3 / Table 9.21.c.2 'MORE THAN 500 m2' (no upper bound): 300 gpm @ 4.5 bar."""
    for occ in ("residential", "hotel_a"):
        r = report(occupancy=occ, height_m=10, floors_above_grade=3, ground_floor_bua_m2=4000,
                   plot_area_m2=8000, has_single_exit_stair=True)
        br = branches(r)
        assert "lowrise_single_exit_over_500" in br
        assert not br & {"lowrise_public_over_3600", "lowrise_residential_over_3600"}
        assert pump(r).spec.startswith("300 gpm @ 4.5 bar")
        spr = named(r, "Automatic Sprinkler System", "required")
        assert len(spr) == 1 and "Table 3.30" in spr[0].detail


# ------------------------------------------------------------ F9A-05 / ruling Q-3
def test_F9A_05_attached_parking_one_governing_pump_and_tank():
    """#4.1.17 (p.695); owner ruling Q-3: one fire pump and one fire water tank line."""
    r = report(occupancy="residential", height_m=10, floors_above_grade=3, floors_below_grade=2,
               depth_below_grade_m=6, ground_floor_bua_m2=1000, plot_area_m2=5000,
               has_parking_area=True, parking_area_m2=2000, parking_height_m=0,
               parking_basement_levels=2, parking_depth_m=6)
    p, t = pump(r), tank(r)
    assert p.spec.startswith("300 gpm @ 4.5 bar")
    assert "Table 9.24.A.2" in p.code_ref and "Table 9.21.b.1" in p.code_ref
    assert "#4.1.17" in p.detail and "Q-3" in p.detail
    assert "#4.1.17" in t.detail
    assert not [it for it in pk_items(r) if it.duty in ("pump", "tank") and it.status == "required"]


# ------------------------------------------------------------ F9A-06 / CH9B2-03 / CH9B2-15 / Q-1
def test_Q1_4_1_7_reading_stated_and_pump_warning():
    r = store(hazard_class="OH2", floors_above_grade=4, height_m=14, ground_floor_bua_m2=500,
              max_unit_area_m2=100, sum_gf_bua_m2=500)
    spr = named(r, "Automatic Sprinkler System (full coverage)", "required")
    g = [it for it in spr if it.source_rule == "g_storage_sprinkler_over_3floors"]
    assert g and "G+3" in g[0].detail and "Q-1" in g[0].detail
    assert "NFPA 13" not in g[0].detail
    warn = named(r, "Sprinkler Pump / Tank Sizing (#4.1.7)", "required")
    assert warn and "#4.1.9" in warn[0].detail and "p.694" in warn[0].detail
    big = store(hazard_class="OH2", floors_above_grade=4, height_m=14, ground_floor_bua_m2=2000,
                sum_gf_bua_m2=2000)
    assert not named(big, "Sprinkler Pump / Tank Sizing (#4.1.7)")


# ------------------------------------------------------------ F9A-07 / PR #27
def test_F9A_07_row_F_gated_to_detached_G1_up_to_150():
    kw = dict(occupancy="healthcare_a", height_m=10, floors_above_grade=2,
              plot_area_m2=5000, tent_marquee_kind="small_detached")
    ok = report(ground_floor_bua_m2=150, **kw)
    assert "lowrise_small_detached" in branches(ok)
    assert not [b for b in branches(ok) if b and b.startswith("lowrise_public_")]
    over = report(ground_floor_bua_m2=2000, **kw)
    assert "lowrise_small_detached_limits_missing" in branches(over)
    assert named(over, "Detached G+1 / 150 m2 (Table 9.21.f.F) - NOT EVALUATED", "not_evaluated")
    assert not named(over, "Automatic Sprinkler", "required")
    tall = report(ground_floor_bua_m2=100, **{**kw, "floors_above_grade": 3})
    assert "lowrise_small_detached_limits_missing" in branches(tall)


def test_F9A_07_rows_A_to_E_only_at_lowrise_height():
    """#4.5.6 sits under 4.5 Lowrise (p.712): an Assembly A 30 m building with 'temporary'
    keeps Table 9.19 and prints no Table 9.21.f not_required lines."""
    r = report(occupancy="assembly_a", height_m=30, floors_above_grade=8, ground_floor_bua_m2=2000,
               plot_area_m2=5000, tent_marquee_kind="temporary")
    br = branches(r)
    assert "lowrise_tent_marquee_extinguishers_only" not in br
    assert not named(r, "Fire Pump", "not_required")
    note = named(r, "Table 9.21.f (tents / site offices) - not applied above 15 m")
    assert note and note[0].status == "conditional"


# ------------------------------------------------------------ F9A-08 / F9A-09 / F9A-11
def test_F9A_08_tool_added_text_removed():
    det = report(occupancy="detention_a", height_m=20, floors_above_grade=5,
                 ground_floor_bua_m2=2000, plot_area_m2=5000)
    pre = named(det, "Pre-action Sprinkler System")
    assert pre and "tamper" not in pre[0].detail.lower() and "Section 3.7" in pre[0].detail
    v = report(occupancy="villa_private", height_m=8, floors_above_grade=2,
               ground_floor_bua_m2=1600, plot_area_m2=3000)
    txt = " ".join((it.detail or "") + (it.spec or "") for it in fp_all(v))
    assert "podiums" not in txt and "Two-compartment" not in txt
    vc = report(occupancy="villa_commercial", height_m=8, floors_above_grade=2,
                ground_floor_bua_m2=400, plot_area_m2=25000)
    assert "Multiple breeching" not in " ".join(it.detail or "" for it in fp_all(vc))
    m = report(occupancy="mall_covered", height_m=18, floors_above_grade=3,
               ground_floor_bua_m2=20000, plot_area_m2=50000)
    assert "Class III" not in " ".join(it.detail or "" for it in fp_all(m))


def test_F9A_09_villa_rows_print_the_not_printed_items():
    v = report(occupancy="villa_private", height_m=8, floors_above_grade=2,
               ground_floor_bua_m2=1600, plot_area_m2=3000)
    assert named(v, "Dry Landing Valves and Risers", "not_required")
    dev = named(v, "Fire Pump Room and Fire Water Tank (commercial developments)")
    assert dev and "developer" in dev[0].detail
    base = report(occupancy="villa_private", height_m=8, floors_above_grade=2,
                  ground_floor_bua_m2=300, plot_area_m2=1000)
    assert "Table 9.23.A.1.b" in named(base, "Automatic Sprinkler System")[0].detail


def test_F9A_11_lowrise_rows_keep_printed_wording():
    p = report(occupancy="hotel_a", height_m=10, floors_above_grade=3,
               ground_floor_bua_m2=4000, plot_area_m2=5000)
    spr = named(p, "Automatic Sprinkler System", "required")
    assert "including basements and podiums (open as well as closed)" in spr[0].detail
    lp = report(occupancy="residential", height_m=10, floors_above_grade=3,
                ground_floor_bua_m2=2000, plot_area_m2=25000)
    yh = named(lp, "Yard Fire Hydrants", "required")
    assert any("Table 9.21.b.3.i shall apply" in (it.detail or "") for it in yh)


# ------------------------------------------------------------ F9A-10 / R-J, R-H
def test_RJ_exactly_90m_stays_table_9_19_with_edge_note():
    r = report(occupancy="residential", height_m=90, floors_above_grade=26,
               ground_floor_bua_m2=1500, plot_area_m2=5000)
    assert r.chapter("FP").selected_branch == "highrise_45_90_small_plot"
    note = named(r, "Height exactly 90.0 m")
    assert note and "R-J" in note[0].detail and "p.696" in note[0].detail
    r2 = report(occupancy="residential", height_m=89.99, floors_above_grade=26,
                ground_floor_bua_m2=1500, plot_area_m2=5000)
    assert not named(r2, "Height exactly 90.0 m")


def test_RH_detention_23m_or_more_note():
    r = report(occupancy="detention_a", height_m=30, floors_above_grade=8,
               ground_floor_bua_m2=2000, plot_area_m2=5000)
    assert r.chapter("FP").selected_branch == "highrise_23_45"
    note = named(r, "Detention 23 m or more - Table 9.20.d items")
    assert note and note[0].status == "conditional"
    assert "Table 9.20.d" in note[0].detail and "R-H" in note[0].detail


# ------------------------------------------------------------ F9A-12
def test_F9A_12_4_1_9_and_4_1_18_printed():
    r = report(occupancy="residential", height_m=30, floors_above_grade=9,
               ground_floor_bua_m2=1500, plot_area_m2=5000)
    assert "#4.1.9" in pump(r).detail
    inf = report(occupancy="infrastructure", plot_area_m2=30000)
    m = named(inf, "Common Fire Pump Set / Master Water Tank (#4.1.17 / #4.1.18)")
    assert m and m[0].status == "recommended" and "500,000 gallons" in m[0].spec


# ------------------------------------------------------------ CH9B2-01 / 06 / 07 / 21 (H9)
def test_CH9B2_01_pump_set_is_electric_plus_diesel_plus_jockey():
    r = report(occupancy="residential", height_m=30, floors_above_grade=9,
               ground_floor_bua_m2=1500, plot_area_m2=5000)
    d = pump(r).detail
    assert "1 electric driven fire pump, 1 diesel driven fire pump and 1 jockey pump" in d
    assert "Table 9.3 item 1.xii" in d and "p.567" in d and "8 hour" in d
    assert "Table 9.6" in d and "item 3.i" in d
    assert "item 1.xv" in d and "Civil Defence" in d          # CH9B2-07 / CH9B2-06
    txt = " ".join((it.detail or "") + " " + (it.spec or "") for it in fp_all(r)).lower()
    assert "electric or diesel" not in txt and "ul/fm" not in txt
    v = report(occupancy="villa_private", height_m=8, floors_above_grade=2,
               ground_floor_bua_m2=1600, plot_area_m2=3000)
    assert "Electric-driven" not in pump(v).detail
    assert "250 gpm" in pump(v).spec
    s = report(occupancy="residential", height_m=120, floors_above_grade=35,
               ground_floor_bua_m2=1800, plot_area_m2=5000)
    up = named(s, "Upper-level Pump Sets (every 90 m)")
    assert up and "item 1.xiii" in up[0].detail and "different sources" in up[0].detail


def test_CH9B2_21_dubai_esl_note_on_pumps_of_500_gpm_or_more():
    big = report(occupancy="residential", height_m=30, floors_above_grade=9,
                 ground_floor_bua_m2=1500, plot_area_m2=5000)
    assert "ESL" in pump(big).detail
    small = report(occupancy="villa_private", height_m=8, floors_above_grade=2,
                   ground_floor_bua_m2=1600, plot_area_m2=3000)
    assert "ESL" not in pump(small).detail


# ------------------------------------------------------------ CH9B2-02 (H10)
def test_CH9B2_02_table_9_29_A_pump_enters_the_merge():
    """p.750 Table 9.29.A row 1 LH 10-13.5 m: without hydrant 750 gpm, with hydrants 1000 gpm."""
    r = store(hazard_class="LH", ground_floor_bua_m2=1000, max_unit_area_m2=500,
              sum_gf_bua_m2=1000, gross_floor_area_m2=2000, has_high_ceiling=True,
              ceiling_height_m=12)
    p = pump(r)
    assert p.spec.startswith("750 gpm") and "without hydrant" in p.spec
    assert "Table 9.29.A" in p.code_ref + p.detail
    assert "250 gpm @ 4.5 bar" in p.detail and "4.5 bar" in p.detail
    y = store(hazard_class="LH", ground_floor_bua_m2=4000, sum_gf_bua_m2=4000,
              has_high_ceiling=True, ceiling_height_m=12)
    assert pump(y).spec.startswith("1000 gpm")
    assert "with hydrants" in pump(y).spec
    # Total GFA blank on 2 floors: the #4.1.6 yard line is NOT EVALUATED, never 'no hydrants'.
    u = store(hazard_class="LH", ground_floor_bua_m2=1000, max_unit_area_m2=500,
              sum_gf_bua_m2=1000, has_high_ceiling=True, ceiling_height_m=12)
    assert pump(u).spec.startswith("1000 gpm") and "NOT EVALUATED" in pump(u).detail


# ------------------------------------------------------------ CH9B2-04 / ruling R-G
def test_RG_specialty_and_hazard_rows_both_evaluated():
    r = store(hazard_class="OH2", ground_floor_bua_m2=2000, sum_gf_bua_m2=2000,
              is_aboveground_tank_storage=True, ast_storage_area_m2=100, ast_tank_capacity_m3=50)
    br = branches(r)
    assert "storage_industrial_tier3_oh2" in br and "storage_aboveground_tanks_r1" in br
    assert named(r, "Automatic Sprinkler System", "required")
    p = pump(r)
    assert p.spec.startswith("350 gpm") and "R-G" in p.detail


# ------------------------------------------------------------ CH9B2-05 + sweep
def test_CH9B2_05_one_reconciled_wet_riser_line():
    r = store(hazard_class="OH1", height_m=30, floors_above_grade=8, ground_floor_bua_m2=5000,
              sum_gf_bua_m2=5000)
    assert not named(r, "Wet Risers and Internal Landing Valves", "not_required")
    wr = named(r, "Wet Riser System", "required")
    assert wr and "Table 9.27 Group B row 4" in wr[0].detail and "Table 9.19" in wr[0].detail


def test_sweep_highrise_and_G4_nursery_print_no_group_V_not_required_lines():
    tall = store(is_plant_nursery=True, height_m=30, floors_above_grade=8,
                 ground_floor_bua_m2=2000, sum_gf_bua_m2=2000)
    assert not [it for it in fp_all(tall) if it.status == "not_required"
                and it.source_rule == "storage_plant_nursery"]
    g4 = store(is_plant_nursery=True, height_m=14, floors_above_grade=5,
               ground_floor_bua_m2=500, max_unit_area_m2=100, sum_gf_bua_m2=500)
    assert not named(g4, "Automatic Sprinkler System", "not_required")


def test_RE_diesel_generator_room_9_31_E_governs_unsprinklered():
    r = report(occupancy="business", business_group="B", height_m=12, floors_above_grade=3,
               ground_floor_bua_m2=400, plot_area_m2=5000, has_diesel_generator_room=True)
    dg = named(r, "Diesel Generator Room - Foam Sprinkler System")
    assert [it.status for it in dg] == ["required"]
    assert "Table 9.30.G" in dg[0].code_ref and "Table 9.31.E" in dg[0].code_ref
    assert "R-E" in dg[0].detail


def test_kitchen_hood_line_states_3_or_more_burners():
    r = report(occupancy="hotel_a", height_m=10, floors_above_grade=3, ground_floor_bua_m2=1000,
               plot_area_m2=5000, has_commercial_kitchen=True)
    k = named(r, "Commercial Kitchen Hood")
    assert k and "for commercial kitchens having 3 or more burners" in k[0].spec


# ------------------------------------------------------------ CH9B2-08 / 09 pump_specs.yaml
def test_CH9B2_08_09_pump_specs_citations():
    spec = yaml.safe_load((ROOT / "rules" / "pump_specs.yaml").read_text(encoding="utf-8"))
    sd = spec["standpipe_dependent"]
    assert "adjacent wet risers" in sd["pump_description"] and "6.ii" in sd["pump_description"]
    assert "p.582-583" not in sd["source"] and "p.582" in sd["source"]
    assert "Table 9.26" in spec["fixed_1000"]["source"] and "p.723" in spec["fixed_1000"]["source"]


# ------------------------------------------------------------ CH9B2-10
def test_CH9B2_10_groups_F_to_H_not_required_lines_and_msds():
    r1 = store(storage_tenancy="single", hazard_class="LH", ground_floor_bua_m2=500,
               sum_gf_bua_m2=500)
    assert named(r1, "Dry Landing Valves and Risers", "not_required")
    assert named(r1, "MSDS Review (DESIGNER OBLIGATION)", "required")
    r3 = store(storage_tenancy="single", hazard_class="OH2", ground_floor_bua_m2=4000,
               sum_gf_bua_m2=4000)
    assert named(r3, "Wet Risers and Internal Landing Valves", "not_required")
    cold = store(is_cold_storage=True, storage_commodity="class_i_iv", ground_floor_bua_m2=2000,
                 sum_gf_bua_m2=2000)
    assert named(cold, "MSDS Review (DESIGNER OBLIGATION)", "required")


# ------------------------------------------------------------ CH9B2-13 / 14 / 20 wording
def test_CH9B2_13_14_20_tool_added_text():
    r = report(occupancy="business", business_group="B", height_m=30, floors_above_grade=9,
               ground_floor_bua_m2=1500, plot_area_m2=5000, has_transformer_room_utility=True,
               has_flammable_liquid_tanks=True, has_control_room=True)
    k = named(r, "Transformer Room (utility)")
    assert k and "DEWA" not in k[0].detail
    c = named(r, "Flammable Liquid Tanks")
    assert c and "AFFF" not in c[0].detail and "Chapter 13" in c[0].detail
    f = named(r, "Control Room / Fire Command Centre")
    assert f and "tool reading" in f[0].detail.lower()


# ------------------------------------------------------------ CH9B2-16 / 17 tunnels
def test_CH9B2_16_17_tunnel_edge_and_missing_length():
    r = report(occupancy="infrastructure", plot_area_m2=30000, has_tunnel=True,
               tunnel_kind="cable", tunnel_length_m=60)
    wr = named(r, "Wet Riser System (throughout)")
    assert wr and "60 m exactly" in wr[0].detail
    m = report(occupancy="infrastructure", plot_area_m2=30000, has_tunnel=True,
               tunnel_kind="cable", tunnel_length_m=0)
    ne = named(m, "Tunnel Length (Table 9.28) - NOT EVALUATED", "not_evaluated")
    assert ne and "Not evaluated" in ne[0].spec


# ------------------------------------------------------------ CH9B2-18
def test_CH9B2_18_4_1_8_house_of_expertise_line():
    r = store(hazard_class="HH", ground_floor_bua_m2=2000, sum_gf_bua_m2=2000)
    h = named(r, "Fire Risk Analysis Report (#4.1.8)")
    assert h and h[0].status == "conditional" and "House of Expertise" in h[0].detail


# ------------------------------------------------------------ CH9B2-19 / ruling Q-4
def test_Q4_storage_tenancy_required_no_default():
    assert Building(occupancy="storage_industrial", height_m=8).storage_tenancy is None
    assert Building(occupancy="storage_industrial", height_m=8,
                    is_single_tenant_storage=True).storage_tenancy == "single"
    assert Building(occupancy="storage_industrial", height_m=8,
                    is_single_tenant_storage=False).storage_tenancy is None
    assert Building(occupancy="storage_industrial", height_m=8,
                    storage_tenancy="multi").is_single_tenant_storage is False
    blank = store(storage_tenancy=None, hazard_class="LH", ground_floor_bua_m2=500,
                  sum_gf_bua_m2=500)
    ne = named(blank, "Storage Tenancy (Table 9.27 Groups A-J) - NOT EVALUATED", "not_evaluated")
    assert ne and "Q-4" in ne[0].detail
    assert not [b for b in branches(blank) if b and b.startswith(("storage_industrial_tier",
                                                                   "storage_single_tenant"))]
    multi = store(hazard_class="LH", ground_floor_bua_m2=500, sum_gf_bua_m2=500)
    assert "storage_industrial_tier2_lh" in branches(multi)
    single = store(storage_tenancy="single", hazard_class="LH", ground_floor_bua_m2=500,
                   sum_gf_bua_m2=500)
    assert "storage_single_tenant_lh_tier1" in branches(single)
