"""Audit 28.10.2026, fix round ch1011: Ch 10 Smoke Control, Ch 11 LPG, Ch 19 EAP,
Annexure 2 submission checklist. One test (or more) per finding of the CH10-11 ledger
(C10-01..12, C11-01..10, EAP-01..05, A2-01..02) and owner rulings R-B, R-D.

Every quoted value was read off the page text named in the test (scratchpad pages/pNNNN.txt).
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import engine  # noqa: E402
from flsc_schema import Building  # noqa: E402
from submission_checklist import build_submission_checklist  # noqa: E402
from test_phase1_findings import items, report  # noqa: E402

BASE = dict(ground_floor_bua_m2=1000)
RB = ("Applies to any enclosed building on the site (warehouse, pump house, office). Ch 10 "
      "prints no row for open yards / aboveground tank farms (owner ruling R-B, 28.10.2026).")


def sc(r, status=None):
    return [it for it in items(r, "SC") if status is None or it.status == status]


def starts(r, code, prefix):
    return [it for it in items(r, code) if it.system.startswith(prefix)]


def one(r, code, prefix):
    hits = starts(r, code, prefix)
    assert len(hits) == 1, [(h.system, h.status) for h in hits]
    return hits[0]


# ================================================================ Ch 10
# ---------------------------------------------------------------- C10-01 / R-D
KITCHEN_III = "Kitchen Cooking Operation Ventilation (malls, hospitals, highrise"
KITCHEN_RES = "Kitchen Cooking Operation Ventilation - apartment / hotel-room kitchens"


@pytest.mark.parametrize("kw", [
    dict(occupancy="mall_covered", height_m=12, gross_floor_area_m2=20000),
    dict(occupancy="healthcare_a", height_m=12),
    dict(occupancy="business", business_group="B", height_m=30),
    dict(occupancy="mercantile_b", height_m=23.0),
    dict(occupancy="healthcare_a", height_m=40),
])
def test_C10_01_R_D_kitchen_16iii_required_malls_hospitals_non_residential_highrise(kw):
    """p.866 Table 10.27 item 16.iii: 'All Kitchens located in Malls, Hospitals and Highrise
    buildings shall be provided with ventilation systems for cooking operations in accordance
    with Section 2.18.' Ruling R-D: required with no commercial-kitchen tick."""
    k = one(report(**kw, **BASE), "SC", KITCHEN_III)
    assert k.status == "required"
    assert k.code_ref == "Ch 10, #3.9 / Table 10.27 item 16.iii" and k.page_ref == "p.866"
    assert "Section 2.18" in k.spec and "R-D" in k.detail
    assert not starts(report(**kw, **BASE), "SC", KITCHEN_RES)


@pytest.mark.parametrize("occ", ["residential", "hotel_a", "hotel_b", "staff_accommodation",
                                 "labour_accommodation", "hostel"])
def test_C10_01_R_D_apartment_and_hotel_room_kitchens_conditional_in_highrise(occ):
    r = report(occupancy=occ, height_m=40, **BASE)
    k = one(r, "SC", KITCHEN_RES)
    assert k.status == "conditional" and "R-D" in k.detail and "item 16.iii" in k.code_ref
    assert not starts(r, "SC", KITCHEN_III)


def test_C10_01_no_16iii_line_lowrise_and_commercial_tick_keeps_16i_16ii():
    low = report(occupancy="residential", height_m=12, **BASE)
    assert not [it for it in sc(low) if it.system.startswith("Kitchen")]
    biz = report(occupancy="business", business_group="B", height_m=12, **BASE)
    assert not [it for it in sc(biz) if it.system.startswith("Kitchen")]
    tick = report(occupancy="hotel_a", height_m=18, has_commercial_kitchen=True, **BASE)
    k = one(tick, "SC", "Kitchen Cooking Operation Ventilation")
    assert k.status == "required" and k.code_ref == "Ch 10, #3.9 / Table 10.27 items 16.i-16.ii"
    assert "All restaurant kitchens" in k.detail and "Section 2.18" in k.spec


