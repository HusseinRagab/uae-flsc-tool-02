"""Phase 2 package ch3 (audit 12.10.2026): Ch 3 means of egress, occupant load,
Ch 2 fire service access. One test per finding fixed (CH3-xx).

Code values in the asserts were read off the rendered pages in audit/shots:
Ch 2 p.206, 207, 212-215, 217, 219, 220; Ch 3 p.242, 248, 250, 283, 285-288, 291,
293-295, 297, 298, 305, 307, 323.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import engine  # noqa: E402
from fire_access import compute_fire_access  # noqa: E402
from flsc_schema import Building  # noqa: E402
from test_phase1_findings import items, lines, report  # noqa: E402


def moe(r, prefix=""):
    return [it for it in items(r, "MOE") if it.system.startswith(prefix)]


def fsa(r, prefix=""):
    return [it for it in items(r, "FSA") if it.system.startswith(prefix)]


def extent_item(r):
    (it,) = fsa(r, "Extent of fire vehicle access")
    return it


# ------------------------------------------------------------------ CH3-01
def test_CH3_01_occupant_load_rounds_up_to_table_3_14_tier():
    """#4.1.2 p.283 'not less than': 4,649 / 9.3 = 499.89 -> 500 -> Table 3.14 row iii.
    Re-pointed for owner ruling 12.10.2026 Ch3 Q2: the 9.3 m2 office row is now entered
    as a per-use area (blank per-use areas take the densest business row, 3.7 m2)."""
    r = report(occupancy="business", height_m=4, floors_above_grade=1,
               gross_floor_area_m2=4649, ground_floor_bua_m2=4649,
               use_areas=[{"row": "2.i", "area_m2": 4649}])
    assert r.occupant_load.occupant_load == 500
    assert r.occupant_load.min_exits == 3


# ------------------------------------------------------------------ CH3-02
def test_CH3_02_densest_table_3_13_row_when_no_per_use_areas():
    """Table 3.13 p.287 row 18.i industrial 9.3 m2; p.286 rows 4.iii-v 9.3 m2.
    Re-pointed for owner ruling 12.10.2026 Ch3 Q2: the densest row is now the factor
    (the phase 2 draft kept the least dense row and reported the denser one beside it)."""
    r = report(occupancy="storage_industrial", height_m=8, floors_above_grade=1,
               gross_floor_area_m2=14000, ground_floor_bua_m2=14000, hazard_class="OH1")
    ol = r.occupant_load
    assert ol.occupant_load == 1506 and ol.factor_m2_per_person == 9.3 and ol.min_exits == 4
    assert "row 18.i" in ol.factor_ref and "densest" in ol.factor_ref
    r = report(occupancy="healthcare_a", height_m=4, floors_above_grade=1,
               gross_floor_area_m2=6000, ground_floor_bua_m2=6000)
    ol = r.occupant_load
    assert ol.occupant_load == 646 and ol.factor_m2_per_person == 9.3 and ol.min_exits == 3


# ------------------------------------------------------------------ CH3-03
def test_CH3_03_no_occupant_load_from_proxy_factors():
    """Table 3.13 (p.285-287) has rows 1-21 only: no row for these occupancies."""
    for occ in ("mixed_multiple", "motor_fuel_dispensing", "infrastructure",
                "high_depth_underground", "low_depth_underground"):
        r = report(occupancy=occ, height_m=10, floors_above_grade=3,
                   gross_floor_area_m2=6000, ground_floor_bua_m2=2000)
        ol = r.occupant_load
        assert ol.occupant_load == 0 and ol.factor_m2_per_person == 0, occ
        assert "Not evaluated" in ol.note and "no row" in ol.note, occ
        assert "Most restrictive" not in ol.factor_ref


# ------------------------------------------------------------------ CH3-04
def test_CH3_04_high_hazard_mercantile_prints_only_row_13_iii():
    """Table 3.16 row 13 p.294: i. Class A,B,C 76/46 m; iii. High Hazard 23/23 m."""
    r = report(occupancy="mercantile_a", height_m=5, floors_above_grade=1,
               gross_floor_area_m2=800, hazard_class="HH")
    travel = moe(r, "Travel")
    assert [t.system for t in travel] == [
        "Travel / Commonpath / Dead-end (High-Hazard Mercantile - Table 3.16 row 13.iii)"]
    assert r.chapter("MOE").selected_branch == "moe_mercantile_high_hazard"
    assert moe(r, "Occupant Load Factor (Mercantile)")
    r = report(occupancy="mercantile_a", height_m=5, floors_above_grade=1,
               gross_floor_area_m2=800, hazard_class="OH1")
    travel = moe(r, "Travel")
    assert [t.system for t in travel] == [
        "Travel / Commonpath / Dead-end (Mercantile A/B/C - Table 3.16 row 13.i)"]


# ------------------------------------------------------------------ CH3-05
def test_CH3_05_private_villa_gets_table_3_27_items():
    """Table 3.27 p.323 items 2.i, 2.iii (floor over 400 m2), 2.vi (basement stair), 4.i."""
    r = report(occupancy="villa_private", height_m=7, floors_above_grade=2, floors_below_grade=1,
               gross_floor_area_m2=1350, ground_floor_bua_m2=450)
    req = {it.system for it in items(r, "MOE", required_only=True)}
    assert "Two Primary Means of Escape - Floor over 400 m2 (Table 3.27 item 2.iii)" in req
    assert "Basement Exit Stair (Table 3.27 item 2.vi)" in req
    assert "Primary and Secondary Means of Escape (Table 3.27 item 2.i)" in req
    (hall,) = moe(r, "Hallway")
    assert "915 mm" in hall.spec and "2030 mm" in hall.spec
    assert not moe(r, "Basement / Parking Podium Travel Distance")
    assert not [it for it in items(r, "MOE") if it.status == "not_required"]
    # Commercial villa: Table 3.28 (#5.6.2: Table 3.27 does not apply), required.
    r = report(occupancy="villa_commercial", height_m=7, floors_above_grade=2,
               gross_floor_area_m2=600, ground_floor_bua_m2=300)
    (it,) = moe(r, "Means of Egress - Commercial Villa")
    assert it.status == "required" and "Table 3.28" in it.code_ref


# ------------------------------------------------------------------ CH3-07
def test_CH3_07_table_2_5_not_less_than_table_2_3_or_2_4():
    """#2.8.7.a p.214: Table 2.5 3/4 'but not less than' Table 2.3 / 2.4 (p.213)."""
    r = report(occupancy="mall_covered", height_m=10, floors_above_grade=2,
               gross_floor_area_m2=60000, ground_floor_bua_m2=40000)
    assert r.fire_access.extent == "Whole perimeter (100%)"
    assert "Table 2.4" in extent_item(r).code_ref
    r = report(occupancy="mall_covered", height_m=10, floors_above_grade=2,
               gross_floor_area_m2=20000, ground_floor_bua_m2=10000)
    assert r.fire_access.extent == "3/4 perimeter"
    # Open mall: Ch 9 gives no sprinklers -> Table 2.3 floor (more than 16,000 m2 -> whole).
    s = compute_fire_access(Building(occupancy="mall_open", height_m=8, floors_above_grade=1,
                                     ground_floor_bua_m2=20000), sprinklered=False)
    assert s.extent == "Whole perimeter (100%)" and "Table 2.3" in s.extent_ref


