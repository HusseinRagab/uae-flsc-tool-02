"""Fix round 28.10.2026, area ch47 (Ch 4 extinguishers, Ch 5 exit signs, Ch 6 emergency
lighting, Ch 7 EVC). One test or more per finding of the CH04-07 ledger; values quoted
from the printed pages of UAE FLSC 2018 (CDGH-OP-25) named in each test.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_phase1_findings import report, items  # noqa: E402

EVC = "Emergency Voice Evacuation or Communication System (EVC)"
TWO_WAY = "Two-way Telephone Communication System"
RB = ("Applies to any enclosed building on the site (warehouse, pump house, office). "
      "Ch {n} prints no row for open yards / aboveground tank farms (owner ruling R-B, "
      "28.10.2026).")


def named(r, code, name):
    return [it for it in items(r, code) if it.system == name]


def t73(r):
    """The Table 7.3 lines (EVC + two-way) of the EVC chapter."""
    return [it for it in items(r, "EVC") if "Table 7.3" in (it.code_ref or "")]


def status_of(r, code, name):
    return [it.status for it in named(r, code, name)]


# ------------------------------------------------------------------ Ch 7
def test_H1_theme_park_tick_requires_evc_item_5():
    """Table 7.3 item 5 p.439 'AMUSEMENT AND THEME PARKS': 'i. Emergency Voice Evacuation
    or Communication System (EVC), in accordance with Section 2.4., Shall be provided.
    ii. Tow-way Telephone System ... shall be provided.'"""
    cases = (dict(occupancy="infrastructure", height_m=0),
             dict(occupancy="mercantile_a", height_m=8, ground_floor_bua_m2=1000),
             dict(occupancy="business", business_group="B", height_m=10),
             dict(occupancy="storage_industrial", height_m=10, gross_floor_area_m2=2000,
                  ground_floor_bua_m2=2000, sum_gf_bua_m2=2000),
             dict(occupancy="residential", height_m=10))
    for kw in cases:
        r = report(is_theme_park=True, **kw)
        e = named(r, "EVC", EVC)
        assert len(e) == 1 and e[0].status == "required", kw
        assert "Table 7.3 item 5" in e[0].code_ref, kw
        assert status_of(r, "EVC", TWO_WAY) == ["required"], kw
        assert not [it for it in items(r, "EVC") if it.status == "not_required"], kw


def test_H3_item_9_uses_larger_of_gfa_and_gf_bua_and_blank_is_not_evaluated():
    """Table 7.3 item 9 p.439 'STORAGE AND INDUSTRIAL OCCUPANCIES HAVING BUILT-UP AREA MORE
    THAN 5000 m2'. GFA blank, GF BUA 8000 m2: required. Both blank: NOT EVALUATED."""
    big = report(occupancy="storage_industrial", height_m=10, gross_floor_area_m2=0,
                 ground_floor_bua_m2=8000)
    e = named(big, "EVC", EVC)
    assert len(e) == 1 and e[0].status == "required" and "Table 7.3 item 9" in e[0].code_ref
    blank = report(occupancy="storage_industrial", height_m=10, gross_floor_area_m2=0,
                   ground_floor_bua_m2=0)
    ne = [it for it in items(blank, "EVC") if "NOT EVALUATED" in it.system]
    assert len(ne) == 1 and ne[0].status == "not_evaluated"
    assert "Table 7.3 item 9" in ne[0].code_ref and "5000 m2" in ne[0].detail
    assert not [it for it in items(blank, "EVC") if it.status == "not_required"]
    small = report(occupancy="storage_industrial", height_m=10, gross_floor_area_m2=3000,
                   ground_floor_bua_m2=2500)
    assert status_of(small, "EVC", "Emergency Voice Evacuation (EVC) - small storage/industrial") \
        == ["not_required"]