@pytest.mark.parametrize("occ", ["parking_open", "parking_enclosed"])
def test_C10_01_R_D_highrise_parking_kitchen_line_conditional(occ):
    """A parking use has no kitchen of its own: conditional (listed as needs ruling)."""
    r = report(occupancy=occ, height_m=30, gross_floor_area_m2=3000, **BASE)
    k = one(r, "SC", "Kitchen Cooking Operation Ventilation")
    assert k.status == "conditional" and "R-D" in k.detail and k.system.endswith("any kitchen)")
    assert not starts(report(occupancy=occ, height_m=12, gross_floor_area_m2=3000, **BASE),
                      "SC", "Kitchen")


# ---------------------------------------------------------------- C10-02
def test_C10_02_storage_blank_gf_bua_not_evaluated_not_lowest_row():
    """p.864 Table 10.26 item 1 tiers by 'TOTAL BUILT-UP GROUND FLOOR AREA'; a blank never
    takes the less than 230 m2 row."""
    r = report(occupancy="storage_industrial", height_m=8, hazard_class="OH1", sum_gf_bua_m2=1000)
    ne = one(r, "SC", "Factory / Warehouse Smoke Extract (Table 10.26 item 1) - NOT EVALUATED")
    assert ne.status == "not_evaluated" and "ground floor built-up area" in ne.system
    assert ne.code_ref == "Ch 10, #3.8 / Table 10.26 item 1" and ne.page_ref == "p.864"
    assert not [it for it in sc(r) if it.source_rule and it.source_rule.startswith("sc_storage_industrial_")
                and "NOT EVALUATED" not in it.system]
    ok = report(occupancy="storage_industrial", height_m=8, hazard_class="OH1",
                ground_floor_bua_m2=200, sum_gf_bua_m2=200)
    assert one(ok, "SC", "Roof Ventilation System").status == "required"
    assert not [it for it in sc(ok) if "NOT EVALUATED" in it.system]


def test_C10_02_open_parking_blank_gfa_not_evaluated_not_purging_not_required():
    """p.860 Table 10.23 item 2.2 (up to 4000 m2) vs 2.3 (more than 4000 m2)."""
    r = report(occupancy="parking_open", height_m=10, **BASE)
    ne = one(r, "SC", "Open Parking Smoke Purging (Table 10.23 item 2.2 / 2.3) - NOT EVALUATED")
    assert ne.status == "not_evaluated" and "gross floor area" in ne.system
    assert not starts(r, "SC", "Smoke Purging / Ventilation NOT Required")
    assert not starts(r, "SC", "Mechanical Smoke Purging OR Jet Fan")
    small = report(occupancy="parking_open", height_m=10, gross_floor_area_m2=3000, **BASE)
    assert one(small, "SC", "Smoke Purging / Ventilation NOT Required").status == "not_required"


# ---------------------------------------------------------------- C10-03
@pytest.mark.parametrize("occ,h,gfa", [("parking_open", 30, 3000), ("parking_open", 30, 6000),
                                       ("parking_enclosed", 30, 3000), ("parking_open", 95, 3000),
                                       ("parking_enclosed", 23.0, 3000)])
def test_C10_03_highrise_parking_stair_printed_once_and_no_req_notreq_pair(occ, h, gfa):
    """p.857 #3.2.1 (Table 10.20, highrise) and p.860 #3.5.1 / Table 10.23 items 1.iv, 2.2.ii,
    2.3.ii (parking stairs more than 23 m): one stair pressurization line citing both."""
    r = report(occupancy=occ, height_m=h, gross_floor_area_m2=gfa, **BASE)
    st = one(r, "SC", "Stair Pressurization")
    assert st.status == "required" and st.system == "Stair Pressurization (parking, height 23 m or more)"
    tall = "Table 10.19" if h > 90 else "Table 10.20"
    assert "Table 10.23" in st.code_ref and tall in st.code_ref
    assert "multiple injection" in st.spec.lower() and "C10-03" in st.detail
    req = {it.system.lower() for it in sc(r, "required")}
    nr = {it.system.lower() for it in sc(r, "not_required")}
    assert not (req & nr)
    assert not starts(r, "SC", "Smoke Purging / Ventilation NOT Required")


