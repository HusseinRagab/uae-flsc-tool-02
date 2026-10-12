"""Phase 2 Ch 8 owner answers (decision cards, 12.10.2026).

Q1 (MCP 25/16 m both as printed), Q2 (cold storage keeps items 19-20 lines) and
Q5 ("on the cable trays" as printed) confirmed the phase 2 coding; their tests are
in test_phase2_ch8.py. Q3, Q4 and Q6 change the coding and are pinned here.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_phase2_ch8 import fa, one  # noqa: E402
from test_phase1_findings import report  # noqa: E402


def test_CH8_Q3_edge_ceilings_take_the_higher_row_required():
    kw = dict(occupancy="business", height_m=30, ground_floor_bua_m2=1500, has_high_ceiling=True)
    at10 = one(report(ceiling_height_m=10.0, **kw),
               "Beam Smoke Detection (High-Ceiling Space exactly 10 m - higher row)")
    at20 = one(report(ceiling_height_m=20.0, **kw),
               "Aspiration Air Sampling (High-Ceiling Space exactly 20 m - higher row)")
    for it, item in ((at10, "Item 18"), (at20, "Item 19")):
        assert it.status == "required"
        assert item in it.detail and "Ch8 Q3" in it.detail


def test_CH8_Q4_plant_nursery_prints_no_table_8_14_or_8_15_lines():
    kw = dict(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000,
              has_stairs=True, has_elevator=True, has_main_electrical_room=True,
              has_fire_pump_room=True, has_boilers=True)
    def titles(r):
        ch = r.chapter("FA")
        return [blk.title for blk in ch.blocks]
    n = report(is_plant_nursery=True, **kw)
    assert not [t for t in titles(n) if "Table 8.14" in t or "Table 8.15" in t], titles(n)
    row = one(n, "Fire Detection and Alarm System NOT REQUIRED (Plant / Vegetation Nursery)")
    assert "Ch8 Q4" in row.detail
    # negative control: the same building as an ordinary store keeps its room lines
    s = report(is_plant_nursery=False, **kw)
    assert [t for t in titles(s) if "Table 8.14" in t] and [t for t in titles(s) if "Table 8.15" in t]


def test_CH8_Q6_parking_general_alarm_does_not_evacuate():
    enc = report(occupancy="parking_enclosed", height_m=10, ground_floor_bua_m2=2000)
    e = one(enc, "General Fire Alarm Does NOT Trigger Evacuation")
    assert e.status == "required" and "item 22 (vii)" in e.detail and "Ch8 Q6" in e.detail
    opn = report(occupancy="parking_open", height_m=10, ground_floor_bua_m2=2000)
    o = one(opn, "General Fire Alarm Does NOT Trigger Evacuation - by analogy with item 22")
    assert "by analogy" in o.detail and "Ch8 Q6" in o.detail
