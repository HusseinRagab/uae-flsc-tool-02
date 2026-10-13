"""Phase 5 (13.10.2026): page gaps closed from the rendered 2018 pages.

CH9D-15, owner ruling 13.10.2026 "Pointer lines": Ch 9 Section 5 gets one line per
required system type naming its table. Text read off p.758-769 (Table 9.32 p.759-761,
9.33 p.762-763, 9.34 p.764-765, 9.35 p.766-767, 9.36 p.768-769).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import engine  # noqa: E402
from flsc_schema import Requirement, SectionBlock  # noqa: E402
from test_phase1_findings import items, report  # noqa: E402

ITM = "FP - Testing, Inspection and Maintenance (Ch 9, Section 5)"


def itm(r):
    blk = next((b for b in r.chapter("FP").blocks if b.title == ITM), None)
    return {it.code_ref: it for it in blk.items} if blk else {}


def test_itm_highrise_points_to_pump_standpipe_sprinkler_tables():
    r = report(occupancy="business", business_group="B", height_m=60,
               ground_floor_bua_m2=1500)
    lines = itm(r)
    for ref in ("Ch 9, #5.5.1 / Table 9.32", "Ch 9, #5.6.1 / Table 9.33",
                "Ch 9, #5.7.1 / Table 9.34"):
        assert ref in lines, ref
    assert "NFPA 20 and NFPA 25" in lines["Ch 9, #5.5.1 / Table 9.32"].spec
    assert lines["Ch 9, #5.7.1 / Table 9.34"].page_ref == "p.764-765"
    assert all(it.status == "required" for it in lines.values())


def test_itm_option_line_points_to_each_table():
    blk = SectionBlock(title="x", items=[Requirement(
        system="Records Room - Automatic Sprinkler (3.5) OR Clean Agent (3.14)",
        status="required", code_ref="t", page_ref="t")])
    out = {it.code_ref: it for it in engine._itm_lines([blk])}
    assert set(out) == {"Ch 9, #5.7.1 / Table 9.34", "Ch 9, #5.9.1 / Table 9.36"}
    assert all("(for the option installed)" in it.spec for it in out.values())


def test_itm_ignores_not_required_lines_and_extinguishers():
    blk = SectionBlock(title="x", items=[
        Requirement(system="Above False Ceiling Spaces - Sprinklers Not Required",
                    status="not_required", code_ref="t", page_ref="t"),
        Requirement(system="Trolley Type Foam Extinguishers", status="required",
                    code_ref="t", page_ref="t")])
    assert engine._itm_lines([blk]) == []


# ---------------------------------------------------------------------------
# Phase 5 class A (13.10.2026): page wording and citations, read off the rendered
# pages (GAPS_ch2_ch3 G1 / G13, GAPS_ch5_ch8 G4 + es side fix, GAPS_ch9 items 2-5,
# GAPS_ch10 G1 a-c). No status, verdict or duty moves.

def named(r, code, prefix):
    return [it for it in items(r, code) if it.system.startswith(prefix)]


def test_p5_ch2_g1_accessway_width_detail_cites_2_8_1_2_6_6_2_6_8():
    r = report(occupancy="business", height_m=30, ground_floor_bua_m2=1000)
    (w,) = named(r, "FSA", "Fire vehicle accessway width")
    assert w.code_ref == "Ch 2, Table 2.1 / #2.6.1 / #2.6.3" and w.page_ref == "p.206-207"
    for v in ("#2.8.1 (p.211): minimum width of 6 m throughout", "#2.6.6 (p.208)",
              "#2.6.8 (p.208)", "hydraulic platforms"):
        assert v in w.detail, v


def test_p5_ch3_g13_door_forces_not_to_exceed():
    r = report(occupancy="business", height_m=8, floors_above_grade=2,
               gross_floor_area_m2=2000, ground_floor_bua_m2=1000)
    (door,) = named(r, "MOE", "Door Assembly Minimums")
    assert ("door forces not to exceed (Table 3.2 item 5.ii): 67 N (15 lbf) to release the "
            "latch, 133 N (30 lbf) to set any door leaf in motion, 67 N (15 lbf) to open any "
            "door leaf to the minimum required width") in door.spec


def test_p5_ch5_sign_detail_running_man_and_colours_are_items_1_2_and_1_3():
    r = report(occupancy="business", height_m=10)
    (s,) = named(r, "ES", "Exit Sign Letter Size + Bilingual EXIT")
    assert "Item 1.2: image of running man" in s.detail
    assert "Item 1.3 COLOURS" in s.detail
    assert "Item 2:" not in s.detail and "Item 3 COLOURS" not in s.detail


def test_p5_ch6_g4_central_battery_cable_test_standards_8_1_9():
    r = report(occupancy="residential", height_m=120)
    cb = [it for it in items(r, "EL") if it.status == "required" and it.detail
          and "CENTRAL BATTERY option" in it.detail]
    assert cb
    d = cb[0].detail
    assert ("acceptable test standards #8.1.9 (p.425): EN 50200, UL 2196, BS 8434-2, "
            "BS 7629-1, BS 6387, IEC 60331-1, IEC 60331-2, IEC 60332-2-2, IEC 60332-3-10, "
            "UL 1724, UL 1685, UL 1666") in d
    assert d.count("IEC 60331-2") == 1          # printed twice (vii, x), listed once
    assert "EN 50200 (930" not in d
    assert "Table 6.2 #4.ii" not in d            # G3 (5% central battery) rides a pending card


def test_p5_ch9_item2_table_9_30_rows_r_to_v_printed_text():
    r = report(occupancy="healthcare_a", height_m=20, ground_floor_bua_m2=2000,
               has_operation_theater=True, has_mri_scanning_room=True, has_records_room=True,
               has_ups_room=True, has_cold_freezer_room=True)
    got = {it.code_ref: it for it in items(r, "FP") if "Table 9.30." in (it.code_ref or "")}
    for row in "RSTUV":
        it = got["Ch 9, #4.14 / Table 9.30." + row]
        assert it.detail.startswith("Table 9.30." + row + ": (i)") and it.page_ref == "p.755"
    assert "90 minutes fire doors, housing exclusively dry type battery" in \
        got["Ch 9, #4.14 / Table 9.30.U"].detail
    assert "(iv) rooms which are separated as part of separated service blocks" in \
        got["Ch 9, #4.14 / Table 9.30.V"].detail
    assert "freezing of wet pipe" not in got["Ch 9, #4.14 / Table 9.30.V"].detail


def test_p5_ch9_item3_class_iii_riser_names_hose_rack_option():
    r = report(occupancy="business", has_tunnel=True, tunnel_kind="road_rail",
               tunnel_length_m=1500, height_m=20, ground_floor_bua_m2=1000, plot_area_m2=2000)
    (w,) = named(r, "FP", "Class III Wet Riser System (throughout)")
    assert ("65 mm landing valve AND 25 mm hose reel OR 40 mm hose rack "
            "(Table 9.6 item 1.i, p.582)") in w.spec


def test_p5_ch9_item4_groups_b_c_not_required_lines():
    for hz in ("OH1", "OH2"):
        small = report(occupancy="storage_industrial", height_m=8, plot_area_m2=20000,
                       ground_floor_bua_m2=500, sum_gf_bua_m2=500, max_unit_area_m2=100,
                       hazard_class=hz)
        dlv = [it for it in named(small, "FP", "Dry Landing Valves")
               if it.status == "not_required"]
        assert dlv, hz
        big = report(occupancy="storage_industrial", height_m=8, plot_area_m2=20000,
                     ground_floor_bua_m2=4000, hazard_class=hz)
        wr = [it for it in named(big, "FP", "Wet Risers and Internal Landing Valves")
              if it.status == "not_required"]
        assert wr, hz


def test_p5_ch9_item5_kitchen_hood_listed_and_approved_by_civil_defence():
    r = report(occupancy="hotel_a", height_m=30, ground_floor_bua_m2=1000, plot_area_m2=3000,
               has_commercial_kitchen=True)
    k = [it for it in items(r, "FP") if it.system.startswith("Commercial Kitchen Hood")][0]
    assert k.code_ref == "Ch 9, #4.15 / Table 9.31.A; #3.12 / Table 9.14 items 3.ii, 6"
    assert "shall be listed and approved by Civil Defence" in k.detail


def test_p5_ch10_g1_rail_rows_under_90_not_entered_and_cable_row_3():
    kw = dict(occupancy="business", height_m=10, has_tunnel=True, ground_floor_bua_m2=1000)
    (u,) = named(report(tunnel_length_m=50, **kw), "SC", "Tunnel Smoke Management")
    assert u.status == "required"
    assert "rail: a jet fan or mechanical ventilation system shall not be mandatory" in u.spec
    assert "row 2 (rail tunnel) item 1" in u.code_ref and u.page_ref == "p.862-863"
    assert "check it there" not in u.detail
    assert "efficiency and fulfillment" in u.detail
    (n,) = named(report(**kw), "SC", "Tunnel Smoke Management")
    assert n.status == "conditional" and "road and rail tunnels" in n.detail
    assert "mechanical smoke purging system using dedicated ducting per Section 2.13" in n.detail
    (c,) = named(report(tunnel_kind="cable", tunnel_length_m=50, **kw), "SC",
                 "Tunnel Smoke Management")
    assert c.status == "required" and c.code_ref.endswith("row 3 (service tunnel) item 1")
    assert "utilizing the tunnel openings" in c.spec and "iii. a jet fan system" in c.detail