# ------------------------------------------------------------------ CH3-08
def test_CH3_08_industrial_volume_is_footprint_times_height():
    """#2.8.8.a / #2.8.9.a p.215: gross cubical extent. 5,000 m2 x 12 m = 60,000 m3."""
    b = Building(occupancy="storage_industrial", height_m=12, floors_above_grade=1,
                 gross_floor_area_m2=5000, ground_floor_bua_m2=5000)
    s = compute_fire_access(b, sprinklered=False)
    assert s.extent == "1/2 perimeter" and "56,801 - 85,200" in s.extent_ref
    assert "60,000 m3" in " ".join(s.notes)
    s = compute_fire_access(b, sprinklered=True)
    assert s.extent == "1/4 perimeter" and "Table 2.7" in s.extent_ref


# ------------------------------------------------------------------ CH3-09
def test_CH3_09_lowrise_45_m_and_commercial_villa_60_m():
    """#2.8.4.a p.212: lowrise up to 15 m, accessway not required, road within 45 m;
    #2.8.3.a p.212: commercial villa cluster within 60 m."""
    r = report(occupancy="residential", height_m=12, floors_above_grade=4,
               gross_floor_area_m2=24000, ground_floor_bua_m2=6000)
    it = extent_item(r)
    assert "45 m" in it.spec and "perimeter" not in it.spec
    assert it.code_ref == "Ch 2, #2.8.4.a" and it.page_ref == "p.212"
    r = report(occupancy="villa_commercial", height_m=7, floors_above_grade=2,
               gross_floor_area_m2=600, ground_floor_bua_m2=300)
    it = extent_item(r)
    assert "60 m" in it.spec and it.code_ref == "Ch 2, #2.8.3.a"