def test_C10_03_open_parking_highrise_corridor_line_governs_and_names_table_10_23():
    r = report(occupancy="parking_open", height_m=30, gross_floor_area_m2=3000, **BASE)
    cor = one(r, "SC", "Enclosed Corridor Smoke Management")
    assert cor.status == "required"
    assert "Table 10.23 item 2.2.i" in cor.detail and "more onerous" in cor.detail
    assert "shall not be required to have any smoke purging or ventilation system" in cor.detail
    assert "#3.2.1" in cor.detail and "#3.5.1" in cor.detail
    big = report(occupancy="parking_open", height_m=30, gross_floor_area_m2=6000, **BASE)
    assert one(big, "SC", "Mechanical Smoke Purging OR Jet Fan").status == "required"
    assert "Table 10.23 item 2.3" in one(big, "SC", "Enclosed Corridor Smoke Management").detail
    # non-parking highrise unchanged: plain stair line, no Table 10.23
    res = report(occupancy="residential", height_m=30, **BASE)
    assert "Table 10.23" not in one(res, "SC", "Stair Pressurization").code_ref


def test_C10_03_attached_parking_30m_stair_once():
    b = Building(occupancy="residential", height_m=60, floors_above_grade=17, floors_below_grade=2,
                 depth_below_grade_m=7, ground_floor_bua_m2=1500, plot_area_m2=5000,
                 has_parking_area=True, parking_area_m2=3000, parking_height_m=30,
                 parking_basement_levels=2)
    r = engine.evaluate(b)
    pk = [it for c in r.attached_parking_chapters if c.chapter_code == "SC"
          for bl in c.blocks for it in bl.items]
    stairs = [it for it in pk if it.system.startswith("Stair Pressurization")
              and it.status == "required" and "basement" not in it.system]
    assert [s.system for s in stairs] == ["Stair Pressurization (parking, height 23 m or more)"]


# ---------------------------------------------------------------- C10-04 + CO cross-reference
def test_C10_04_enclosed_parking_line_prints_1ii_1iii_and_co_cross_reference():
    r = report(occupancy="parking_enclosed", height_m=12, **BASE)
    p = one(r, "SC", "Mechanical Smoke Purging via Dedicated Ducting")
    assert "single basement carparks, having an area less than 3600 m2" in p.detail
    assert "A jet fan system shall not be permitted in enclosed parking" in p.detail
    co = one(r, "SC", "Carbon Monoxide (CO) Detection Interfaced with the Ventilation System")
    assert co.status == "required"
    assert co.code_ref == "Ch 3, Table 3.37 item 7.i" and co.page_ref == "p.338"
    assert "interfacing with ventilation system" in co.detail
    assert not starts(report(occupancy="parking_open", height_m=12, gross_floor_area_m2=3000, **BASE),
                      "SC", "Carbon Monoxide")


# ---------------------------------------------------------------- C10-05
@pytest.mark.parametrize("flag,name", [("has_fire_pump_room", "Fire Pump Room"),
                                       ("has_control_room", "Emergency Command Centre"),
                                       ("has_diesel_generator_room", "Diesel Generator Room")])
def test_C10_05_items_5_7_print_section_2_17_and_temperature_control(flag, name):
    r = report(occupancy="business", business_group="B", height_m=12, **{flag: True}, **BASE)
    it = one(r, "SC", name)
    assert "dedicated mechanical ventilation system in accordance with Section 2.17" in it.spec
    assert "Rooms shall be temperature controlled" in it.detail
    assert "Dedicated AHU are recommended" in it.detail
    assert "item ii" in it.detail


# ---------------------------------------------------------------- C10-06
def test_C10_06_infrastructure_without_building_gets_no_table_10_21_lines():
    r = report(occupancy="infrastructure", height_m=0)
    bad = [it.system for it in sc(r) if it.source_rule and it.source_rule.startswith("sc_midrise_lowrise")]
    assert bad == []
    # with a road tunnel the Table 10.25 line still prints
    t = report(occupancy="infrastructure", height_m=0, has_tunnel=True, tunnel_length_m=200)
    assert starts(t, "SC", "Tunnel Smoke Management")


# ---------------------------------------------------------------- C10-07
def test_C10_07_highrise_lobby_two_cases_no_preference():
    r = report(occupancy="residential", height_m=40, **BASE)
    lob = one(r, "SC", "Passenger Elevator Lobby OR Lift Hoistway Pressurization")
    assert "preferred" not in (lob.detail or "") and "preferred" not in (lob.spec or "")
    assert "Section 2.19" in lob.spec and "1-hour" in lob.detail


