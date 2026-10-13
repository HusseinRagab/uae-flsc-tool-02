"""Phase 5 Ch 2 / Ch 3 (13.10.2026): page requirements added from the rendered 2018 pages.

Owner card 13.10.2026 05:45Z "Add all 9" (option A): GAPS_ch2_ch3 G2, G3, G4, G5, G7,
G8, G9, G10, G11; cards "Fire lift buildings" (G6) and "Add item 4.iii" (G12). Text read
off p.208-211, 221, 225 (Ch 2) and p.255, 313, 316, 324, 338 (Ch 3).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_phase1_findings import items, report  # noqa: E402


def named(r, code, prefix):
    return [it for it in items(r, code) if it.system.startswith(prefix)]


# ------------------------------------------------------------------ Ch 2 (FSA)

def test_g2_accessway_position_2_to_10_m_where_an_accessway_is_required():
    r = report(occupancy="business", height_m=20, ground_floor_bua_m2=1000)
    (it,) = named(r, "FSA", "Accessway position from the building")
    assert it.status == "required"
    assert "not less than 2 m or more than 10 m from the building" in it.spec
    assert it.code_ref == "Ch 2, #2.8.2" and it.page_ref == "p.211"
    assert "Figure 2.4 (p.208)" in it.detail
    # #2.8.4.a lowrise / #2.8.3.a commercial villa: access road within 45 / 60 m, no line.
    for occ in ("business", "villa_commercial", "villa_private"):
        r = report(occupancy=occ, height_m=8, ground_floor_bua_m2=500)
        assert not named(r, "FSA", "Accessway position"), occ


def test_g3_inspection_pathway_1_m_on_every_building():
    for kw in ({"occupancy": "villa_private", "height_m": 7},
               {"occupancy": "business", "height_m": 60, "ground_floor_bua_m2": 1500}):
        r = report(**kw)
        (it,) = named(r, "FSA", "Firefighter inspection pathway")
        assert it.status == "required" and "minimum 1 m wide" in it.spec
        assert it.code_ref == "Ch 2, #2.6.7" and it.page_ref == "p.208"
    assert not named(report(occupancy="business", height_m=60), "MOE",
                     "Firefighter inspection pathway")


def test_g4_turning_facility_and_figures_2_5_to_2_7():
    r = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000)
    (dead,) = named(r, "FSA", "Access road dead end")
    assert "Maximum dead end 45 m" in dead.spec
    assert "U-turn, Y-turn, T-turn or roundabout" in dead.spec
    assert dead.code_ref == "Ch 2, Table 2.1 / #2.7.1" and dead.page_ref == "p.206, 209"
    (turn,) = named(r, "FSA", "Access road turning circle")
    assert "radius 12 m" in turn.spec
    for v in ("(R3) 12000 mm", "(R2) 11000 mm", "(R1) 7000 mm"):
        assert v in turn.spec, v
    assert "Figure 2.6 (p.209)" in turn.detail and "Figure 2.7 (p.210)" in turn.detail
    assert "6000, 36000, 20000, 11000, 6000 and R 7000 mm" in turn.detail
    assert "20000, 19000, 6000 and R 7000 mm" in turn.detail
    # Not a separate line: one dead-end and one turning line only.
    assert len(named(r, "FSA", "Access road")) == 5


def test_g5_firefighters_lift_lobby_super_highrise_only():
    r = report(occupancy="business", height_m=120, ground_floor_bua_m2=1500)
    (it,) = named(r, "FSA", "Firefighter's Lift Lobby")
    assert it.status == "required" and it.page_ref == "p.221"
    for v in ("9 m2", "2440 mm", "60 minutes fire door", "1-hour", "combustible"):
        assert v in it.spec, v
    assert "#2.9.5.f" in it.detail
    r = report(occupancy="business", height_m=60, ground_floor_bua_m2=1500)
    assert not named(r, "FSA", "Firefighter's Lift Lobby")
    assert named(r, "FSA", "Fire Lift")      # the Fire Lift line is unchanged


def test_g6_fire_exit_stair_only_where_the_fire_lift_is_required():
    r = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000)
    (it,) = named(r, "FSA", "Fire Exit Stair for fire fighters")
    assert it.status == "required"
    assert it.code_ref == "Ch 2, #2.9.6.a-b" and it.page_ref == "p.221"
    for v in ("2 hour rated", "smoke proof", "every habitable floor", "LPG tanks"):
        assert v in it.spec, v
    assert "highrise of 23 m or more" in it.detail and "roof-mounted LPG" not in it.detail
    r = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000,
               has_lpg_tank_roof_mounted=True)
    (it,) = named(r, "FSA", "Fire Exit Stair for fire fighters")
    assert "Ticked: roof-mounted LPG tanks" in it.detail
    (mall,) = named(report(occupancy="mall_covered", height_m=10, ground_floor_bua_m2=5000),
                    "FSA", "Fire Exit Stair for fire fighters")
    assert "mall" in mall.detail
    for kw in ({"occupancy": "business", "height_m": 20, "ground_floor_bua_m2": 1000},
               {"occupancy": "villa_private", "height_m": 7}):
        r = report(**kw)
        assert not named(r, "FSA", "Fire Lift")
        assert not named(r, "FSA", "Fire Exit Stair"), kw


def test_g7_fireboat_berth_on_the_waterfront_tick():
    r = report(occupancy="residential", height_m=40, ground_floor_bua_m2=1200,
               is_waterfront=True)
    (it,) = named(r, "FSA", "Fireboat access from the water front")
    assert it.status == "required"
    assert it.code_ref == "Ch 2, #3.2.1-#3.2.5 / Table 2.9" and it.page_ref == "p.225"
    for v in ("length 15 m", "width 5 m", "vertical clearance 6 m", "within 45 m",
              "corrosion resistant"):
        assert v in it.spec, v
    assert named(r, "FSA", "Waterfront property fire access")
    r = report(occupancy="residential", height_m=40, ground_floor_bua_m2=1200)
    assert not named(r, "FSA", "Fireboat")


# ------------------------------------------------------------------ Ch 3 (MOE)

def test_g8_stair_width_both_rows_as_text_every_occupancy():
    for occ in ("business", "villa_private", "villa_commercial", "parking_enclosed"):
        r = report(occupancy=occ, height_m=8, floors_above_grade=2,
                   gross_floor_area_m2=600, ground_floor_bua_m2=300)
        (st,) = named(r, "MOE", "Stair Geometry (Ch 3, #3.3)")
        assert ("not less than 1200 mm serving up to 2000 persons, not less than 1420 mm "
                "serving more than 2000 persons") in st.spec, occ
        assert "100 mm on each side at a height of 865 mm to 965 mm" in st.spec
        assert "Tread depth ≥ 280 mm" in st.spec       # items 2-5 kept
    r = report(occupancy="villa_private", height_m=7, floors_above_grade=2,
               gross_floor_area_m2=600, ground_floor_bua_m2=300)
    (prec,) = named(r, "MOE", "Villa: General Ch 3 Items")
    assert "not itemised" not in prec.detail and "#3.3.2 (p.255)" in prec.detail
    # Exactly one stair line: no automatic 1200 / 1420 pick line.
    assert not [it for it in items(r, "MOE") if "1420" in (it.system or "")]


def test_g9_commercial_villa_table_3_28_items():
    r = report(occupancy="villa_commercial", height_m=7, floors_above_grade=2,
               floors_below_grade=1, gross_floor_area_m2=1350, ground_floor_bua_m2=450)
    req = {it.system: it for it in items(r, "MOE") if it.status == "required"}
    for n in ("Commercial Villa: Separation (Table 3.28 item 2.i)",
              "Commercial Villa: Primary and Secondary Means of Escape (Table 3.28 item 3.i)",
              "Commercial Villa: Doors (Table 3.28 item 4)",
              "Commercial Villa: Hallway (Table 3.28 item 5.i)",
              "Commercial Villa: Two Primary Means of Escape - Floor over 400 m2 "
              "(Table 3.28 item 3.iii)",
              "Commercial Villa: Basement Exit Stair (Table 3.28 item 3.vi)"):
        assert n in req and req[n].page_ref == "p.324", n
    (multi,) = named(r, "MOE", "Commercial Villa: Egress Through a Nonresidential")
    assert multi.status == "conditional"
    (head,) = named(r, "MOE", "Means of Egress - Commercial Villa")
    assert "#5.7 prevails (#5.7.1)" in head.spec and head.code_ref == "Ch 3, #5.7.1 / Table 3.28"
    (prec,) = named(r, "MOE", "Villa: General Ch 3 Items")
    assert "Table 3.28 prevails (#5.7.1)" in prec.spec and "#5.7.1" in prec.code_ref
    assert prec.page_ref == "p.246-259, 323-324"
    # 400 m2 rule: conditional with no storey area and a GFA over 400 m2; absent when a
    # storey area of 400 m2 or less is entered.
    r = report(occupancy="villa_commercial", height_m=7, floors_above_grade=2,
               gross_floor_area_m2=700, ground_floor_bua_m2=0)
    (two,) = named(r, "MOE", "Commercial Villa: Two Primary")
    assert two.status == "conditional"
    r = report(occupancy="villa_commercial", height_m=7, floors_above_grade=2,
               gross_floor_area_m2=700, ground_floor_bua_m2=350, largest_storey_area_m2=380)
    assert not named(r, "MOE", "Commercial Villa: Two Primary")
    assert not named(r, "MOE", "Commercial Villa: Basement")
    # Private villa: none of the Table 3.28 lines.
    r = report(occupancy="villa_private", height_m=7, floors_above_grade=2,
               floors_below_grade=1, gross_floor_area_m2=1350, ground_floor_bua_m2=450)
    assert not named(r, "MOE", "Commercial Villa")


def test_g10_healthcare_a_b_smoke_compartments():
    for occ in ("healthcare_a", "healthcare_b"):
        r = report(occupancy=occ, height_m=12, gross_floor_area_m2=3000,
                   ground_floor_bua_m2=1000)
        (it,) = named(r, "MOE", "Smoke Compartments (Table 3.22 item 7)")
        assert it.status == "required" and it.page_ref == "p.313", occ
        assert "minimum of 2 smoke compartments, each not exceeding 2100 m2" in it.spec
        assert "1 hour fire resistance rated" in it.spec and "1090 mm" in it.detail
    r = report(occupancy="healthcare_c", height_m=12, gross_floor_area_m2=3000,
               ground_floor_bua_m2=1000)
    assert not named(r, "MOE", "Smoke Compartments (Table 3.22")


def test_g11_ambulatory_smoke_compartments_storey_over_900_m2():
    name = "Smoke Compartments - Storey over 900 m2 (Table 3.23 item 6)"
    r = report(occupancy="healthcare_c", height_m=8, floors_above_grade=2,
               gross_floor_area_m2=2000, ground_floor_bua_m2=1000)
    (it,) = named(r, "MOE", name)
    assert it.status == "required" and it.page_ref == "p.316"
    assert "each not exceeding 2000 m2" in it.spec and "1090 mm" in it.detail
    # No storey area, GFA over 900 m2 spread to 667 m2 per storey: conditional, not met.
    r = report(occupancy="healthcare_c", height_m=10, floors_above_grade=3,
               gross_floor_area_m2=2000)
    (it,) = named(r, "MOE", name)
    assert it.status == "conditional"
    # Storey area entered at 900 m2 or less: absent.
    r = report(occupancy="healthcare_c", height_m=10, floors_above_grade=3,
               gross_floor_area_m2=2000, ground_floor_bua_m2=700, largest_storey_area_m2=800)
    assert not named(r, "MOE", "Smoke Compartments")
    r = report(occupancy="healthcare_a", height_m=8, gross_floor_area_m2=2000,
               ground_floor_bua_m2=1000)
    assert not named(r, "MOE", "Smoke Compartments - Storey over 900")


def test_g12_parking_single_exit_and_ramp_allowance():
    ramp = ("In 1 level below or 1 level above discharge level of parking, vehicle ramp shall "
            "be considered as one of the means of egress, provided no shutters or doors are "
            "installed in such ramps.")
    for occ in ("parking_enclosed", "parking_open"):
        r = report(occupancy=occ, height_m=12, gross_floor_area_m2=6000,
                   ground_floor_bua_m2=1500)
        (it,) = named(r, "MOE", "Single Exit Not Permitted - Parking (Table 3.37 item 4)")
        assert it.status == "required" and it.page_ref == "p.338", occ
        assert "Single exit is not permitted" in it.spec and ramp in it.spec
        assert it.code_ref == "Ch 3, #5.16.1 / Table 3.37 item 4"
    r = report(occupancy="business", height_m=12, gross_floor_area_m2=6000,
               ground_floor_bua_m2=1500)
    assert not named(r, "MOE", "Single Exit Not Permitted - Parking")