# ------------------------------------------------------------------ CH3-10
def test_CH3_10_ch2_fire_lift_and_emergency_command_centre():
    """#2.9.4.a p.220 fire lift: highrise 23 m or more, more than 2 basements, malls.
    #2.9.3.a p.219 ECC: highrise 23 m, malls; #2.9.3.d 19 m2, 3 m."""
    r = report(occupancy="mall_covered", height_m=10, floors_above_grade=2,
               gross_floor_area_m2=20000, ground_floor_bua_m2=10000)
    assert [it.status for it in fsa(r, "Fire Lift")] == ["required"]
    (ecc,) = fsa(r, "Emergency Command Centre")
    assert ecc.status == "required" and "19 m2" in ecc.spec and "3 m" in ecc.spec
    r = report(occupancy="residential", height_m=23.0, floors_above_grade=7,
               gross_floor_area_m2=7000, ground_floor_bua_m2=1000)
    assert [it.status for it in fsa(r, "Fire Lift")] == ["required"]
    r = report(occupancy="residential", height_m=12, floors_above_grade=4, floors_below_grade=3,
               gross_floor_area_m2=7000, ground_floor_bua_m2=1000)
    (lift,) = fsa(r, "Fire Lift")
    assert lift.status == "required" and "more than 2 basements" in lift.detail
    r = report(occupancy="residential", height_m=12, floors_above_grade=4,
               gross_floor_area_m2=4000, ground_floor_bua_m2=1000)
    assert not fsa(r, "Fire Lift") and not fsa(r, "Emergency Command Centre")


# ------------------------------------------------------------------ CH3-11
def test_CH3_11_table_2_1_and_tower_setback_items():
    """Table 2.1 p.206: 41,000 / 81,000 kg, dead end 45 m, gateways 4.5 m, radius 12 m;
    #2.5.1 signage 50 mm; #2.8.6.b.1 p.213 1/4 tower perimeter beyond 30 m."""
    r = report(occupancy="business", height_m=40, floors_above_grade=10,
               gross_floor_area_m2=10000, ground_floor_bua_m2=1000)
    spec = " | ".join(it.spec for it in fsa(r))
    for v in ("41,000 kg", "81,000 kg", "Maximum dead end 45 m", "gateways 4.5 m",
              "radius 12 m", "50 mm"):
        assert v in spec, v
    # Re-pointed for owner ruling 12.10.2026 Ch3 Q6: the tower line needs its checkbox.
    assert not fsa(r, "Tower set back more than 30 m")
    r = report(occupancy="business", height_m=40, floors_above_grade=10,
               gross_floor_area_m2=10000, ground_floor_bua_m2=1000, tower_setback_over_30m=True)
    (tower,) = fsa(r, "Tower set back more than 30 m")
    assert tower.status == "required" and "1/4 (25 percent)" in tower.spec
    assert tower.code_ref == "Ch 2, #2.8.6.b" and tower.page_ref == "p.213"


