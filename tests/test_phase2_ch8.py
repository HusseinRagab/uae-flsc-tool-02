"""Phase 2 audit fixes, package ch8 (Ch 8 Fire Detection and Alarm), audit 12.10.2026.

One test per finding fixed. Code values in the asserts were read off the rendered
pages of UAE FLSC 2018 (CDGH-OP-25) named in rules/ch8_fire_alarm.yaml.
Run with `python -m pytest tests/test_phase2_ch8.py`.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_phase1_findings import report, items  # noqa: E402


def fa(r, status=None):
    out = items(r, "FA")
    return [it for it in out if status is None or it.status == status]


def one(r, name):
    found = [it for it in fa(r) if it.system == name]
    assert len(found) == 1, (name, [it.system for it in fa(r)])
    return found[0]


def text(it):
    return " ".join(x or "" for x in (it.system, it.spec, it.detail, it.code_ref, it.page_ref))


# ------------------------------------------------------------------ CH8-01
def test_CH8_01_mcp_travel_reduced_to_25_and_16_m():
    r = report(occupancy="healthcare_a", height_m=20, ground_floor_bua_m2=2000)
    mcp = one(r, "Manual Call Point (MCP) Spacing & Mounting")
    assert "61 m" in mcp.spec and "25 m and 16 m" in mcp.spec
    assert "limited mobility" in mcp.spec and "rapid fire development" in mcp.spec
    red = one(r, "MCP Travel Distance Reduced to 25 m and 16 m (limited mobility / rapid fire development)")
    assert red.status == "conditional" and "item 4 (vii)-(viii)" in red.code_ref
    # an ordinary business building gets the reduction text but not the extra line
    b = report(occupancy="business", height_m=20, ground_floor_bua_m2=800)
    assert not [it for it in fa(b) if it.system.startswith("MCP Travel Distance Reduced")]


# ------------------------------------------------------------------ CH8-02
def test_CH8_02_super_highrise_pas_15_s_escalates_to_all_floors_above():
    r = report(occupancy="business", height_m=120, ground_floor_bua_m2=1500, plot_area_m2=5000)
    pas = one(r, "Positive Alarm Sequence (PAS)")
    d = pas.detail
    assert "within 15 s, or multiple alarms are triggered from other initiating devices within 180 s" in d
    assert "entire floors above the fire floor and 1 floor below" in d
    assert "240 s" in d and "entire building" in d
    hr = report(occupancy="business", height_m=60, ground_floor_bua_m2=1500, plot_area_m2=5000)
    assert "entire floors above the fire floor" in one(hr, "Positive Alarm Sequence (PAS) - 15/180/240 s").detail


# ------------------------------------------------------------------ CH8-04
def test_CH8_04_interface_and_missing_row_items():
    edu = report(occupancy="education_b", height_m=12, ground_floor_bua_m2=1500)
    i = one(edu, "System Interfaces (pump, suppression, gas, door release, elevator recall, smoke control)")
    assert "Section 4.1" in i.detail and "item 15 (iii)" in i.detail
    for occ, kw in (("healthcare_a", {}), ("mall_covered", {}), ("storage_industrial", {}),
                    ("parking_enclosed", {}), ("motor_fuel_dispensing", {"height_m": 6})):
        args = dict(occupancy=occ, height_m=12, ground_floor_bua_m2=1500)
        args.update(kw)
        r = report(**args)
        assert [it for it in fa(r, "required") if it.system.startswith("System Interfaces")], occ
    det = report(occupancy="detention_a", height_m=12, ground_floor_bua_m2=2000)
    names = [it.system for it in fa(det, "required")]
    assert "General Fire Alarm Does NOT Trigger Evacuation" in names
    assert "System Interfaces (pump, gas, door release, elevator recall, smoke control)" in names
    smoke = one(det, "Smoke Detection throughout (all areas other than prison cells and inmates areas)")
    assert "item 17 (ii)" in smoke.detail
    push = one(det, "Supervisor / Staff Evacuation Push Buttons")
    assert "Civil Defence notification" in push.detail
    mall = report(occupancy="mall_covered", height_m=12, ground_floor_bua_m2=5000)
    assert "Mall management office" in one(mall, "Main FACP at Continuously Attended Location").detail
    st = report(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000,
                is_single_tenant_storage=True)
    assert "item" in one(st, "Main FACP at Continuously Attended Location (single-tenant warehouse)").code_ref
    fuel = report(occupancy="motor_fuel_dispensing", height_m=6, ground_floor_bua_m2=300)
    assert "Mini Mart cash counter" in one(fuel, "Main FACP at Continuously Attended Location").detail


# ------------------------------------------------------------------ CH8-05
def test_CH8_05_pas_includes_multiple_alarms_clause():
    cases = [
        (dict(occupancy="hotel_a", height_m=20), "Positive Alarm Sequence (PAS) - 120 s", "120 s"),
        (dict(occupancy="residential", height_m=20), "Positive Alarm Sequence (PAS) - 180 s", "180 s"),
        (dict(occupancy="parking_enclosed", height_m=12), "Positive Alarm Sequence (PAS) - 120 s", "120 s"),
        (dict(occupancy="mall_covered", height_m=12), "Positive Alarm Sequence (PAS) - 180 s per tenant", "180 s"),
        (dict(occupancy="motor_fuel_dispensing", height_m=6), "Positive Alarm Sequence (PAS) - 180 s", "180 s"),
        (dict(occupancy="parking_open", height_m=12),
         "Positive Alarm Sequence (PAS) - 120 s - by analogy with item 22", "120 s"),
    ]
    for kw, name, secs in cases:
        r = report(ground_floor_bua_m2=1500, **kw)
        d = one(r, name).detail
        assert "multiple alarms are triggered from other initiating devices" in d, kw
        assert secs in d, kw


# ------------------------------------------------------------------ CH8-06
def test_CH8_06_kitchen_items_for_every_building():
    r = report(occupancy="residential", height_m=20, ground_floor_bua_m2=800)
    o = one(r, "Listed Kitchen Detector OR Heat-in-Kitchen + Smoke-in-Living (Open Kitchen)")
    c = one(r, "Listed Kitchen Detector OR Heat Detector (Closed Kitchen)")
    assert o.status == c.status == "conditional"
    assert "3 m away from the kitchen counter" in o.detail and "item 28" in o.code_ref
    assert "item 29" in c.code_ref
    # the commercial kitchen hood (Table 8.15 item 1) stays on its own flag
    assert not [it for it in fa(r) if "Kitchen Hood" in it.system]


# ------------------------------------------------------------------ CH8-07
def test_CH8_07_transformer_rooms_trigger_table_8_15_item_8():
    for flag in ("has_transformer_room_private", "has_transformer_room_utility",
                 "has_oil_filled_transformers"):
        r = report(occupancy="business", height_m=20, ground_floor_bua_m2=800, **{flag: True})
        t = one(r, "Linear Heat Detection (Transformers)")
        assert t.status == "required" and "item 8" in t.code_ref
        assert "on the cable trays" in t.spec.lower()
    r = report(occupancy="business", height_m=20, ground_floor_bua_m2=800)
    assert not [it for it in fa(r) if "Transformers" in it.system]


# ------------------------------------------------------------------ CH8-08
def test_CH8_08_table_8_1_general_values_printed():
    r = report(occupancy="residential", height_m=20, ground_floor_bua_m2=800)
    gen = " ".join(text(it) for it in fa(r) if (it.source_rule or "").startswith("fa_general"))
    for v in ("2 hour fire rated", "Class A", "loop isolators", "24 hours", "30 minutes",
              "20 percent", "75 dBA", "110 dBA", "105 dBA", "2.29 m", "4.57 m", "30.5 m",
              "2 m and not greater than 2.44 m", "12.2 m", "stairwell entrances",
              "all exits to open air"):
        assert v in gen, v
    w = one(r, "Fire Alarm Wiring - 2 hour fire rated, Class A, loop isolators")
    assert w.page_ref == "p.458"
    assert one(r, "FA Secondary Power Supply and Battery Calculations").page_ref == "p.462"


# ------------------------------------------------------------------ CH8-10 (rest)
def test_CH8_10_cold_storage_items_from_19_20_cited_as_such():
    r = report(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000,
               is_cold_storage=True)
    for name, ref in (("External Audio-Visual Notification Devices", "items 19-20 (vi)"),
                      ("General Fire Alarm = Evacuation Alarm", "items 19-20 (vii)")):
        it = one(r, name)
        assert ref in it.code_ref and "item 21" not in it.code_ref
        assert "Not printed in Table 8.13 item 21" in it.detail


# ------------------------------------------------------------------ CH8-14
def test_CH8_14_permitted_options_not_required_status():
    hc = report(occupancy="healthcare_a", height_m=20, ground_floor_bua_m2=2000)
    assert one(hc, "Visual Notification Devices in Critical Care in lieu of audible (permitted)").status == "conditional"
    edu = report(occupancy="education_b", height_m=12, ground_floor_bua_m2=1500)
    cover = one(edu, "Manual Call Points Enclosed with Listed Cover Box (permitted)")
    assert cover.status == "conditional" and "Lockable" not in cover.system
    det = report(occupancy="detention_a", height_m=12, ground_floor_bua_m2=2000)
    assert one(det, "Lockable Manual Call Points (permitted)").status == "conditional"
    mall = report(occupancy="mall_covered", height_m=12, ground_floor_bua_m2=5000)
    assert one(mall, "Visual Display Notification with Messages + Voice Speakers + PA (permitted)").status == "conditional"
    st = report(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000)
    assert one(st, "Single FACP for Multi-Tenant Warehouse (permitted)").status == "conditional"


# ------------------------------------------------------------------ CH8-16
def test_CH8_16_civil_defence_link_cites_ch16_and_gateway_14_3_v():
    r = report(occupancy="residential", height_m=20, ground_floor_bua_m2=800)
    cd = one(r, "FACP Signals to Civil Defence (Smart Monitoring System)")
    assert cd.code_ref == "Ch 16, Table 16.1 item 1" and cd.page_ref == "p.1126"
    assert "'Fire Alarm'" in cd.spec and "'Fault'" in cd.spec
    assert "supervisory + trouble" not in (cd.detail or "")
    gw = one(r, "Listed Barrier Gateway between FACP and Other Systems")
    assert "item 14.3 (v)" in gw.code_ref and gw.page_ref == "p.459"
    # the gateway text is no longer repeated inside the Civil Defence item
    assert "gateway" not in (cd.detail or "").lower()


# ------------------------------------------------------------------ CH8-17
def test_CH8_17_page_and_clause_references():
    r = report(occupancy="business", height_m=12, ground_floor_bua_m2=800,
               has_pantries=True, has_laundry_storage_rooms=True, has_processing_plant=True)
    assert one(r, "Heat Detection (Pantry)").page_ref == "p.510"
    assert one(r, "Smoke Detection (Laundry / Storage Rooms)").page_ref == "p.510"
    assert one(r, "Smoke Detection and Alarm System (entire building)").page_ref == "p.503"
    aud = one(r, "Audible Notification - listed sounders / bells per UL 464 / UL 1480 / FM 3150 / EN 54-3")
    assert "#7.1.14" in aud.code_ref and "p.521" in aud.page_ref and "Table 8.1.a" not in aud.code_ref
    assert "Ch 12" not in text(one(r, "Risk-Assessment-Based FA (Processing / Generating Plants)"))


# ------------------------------------------------------------------ CH8-18
def test_CH8_18_table_8_15_text_as_printed():
    r = report(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000,
               has_bulk_flammable_gas_storage=True, has_cooling_towers=True,
               has_commercial_kitchen=True, has_chemical_warehouse=True)
    gas = one(r, "IS Flame + Gas Detection (Bulk Flammable Gas Storage)")
    assert "Gas Detection (Particular Type)" in gas.spec and "House of Expertise" in gas.spec
    assert "Ch 11" not in text(gas) and "Cross-zoned" not in text(gas)
    ct = one(r, "Linear Heat Detection (Cooling Towers)")
    assert "on the cable trays" in ct.spec.lower() and "basin" not in text(ct)
    hood = one(r, "Fusible-Link Heat Detection (Kitchen Hood)")
    assert "wet-chemical" not in text(hood) and "Pre-engineered Systems shall be acceptable" in hood.detail
    chem = one(r, "Risk-Assessment-Based FA (Chemical Warehouse)")
    assert "typically" not in text(chem) and "comprehensive Risk assessment" in chem.detail


# ------------------------------------------------------------------ CH8-19
def test_CH8_19_converted_private_villa_takes_item_14():
    r = report(occupancy="villa_private", height_m=7, floors_above_grade=2, ground_floor_bua_m2=400,
               villa_converted_use=True)
    assert r.chapter("FA").selected_branch == "fa_villa_converted"
    refs = {it.code_ref for it in fa(r) if it.source_rule and it.source_rule.startswith("fa_villa")}
    assert refs == {"Ch 8, #5.1 / Table 8.13 item 14"}
    plain = report(occupancy="villa_private", height_m=7, floors_above_grade=2, ground_floor_bua_m2=400)
    assert plain.chapter("FA").selected_branch == "fa_villa_private"
    com = report(occupancy="villa_commercial", height_m=7, floors_above_grade=2, ground_floor_bua_m2=400)
    assert all(it.code_ref == "Ch 8, #5.1 / Table 8.13 item 25"
               for it in fa(com) if it.source_rule == "fa_villa_commercial")


# ------------------------------------------------------------------ CH8-20 (item 9 part)
def test_CH8_20_item_9_electrical_room_not_narrowed_to_main():
    r = report(occupancy="business", height_m=12, ground_floor_bua_m2=800, has_main_electrical_room=True)
    e = one(r, "Smoke Detection (Electrical Rooms)")
    assert "every electrical room" in e.detail and "item 9" in e.code_ref


# ------------------------------------------------------------------ CH8-21 (ceiling part)
def test_CH8_21_ceiling_10_and_20_m_code_gap_named():
    kw = dict(occupancy="business", height_m=30, ground_floor_bua_m2=1500, has_high_ceiling=True)
    at20 = report(ceiling_height_m=20.0, **kw)
    a = one(at20, "Aspiration Air Sampling (High-Ceiling Space exactly 20 m - higher row)")
    assert "Code gap at exactly 20 m" in a.detail
    assert not [it for it in fa(at20) if it.system.startswith("Aspiration Air Sampling (High-Ceiling Spaces more")]
    above = report(ceiling_height_m=25.0, **kw)
    a = one(above, "Aspiration Air Sampling (High-Ceiling Spaces more than 20 m)")
    assert "more than 20 m" in a.detail and ">=" not in text(a)
    at10 = report(ceiling_height_m=10.0, **kw)
    b = one(at10, "Beam Smoke Detection (High-Ceiling Space exactly 10 m - higher row)")
    assert "Code gap at exactly 10 m" in b.detail  # status: see test_phase2_ch8_answers Q3
    mid = report(ceiling_height_m=15.0, **kw)
    assert not [it for it in fa(mid) if "exactly" in it.system]


# ------------------------------------------------------------------ CH8-22
def test_CH8_22_reminders_and_proxy_flags():
    n = report(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000,
               is_plant_nursery=True)
    names = [it.system for it in fa(n)]
    assert not [x for x in names if "Bedrooms" in x or "Living Rooms" in x or "Kitchen" in x]
    # roof with the combined LPG/restaurant input only: conditional, not required
    roof = report(occupancy="business", height_m=20, ground_floor_bua_m2=800,
                  has_roof_lpg_or_restaurant=True)
    assert one(roof, "Manual FA System (Roof Restaurant / Sheesha / Assembly)").status == "conditional"
    rest = report(occupancy="business", height_m=20, ground_floor_bua_m2=800,
                  has_roof_restaurant_assembly=True, has_roof_lpg_or_restaurant=True)
    assert one(rest, "Manual FA System (Roof Restaurant / Sheesha / Assembly)").status == "required"
    # a food truck of any fuel takes Table 8.14 item 34
    ft = report(occupancy="business", height_m=20, ground_floor_bua_m2=800, has_food_trucks=True)
    assert one(ft, "Heat Detector (Food Truck)").status == "required"
    lpg = report(occupancy="business", height_m=20, ground_floor_bua_m2=800,
                 has_lpg_cylinders_food_truck=True)
    assert one(lpg, "Heat Detector (Food Truck)").status == "required"


# ------------------------------------------------------------------ open yard vs warehouse row
def test_open_yard_takes_table_8_14_item_37_not_items_19_20():
    """Open-yard storage is Table 8.14 item 37 (manual FA). The engine unions
    matching branches, so items 19-20 (smoke throughout + immediate evacuation)
    must not also fire."""
    yard = report(occupancy="storage_industrial", height_m=8, floors_above_grade=1,
                  ground_floor_bua_m2=2500, hazard_class="LH", is_open_yard_storage=True)
    assert yard.chapter("FA").selected_branch == "fa_open_yard"
    names = [it.system for it in fa(yard)]
    assert "Smoke Detection and Alarm System (entire building)" not in names
    assert "General Fire Alarm = Evacuation Alarm" not in names
    assert "Automatic Smoke Detection NOT REQUIRED (Open Yard / Open Storage Shed)" in names
    shed = one(yard, "Manual FA System (Open Storage Shed)")
    assert shed.status == "required"
    assert "automatic detection not required" in shed.detail.lower()

    warehouse = report(occupancy="storage_industrial", height_m=8, floors_above_grade=1,
                       ground_floor_bua_m2=2500, hazard_class="LH")
    assert warehouse.chapter("FA").selected_branch == "fa_storage_industrial"
    assert one(warehouse, "Smoke Detection and Alarm System (entire building)").status == "required"
    assert not [it for it in fa(warehouse) if it.system.startswith("Manual FA System (Open Storage Shed)")]
