"""Owner rulings R1-R13 and R2b (Hussein, 12.10.2026): one test per ruling.

Each test names the ruling it pins. Code values come from UAE FLSC 2018
(CDGH-OP-25) as read off the printed pages cited in the rule YAML. Run with
`python -m pytest tests/test_rulings.py`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import engine  # noqa: E402
from flsc_schema import Building  # noqa: E402
from test_phase1_findings import report, items, lines, pump, tank  # noqa: E402


def names(r, code, status=None):
    return [it.system for it in items(r, code) if status is None or it.status == status]


def branch(r, code):
    return r.chapter(code).selected_branch


# ---------------------------------------------------------------- R1
def test_R1_23_0_m_is_highrise_everywhere():
    """23.0 m exactly is highrise (Table 1.7 p.67, FAQ Q27 p.1282): Ch 8 highrise row."""
    b = Building(occupancy="residential", height_m=23.0, floors_above_grade=7)
    assert b.height_class == "highrise"
    assert Building(occupancy="residential", height_m=22.99, floors_above_grade=7).height_class == "midrise"
    r = report(occupancy="residential", height_m=23.0, ground_floor_bua_m2=1000, plot_area_m2=3000)
    assert branch(r, "FA") == "fa_highrise"


# ---------------------------------------------------------------- R2 / R2b
def test_R2_lowrise_with_3_basements_takes_table_9_20_a_row_h():
    r = report(occupancy="residential", height_m=12, floors_below_grade=3, depth_below_grade_m=10.5,
               ground_floor_bua_m2=1000, plot_area_m2=5000)
    assert "Table 9.20.a.1" in pump(r).code_ref
    assert pump(r).spec.startswith("750 gpm @ 6.9 bar")
    assert tank(r).spec.startswith("45 minutes")


def test_R2b_lowrise_deeper_than_7_m_with_2_basements_takes_row_h():
    r = report(occupancy="residential", height_m=12, floors_below_grade=2, depth_below_grade_m=8,
               ground_floor_bua_m2=1000, plot_area_m2=5000)
    assert "Table 9.20.a.1" in pump(r).code_ref
    shallow = report(occupancy="residential", height_m=12, floors_below_grade=2, depth_below_grade_m=6,
                     ground_floor_bua_m2=1000, plot_area_m2=5000)
    assert "Table 9.20.a" not in pump(shallow).code_ref


# ---------------------------------------------------------------- R3
def test_R3_table_9_24_A_3_exactly_3_standpipes_is_1000_gpm():
    r = report(occupancy="parking_enclosed", height_m=18, ground_floor_bua_m2=4000,
               plot_area_m2=6000, wet_riser_standpipes=3)
    assert pump(r).spec.startswith("1000 gpm")
    r2 = report(occupancy="parking_enclosed", height_m=18, ground_floor_bua_m2=4000,
                plot_area_m2=6000, wet_riser_standpipes=2)
    assert pump(r2).spec.startswith("750 gpm")


# ---------------------------------------------------------------- R4
def test_R4_9_21_b_3_i_uses_table_9_21_a_tiers():
    small = report(occupancy="residential", height_m=10, ground_floor_bua_m2=400, plot_area_m2=25000)
    mid = report(occupancy="residential", height_m=10, ground_floor_bua_m2=2000, plot_area_m2=25000)
    big = report(occupancy="residential", height_m=10, ground_floor_bua_m2=5000, plot_area_m2=25000)
    sprk = "Automatic Sprinkler System (full coverage incl. basements & podiums)"
    assert sprk not in names(small, "FP", "required")
    assert sprk in names(mid, "FP", "required")
    assert sprk in names(big, "FP", "required")
    assert any("Wet Riser" in n for n in names(big, "FP", "required"))
    assert all("1000 gpm @ 6.9 bar" in pump(x).spec for x in (small, mid, big))
    assert all(tank(x).spec.startswith("60 minutes") for x in (small, mid, big))


# ---------------------------------------------------------------- R5
def test_R5_aboveground_lpg_tank_fixed_water_spray_per_ch_11():
    r = report(occupancy="residential", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_lpg_tanks=True)
    lpg = [it for it in items(r, "FP") if it.system.startswith("LPG Tanks")]
    assert len(lpg) == 1 and lpg[0].status == "required"
    assert "Table 11.5 item 5" in lpg[0].code_ref


# ---------------------------------------------------------------- R6
def test_R6_mall_23_m_or_more_takes_table_9_6_item_13_zoning_and_second_pump_set():
    r = report(occupancy="mall_covered", height_m=60, floors_above_grade=12,
               ground_floor_bua_m2=10000, plot_area_m2=30000)
    assert "Wet Riser Zoning - High Zone and Low Zone, looped" in names(r, "FP", "required")
    assert "Second Fire Pump Set + Dedicated Water Tank" not in names(r, "FP")
    tall = report(occupancy="mall_covered", height_m=95, floors_above_grade=20,
                  ground_floor_bua_m2=10000, plot_area_m2=30000)
    assert "Second Fire Pump Set + Dedicated Water Tank" in names(tall, "FP", "required")


# ---------------------------------------------------------------- R7
def test_R7_highrise_height_items_for_every_occupancy_one_alarm_protocol():
    hotel = report(occupancy="hotel_a", height_m=60, ground_floor_bua_m2=1200, plot_area_m2=5000)
    fa = names(hotel, "FA", "required")
    assert "Sub-FACPs / Annunciators every 45 m" in fa
    assert "Highrise Main FACP - Redundancy and Hot-Swap" in fa
    assert "Positive Alarm Sequence (PAS) - 120 s" in fa
    assert "5-Floor Phased Evacuation Alarm" not in fa
    assert not any(n.startswith("Positive Alarm Sequence (PAS) - 15/180/240") for n in fa)
    hc = report(occupancy="healthcare_a", height_m=120, ground_floor_bua_m2=2000, plot_area_m2=8000)
    fa = names(hc, "FA", "required")
    assert "Sub-FACPs / Annunciators every 45 m" in fa
    assert "Highrise Main FACP - Redundancy and Hot-Swap" in fa
    res = report(occupancy="residential", height_m=60, ground_floor_bua_m2=1200, plot_area_m2=5000)
    fa = names(res, "FA", "required")
    assert "5-Floor Phased Evacuation Alarm" in fa and "Sub-FACPs / Annunciators every 45 m" in fa
    low = report(occupancy="residential", height_m=20, ground_floor_bua_m2=1200, plot_area_m2=5000)
    assert "Sub-FACPs / Annunciators every 45 m" not in names(low, "FA")


# ---------------------------------------------------------------- R8
def test_R8_table_9_29_only_in_sprinklered_buildings_with_note():
    kw = dict(height_m=10, ground_floor_bua_m2=400, plot_area_m2=1000, has_pantries=True,
              has_garbage_chute=True)
    bare = report(occupancy="business", **kw)
    assert not any("Automatic Sprinkler" in n for n in names(bare, "FP", "required"))
    p = [it for it in items(bare, "FP") if it.system.startswith("Pantry Sprinklers")]
    assert len(p) == 1 and p[0].status == "not_required" and "#4.13.1" in p[0].code_ref
    hi = report(occupancy="business", has_high_ceiling=True, ceiling_height_m=12, **kw)
    assert hi.high_ceiling.not_required and hi.high_ceiling.k_factor is None
    sprk = report(occupancy="hotel_a", height_m=10, ground_floor_bua_m2=1000, plot_area_m2=3000,
                  has_pantries=True)
    p = [it for it in items(sprk, "FP") if it.system.startswith("Pantry Sprinklers")]
    assert len(p) == 1 and p[0].status == "required"


# ---------------------------------------------------------------- R9
def test_R9_open_parking_non_sprinklered_travel_91_m_conflict_flagged():
    r = report(occupancy="parking_open", height_m=12, ground_floor_bua_m2=3000, plot_area_m2=5000)
    t = [it for it in items(r, "MOE") if it.system == "Travel Distance (Open Podium Parking)"]
    assert len(t) == 1
    assert "NS 91 m" in t[0].spec and "sprinklered or non-sprinklered" not in t[0].spec
    assert "CODE CONFLICT" in t[0].detail and "Table 3.15.b item iv" in t[0].detail


# ---------------------------------------------------------------- R10
def test_R10_open_mall_item_13_open_parking_item_22_by_analogy():
    mall = report(occupancy="mall_open", height_m=10, ground_floor_bua_m2=3000, plot_area_m2=6000)
    assert branch(mall, "FA") != "fa_mall"
    assert "Open Mall - Table 8.13 item 13 MERCANTILE applies" in names(mall, "FA")
    assert "Positive Alarm Sequence (PAS) - 180 s" in names(mall, "FA", "required")
    covered = report(occupancy="mall_covered", height_m=10, ground_floor_bua_m2=3000, plot_area_m2=6000)
    assert branch(covered, "FA") == "fa_mall"
    park = report(occupancy="parking_open", height_m=12, ground_floor_bua_m2=3000, plot_area_m2=5000)
    fa = items(park, "FA")
    assert "Manual Fire Detection and Alarm System" not in [it.system for it in fa]
    occ_rows = [it for it in fa if it.source_rule == "fa_parking_open"]
    assert occ_rows and all("analogy" in (it.system + (it.detail or "")) for it in occ_rows)


# ---------------------------------------------------------------- R11
def test_R11_table_9_29_A_band_edges_take_the_higher_band():
    assert engine._pick_band(13.4) == "band_10_13_5"
    assert engine._pick_band(13.5) == "band_13_5_18"
    assert engine._pick_band(18) == "band_18_30"
    assert engine._pick_band(30) == "band_18_30"
    r = report(occupancy="hotel_a", height_m=20, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_high_ceiling=True, ceiling_height_m=18, hazard_class="LH")
    assert r.high_ceiling.height_range == "18 m to 30 m"
    assert "ruling R11" in r.high_ceiling.note


# ---------------------------------------------------------------- R12
def test_R12_mv_room_takes_hv_wheeled_co2_labelled():
    mv = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
                has_mv_room=True)
    fe = [it for it in items(mv, "FE") if "MV Room" in it.system]
    assert len(fe) == 1 and fe[0].spec == "Wheeled CO2 12 kg"
    assert "Engineering decision" in fe[0].detail
    lv = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
                has_lv_mv_room=True)
    fe = [it for it in items(lv, "FE") if it.system == "Class C Extinguisher - LV Room"]
    assert len(fe) == 1 and fe[0].spec.startswith("CO2 5 kg")
    # Table 9.30.J is printed "LV ROOMS AND MV ROOMS" (p.753): the clean agent row fires on either.
    assert any(n.startswith("LV / MV Room - Clean Agent") for n in names(mv, "FP", "required"))


# ---------------------------------------------------------------- R13
def test_R13_most_restrictive_mixed_keeps_most_onerous_line_per_system():
    kw = dict(height_m=10, ground_floor_bua_m2=1000, plot_area_m2=3000)
    alone = report(occupancy="business", **kw)
    evc_name = "Emergency Voice Evacuation or Communication System (EVC)"
    assert evc_name not in names(alone, "EVC", "required")
    mixed = report(occupancy="business", secondary_occupancies=["hotel_a"],
                   mixed_occupancy_mode="most_restrictive", **kw)
    evc = names(mixed, "EVC", "required")
    assert evc_name in evc
    assert not names(mixed, "EVC", "not_required")
    sp = [it for it in items(mixed, "FP") if it.system.startswith("Automatic Sprinkler System")]
    assert sp and sp[0].status == "required" and "from hotel_a" in sp[0].detail
    st = [it for it in items(mixed, "FP") if it.system.startswith("Stair Shaft Sprinklers")]
    assert [it.status for it in st] == ["required"]
    assert len(lines(mixed, "FP", "Fire Pump")) == 1 and len(lines(mixed, "FP", "Fire Water Tank")) == 1
    assert "R13" in mixed.mixed_occupancy_note
    # Secondaries listed without the mode change nothing, and the note says so.
    unset = report(occupancy="business", secondary_occupancies=["hotel_a"], **kw)
    assert names(unset, "EVC", "required") == names(alone, "EVC", "required")
    assert "not evaluated" in unset.mixed_occupancy_note