def test_M2_mixed_multiple_no_occupancy_listed_is_not_evaluated():
    """Table 7.3 p.439 items 3-9 list occupancies at any height; a mixed building whose
    occupancies are not listed cannot be passed (same rule as Ch 4 Class A, P3 Ch47 Q2)."""
    r = report(occupancy="mixed_multiple", height_m=10)
    ne = [it for it in items(r, "EVC") if "NOT EVALUATED" in it.system]
    assert len(ne) == 1 and ne[0].status == "not_evaluated" and "Table 7.3" in ne[0].code_ref
    assert not [it for it in items(r, "EVC") if it.status == "not_required"]
    tall = report(occupancy="mixed_multiple", height_m=30)
    assert status_of(tall, "EVC", EVC) == ["required"]
    assert not [it for it in items(tall, "EVC") if "NOT EVALUATED" in it.system]
    listed = report(occupancy="mixed_multiple", height_m=10, mixed_occupancy_mode="most_restrictive",
                    secondary_occupancies=["business"], business_group="B")
    assert not [it for it in items(listed, "EVC") if "NOT EVALUATED" in it.system]


def test_L1_one_evc_and_one_two_way_line_citing_every_table_7_3_row():
    """Table 7.3 p.439 prints one requirement (i. EVC, ii. two-way telephone) for all nine
    rows: one line set, citing every row that requires it."""
    st = report(occupancy="storage_industrial", height_m=30, gross_floor_area_m2=8000,
                ground_floor_bua_m2=4000)
    e, t = named(st, "EVC", EVC), named(st, "EVC", TWO_WAY)
    assert len(e) == 1 and len(t) == 1
    assert "Table 7.3 items 2 and 9" in e[0].code_ref and "Table 7.3 items 2 and 9" in t[0].code_ref
    mall = report(occupancy="mall_covered", height_m=30, ground_floor_bua_m2=8000)
    assert [it.code_ref for it in named(mall, "EVC", EVC)] == ["Ch 7, #3.1 / Table 7.3 items 2 and 3"]
    asm = report(occupancy="assembly_a", height_m=10, has_amusement_confounding=True)
    assert len(t73(asm)) == 2
    assert "Table 7.3 items 4 and 5" in named(asm, "EVC", EVC)[0].code_ref
    one = report(occupancy="hotel_a", height_m=10)
    assert [it.code_ref for it in named(one, "EVC", EVC)] == ["Ch 7, #3.1 / Table 7.3 item 7"]


def test_PR19_amusement_row_not_printed_beside_not_required_rows():
    """Table 7.3 item 5 p.439 requires EVC; the 'not listed' rows are tool text and must not
    print beside it (Cursor PR #19, sweep class 3)."""
    for kw in (dict(occupancy="residential", height_m=12),
               dict(occupancy="business", business_group="A", height_m=10),
               dict(occupancy="villa_private", height_m=6)):
        r = report(has_amusement_confounding=True, **kw)
        assert status_of(r, "EVC", EVC) == ["required"], kw
        assert not [it for it in items(r, "EVC") if it.status == "not_required"], kw


def test_L2_installation_height_reads_printed_122_mm_as_1220_mm():
    """Table 7.1 item 10.i p.436 prints 'a minimum of 910 mm and a maximum of 122 mm'."""
    r = report(occupancy="hotel_a", height_m=10)
    (h,) = named(r, "EVC", "Installation Heights (910-1220 mm mounting envelope)")
    assert "122 mm" in h.detail and "1220 mm" in h.detail and "Table 7.2 item 5.ii" in h.detail


def test_L3_permissions_are_not_printed_as_required():
    """p.433 Table 7.1 item 3 PAS '... shall be permitted'; p.434 item 4.1 tone 'shall be
    permitted to be part of the voice message'."""
    r = report(occupancy="hotel_a", height_m=10)
    assert status_of(r, "EVC", "Positive Alarm Sequence (Delayed Alarm)") == ["conditional"]
    assert status_of(r, "EVC", "Tone in Sleeping-Risk Occupancies") == ["conditional"]