# ---------------------------------------------------------------- C10-08
def test_C10_08_open_plan_office_highrise_stair_once_and_required():
    r = report(occupancy="business", business_group="B", height_m=30, **BASE)
    assert not starts(r, "SC", "Stair Pressurization (open-plan office")
    st = one(r, "SC", "Stair Pressurization")
    assert st.status == "required" and "Table 10.27 item 3.iii" in st.code_ref
    assert "stairs of open plan offices in highrise buildings shall be pressurized" in st.detail


# ---------------------------------------------------------------- C10-09
def test_C10_09_section_2_5_general_requirements_line():
    r = report(occupancy="residential", height_m=40, **BASE)
    g = one(r, "SC", "Smoke Control General Requirements (Section 2.5 / Table 10.3)")
    assert g.status == "required" and g.page_ref == "p.809, p.822, p.836, p.1281"
    for s in ("secondary source of power supply", "2 hour fire-resistance rating",
              "not exceed 60 seconds", "400°C for 2 hours"):
        assert s in g.spec, s
    assert "Metal conduits in lieu of 2 hour fire resistance rating shall not be acceptable" in g.detail
    # no required smoke control system -> no general line
    low = report(occupancy="residential", height_m=10, has_fire_pump_room=False, **BASE)
    assert not starts(low, "SC", "Smoke Control General Requirements")


def test_C10_09_warehouse_rows_state_back_up_power():
    r = report(occupancy="storage_industrial", height_m=8, hazard_class="OH1",
               ground_floor_bua_m2=2500, sum_gf_bua_m2=2500)
    ex = one(r, "SC", "Mechanical Roof Exhaust Fans")
    assert "THAT DO NOT HAVE BACK-UP POWER" in ex.detail


# ---------------------------------------------------------------- C10-10
def test_C10_10_air_change_rates_printed():
    res = report(occupancy="residential", height_m=40, floors_below_grade=1,
                 depth_below_grade_m=4, **BASE)
    assert "6 air changes per hour" in one(res, "SC", "Enclosed Corridor Smoke Management").spec
    assert "6 air changes per hour" in one(res, "SC", "Corridor and Open Circulation Smoke Management").spec
    rooms = one(res, "SC", "Enclosed Rooms > 280 m2")
    assert "10 air changes per hour" in rooms.detail and "9 air changes per hour" in rooms.detail
    park = report(occupancy="parking_enclosed", height_m=12, **BASE)
    p = one(park, "SC", "Mechanical Smoke Purging via Dedicated Ducting")
    assert "10 air changes per hour in a single smoke zone of not more than 3600 m2" in p.spec
    assert "FAQ #31" in p.detail and "9 air changes per hour" in p.detail
    for occ in ("healthcare_a", "education_b"):
        r = report(occupancy=occ, height_m=12, **BASE)
        cor = [it for it in sc(r, "required") if "Corridor" in it.system and "Section 2.8" in (it.spec or "")]
        assert cor and all("6 air changes per hour" in c.spec for c in cor), occ


# ---------------------------------------------------------------- C10-11
def test_C10_11_open_parking_large_hybrid_zoning_and_definition():
    r = report(occupancy="parking_open", height_m=10, gross_floor_area_m2=6000, **BASE)
    o = one(r, "SC", "Mechanical Smoke Purging OR Jet Fan System")
    assert "combination thereof as a hybrid system" in o.spec
    assert "zoning shall be permitted to be 4000 m2" in o.detail
    assert "0.4 m2 for each linear meter" in o.detail and "40 percent" in o.detail
    assert "20 percent open" in o.detail and "within 30 m" in o.detail
    assert "At least 10 air-changes per hour" in o.detail


# ---------------------------------------------------------------- C10-12
def test_C10_12_mall_tenant_over_1000_conditional():
    r = report(occupancy="mall_covered", height_m=12, gross_floor_area_m2=20000, **BASE)
    t = one(r, "SC", "Anchor / Hypermarket / Tenant > 1000")
    assert t.status == "conditional" and "1000 m2" in t.detail and "6 ACH" in t.detail


