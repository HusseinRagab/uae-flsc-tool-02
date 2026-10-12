"""Phase 2 follow-up owner answers (decision cards, 12.10.2026 14:58Z).

F1 plant nursery prints no Table 8.1 lines; F7 Tables 3.15.a / 3.15.b print one S or
NS column; F8 attached parking takes the parent building's sprinkler status.
F2-F6 confirmed the coding already in place (F6 per-storey uses is phase 3).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import engine  # noqa: E402
from flsc_schema import Building  # noqa: E402
from test_phase1_findings import report, items  # noqa: E402

MOE = engine.load_rules("ch3_means_of_egress.yaml")


def moe_line(ch, name):
    found = [it for blk in ch.blocks for it in blk.items if it.system == name]
    assert len(found) == 1, (name, [it.system for blk in ch.blocks for it in blk.items])
    return found[0]


def test_F1_plant_nursery_prints_only_the_item_28_line():
    n = report(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000,
               is_plant_nursery=True, has_stairs=True, has_main_electrical_room=True)
    names = [it.system for it in items(n, "FA")]
    assert names == ["Fire Detection and Alarm System NOT REQUIRED (Plant / Vegetation Nursery)"], names
    assert "F1" in items(n, "FA")[0].detail
    # negative control: an ordinary store keeps the Table 8.1 system lines
    s = report(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000)
    assert any("Wiring" in it.system for it in items(s, "FA"))


def test_F7_table_3_15_a_prints_one_column():
    b = Building(occupancy="business", height_m=12, floors_above_grade=3,
                 gross_floor_area_m2=3000, ground_floor_bua_m2=1000)
    name = "Exit Remoteness - Lowrise / Midrise (Table 3.15.a items i-iv)"
    s = moe_line(engine.evaluate_moe(b, MOE, sprinklered=True), name)
    ns = moe_line(engine.evaluate_moe(b, MOE, sprinklered=False), name)
    assert s.spec.startswith("Column S (sprinklered): 1/3 of floor diagonal") and "1/2" not in s.spec
    assert ns.spec.startswith("Column NS (non-sprinklered): 1/2 of floor diagonal") and "1/3" not in ns.spec
    assert "F7" in s.detail
    hb = Building(occupancy="business", height_m=40, floors_above_grade=11,
                  gross_floor_area_m2=11000, ground_floor_bua_m2=1000)
    h = moe_line(engine.evaluate_moe(hb, MOE, sprinklered=True),
                 "Exit Remoteness - Highrise / Super-highrise (Table 3.15.a items v-vi)")
    assert h.spec.startswith("Column S (sprinklered): 1/3 of floor diagonal")


def test_F7_table_3_15_b_prints_one_column():
    b = Building(occupancy="parking_enclosed", height_m=6, floors_above_grade=2,
                 floors_below_grade=2, gross_floor_area_m2=6000, ground_floor_bua_m2=2000)
    name = "Basement / Parking Podium Travel Distance (Table 3.15.b)"
    s = moe_line(engine.evaluate_moe(b, MOE, sprinklered=True), name)
    ns = moe_line(engine.evaluate_moe(b, MOE, sprinklered=False), name)
    assert "61 m" in s.spec and "122 m" in s.spec and "46 m" not in s.spec
    assert "46 m" in ns.spec and "91 m" in ns.spec and "61 m" not in ns.spec


def test_F8_attached_parking_uses_parent_sprinkler_status(monkeypatch):
    b = Building(occupancy="business", height_m=40, floors_above_grade=11,
                 floors_below_grade=2, gross_floor_area_m2=11000, ground_floor_bua_m2=1000,
                 has_parking_area=True, parking_area_m2=2000)
    seen = []
    real = engine.evaluate_moe

    def spy(bb, rules, sprinklered=None):
        seen.append((bb.occupancy, sprinklered))
        return real(bb, rules, sprinklered=sprinklered)
    monkeypatch.setattr(engine, "evaluate_moe", spy)
    engine.evaluate_attached_parking(b)
    assert seen == [("parking_enclosed", engine.building_sprinklered(b))]