def test_L4_missing_table_7_1_and_section_4_5_lines_added():
    """p.431 #2.2.5; p.433 Table 7.1 item 2.2.i; p.435 items 7.1.i-iii and 8.iii;
    p.440 #4.4.2; p.441 #5.1 / Table 7.4."""
    r = report(occupancy="hotel_a", height_m=10)
    req = {it.code_ref: it for it in items(r, "EVC", required_only=True)}
    refs = " | ".join(req)
    for ref in ("#2.2.5", "Table 7.1 item 2.2", "Table 7.1 item 7.1", "#4.4.2", "Table 7.4"):
        assert ref in refs, ref
    txt = " ".join(f"{it.spec} {it.detail}" for it in req.values())
    for v in ("shall be automatic", "usage instructions", "operating instructions shall be posted",
              "Chapter 8", "intelligibility"):
        assert v in txt, v
    # Table 7.1 item 8 applies where ancillary functions (music, paging) are provided.
    anc = [it for it in items(r, "EVC") if "Table 7.1 item 8" in (it.code_ref or "")]
    assert len(anc) == 1 and anc[0].status == "conditional"
    assert "inspected and tested annually" in anc[0].detail
    # Not printed where EVC is not required.
    assert not [it for it in items(report(occupancy="business", business_group="A", height_m=10),
                                   "EVC") if "Table 7.4" in (it.code_ref or "")]


# ------------------------------------------------------------------ R-B (M6)
def test_M6_RB_open_yard_and_tank_farm_get_conditional_warehouse_packages():
    """Owner ruling R-B 28.10.2026: Ch 5 / 6 / 7 warehouse packages stay for Groups T and U,
    as conditional, with the R-B wording; never not required."""
    for flag in ("is_open_yard_storage", "is_aboveground_tank_storage"):
        r = report(occupancy="storage_industrial", height_m=8, gross_floor_area_m2=8000,
                   ground_floor_bua_m2=8000, **{flag: True})
        for code, n in (("ES", 5), ("EL", 6), ("EVC", 7)):
            its = items(r, code)
            assert not [it for it in its if it.status == "required"], (flag, code)
            cond = [it for it in its if it.status == "conditional"]
            assert cond, (flag, code)
            assert all(RB.format(n=n) in (it.detail or "") for it in cond), (flag, code)
        assert status_of(r, "EL", "Monitored Self-Contained EL (Section 3.3)") == ["conditional"]
        assert status_of(r, "EVC", EVC) == ["conditional"]
    plain = report(occupancy="storage_industrial", height_m=8, gross_floor_area_m2=8000,
                   ground_floor_bua_m2=8000)
    assert status_of(plain, "EVC", EVC) == ["required"]


# ------------------------------------------------------------------ Ch 5
def test_M4_theme_park_and_assembly_b_photoluminescent_strips():
    """Table 5.3 item 6.vi p.397 'All amusement parks, indoor rides, theme parks, play areas
    shall be provided with Photoluminescent Exit Marking strips per Table 5.1. 4.';
    Table 1.1 p.48 Assembly Group B '1. Amusement Park', '7. Indoor Kid's Play Areas'."""
    name = ("Photoluminescent Exit Marking Strips (Amusement / Indoor Rides / Theme Parks / "
            "Play Areas)")
    tp = report(occupancy="assembly_b", height_m=10, is_theme_park=True)
    assert status_of(tp, "ES", name) == ["required"]
    tp2 = report(occupancy="mercantile_a", height_m=8, ground_floor_bua_m2=1000, is_theme_park=True)
    assert status_of(tp2, "ES", name) == ["required"]
    asm_b = report(occupancy="assembly_b", height_m=10)
    (c,) = named(asm_b, "ES", name)
    assert c.status == "conditional" and "Table 1.1" in c.detail and "p.48" in c.detail
    assert "Amusement Park" in c.detail and "Indoor Kid's Play Areas" in c.detail
    assert not named(report(occupancy="assembly_a", height_m=10), "ES", name)