# ---------------------------------------------------------------- R-B (Cursor PRs #29, #30)
@pytest.mark.parametrize("flag", ["is_aboveground_tank_storage", "is_open_yard_storage"])
@pytest.mark.parametrize("gf", [200, 600, 1500, 2500])
def test_R_B_groups_T_U_table_10_26_rows_conditional_with_ruling_wording(flag, gf):
    r = report(occupancy="storage_industrial", height_m=8, hazard_class="HH",
               ground_floor_bua_m2=gf, gross_floor_area_m2=gf, sum_gf_bua_m2=gf, **{flag: True})
    rows = [it for it in sc(r) if (it.source_rule or "").startswith("sc_storage_industrial_")]
    assert rows
    for it in rows:
        assert it.status == "conditional", it.system
        assert it.detail.startswith(RB), it.detail
        assert it.status != "not_required"
    plain = report(occupancy="storage_industrial", height_m=8, hazard_class="HH",
                   ground_floor_bua_m2=gf, gross_floor_area_m2=gf, sum_gf_bua_m2=gf)
    assert all(it.status == "required" for it in sc(plain)
               if (it.source_rule or "").startswith("sc_storage_industrial_"))


# ================================================================ Ch 11
TANKS = dict(occupancy="residential", height_m=30, has_lpg_tanks=True, **BASE)


def test_C11_01_tanker_parking_and_point_of_transfer_with_any_lpg_tank():
    r = report(**TANKS)
    park = one(r, "LPG", "LPG Bulk Tanker Parking Area (#4.8)")
    assert park.status == "required" and park.page_ref == "p.929"
    assert "minimum 14 meters in length, 4 meters clear wide" in park.spec
    assert "minimum 20 meters in length, 4 meters clear wide" in park.spec
    assert "15000 liters (3,300 Gal.)" in park.spec
    assert "No LPG installation without dedicated, safe clear parking" in park.detail
    assert "5 m" in park.detail and "tank capacity" in park.detail
    pt = one(r, "LPG", "Point of Transfer Separation Distances (Table 11.13)")
    assert pt.status == "required" and pt.page_ref == "p.925-926"
    for s in ("3 m", "7.6 m", "15 m", "1.5 m", "6 m"):
        assert s in pt.spec
    assert "doubled" in pt.detail and "one-half" in pt.detail
    for kind in ("has_lpg_tank_roof_mounted", "has_lpg_tank_underground_mounded"):
        assert starts(report(**TANKS, **{kind: True}), "LPG", "LPG Bulk Tanker Parking Area")
    infra = report(occupancy="residential", height_m=30, has_gas_infra_connection=True, **BASE)
    assert not starts(infra, "LPG", "LPG Bulk Tanker Parking Area")


FLAME = dict(occupancy="assembly_b", height_m=10, has_lpg_flame_effect=True,
             lpg_flame_effect_show="outdoor", **BASE)


def test_C11_02_flame_effect_table_11_12_items_3_4_7():
    r = report(**FLAME)
    sep = one(r, "LPG", "Flame Effect LPG Separation Distances (Table 11.12 #3)")
    assert sep.page_ref == "p.924"
    for s in ("6 m distance shall be maintained between cylinder compartment to any fire exit route",
              "10 m distance shall be maintained from LPG container compartment to Fire Hydrant",
              "3 m distance shall be maintained from cylinders to drains"):
        assert s in sep.spec, s
    mg = one(r, "LPG", "Flame Effect LPG Management (Table 11.12 #4, #7)")
    assert "low pressure supervision devices shall be installed" in mg.spec
    assert "'hold-open' type" in mg.spec
    assert "supervised and monitored by fire safety personnel" in mg.detail
    inst = one(r, "LPG", "Flame Effect LPG Installation (Table 11.12)")
    assert "Low-pressure interlock" not in inst.detail and "flame-out" not in inst.detail


UG = dict(TANKS, has_lpg_tank_underground_mounded=True)


def test_C11_03_underground_rows_printed_and_unprinted_text_removed():
    r = report(**UG)
    ug = one(r, "LPG", "Underground / Mounded LPG Tank Installation (Table 11.9)")
    allt = " ".join((it.spec or "") + " " + (it.detail or "") for it in items(r, "LPG"))
    for gone in ("monitoring access shaft", "Monitoring shaft", "vent risers", "Annual potential measurement",
                 "corrosion-rate monitoring", "high-point relief"):
        assert gone not in allt, gone
    for s in ("Buildings, sheds and canopies shall not be constructed over any underground or mounded",
              "at least 15 cm below grade", "at least 46 cm below grade", "more than 3 m below grade",
              "relief valves open to sky at grade level"):
        assert s in ug.spec + ug.detail, s
    ins = one(r, "LPG", "Underground / Mounded Tank Installation and Mounding (Table 11.9 #2)")
    for s in ("Cathodic protection shall be provided", "Concrete bed shall be provided",
              "at least 30 cm", "1.2 m in diameter", "free of rocks"):
        assert s in ins.spec + ins.detail, s
    gd = one(r, "LPG", "Explosion-Proof Gas Detector at Every Underground / Mounded Tank")
    assert gd.status == "required" and gd.code_ref == "Ch 11, Table 11.9 #2.xvi" and gd.page_ref == "p.916"