# ------------------------------------------------------------------ CH3-12
def test_CH3_12_table_3_14_is_per_storey():
    """#4.3.1 p.288 / #4.1.3 p.283: the exit count is per storey.
    Re-pointed for owner ruling 12.10.2026 Ch3 Q1: the interim 'at least k, up to n' bound
    is gone. Largest storey entered (1,000 m2 / 9.3 -> 108 -> 2 exits); blank -> whole GFA."""
    kw = dict(occupancy="business", height_m=40, floors_above_grade=10,
              gross_floor_area_m2=10000, ground_floor_bua_m2=1000,
              use_areas=[{"row": "2.i", "area_m2": 10000}])
    ol = report(largest_storey_area_m2=1000, **kw).occupant_load
    assert ol.occupant_load == 1076 and ol.storey_occupant_load == 108 and ol.min_exits == 2
    assert "at least" not in ol.exit_ref and "up to" not in ol.exit_ref
    ol = report(**kw).occupant_load
    assert ol.storey_occupant_load == 1076 and ol.min_exits == 4


# ------------------------------------------------------------------ CH3-13
def test_CH3_13_mall_factor_from_gla():
    """Table 3.13 row 14 p.287: GLA less than 14,000 m2 -> 2.8 m2; 14,000 m2 -> 3.3 m2,
    +0.1 m2 per 1,290 m2, max 5.1 m2. Re-pointed for owner ruling 12.10.2026 Ch3 Q3: a big
    mall is evaluated (blank GLA = GFA, labelled), no longer 'not evaluated'."""
    r = report(occupancy="mall_covered", height_m=10, floors_above_grade=2,
               gross_floor_area_m2=80000, ground_floor_bua_m2=40000)
    ol = r.occupant_load
    assert ol.evaluated and ol.factor_m2_per_person == 5.1 and ol.occupant_load == 15687
    assert "GFA used as the GLA" in ol.factor_ref
    r = report(occupancy="mall_covered", height_m=5, floors_above_grade=1,
               gross_floor_area_m2=10000, ground_floor_bua_m2=10000)
    assert r.occupant_load.factor_m2_per_person == 2.8
    assert r.occupant_load.occupant_load == 3572


# ------------------------------------------------------------------ CH3-14
def test_CH3_14_staff_labour_hostel_use_table_3_16_row_7():
    """Table 3.16 row 7 p.293: S 15 / NS 10.7, S 15 / NS 10.7, S 76 / NS 61 m."""
    for occ in ("labour_accommodation", "staff_accommodation", "hostel"):
        r = report(occupancy=occ, height_m=12, floors_above_grade=4,
                   gross_floor_area_m2=4000, ground_floor_bua_m2=1000)
        (t,) = moe(r, "Travel")
        # Re-pointed for owner ruling 12.10.2026 Ch3 Q8: one column, named.
        want = "Travel 76 m" if engine.building_sprinklered(r.building) else "Travel 61 m"
        assert want in t.spec and "row 7" in t.system, occ
        assert "Apartment" not in t.spec
    r = report(occupancy="residential", height_m=12, floors_above_grade=4,
               gross_floor_area_m2=4000, ground_floor_bua_m2=1000)
    (t,) = moe(r, "Travel")
    want = ("Apartment main door to exit (6.i): commonpath 15 m, dead end 15 m, travel 61 m"
            if engine.building_sprinklered(r.building) else
            "Apartment main door to exit (6.i): commonpath 10.7 m, dead end 10.7 m, travel 30 m")
    assert want in t.spec


# ------------------------------------------------------------------ CH3-15
def test_CH3_15_table_3_15_a_and_3_15_b_scope():
    """#4.4.8 p.291: Table 3.15.a does not apply to basements / podiums used only for
    parking and service rooms; Table 3.15.b does."""
    r = report(occupancy="parking_enclosed", height_m=5, floors_above_grade=1,
               floors_below_grade=3, gross_floor_area_m2=8000)
    assert not moe(r, "Exit Remoteness")
    assert moe(r, "Basement / Parking Podium Travel Distance")
    r = report(occupancy="high_depth_underground", height_m=5, floors_above_grade=1,
               floors_below_grade=3, gross_floor_area_m2=8000, has_parking_area=False)
    assert not moe(r, "Basement / Parking Podium Travel Distance")
    r = report(occupancy="business", height_m=12, floors_above_grade=4,
               floors_below_grade=2, gross_floor_area_m2=6000, has_parking_area=True)
    assert moe(r, "Basement / Parking Podium Travel Distance")