def test_M3_storage_photoluminescent_strips_cold_cable_basement():
    """Table 5.3 item 15.ii p.399 'High hazard areas (GROUP A-1 and GROUP A-2), Robotic
    storage and cold storage areas, industrial basements, Cable spread areas, shall be
    provided with Photoluminescent Exit Marking strips as per Table 5.1. 4.'"""
    name = ("Photoluminescent Exit Marking Strips (HH / Robotic / Cold / Cable Spread / "
            "Industrial Basements)")
    base = dict(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000)
    for extra in (dict(is_cold_storage=True), dict(has_cable_spread_areas=True),
                  dict(floors_below_grade=1), dict(basement_bua_m2=500),
                  dict(has_hh_storage_zones=True)):
        r = report(**base, **extra)
        assert status_of(r, "ES", name) == ["required"], extra
    assert not named(report(**base), "ES", name)
    assert not named(report(occupancy="business", business_group="A", height_m=10,
                            has_cable_spread_areas=True, floors_below_grade=1), "ES", name)


def test_L7_photoluminescent_spec_line_conditional_and_ul1994_from_5_1_5():
    """p.387 #2.2.5 '... or Signs shall be Photoluminescent' (one option); Table 5.1 item 4
    p.390; #5.1.5 p.401 'UL 1994, Standard for Luminous Egress Path Marking Systems'."""
    r = report(occupancy="hotel_a", height_m=18, ground_floor_bua_m2=1000)
    (p,) = named(r, "ES", "Photoluminescent Sign Specifications (UL 1994)")
    assert p.status == "conditional"
    assert "#5.1.5" in p.code_ref and "p.401" in p.page_ref and "#2.2.5" in p.detail


def test_L9_table_5_2_item_3_visibility_line():
    """Table 5.2 item 3 VISIBILITY p.395."""
    r = report(occupancy="hotel_a", height_m=18, ground_floor_bua_m2=1000)
    v = [it for it in items(r, "ES") if "Table 5.2 item 3" in (it.code_ref or "")]
    assert len(v) == 1 and v[0].status == "required"
    assert "No decorations, furnishings, or equipment that impairs visibility" in v[0].detail
    assert not [it for it in items(report(occupancy="villa_private", height_m=6), "ES")
                if "Table 5.2 item 3" in (it.code_ref or "")]


# ------------------------------------------------------------------ Ch 6
def test_L5_coverage_line_cites_table_6_1_item_1_for_its_landing_rows():
    """Table 6.1 item 1.ii-iv and 1.viii p.408 (landings, change of direction, outside exit
    stair, toilets / elevators / car parks / escalators); Table 6.6 items 1-27 p.420."""
    r = report(occupancy="hotel_a", height_m=18, ground_floor_bua_m2=1000)
    cov = [it for it in items(r, "EL") if it.source_rule == "el_g_coverage_mandatory"
           and it.system.startswith("Mandatory EL Coverage")]
    assert len(cov) == 1
    c = cov[0]
    assert "Table 6.1 item 1.ii-iv, 1.viii" in c.code_ref and "Table 6.6 items 1-27" in c.code_ref
    assert "p.408" in c.page_ref and "p.420" in c.page_ref
    assert "LARGE PLANT ROOMS" in c.detail.upper()


# ------------------------------------------------------------------ Ch 4
def test_H2_Q2_tank_storage_and_flammable_liquid_warehouse_get_wheeled_foam():
    """Table 4.3 row 3 item 2.i p.376 'Bulk storage of flammable liquids': 'Wheeled Type Foam
    (ONE) 50 Liters (13 Gal) AND Multi-purpose Dry Powder (ONE) 2-A, 20-B, C 4 Kg'; 15 m.
    Group T (H2) and Group R (ruling Q-2)."""
    name = "Class B Wheeled Foam Extinguisher - Bulk Flammable Liquid"
    for flag in ("is_aboveground_tank_storage", "is_flammable_liquid_warehouse",
                 "has_bulk_flammable_liquid_storage"):
        r = report(occupancy="storage_industrial", height_m=8, ground_floor_bua_m2=2000,
                   **{flag: True})
        (w,) = named(r, "FE", name)
        assert w.status == "required" and "row 3 item 2" in w.code_ref, flag
        for v in ("50 L (13 Gal)", "2-A, 20-B, C 4 kg", "15 m"):
            assert v in w.spec, (flag, v)
    assert not named(report(occupancy="storage_industrial", height_m=8,
                            ground_floor_bua_m2=2000), "FE", name)