def test_C11_04_asme_reduction_conditional():
    a = one(report(**UG), "LPG", "ASME Container Reduction Allowance")
    assert a.status == "conditional" and "3.b" in a.code_ref


def test_C11_05_general_listing_cites_2_2_1_2_2_2_without_unprinted_exclusion():
    g = one(report(**TANKS), "LPG", "Civil Defence Listing + Approved Contractor (Universal)")
    assert g.code_ref == "Ch 11, #2.2.1-#2.2.3" and g.page_ref == "p.883"
    assert "General contractors" not in g.detail and "NOT permitted" not in g.detail
    assert "qualified, approved and licensed by Civil Defence" in g.detail


def test_C11_06_exterior_shut_off_valve_cites_2_3_14_6():
    v = one(report(**TANKS), "LPG", "Exterior Emergency Shut-off Valve per Building (#2.3.14.6)")
    assert v.code_ref == "Ch 11, #2.3.14.5-#2.3.14.6" and v.page_ref == "p.890"
    assert "plainly marked" in v.spec and "Section 2.5" not in v.spec
    assert "fire department" not in (v.detail or "")
    assert not starts(report(**TANKS), "LPG", "Manual Master Shut-off Valve")


CYL = dict(occupancy="mercantile_b", height_m=8, has_gas_cylinders_villa=True,
           is_new_or_modified_building=False, **BASE)


def test_C11_07_cylinder_regulation_prints_commercial_stage_and_hose_text():
    reg = one(report(**CYL), "LPG", "Two-Stage Pressure Regulation")
    assert "5 psi (0.350 bar) for large commercial customers" in reg.spec
    assert "75 mbar for residential customers" in reg.spec and "0.5 psi (0.035 bar)" in reg.spec
    assert reg.code_ref == "Ch 11, Table 11.4 #1.iii; #2.3.12.3" and reg.page_ref == "p.900, p.889"
    assert "only at appliance end" not in reg.detail
    assert "The hose shall be securely connected to the appliance" in reg.detail


@pytest.mark.parametrize("kw", [TANKS, CYL, dict(occupancy="residential", height_m=30,
                                                   has_gas_infra_connection=True, **BASE)])
def test_C11_08_pipe_routing_exclusions_and_marking(kw):
    p = one(report(**kw), "LPG", "LPG Piping Prohibited Areas + Pipe Marking (#2.2.7, #2.3.9.11)")
    assert p.status == "required" and p.page_ref == "p.884, p.889"
    for s in ("smoke stop lobbies", "fire-fighting water tank rooms", "areas of refuge",
              "protected corridors", "protected staircases", "bedrooms"):
        assert s in p.spec, s
    assert '"Orange"' in p.detail and '"Yellow"' in p.detail and "not more than 3 m" in p.detail


def test_C11_09_roof_tank_over_90m_prints_no_install_rows():
    r = report(occupancy="residential", height_m=95, has_lpg_tanks=True,
               has_lpg_tank_roof_mounted=True, gross_floor_area_m2=30000, **BASE)
    na = one(r, "LPG", "Roof LPG Tank Not Allowed")
    assert na.status == "required" and "Tables 11.7 and 11.8" in na.detail
    for p in ("Roof-Mounted LPG Tank", "Roof Tank ", "Mall 4,000 Gal Allowance"):
        assert not starts(r, "LPG", p), p
    ok = report(occupancy="residential", height_m=90, has_lpg_tanks=True,
                has_lpg_tank_roof_mounted=True, **BASE)
    assert starts(ok, "LPG", "Roof-Mounted LPG Tank Installation (Table 11.7)")


