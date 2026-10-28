"""Audit 28.10.2026, fix round area ch123: Ch 1 definitions, Ch 2 Fire Service Access,
Ch 3 Means of Egress, Ch 15 Accessibility.

Findings CH123-01 to CH123-25 (ledger findings/CH01-03.md), audit H1 (CO detection,
Table 3.37 item 7.i, p.338) and H2 = CH123-02 under owner ruling R-A (28.10.2026: ECC 1 h
sprinklered, 2 h not; Ch 1 Table 1.9 item 1 p.73, FAQ Q8 p.1273; conflict Ch 2 #2.9.3.c
p.219). Values pinned as printed on the pages named in each test.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import engine  # noqa: E402
from flsc_schema import OCCUPANCY_DEFS, Building  # noqa: E402
from occupant_load import TABLE_3_13_ROWS  # noqa: E402
from test_phase1_findings import items, report  # noqa: E402


def named(r, code, prefix):
    return [it for it in items(r, code) if it.system.startswith(prefix)]


def pk_items(r, code):
    ch = next(c for c in r.attached_parking_chapters if c.chapter_code == code)
    return [it for b in ch.blocks for it in b.items]


def spr(**kw):
    kw.setdefault("floors_above_grade", max(1, int(kw.get("height_m", 3) // 3.5)))
    return engine.building_sprinklered(Building(**kw))


ENCLOSED = dict(occupancy="parking_enclosed", height_m=12, floors_above_grade=3,
                ground_floor_bua_m2=3000, plot_area_m2=5000)
HOSPITAL_NS = dict(occupancy="healthcare_a", height_m=10, gross_floor_area_m2=1000,
                   ground_floor_bua_m2=500, floors_above_grade=2)
SCHOOL_NS = dict(occupancy="education_b", height_m=4, floors_above_grade=1,
                 gross_floor_area_m2=300, ground_floor_bua_m2=300)


# ------------------------------------------------------------ H1 / CH123-01
def test_CH123_01_co_detection_enclosed_parking_table_3_37_item_7_i():
    r = report(**ENCLOSED)
    (it,) = named(r, "MOE", "Carbon Monoxide Detection")
    assert it.status == "required"
    assert it.spec.startswith("Carbon monoxide detection shall be provided in all enclosed "
                              "parking structures.")
    assert "complete with control panel and interfacing with ventilation system" in it.spec
    assert it.code_ref == "Ch 3, #5.16.1 / Table 3.37 item 7.i" and it.page_ref == "p.338"


def test_CH123_01_co_detection_attached_enclosed_parking_sub_run():
    r = report(occupancy="business", height_m=40, floors_above_grade=11, floors_below_grade=2,
               gross_floor_area_m2=11000, ground_floor_bua_m2=1000, business_group="A",
               has_parking_area=True, attached_parking_kind="enclosed", parking_area_m2=2000,
               parking_height_m=0, parking_basement_levels=2)
    co = [it for it in pk_items(r, "MOE") if it.system.startswith("Carbon Monoxide Detection")]
    assert len(co) == 1 and co[0].status == "required" and "7.i" in co[0].code_ref


def test_CH123_01_no_co_line_for_open_parking():
    r = report(occupancy="parking_open", height_m=12, floors_above_grade=3,
               ground_floor_bua_m2=3000, plot_area_m2=5000)
    assert not named(r, "MOE", "Carbon Monoxide Detection")


# ------------------------------------------------------------ H2 / CH123-02 (R-A)
def test_CH123_02_ecc_2_hour_when_not_sprinklered_ruling_R_A():
    kw = dict(occupancy="mall_open", height_m=6, floors_above_grade=1,
              ground_floor_bua_m2=900, gross_floor_area_m2=900, plot_area_m2=3000)
    assert spr(**kw) is False
    (it,) = named(report(**kw), "FSA", "Emergency Command Centre")
    assert "separated by a 2-hour fire barrier" in it.spec and "1-hour" not in it.spec
    assert "Table 1.9 item 1" in it.code_ref and "Q8" in it.code_ref
    assert it.page_ref == "p.219, 73, 1273"
    assert "#2.9.3.c (p.219)" in it.detail and "R-A" in it.detail


def test_CH123_02_ecc_1_hour_when_sprinklered():
    kw = dict(occupancy="business", height_m=40, floors_above_grade=11,
              ground_floor_bua_m2=1000, gross_floor_area_m2=11000, business_group="A")
    assert spr(**kw) is True
    (it,) = named(report(**kw), "FSA", "Emergency Command Centre")
    assert "separated by a 1-hour fire barrier" in it.spec and "2-hour" not in it.spec


# ------------------------------------------------------------ CH123-03
def test_CH123_03_extra_hazard_group_1_takes_group_b_rows():
    r = report(occupancy="storage_industrial", height_m=8, floors_above_grade=1,
               ground_floor_bua_m2=2000, gross_floor_area_m2=2000, plot_area_m2=5000,
               hazard_class="HH", sum_gf_bua_m2=2000)
    moe = r.chapter("MOE")
    assert moe.selected_branch == "moe_storage_industrial_eh1"
    (olf,) = named(r, "MOE", "Occupant Load Factor (Extra Hazard Group 1")
    assert "Stair capacity 7.6 mm/person; ramp 5 mm/person" in olf.spec
    assert "18 mm" not in olf.spec
    (t,) = named(r, "MOE", "Travel / Commonpath / Dead-end (Extra Hazard Group 1")
    assert t.code_ref == "Ch 3, #4.5 / Table 3.16 rows 17, 19"
    if spr(occupancy="storage_industrial", height_m=8, floors_above_grade=1,
           ground_floor_bua_m2=2000, gross_floor_area_m2=2000, plot_area_m2=5000,
           hazard_class="HH", sum_gf_bua_m2=2000):
        assert "commonpath 30 m, dead end 30 m, travel 122 m" in t.spec
    else:
        assert "commonpath 15 m, dead end 15 m, travel 61 m" in t.spec
    assert not named(r, "MOE", "Travel / Commonpath / Dead-end (HH Storage")
    assert "#1.1.13.4.a p.529" in r.occupant_load.factor_ref


def test_CH123_03_extra_hazard_group_2_keeps_group_a_rows():
    r = report(occupancy="storage_industrial", height_m=8, floors_above_grade=1,
               ground_floor_bua_m2=2000, gross_floor_area_m2=2000, plot_area_m2=5000,
               hazard_class="HH", is_extra_hazard_2=True, sum_gf_bua_m2=2000)
    assert r.chapter("MOE").selected_branch == "moe_storage_industrial_high_hazard"
    (olf,) = named(r, "MOE", "Occupant Load Factor (High-hazard")
    assert "Stair capacity 18 mm/person; ramp 10 mm/person" in olf.spec


# ------------------------------------------------------------ CH123-04
def test_CH123_04_daycare_groups_by_use_not_headcount():
    assert "child day care centers, old age care centers" in OCCUPANCY_DEFS["daycare_a"]
    assert "adult day care centers" in OCCUPANCY_DEFS["daycare_b"]
    assert "Table 1.1 row 10 (p.50)" in OCCUPANCY_DEFS["daycare_a"]
    for k in ("daycare_a", "daycare_b", "daycare_c"):
        assert "12 clients" not in OCCUPANCY_DEFS[k] and "4 to 6" not in OCCUPANCY_DEFS[k], k
    text = (ROOT / "rules" / "ch3_means_of_egress.yaml").read_text(encoding="utf-8")
    assert ">12 clients" not in text and "7-12 clients" not in text and "4-6 clients" not in text


# ------------------------------------------------------------ CH123-05 / owner ruling 28.10.2026 item 5
def test_CH123_05_hospital_sleeping_areas_require_sprinklers():
    """Table 3.16 row 4.i p.293 prints S only. Table 9.21.a.1 (GF BUA up to 500 m2)
    would otherwise be hose-reel only. Owner ruling: sprinklers required; S limits apply."""
    assert spr(**HOSPITAL_NS) is True
    r = report(**HOSPITAL_NS)
    assert not [it for it in items(r, "MOE") if "Hospital Sleeping Areas" in it.system
                and "NOT EVALUATED" in it.system]
    (t,) = named(r, "MOE", "Travel / Dead-end / Commonpath (Hospitals")
    assert t.status == "required"
    assert "Column S (sprinklered)" in t.spec
    assert "commonpath 30 m" in t.spec and "dead end 9.1 m" in t.spec and "travel 61 m" in t.spec
    assert "NOT EVALUATED" not in t.spec
    sp = named(r, "FP", "Automatic Sprinkler System (hospital sleeping areas)")
    assert len(sp) == 1 and sp[0].status == "required"
    assert "Table 3.16 row 4.i" in sp[0].code_ref
    # Table 9.21.f.F (extinguishers only) does not waive hospital sleeping-area sprinklers.
    tiny = report(occupancy="healthcare_a", height_m=8, floors_above_grade=2,
                  ground_floor_bua_m2=150, plot_area_m2=500, tent_marquee_kind="small_detached")
    assert spr(occupancy="healthcare_a", height_m=8, floors_above_grade=2,
               ground_floor_bua_m2=150, tent_marquee_kind="small_detached") is True
    assert not [it for it in items(tiny, "FP") if it.system == "Automatic Sprinkler System"
                and it.status == "not_required"]
    assert named(tiny, "FP", "Automatic Sprinkler System (hospital sleeping areas)")[0].status == "required"


def test_CH123_05_sprinklered_hospital_has_no_not_evaluated_line():
    r = report(occupancy="healthcare_a", height_m=30, floors_above_grade=8,
               gross_floor_area_m2=8000, ground_floor_bua_m2=1000)
    assert not [it for it in items(r, "MOE") if "Hospital Sleeping Areas" in it.system]


# ------------------------------------------------------------ CH123-06
def test_CH123_06_residential_a_table_3_24_rows():
    r = report(occupancy="residential", height_m=30, floors_above_grade=8,
               gross_floor_area_m2=8000, ground_floor_bua_m2=1000)
    (c,) = named(r, "MOE", "Residential A: Corridor (Table 3.24 item 3)")
    assert c.status == "required"
    assert "minimum of 1200 mm in width" in c.spec and "1 hour fire resistance rated" in c.spec
    (s,) = named(r, "MOE", "Residential A: Dwelling Unit Separation")
    assert "minimum of 1 hour fire resistance rating" in s.spec and s.page_ref == "p.319"
    (h,) = named(r, "MOE", "Residential A: Hazardous Area Separation")
    assert h.status == "conditional" and "garbage chutes: 2 hour" in h.spec
    (se,) = named(r, "MOE", "Residential A: Single Exit Stair Permission")
    assert se.status == "conditional" and "does not exceed 500 m2" in se.spec
    assert "not more than 6 dwelling units" in se.spec and "10.7 m" in se.spec


def test_CH123_06_residential_single_exit_stair_ticked_is_required():
    r = report(occupancy="residential", height_m=12, floors_above_grade=3,
               gross_floor_area_m2=1200, ground_floor_bua_m2=400, has_single_exit_stair=True)
    (se,) = named(r, "MOE", "Residential A: Single Exit Stair Permission")
    assert se.status == "required" and se.code_ref == "Ch 3, #5.5.1 / Table 3.24 item 2"


def test_CH123_06_residential_b_table_3_25_rows():
    r = report(occupancy="staff_accommodation", height_m=12, floors_above_grade=3,
               gross_floor_area_m2=7500, ground_floor_bua_m2=2500, largest_storey_area_m2=2500)
    (se,) = named(r, "MOE", "Residential B: Single Exit Not Permitted")
    assert se.status == "required" and se.spec.startswith("Single exit shall not be permitted.")
    (sc,) = named(r, "MOE", "Residential B: Smoke Compartments")
    assert sc.status == "required" and "not exceeding 61 m travel distance" in sc.spec
    assert sc.code_ref == "Ch 3, #5.5.2 / Table 3.25 item 6" and sc.page_ref == "p.321"


def test_CH123_06_residential_c_table_3_26_rows():
    r = report(occupancy="labour_accommodation", height_m=12, floors_above_grade=3,
               gross_floor_area_m2=3000, ground_floor_bua_m2=1000)
    (c,) = named(r, "MOE", "Residential C: Corridor (Table 3.26 item 2)")
    assert "unless it is an open corridor" in c.spec and c.page_ref == "p.322"
    (se,) = named(r, "MOE", "Residential C: Single Exit Not Permitted")
    assert "2 enclosed exits" in se.spec


# ------------------------------------------------------------ CH123-07
def test_CH123_07_hotel_table_3_30_rows():
    r = report(occupancy="hotel_a", height_m=30, floors_above_grade=8,
               gross_floor_area_m2=8000, ground_floor_bua_m2=1000)
    (d,) = named(r, "MOE", "Hotel: Exit Discharge Distance (Table 3.30 item 8)")
    assert d.status == "required" and "shall not exceed 30 m" in d.spec and d.page_ref == "p.328"
    (c,) = named(r, "MOE", "Hotel: Corridors (Table 3.30 item 2)")
    assert "1200 mm" in c.spec and "1 hour fire resistance rated" in c.spec
    (two,) = named(r, "MOE", "Hotel: Two Exit Access Doors - Room over 185 m2")
    assert two.status == "conditional" and "larger than 185 m2" in two.spec


def test_CH123_07_daycare_table_3_31_rows():
    r = report(occupancy="daycare_a", height_m=12, floors_above_grade=3,
               gross_floor_area_m2=1500, ground_floor_bua_m2=500)
    (sc,) = named(r, "MOE", "Daycare Group A: Location / Smoke Compartments")
    assert sc.status == "required" and "minimum of 2 smoke compartments" in sc.spec
    (se,) = named(r, "MOE", "Daycare: Single Exit Not Permitted")
    assert se.status == "required"
    (c,) = named(r, "MOE", "Daycare: Corridors (Table 3.31 item 2)")
    assert "1200 mm" in c.spec
    # Group B: no smoke compartment line; the group-less option: conditional.
    rb = report(occupancy="daycare_b", height_m=12, floors_above_grade=3,
                gross_floor_area_m2=1500, ground_floor_bua_m2=500)
    assert not named(rb, "MOE", "Daycare Group A: Location")
    rc = report(occupancy="daycare_c", height_m=12, floors_above_grade=3,
                gross_floor_area_m2=1500, ground_floor_bua_m2=500)
    (cc,) = named(rc, "MOE", "Daycare Group A: Location")
    assert cc.status == "conditional"


def test_CH123_07_mercantile_table_3_32_rows():
    r = report(occupancy="mercantile_b", height_m=8, floors_above_grade=2,
               gross_floor_area_m2=2000, ground_floor_bua_m2=1000)
    (a,) = named(r, "MOE", "Mercantile: Aisles (Table 3.32 item 3)")
    assert "not less than 915 mm" in a.spec and "not less than 1200 mm" in a.spec
    assert "not less than 1525 mm" in a.spec
    (e,) = named(r, "MOE", "Mercantile: Exits (Table 3.32 item 4)")
    assert "Not less than 50 % of the exits reached without passing through check-out" in e.spec
    assert "exits through kitchen not permitted" in e.spec
    assert r.chapter("MOE").selected_branch == "moe_mercantile"


def test_CH123_07_mercantile_parking_separation_when_parking_ticked():
    r = report(occupancy="mercantile_b", height_m=8, floors_above_grade=2,
               gross_floor_area_m2=2000, ground_floor_bua_m2=1000,
               has_parking_area=True, parking_area_m2=1000, parking_height_m=0,
               parking_basement_levels=1, floors_below_grade=1)
    (p,) = named(r, "MOE", "Mercantile: Parking Separation")
    assert p.status == "required" and "minimum 2-hour fire resistance rating" in p.spec


def test_CH123_07_education_rescue_window_non_sprinklered_and_93_m2_rooms():
    assert spr(**SCHOOL_NS) is False
    r = report(**SCHOOL_NS)
    (w,) = named(r, "MOE", "Rescue Window in Non-sprinklered Building (Table 3.21 item 7)")
    assert w.status == "required" and "greater than 23 m2" in w.spec
    assert "510 mm in width and 610 mm in height" in w.spec and "1120 mm" in w.spec
    (d,) = named(r, "MOE", "Two Exit Access Doors - Room over 93 m2 (Table 3.21 item 4)")
    assert d.status == "conditional"
    rs = report(occupancy="education_b", height_m=30, floors_above_grade=8,
                gross_floor_area_m2=8000, ground_floor_bua_m2=1000)
    assert not named(rs, "MOE", "Rescue Window")


# ------------------------------------------------------------ CH123-08
def test_CH123_08_parking_table_3_37_items():
    r = report(**ENCLOSED)
    (f,) = named(r, "MOE", "Parking Flooring (Table 3.37 item 6)")
    assert f.spec == ("Floor surfaces shall be of noncombustible material. Floors shall be "
                      "graded and equipped with drains.")
    (s,) = named(r, "MOE", "Parking Exit Signs (Table 3.37 item 8)")
    assert "distinguishable from Vehicle Exit route" in s.spec
    (m,) = named(r, "MOE", "Parking Multiple Occupancy (Table 3.37 item 1)")
    assert m.status == "conditional"
    assert m.spec.startswith("Parking structures within 3 m of a building shall be separated by "
                             "fire barrier having a minimum 2-hour fire resistance rating")
    (fd,) = named(r, "MOE", "Parking Fuel Dispensing Exits (Table 3.37 item 5)")
    assert fd.status == "conditional" and "no upward travel permitted" in fd.spec


def test_CH123_08_robotic_parking_table_3_37_item_3():
    r = report(**ENCLOSED, has_robotic_parking=True)
    (it,) = named(r, "MOE", "Robotic or Automatic Parking (Table 3.37 item 3)")
    assert it.status == "required"
    assert "At least two means of egress remote from each other" in it.spec
    assert "intervals of 6 m vertically and 30 m horizontally" in it.spec


# ------------------------------------------------------------ CH123-09
def test_CH123_09_stair_separation_blockwork_lowrise_rcc_otherwise():
    low = report(occupancy="business", height_m=10, floors_above_grade=3, business_group="A",
                 gross_floor_area_m2=1500, ground_floor_bua_m2=500)
    (a,) = named(low, "MOE", "Exit Stair Separation (Table 3.4 item 7)")
    assert "at least block-work and ensure 2 hour fire resistance rating" in a.spec
    assert "3 m above the top most landing" in a.spec and a.page_ref == "p.259"
    high = report(occupancy="business", height_m=30, floors_above_grade=8, business_group="A",
                  gross_floor_area_m2=8000, ground_floor_bua_m2=1000)
    (b,) = named(high, "MOE", "Exit Stair Separation (Table 3.4 item 7)")
    assert "RCC (Reinforced Concrete) and ensure 2 hour fire resistance rating" in b.spec
    deep = report(occupancy="business", height_m=10, floors_above_grade=3, business_group="A",
                  floors_below_grade=3, gross_floor_area_m2=3000, ground_floor_bua_m2=500)
    (c,) = named(deep, "MOE", "Exit Stair Separation (Table 3.4 item 7)")
    assert "RCC" in c.spec


def test_CH123_09_stair_penetrations_item_8():
    r = report(occupancy="business", height_m=10, floors_above_grade=3, business_group="A",
               gross_floor_area_m2=1500, ground_floor_bua_m2=500)
    (p,) = named(r, "MOE", "Penetrations into Stair Space (Table 3.4 item 8)")
    assert "Fire Hose Reel and Landing valve cabinets shall not be located in the stair " \
           "enclosure" in p.spec
    assert "AC units" in p.spec and p.code_ref == "Ch 3, #3.3 / Table 3.4 item 8"


# ------------------------------------------------------------ CH123-10 / CH123-23
def test_CH123_10_robotic_olf_line_only_with_robotic_parking():
    r = report(**ENCLOSED)
    assert not [it for it in items(r, "MOE") if "Robotic" in it.system]
    rr = report(**ENCLOSED, has_robotic_parking=True)
    (o,) = named(rr, "MOE", "Occupant Load Factor (Mechanical / Robotic Parking")
    assert "46.5 m2" in o.spec and o.code_ref == "Ch 3, Table 3.13 row 20.i"
    (t,) = named(rr, "MOE", "Travel / Commonpath / Dead-end (Mechanical / Robotic Parking")
    assert t.code_ref == "Ch 3, #4.5 / Table 3.16 row 21" and t.page_ref == "p.295"


def test_CH123_23_robotic_parking_occupant_load_row_20_i():
    ol = report(**ENCLOSED, has_robotic_parking=True).occupant_load
    assert ol.factor_m2_per_person == 46.5 and "row 20.i" in ol.factor_ref
    ol = report(**ENCLOSED).occupant_load
    assert ol.factor_m2_per_person == 27.9 and "row 19.i" in ol.factor_ref


# ------------------------------------------------------------ CH123-11
def test_CH123_11_fire_lift_items_i_and_l():
    r = report(occupancy="business", height_m=40, floors_above_grade=11, business_group="A",
               ground_floor_bua_m2=1000, gross_floor_area_m2=11000)
    (it,) = named(r, "FSA", "Fire Lift")
    assert "all the passenger lifts brought to the ground floor or egress level or " \
           "alternative floor" in it.spec and "(#2.9.4.i)" in it.spec
    assert "sections 5.3 and 5.6-5.12 of BS EN 81-72" in it.spec and "(#2.9.4.l)" in it.spec
    assert it.code_ref == "Ch 2, #2.9.4.a-l"


# ------------------------------------------------------------ CH123-12
def test_CH123_12_section_2_10_items():
    r = report(occupancy="business", height_m=40, floors_above_grade=11, business_group="A",
               ground_floor_bua_m2=1000, gross_floor_area_m2=11000)
    (y,) = named(r, "FSA", "Yard fire hydrants for fire fighters")
    assert y.status == "conditional" and "500 gpm through a single hydrant with two outlets" in y.spec
    assert "250 gpm per outlet" in y.spec and "6.9 bars" in y.spec and y.page_ref == "p.222"
    (bi,) = named(r, "FSA", "Breeching inlets")
    assert bi.status == "required"
    assert "not less than 457 mm nor more than 1219 mm" in bi.spec and "25.4 mm" in bi.spec
    assert "four 65 mm (4-Way)" in bi.spec and bi.code_ref == "Ch 2, #2.10.2"
    (h,) = named(r, "FSA", "Fire hose cabinets for fire fighters")
    assert "within 6 m from the stair door and not inside the stair core" in h.spec
    (p,) = named(r, "FSA", "Fire pump room access")
    assert "posted in the Emergency Command Center and Reception" in p.spec
    assert p.code_ref == "Ch 2, #2.10.4"


# ------------------------------------------------------------ CH123-15
def test_CH123_15_open_parking_definition_has_a_spec():
    r = report(occupancy="parking_open", height_m=12, floors_above_grade=3,
               ground_floor_bua_m2=3000, plot_area_m2=5000)
    (d,) = named(r, "MOE", "Open-parking definition")
    assert d.spec and "not less than 0.4 m2 for each linear meter" in d.spec
    assert "within 30 m of the permanent natural ventilation opening" in d.spec


# ------------------------------------------------------------ CH123-16
def test_CH123_16_hh_mercantile_no_panic_hardware_claim():
    r = report(occupancy="mercantile_a", height_m=6, floors_above_grade=1,
               gross_floor_area_m2=800, hazard_class="HH")
    (t,) = named(r, "MOE", "Travel / Commonpath / Dead-end (High-Hazard Mercantile")
    assert "panic hardware (" not in t.detail and "Outswing" not in t.detail
    assert "no panic-hardware trigger" in t.detail


# ------------------------------------------------------------ CH123-17
def test_CH123_17_business_single_exit_limits_stated():
    r = report(occupancy="business", height_m=8, floors_above_grade=2, business_group="A",
               gross_floor_area_m2=600, ground_floor_bua_m2=300)
    (it,) = named(r, "MOE", "Single Exit Permission (Business - Table 3.19)")
    for v in ("not more than 4570 mm in height", "rooms exceeding 280 m2 in area require 2 exit "
              "doors", "shall not serve any other stories", "(S 30 m, NS 23 m)"):
        assert v in it.spec, v
    assert "over-provisioning" not in (it.detail or "")


# ------------------------------------------------------------ CH123-18
def test_CH123_18_private_villa_multiple_occupancy_line():
    r = report(occupancy="villa_private", height_m=7, floors_above_grade=2)
    (it,) = named(r, "MOE", "Egress Through a Nonresidential Occupancy (Table 3.27 item 1)")
    assert it.status == "conditional" and "1 hour fire resistance rated corridor" in it.spec


# ------------------------------------------------------------ CH123-19
def test_CH123_19_waterfront_lowrise_private_villa_takes_lowrise_row():
    r = report(occupancy="villa_private", height_m=7, floors_above_grade=2, is_waterfront=True)
    (it,) = named(r, "FSA", "Waterfront property fire access")
    assert it.spec.startswith("Lowrise buildings: maximum distance from fire access road shall "
                              "not exceed 60 m")


# ------------------------------------------------------------ CH123-20
def test_CH123_20_gate_locks_barriers_turf_and_100_m2_exemption():
    r = report(occupancy="business", height_m=30, floors_above_grade=8, business_group="A",
               gross_floor_area_m2=8000, ground_floor_bua_m2=1000)
    (g,) = named(r, "FSA", "Access road gateways")
    assert "attended continuously by security guards" in g.spec and "#2.4.4" in g.code_ref
    (bt,) = named(r, "FSA", "Security barriers and turfed accessways")
    assert bt.status == "conditional" and "not more than 3 meters apart" in bt.spec
    (w,) = named(r, "FSA", "Fire vehicle accessway width")
    assert "less than 100 m2 and are remotely located" in w.detail


# ------------------------------------------------------------ CH123-21
def test_CH123_21_lowrise_line_says_road_not_accessway():
    r = report(occupancy="business", height_m=10, floors_above_grade=3, business_group="A",
               gross_floor_area_m2=1500, ground_floor_bua_m2=500)
    assert not named(r, "FSA", "Fire vehicle accessway width")
    (it,) = named(r, "FSA", "Fire access road width + clearance")
    assert "accessway is not required" in it.spec and "#2.8.4.a" in it.code_ref


# ------------------------------------------------------------ CH123-22
def test_CH123_22_villa_accessibility_wording():
    r = report(occupancy="villa_private", height_m=7, floors_above_grade=2)
    acc = items(r, "ACC")
    v = next(it for it in acc if it.source_rule == "acc_villa")
    assert "opts into" not in v.spec and "#2.2.1" in v.code_ref
    assert "accessible routes, doors, elevators, stairs, refuge areas and parking" in v.spec
    w = next(it for it in acc if it.source_rule == "acc_wheelchairs")
    assert "not yet read" not in w.detail and "#2.2.1, p.1090" in w.detail


# ------------------------------------------------------------ CH123-24
def test_CH123_24_parking_row_labels_name_both_letterings():
    assert "Table 1.1 Group B" in TABLE_3_13_ROWS["20.i"][0]
    assert "Table 1.1 Group A" in TABLE_3_13_ROWS["19.i"][0]
    assert "Table 1.1 Group C" in TABLE_3_13_ROWS["19.ii"][0]


# ------------------------------------------------------------ CH123-25
def test_CH123_25_door_ratings_and_exit_discharge():
    r = report(occupancy="business", height_m=30, floors_above_grade=8, business_group="A",
               gross_floor_area_m2=8000, ground_floor_bua_m2=1000)
    (d,) = named(r, "MOE", "Fire Resistance Rating of Doors (Table 3.3.a)")
    assert d.spec.startswith("Exit stair: 90 Minutes") and d.page_ref == "p.254"
    (x,) = named(r, "MOE", "Exit Discharge (Table 3.12)")
    assert "minimum of 50 %" in x.spec and "1/3 (One-third)" in x.spec
    (u,) = named(r, "MOE", "Unit Door Fire Rating (Table 3.3.b)")
    assert "None if sprinklered" in u.spec


def test_CH123_25_unsprinklered_office_door_60_minutes_and_full_discharge():
    kw = dict(occupancy="business", height_m=4, floors_above_grade=1, business_group="A",
              gross_floor_area_m2=300, ground_floor_bua_m2=300)
    assert spr(**kw) is False
    r = report(**kw)
    (u,) = named(r, "MOE", "Unit Door Fire Rating (Table 3.3.b)")
    assert "60 Minutes, if not sprinklered" in u.spec
    (x,) = named(r, "MOE", "Exit Discharge (Table 3.12)")
    assert "100% of the required number of exits" in x.spec and "1/2 (One-half)" in x.spec


def test_CH123_25_horizontal_exits_and_evacuation_elevators_follow_the_ticks():
    base = dict(occupancy="healthcare_a", height_m=30, floors_above_grade=8,
                gross_floor_area_m2=8000, ground_floor_bua_m2=1000)
    r = report(**base)
    (h,) = named(r, "MOE", "Horizontal Exits (Table 3.6)")
    assert h.status == "conditional"
    (e,) = named(r, "MOE", "Elevators as Means of Egress (Table 3.11)")
    assert e.status == "conditional"
    r = report(**base, has_horizontal_exits=True, has_evacuation_elevator=True)
    (h,) = named(r, "MOE", "Horizontal Exits (Table 3.6)")
    assert h.status == "required" and "Doors 90 minutes fire resistance rated" in h.spec
    (e,) = named(r, "MOE", "Elevators as Means of Egress (Table 3.11)")
    assert e.status == "required" and "Building fully sprinklered" not in e.spec
    assert "building fully sprinklered" in e.spec
    for name in ("Smokeproof Enclosures (Table 3.7)", "Exit Passageways (Table 3.8)",
                 "Ramps as Means of Egress (Table 3.9)"):
        (c,) = named(r, "MOE", name)
        assert c.status == "conditional", name


def test_CH123_25_component_tables_not_on_villas():
    r = report(occupancy="villa_private", height_m=7, floors_above_grade=2)
    for name in ("Fire Resistance Rating of Doors", "Exit Discharge (Table 3.12)",
                 "Horizontal Exits", "Smokeproof Enclosures"):
        assert not named(r, "MOE", name), name