def test_M5_homes_kitchen_line_conditional_for_hotels():
    """Table 4.3 row 6 item 1 p.377 'KITCHEN, HOMES': Multi-purpose Dry Powder 3A, 20-B, C
    2.5 Kg, inside kitchen next to Kitchen exit door."""
    name = "Class K Fire Extinguisher (Residential Kitchen)"
    for occ in ("hotel_a", "hotel_b", "hotel_c"):
        (k,) = named(report(occupancy=occ, height_m=10), "FE", name)
        assert k.status == "conditional", occ
        assert "guest rooms / apartments have kitchens" in k.spec, occ
        assert "2.5 kg" in k.spec, occ
    for occ in ("residential", "villa_private", "villa_commercial"):
        assert status_of(report(occupancy=occ, height_m=6), "FE", name) == ["required"], occ


def test_L6_ahu_line_cites_mechanical_plant_room_item_5():
    """Table 4.3 row 4 p.376 '4. AHU ROOM', '5. MECHANICAL PLANT ROOM'."""
    r = report(occupancy="business", business_group="A", height_m=10, has_ahu_room=True)
    c = [it for it in items(r, "FE") if it.source_rule == "fe_class_c_ahu"]
    assert len(c) == 1 and "row 4 items 4-5" in c[0].code_ref
    assert "Mechanical Plant Room" in c[0].system


def test_L8_villa_class_a_wording_follows_print():
    """Table 4.3 row 1 p.373 item 5 RESIDENTIAL 'i. Apartments ii. Corridors' (villas not
    listed); 2.5 kg is the row 6 KITCHEN, HOMES size (p.377)."""
    r = report(occupancy="villa_private", height_m=6)
    (a,) = named(r, "FE", "Class A Fire Extinguisher (recommended for villas)")
    assert a.status == "recommended"
    assert "2.5 kg or 4 kg" not in a.spec and "2-A, 20-B, C 4 kg per villa floor" in a.spec
    assert "not listed" in a.detail and "row 6" in a.detail
    assert "without explicit villa carve-out" not in a.detail


def test_L10_truck_gets_no_class_c_room_lines():
    """Table 4.3 row 4 items 1-3 p.376 are rooms (electrical / LV, telephone, lift machine);
    a food truck or mercantile truck has none."""
    for t in ("food_truck", "mercantile_truck"):
        r = report(occupancy="mercantile_c", mercantile_c_type=t, height_m=3)
        bad = [it.system for it in items(r, "FE") if it.status == "required"
               and it.source_rule in ("fe_class_c_main_electrical", "fe_class_c_telephone",
                                      "fe_class_c_lift_machine")]
        assert not bad, (t, bad)
    kiosk = report(occupancy="mercantile_c", mercantile_c_type="kiosk_permanent", height_m=4,
                   kiosk_in_sprinklered_area_or_mall=False)
    assert [it for it in items(kiosk, "FE") if it.source_rule == "fe_class_c_main_electrical"]


def test_L11_converted_villa_class_a_open_question_note():
    """L11 UNSURE: Ch 4 prints no villa conversion clause (Table 4.3 row 1 p.373-374); a note
    states the open question, routing unchanged."""
    r = report(occupancy="villa_private", height_m=6, villa_converted_use=True)
    notes = [it for it in items(r, "FE") if it.source_rule == "fe_g_class_a_villa_converted"]
    assert len(notes) == 1 and notes[0].status == "conditional"
    assert "owner ruling" in notes[0].detail.lower()
    assert status_of(r, "FE", "Class A Fire Extinguisher (recommended for villas)") == ["recommended"]
    assert not [it for it in items(report(occupancy="villa_private", height_m=6), "FE")
                if it.source_rule == "fe_g_class_a_villa_converted"]