def test_C11_10_tables_11_6_b_c_d_values_printed():
    sep = one(report(**TANKS), "LPG", "Tank Separation Distances")
    assert "Table 11.6.b" in sep.detail and "with 1 hour fire wall" in sep.detail
    assert "2,001-30,000 Gal 15 m / 7.6 m" in sep.detail
    assert "Table 11.6.c" in sep.detail and "6 m to bund wall" in sep.detail
    assert "Table 11.6.d" in sep.detail and "Risk Assessment is required" in sep.detail
    assert sep.page_ref == "p.906-908"


# ================================================================ Ch 19 EAP
def _drill(r):
    return one(r, "EAP", "Drills and training")


@pytest.mark.parametrize("kw,row,must", [
    (dict(occupancy="residential", height_m=40), "#3.6",
     ["Drills shall involve entire occupants, with total evacuation alarm", "non-working day"]),
    (dict(occupancy="staff_accommodation", height_m=40), "#3.6",
     ["Drills shall involve entire occupants, with total evacuation alarm"]),
    (dict(occupancy="business", business_group="B", height_m=30), "#3.4",
     ["Drills shall involve entire occupants, with total evacuation alarm"]),
    (dict(occupancy="hotel_a", height_m=30), "#3.5",
     ["Drills shall not be required to involve Hotel guests and visitors"]),
    (dict(occupancy="healthcare_a", height_m=12), "#3.7",
     ["Drills shall not be required to involve occupants, patients or visitors", "non-visiting hours"]),
    (dict(occupancy="healthcare_b", height_m=12), "#3.7", ["non-visiting hours"]),
    (dict(occupancy="detention_a", height_m=12), "#3.8", ["non-visiting hours"]),
    (dict(occupancy="mall_covered", height_m=12, gross_floor_area_m2=20000), "#3.9",
     ["Drills shall not be required to involve public", "volunteers as public"]),
    (dict(occupancy="assembly_a", height_m=12), "#3.2", ["twice every 6 months"]),
    (dict(occupancy="education_b", height_m=12), "#3.3", ["entire school occupants"]),
])
def test_EAP_01_drills_per_table_19_2_occupancy_row(kw, row, must):
    d = _drill(report(**kw, **BASE))
    assert d.status == "required"
    assert f"Table 19.2 {row}" in d.spec
    for s in must:
        assert s in d.spec, s
    # the facility management team drill (#3.1) applies to every building as well
    assert "#3.1.ii" in d.spec


@pytest.mark.parametrize("kw", [dict(occupancy="residential", height_m=12),
                                dict(occupancy="business", business_group="B", height_m=12),
                                dict(occupancy="hotel_a", height_m=18),
                                dict(occupancy="mercantile_b", height_m=8)])
def test_EAP_01_lowrise_midrise_fm_drill_and_all_occupants_participate(kw):
    d = _drill(report(**kw, **BASE))
    assert "#3.1.ii" in d.spec and "every 6 months" in d.spec
    assert "#3.4" not in d.spec and "#3.6" not in d.spec and "#3.5" not in d.spec
    assert "All building occupants shall participate" in d.detail
    assert "no occupant drill frequency" in d.detail


@pytest.mark.parametrize("kw", [dict(occupancy="business", business_group="B", height_m=10),
                                dict(occupancy="mercantile_b", height_m=8),
                                dict(occupancy="residential", height_m=40)])
def test_EAP_02_command_roles_and_strategy_in_every_building(kw):
    r = report(**kw, **BASE)
    team = one(r, "EAP", "Emergency response team & fire wardens")
    assert team.status == "required" and team.code_ref == "Ch 19, Table 19.1 item 4.2.i"
    for s in ("a. Incident Fire Commander", "b. Assistant Incident Fire Commander", "c. Fire Warden",
              "d. Assistant Fire Warden", "e. Response Team of minimum 4 personnel",
              "Fire Responder, First Aider, Assembly Point Coordinator, Drill observer"):
        assert s in team.spec, s
    assert one(r, "EAP", "Evacuation strategy").status == "required"