# ------------------------------------------------------------------ CH3-16
def test_CH3_16_hh_doors_outswing_only_citation_item_4_i():
    """Table 3.2 item 4.i p.248 (swing); item 12 p.250 sets no panic-hardware trigger."""
    r = report(occupancy="storage_industrial", height_m=8, floors_above_grade=1,
               gross_floor_area_m2=3000, ground_floor_bua_m2=3000, hazard_class="HH")
    (d,) = moe(r, "Hazardous Area Doors")
    assert d.status == "required" and "swing in the direction of egress" in d.spec
    assert "panic" not in d.spec.lower() and "item 8" not in d.code_ref
    assert d.code_ref == "Ch 3, #3.2 / Table 3.2 item 4.i" and d.page_ref == "p.248"


# ------------------------------------------------------------------ CH3-17
def test_CH3_17_fire_access_citations_full():
    """Table 2.4 p.213 (sprinklered midrise, 4,001 - 8,000 m2 -> 1/4); width and clearance
    in Table 2.1 p.206 and #2.6.1 / #2.6.3 p.207."""
    s = Building(occupancy="residential", height_m=20, floors_above_grade=6,
                 gross_floor_area_m2=36000, ground_floor_bua_m2=6000)
    r = engine.evaluate(s)
    assert r.fire_access.sprinklered_assumed is True
    it = extent_item(r)
    assert it.spec == "1/4 perimeter"
    assert it.code_ref == "Ch 2, #2.8.6 / Table 2.4" and it.page_ref == "p.213"
    (w,) = fsa(r, "Fire vehicle accessway width")
    assert w.code_ref == "Ch 2, Table 2.1 / #2.6.1 / #2.6.3" and w.page_ref == "p.206-207"


# ------------------------------------------------------------------ CH3-18
def test_CH3_18_branch_pages_include_table_3_16_page():
    """Table 3.16 rows 10-18 p.294, rows 19-22 p.295; villas Table 3.27 p.323."""
    rules = engine.load_rules("ch3_means_of_egress.yaml")
    page = {br["id"]: br["page"] for br in rules["branches"]}
    assert page["moe_mall"] == "p.287, 294"
    assert page["moe_mercantile"] == "p.286, 294"
    assert page["moe_detention"] == "p.286, 294"
    assert page["moe_storage_industrial_ordinary"] == "p.287, 294-295"
    assert page["moe_storage_industrial_high_hazard"] == "p.287, 294"
    assert page["moe_animal_housing"] == "p.287, 295"
    assert page["moe_villa_private"] == "p.323"


# ------------------------------------------------------------------ CH3-19
def test_CH3_19_education_two_exit_stairs_required():
    """Table 3.20 item 4 p.305; Table 3.21 item 5 p.307: single exit stair not permitted."""
    for occ, ref in (("education_a", "Table 3.20 item 4"), ("education_b", "Table 3.21 item 5"),
                     ("education_c", "Table 3.21 item 5")):
        r = report(occupancy=occ, height_m=8, floors_above_grade=2,
                   gross_floor_area_m2=2000, ground_floor_bua_m2=1000)
        (it,) = moe(r, "Minimum 2 Exit Stairs")
        assert it.status == "required" and ref in it.code_ref, occ


# ------------------------------------------------------------------ CH3-20
def test_CH3_20_door_force_and_aisle_riser_text():
    """Table 3.17 item 8.iii p.298: aisle riser 100-205 mm; item 3.i p.297: 178 mm is the
    factor-A threshold. Table 3.2 item 5.ii: 133 N to set the leaf in motion."""
    r = report(occupancy="business", height_m=8, floors_above_grade=2,
               gross_floor_area_m2=2000, ground_floor_bua_m2=1000)
    (door,) = moe(r, "Door Assembly Minimums")
    assert "133 N" in door.spec and "max opening force 67 N" not in door.spec
    (stair,) = moe(r, "Stair Geometry")
    assert "178 mm being" not in stair.detail
    assert "205 mm" in stair.detail and "factor A" in stair.detail


