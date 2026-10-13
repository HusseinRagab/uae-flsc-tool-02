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
