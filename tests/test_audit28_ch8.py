"""Audit 28.10.2026, fix round, area ch8 (Ch 8 Fire Detection and Alarm).

One or more tests per finding of findings/CH08.md (CH8-01 to CH8-19, except CH8-04 which
the lead session fixes in engine._merge_most_restrictive) and owner rulings R-B and R-I.
Values in the asserts were read off the page text of UAE FLSC 2018 (CDGH-OP-25) named in
each test. Run with `python -m pytest tests/test_audit28_ch8.py`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine  # noqa: E402
from flsc_schema import Building  # noqa: E402
from test_phase1_findings import report, items  # noqa: E402

R_B = ("Applies to any enclosed building on the site (warehouse, pump house, office). "
       "Ch 8 prints no row for open yards / aboveground tank farms (owner ruling R-B, "
       "28.10.2026).")


def fa(r, status=None):
    return [it for it in items(r, "FA") if status is None or it.status == status]


def named(r, prefix, status=None):
    return [it for it in fa(r, status) if it.system.startswith(prefix)]


def one(r, prefix, status=None):
    found = named(r, prefix, status)
    assert len(found) == 1, (prefix, [(it.system, it.status) for it in fa(r)])
    return found[0]


def text(it):
    return " ".join(x or "" for x in (it.system, it.spec, it.detail, it.code_ref, it.page_ref))


def warehouse(**kw):
    base = dict(occupancy="storage_industrial", height_m=10, floors_above_grade=1,
                ground_floor_bua_m2=2000, gross_floor_area_m2=2000, plot_area_m2=6000,
                sum_gf_bua_m2=2000, hazard_class="OH2")
    base.update(kw)
    return report(**base)


# ------------------------------------------------------------------ CH8-01
def test_CH8_01_group_t_tank_storage_gets_table_8_15_item_3():
    r = warehouse(is_aboveground_tank_storage=True, hazard_class="HH")
    t = one(r, "Intrinsically Safe Flame + Linear Heat (Flammable Liquid Tanks)", "required")
    assert "Table 8.15 item 3" in t.code_ref and t.page_ref.startswith("p.512")
    assert "Section 4.9" in t.spec and "Section 4.8" in t.spec and "tank roof" in t.spec
    # p.513 items 10-11 print the same two systems; named, not printed twice
    assert "items 10-11" in t.detail.lower() and "Group T" in t.detail
    # the separate tick still works on its own
    r2 = report(occupancy="business", business_group="B", height_m=10, ground_floor_bua_m2=800,
                plot_area_m2=2000, has_flammable_liquid_tanks=True)
    assert named(r2, "Intrinsically Safe Flame + Linear Heat (Flammable Liquid Tanks)", "required")


# ------------------------------------------------------------------ CH8-02 / R-B
def test_CH8_02_open_yard_items_19_20_package_conditional_with_R_B_wording():
    r = warehouse(is_open_yard_storage=True)
    smoke = one(r, "Smoke Detection and Alarm System (entire building)")
    assert smoke.status == "conditional" and R_B in smoke.detail
    for prefix in ("External Audio-Visual Notification Devices", "General Fire Alarm = Evacuation Alarm",
                   "System Interfaces"):
        it = one(r, prefix)
        assert it.status == "conditional" and R_B in it.detail, prefix
    # nothing from the items 19-20 rows is left required for an open yard
    assert not [it for it in fa(r, "required")
                if it.source_rule and it.source_rule.startswith("fa_storage")]
    shed = one(r, "Manual FA System (Open Storage Shed)")
    assert shed.status == "conditional" and "where a shed / structure exists" in shed.system
    assert "Table 8.14 item 37" in shed.code_ref and shed.page_ref == "p.511"


def test_CH8_02_group_t_items_19_20_package_conditional_and_plain_warehouse_unchanged():
    t = warehouse(is_aboveground_tank_storage=True, hazard_class="HH")
    smoke = one(t, "Smoke Detection and Alarm System (entire building)")
    assert smoke.status == "conditional" and R_B in smoke.detail
    assert not named(t, "Manual FA System (Open Storage Shed)")
    w = warehouse()
    assert one(w, "Smoke Detection and Alarm System (entire building)").status == "required"
    assert one(w, "General Fire Alarm = Evacuation Alarm").status == "required"


# ------------------------------------------------------------------ CH8-03
def test_CH8_03_infrastructure_has_no_building_fire_alarm():
    r = engine.evaluate(Building(occupancy="infrastructure", plot_area_m2=20000))
    lines = fa(r)
    assert len(lines) == 1, [(it.system, it.status) for it in lines]
    it = lines[0]
    assert it.status == "conditional"
    assert "Table 8.13" in text(it) and "yard hydrant network" in it.detail
    assert "pump house" in it.detail and "control building" in it.detail
    assert r.chapter("FA").selected_branch == "fa_infrastructure"
    assert not engine.fa_automatic_detection_required(Building(occupancy="infrastructure"))


# ------------------------------------------------------------------ CH8-05 / 06 / 10
def test_CH8_05_06_10_ch8_lines_state_the_printed_ch8_condition():
    r = report(occupancy="business", business_group="B", height_m=10, ground_floor_bua_m2=800,
               plot_area_m2=2000, has_cooling_towers=True, has_commercial_kitchen=True,
               has_laundry_storage_rooms=True, has_pantries=True, has_fire_pump_room=True,
               has_garbage_chute=True)
    ct = one(r, "Linear Heat Detection (Cooling Towers)")
    assert "every cooling tower" in ct.detail and "Table 9.31.G" in ct.detail
    hood = one(r, "Fusible-Link Heat Detection (Kitchen Hood)")
    assert "every kitchen hood" in hood.detail and "Table 9.31.A" in hood.detail
    laundry = one(r, "Smoke Detection (Laundry / Storage Rooms)")
    assert "every laundry and storage room" in laundry.detail
    assert "every pantry" in one(r, "Heat Detection (Pantry)").detail
    assert "every pump room" in one(r, "Heat Detection (Fire Pump Room)").detail
    garbage = one(r, "Heat Detection (Garbage Chute / Garbage Room)")
    assert "every garbage room" in garbage.detail and "Table 8.14 item 25" in garbage.code_ref


# ------------------------------------------------------------------ CH8-07
def _tent(kind, occ="assembly_b"):
    return report(occupancy=occ, height_m=4, floors_above_grade=1, ground_floor_bua_m2=300,
                  plot_area_m2=1000, tent_marquee_kind=kind)


def test_CH8_07_temporary_tent_item_32_required_and_no_addressable_system():
    r = _tent("temporary")
    t = one(r, "Battery Operated Smoke Detectors (Temporary Tent)", "required")
    assert "Table 8.14 item 32" in t.code_ref and t.page_ref == "p.511"
    assert "listed and approved by Civil Defence" in t.spec
    assert not named(r, "Addressable Fire Detection & Alarm Control Panel (FACP)")
    assert not named(r, "Smoke Detection and Alarm System (entire building)")
    assert not named(r, "Smoke Detection in Temporary Kiosks / Tents / Modular Houses-Offices")
    row = one(r, "Table 8.13 Building Fire Detection and Alarm System - not applied", "not_required")
    assert "Table 9.21.f" in row.detail and "p.712" in row.detail and "item 32" in row.detail


def test_CH8_07_site_offices_item_33_required():
    for kind in ("site_office_short", "site_office_long"):
        r = _tent(kind, occ="business")
        m = one(r, "Smoke Detector (Temporary Modular House / Office)", "required")
        assert "Table 8.14 item 33" in m.code_ref and "Section 4.3" in m.spec
        assert not named(r, "Addressable Fire Detection & Alarm Control Panel (FACP)")


def test_CH8_07_permanent_tent_keeps_the_building_system():
    r = _tent("permanent")
    assert one(r, "Smoke Detection and Alarm System (entire building)").status == "required"
    assert named(r, "Addressable Fire Detection & Alarm Control Panel (FACP)")
    assert not named(r, "Battery Operated Smoke Detectors (Temporary Tent)")


# ------------------------------------------------------------------ CH8-08
def test_CH8_08_highrise_warehouse_and_parking_get_the_R7_note():
    w = warehouse(height_m=30, floors_above_grade=6)
    n = one(w, "Highrise 5-Floor Phased Evacuation and PAS 15/180/240 s - not applied", "not_required")
    assert "items 19-20" in n.detail and "General Fire Alarm shall be the evacuation alarm" in n.detail
    p = report(occupancy="parking_enclosed", height_m=30, floors_above_grade=8,
               ground_floor_bua_m2=3000, plot_area_m2=5000)
    n = one(p, "Highrise 5-Floor Phased Evacuation and PAS 15/180/240 s - not applied", "not_required")
    assert "item 22 (vii)-(viii)" in n.detail and "120 s" in n.detail
    low = warehouse()
    assert not named(low, "Highrise 5-Floor Phased Evacuation")


# ------------------------------------------------------------------ CH8-09
def test_CH8_09_villa_stair_top_detector_without_has_stairs():
    r = report(occupancy="villa_private", height_m=7, floors_above_grade=2,
               ground_floor_bua_m2=300, plot_area_m2=800, has_stairs=False)
    s = one(r, "Smoke Detection at Top of Stair Shaft", "required")
    assert "Table 8.14 item 14" in s.code_ref and s.page_ref == "p.510"
    one_storey = report(occupancy="villa_private", height_m=4, floors_above_grade=1,
                        ground_floor_bua_m2=300, plot_area_m2=800, has_stairs=False)
    assert not named(one_storey, "Smoke Detection at Top of Stair Shaft")


# ------------------------------------------------------------------ R-I (Cursor PR #14)
def test_R_I_robotic_parking_item_23_detection_with_item_22_notification():
    for occ in ("parking_enclosed", "parking_open"):
        r = report(occupancy=occ, height_m=12, floors_above_grade=4, ground_floor_bua_m2=3000,
                   plot_area_m2=5000, has_robotic_parking=True)
        assert named(r, "Aspiration Air Sampling (Vehicle Stacking / Storing Areas)", "required")
        assert not [it for it in fa(r, "required") if it.system.startswith(
            ("Conditional FA System", "Manual Fire Detection and Alarm System",
             "Heat Detection and Alarm System"))], occ
        dropped = one(r, "Item 22 Sprinkler-Dependent Detection - not applied", "not_required")
        assert "R-I" in dropped.detail and "item 23" in dropped.detail
        for prefix in ("Audio-Visual Notification", "System Interfaces",
                       "General Fire Alarm Does NOT Trigger Evacuation",
                       "Positive Alarm Sequence (PAS) - 120 s"):
            assert named(r, prefix, "required"), (occ, prefix)
        facp = one(r, "Main FACP at Continuously Attended Location")
        assert "item 23" not in facp.code_ref and "Table 8.1 item 14.1 (vi)" in facp.code_ref
        assert facp.page_ref == "p.458"


# ------------------------------------------------------------------ CH8-11
def test_CH8_11_cold_storage_text_no_longer_pending():
    r = warehouse(is_cold_storage=True)
    for prefix in ("External Audio-Visual Notification Devices", "General Fire Alarm = Evacuation Alarm"):
        it = one(r, prefix)
        assert "pending" not in it.detail and "Ch8 Q2" in it.detail


# ------------------------------------------------------------------ CH8-12
def test_CH8_12_diesel_generator_one_heat_detection_line():
    r = report(occupancy="hotel_a", height_m=18, floors_above_grade=5, ground_floor_bua_m2=1000,
               plot_area_m2=2000, has_diesel_generator_room=True)
    dg = [it for it in fa(r) if "Diesel Generator" in it.system]
    assert len(dg) == 1, [it.system for it in dg]
    assert "Table 8.14 item 8" in dg[0].code_ref and "Table 8.15 item 5" in dg[0].code_ref
    assert dg[0].page_ref == "p.509; p.512"


# ------------------------------------------------------------------ CH8-13
def test_CH8_13_private_villa_facp_or_monitoring_panel():
    r = report(occupancy="villa_private", height_m=7, floors_above_grade=2,
               ground_floor_bua_m2=300, plot_area_m2=800)
    it = one(r, "FACP or Monitoring Panel at Continuously Attended Location")
    assert "item 26 (iii)" in it.detail
    assert not [x for x in fa(r) if "Cluster Radio" in x.system and x.source_rule == "fa_villa_private"]


# ------------------------------------------------------------------ CH8-14
def test_CH8_14_villa_wiring_line_names_the_wireless_alternative():
    v = report(occupancy="villa_private", height_m=7, floors_above_grade=2,
               ground_floor_bua_m2=300, plot_area_m2=800)
    w = one(v, "Fire Alarm Wiring - 2 hour fire rated, Class A, loop isolators")
    assert w.status == "conditional" and "Section 4.11" in w.detail and "wireless" in w.detail.lower()
    b = report(occupancy="business", business_group="B", height_m=10, ground_floor_bua_m2=800,
               plot_area_m2=2000)
    assert one(b, "Fire Alarm Wiring - 2 hour fire rated, Class A, loop isolators").status == "required"


# ------------------------------------------------------------------ CH8-15
def test_CH8_15_contractor_text_cites_6_2_1():
    r = report(occupancy="business", business_group="B", height_m=10, ground_floor_bua_m2=800,
               plot_area_m2=2000)
    it = one(r, "Addressable Fire Detection & Alarm Control Panel (FACP)")
    assert "#6.2.1" in it.code_ref and "p.514" in it.page_ref
    assert "Table 8.1 item 1" in it.code_ref and "p.455" in it.page_ref


# ------------------------------------------------------------------ CH8-16
def test_CH8_16_items_9_13_cited_only_for_their_occupancies():
    a = report(occupancy="animal_housing", animal_housing_group="B", height_m=6,
               ground_floor_bua_m2=500, plot_area_m2=2000)
    ch = a.chapter("FA")
    assert "items 3-4" in ch.selected_branch_section and "9-13" not in ch.selected_branch_section
    pas = one(a, "Positive Alarm Sequence (PAS) - 180 s")
    assert "9-13" not in pas.detail and "9-13" not in (pas.code_ref or "")
    b = report(occupancy="business", business_group="B", height_m=10, ground_floor_bua_m2=800,
               plot_area_m2=2000)
    assert "items 3-4 + 9-13" in b.chapter("FA").selected_branch_section


# ------------------------------------------------------------------ CH8-17
def test_CH8_17_highrise_text_23_m_or_more():
    r = report(occupancy="business", business_group="B", height_m=23, floors_above_grade=7,
               ground_floor_bua_m2=1000, plot_area_m2=3000)
    s = one(r, "Smoke Detection and Alarm System (entire building)")
    assert "more than 23 m" not in s.detail and "23 m or more up to 90 m" in s.detail


# ------------------------------------------------------------------ CH8-18
def test_CH8_18_parking_detection_line_states_which_branch_applies():
    spr = report(occupancy="parking_enclosed", height_m=20, floors_above_grade=5,
                 ground_floor_bua_m2=5000, gross_floor_area_m2=5000, plot_area_m2=10000)
    assert engine.building_sprinklered(spr.building)
    m = one(spr, "Manual Fire Detection and Alarm System", "required")
    assert "item 22 (i)-(ii)" in m.code_ref and "Section 4.10" in m.spec
    assert not named(spr, "Conditional FA System")
    assert not named(spr, "Heat Detection and Alarm System")
    bare = report(occupancy="parking_enclosed", height_m=3, floors_above_grade=1,
                  floors_below_grade=1, ground_floor_bua_m2=500, gross_floor_area_m2=500,
                  plot_area_m2=1000)
    assert not engine.building_sprinklered(bare.building)
    h = one(bare, "Heat Detection and Alarm System", "required")
    assert "item 22 (iii)" in h.code_ref and "Section 4.7" in h.spec
    # open parking: same resolution, by analogy (ruling R10)
    op = report(occupancy="parking_open", height_m=12, floors_above_grade=3,
                ground_floor_bua_m2=3000, plot_area_m2=5000)
    it = [x for x in fa(op, "required") if x.source_rule == "fa_parking_open"
          and "Detection and Alarm System" in x.system]
    assert len(it) == 1 and "analogy" in it[0].system


def test_CH8_18_attached_parking_follows_the_host_sprinklers():
    r = report(occupancy="business", business_group="B", height_m=30, floors_above_grade=8,
               floors_below_grade=1, depth_below_grade_m=4, ground_floor_bua_m2=1500,
               gross_floor_area_m2=12000, plot_area_m2=4000, has_parking_area=True,
               parking_area_m2=300)
    assert engine.building_sprinklered(r.building)
    park = [it for c in r.attached_parking_chapters if c.chapter_code == "FA"
            for blk in c.blocks for it in blk.items]
    assert [it for it in park if it.system.startswith("Manual Fire Detection and Alarm System")]
    assert not [it for it in park if it.system.startswith("Heat Detection and Alarm System")]


# ------------------------------------------------------------------ CH8-19
def test_CH8_19_table_8_1_items_as_general_lines():
    r = report(occupancy="business", business_group="B", height_m=10, ground_floor_bua_m2=800,
               plot_area_m2=2000)
    mcp = one(r, "Manual Call Point to Alarm Signal - not more than 10 s")
    assert "item 4 (ii)" in mcp.code_ref and mcp.page_ref == "p.456"
    st = one(r, "Stairs - Voice Speakers; Sounders Not Required")
    assert "item 6 (iii)-(iv)" in st.code_ref
    hv = one(r, "Detectors Not Less Than 1 m from Supply / Return Diffusers")
    assert "item 9 (i)" in hv.code_ref and hv.page_ref == "p.457"
    facp = one(r, "FACP Spare Capacity 20% and Attended Location")
    assert "20%" in facp.spec and "item 14.1 (v)-(viii)" in facp.code_ref
    assert "unattended room, service rooms" in facp.detail
    act = one(r, "Actuation within 10 s; Trouble Signal within 200 s")
    assert "item 14.3 (i)-(iv)" in act.code_ref and act.page_ref == "p.459"
    zones = one(r, "Notification on Each Floor / Notification Zones")
    assert "item 14.12 (i)" in zones.code_ref and "item 18 (i)" in zones.code_ref
    vis = one(r, "Visible Notification Devices - Flash Rate, Pulse, Intensity, Low-Ceiling Mounting")
    for v in ("1 Hz", "2 Hz", "0.2 s", "40%", "1000 cd", "150 mm"):
        assert v in vis.spec, v
    assert "item 17 (ii)-(v), (ix)" in vis.code_ref and vis.page_ref == "p.463"