# ------------------------------------------------------------------ CH3-21
def test_CH3_21_sprinkler_status_from_ch9_table_2_3_reachable():
    """Table 2.3 p.213 (midrise without sprinklers): 2,000 - 4,000 m2 -> 1/4 perimeter."""
    b = Building(occupancy="business", height_m=20, floors_above_grade=6,
                 gross_floor_area_m2=18000, ground_floor_bua_m2=3000)
    s = compute_fire_access(b, sprinklered=False)
    assert s.extent == "1/4 perimeter" and "Table 2.3" in s.extent_ref
    s = compute_fire_access(b, sprinklered=True)
    assert "1/6" in s.extent and "Table 2.4" in s.extent_ref
    # The engine passes the Ch 9 result, not a height guess.
    for occ, h in (("mall_open", 20), ("business", 10), ("residential", 40)):
        bb = Building(occupancy=occ, height_m=h, floors_above_grade=max(1, int(h // 3.5)),
                      gross_floor_area_m2=6000, ground_floor_bua_m2=3000)
        assert engine.evaluate(bb).fire_access.sprinklered_assumed == engine.building_sprinklered(bb)
    # Table 2.7 printed overlap 113,001 - 113,600 m3: re-pointed for owner ruling
    # 12.10.2026 Ch3 Q4, the higher band (3/4) is taken and stated.
    b = Building(occupancy="storage_industrial", height_m=10, floors_above_grade=1,
                 ground_floor_bua_m2=11330)
    s = compute_fire_access(b, sprinklered=True)
    assert s.extent == "3/4 perimeter" and "Ch3 Q4" in s.extent_ref


# ------------------------------------------------------------------ CH3-22
def test_CH3_22_actual_use_travel_and_education_corridors():
    """Table 3.16 p.293-295 has no row for these occupancies; Table 3.20 item 2 p.305 and
    Table 3.21 item 2 p.307 corridors 1830 mm / 3000 mm."""
    r = report(occupancy="motor_fuel_dispensing", height_m=5, floors_above_grade=1,
               gross_floor_area_m2=300, ground_floor_bua_m2=300)
    (t,) = moe(r, "Travel / Dead-end / Commonpath by Actual Use")
    assert t.status == "required" and "actual use" in t.spec
    r = report(occupancy="education_a", height_m=8, floors_above_grade=2,
               gross_floor_area_m2=2000, ground_floor_bua_m2=1000)
    (c,) = moe(r, "Corridors (Table 3.20 item 2)")
    assert "1830 mm" in c.spec
    r = report(occupancy="education_b", height_m=8, floors_above_grade=2,
               gross_floor_area_m2=2000, ground_floor_bua_m2=1000)
    (c,) = moe(r, "Corridors (Table 3.21 item 2)")
    assert "1830 mm" in c.spec and "3000 mm" in c.spec


# ------------------------------------------------------------------ text rules
def test_ch3_package_text_has_no_banned_characters():
    """Brief rule 3: '#' for clauses; no tilde, approximately sign or section sign."""
    for occ, h in (("storage_industrial", 12), ("mall_covered", 100), ("business", 40),
                   ("villa_private", 7), ("mixed_multiple", 20)):
        r = report(occupancy=occ, height_m=h, gross_floor_area_m2=12000,
                   ground_floor_bua_m2=4000)
        texts = [r.occupant_load.note, r.occupant_load.exit_ref, r.occupant_load.factor_ref]
        for code in ("FSA", "MOE"):
            texts += [x for it in items(r, code) for x in (it.spec, it.detail, it.code_ref) if x]
        joined = " ".join(texts)
        for ch in ("~", "≈", "§"):
            assert ch not in joined, (occ, ch)