def test_EAP_03_strategy_wording_as_printed():
    for kw in (dict(occupancy="healthcare_a", height_m=12), dict(occupancy="residential", height_m=40)):
        s = one(report(**kw, **BASE), "EAP", "Evacuation strategy")
        assert s.spec.startswith("Partial evacuation")
        assert "would be a suitable strategy" in s.spec
        assert "total evacuation for low/midrise" not in s.spec
        assert "shall be evaluated and certified by Civil Defence" in s.detail
    low = one(report(occupancy="business", business_group="B", height_m=10, **BASE), "EAP",
              "Evacuation strategy")
    assert not low.spec.startswith("Partial") and "Table 19.1 item 3" in low.spec


def test_EAP_04_villa_note_states_p1233_read_and_keeps_conditional():
    r = report(occupancy="villa_private", height_m=6, ground_floor_bua_m2=300)
    for it in items(r, "EAP"):
        assert it.status == "conditional", it.system
        assert "not yet read" not in (it.detail or "")
        assert "#2.1.1" in it.detail and "p.1233" in it.detail


def test_EAP_05_written_plan_language_evacuation_plan_vests_notice():
    r = report(occupancy="business", business_group="B", height_m=10, **BASE)
    w = one(r, "EAP", "Written Emergency Action Plan")
    assert "primarily in Arabic and English" in w.detail
    assert "Chapter 5. Table 5.1.8" in w.detail
    v = one(r, "EAP", "Response team vests")
    assert v.status == "required" and v.code_ref == "Ch 19, Table 19.1 item 9" and v.page_ref == "p.1244"
    assert "fluorescent jacket/vest" in v.spec
    assert "at least one week prior to the drill" in _drill(r).detail


# ================================================================ Annexure 2
def _cl(r):
    return {pkg: (note, req) for pkg, note, req in build_submission_checklist(r)}


def test_A2_01_file_names_do_not_submit_and_discipline_rejections():
    r = report(occupancy="residential", height_m=40, **BASE)
    cl = _cl(r)
    fn = cl["File names (Table A2.1 #3)"]
    assert fn[1] is True and "XXXXX (Application number)_LIFE SAFETY" in fn[0]
    assert "LPG NOT REQUIRED" in fn[0] and "Untitled" in fn[0]
    dn = cl["Drawings not to be submitted (Table A2.1 #4)"]
    assert dn[1] is True and "HVAC" in dn[0] and "Landscaping" in dn[0]
    ls = cl["Architecture / Life Safety rejection checks (Table A2.1 #5.ii.b-h, l-n)"]
    assert ls[1] is True and "1/3 of building diagonal" in ls[0] and "hatch entry" in ls[0]
    assert cl["Fire lift in dedicated shaft (Table A2.1 #5.ii.i)"][1] is True
    assert cl["Generator room (Table A2.1 #5.ii.k)"][1] is True
    assert cl["Fire lift lobby (Table A2.1 #5.ii.j)"][1] is False
    assert cl["Fire Detection and Alarm rejection checks (Table A2.1 #5.iii)"][1] is True
    assert "voice speakers" in cl["Fire Detection and Alarm rejection checks (Table A2.1 #5.iii)"][0]
    assert cl["Emergency Lighting rejection checks (Table A2.1 #5.iv)"][1] is True
    assert "vertical turbine" in cl["Fire Protection rejection checks (Table A2.1 #5.v)"][0]
    sc_ = cl["Smoke Control rejection checks (Table A2.1 #5.vi)"]
    assert sc_[1] is True and "With HVAC drawings" in sc_[0] and "arrow marks" in sc_[0]
    assert cl["LPG / Natural gas rejection checks (Table A2.1 #5.vii)"][1] is False
    lpg = _cl(report(**TANKS))["LPG / Natural gas rejection checks (Table A2.1 #5.vii)"]
    assert lpg[1] is True and "fill line" in lpg[0]
    low = _cl(report(occupancy="business", business_group="B", height_m=10, **BASE))
    assert low["Fire lift in dedicated shaft (Table A2.1 #5.ii.i)"][1] is False
    assert low["Generator room (Table A2.1 #5.ii.k)"][1] is False
    sup = _cl(report(occupancy="residential", height_m=95, **BASE))
    assert sup["Fire lift lobby (Table A2.1 #5.ii.j)"][1] is True
    assert "Figure A2.1.1" in cl["Legends per discipline (Table A2.1 #6)"][0]


def test_A2_02_no_unprinted_consultant_declaration_item():
    cl = _cl(report(occupancy="residential", height_m=40, **BASE))
    assert not [k for k in cl if "Consultant declaration" in k or "HoE" in k]
