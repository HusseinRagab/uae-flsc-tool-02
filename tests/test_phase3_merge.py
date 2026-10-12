"""Phase 3 merge fixes (coordinator): Ch 9 / Ch 11 LPG roof + underground consistency,
audit ENG-19 rule id rename."""
from pathlib import Path

from test_phase1_findings import items, report

ROOT = Path(__file__).resolve().parent.parent
SPRAY = "LPG Tanks (aboveground, roof or podium) - Fixed Water Spray System"


def _spray(**kw):
    r = report(occupancy="residential", height_m=30, has_lpg_tanks=True, **kw)
    return [it.status for it in items(r, "FP") if it.system == SPRAY]


def test_lpg_roof_and_underground_roof_spray_required():
    # Table 9.31.B i (p.756) and Ch 11 Table 11.7 #5: roof tanks need the spray even
    # when underground / mounded tanks are also ticked (Ch 11 prints it required).
    assert _spray(has_lpg_tank_roof_mounted=True,
                  has_lpg_tank_underground_mounded=True) == ["required"]


def test_lpg_underground_only_not_required():
    # Owner ruling 12.10.2026, P3 Ch11 Q4: with the at-grade input, underground / mounded
    # tanks alone declare no aboveground tank (Table 9.31.B i-ii p.756, Table 11.9 #5).
    assert _spray(has_lpg_tank_underground_mounded=True) == ["not_required"]


def test_lpg_underground_and_at_grade_required():
    assert _spray(has_lpg_tank_underground_mounded=True,
                  has_lpg_tank_at_grade=True) == ["required"]


def test_mixed_multiple_without_list_names_class_a_not_evaluated():
    # P3 Ch47 Q2: mixed_multiple has no Class A line of its own; with no occupancies
    # listed it is named NOT EVALUATED, never silently absent.
    r = report(occupancy="mixed_multiple", height_m=12)
    assert any(it.system == "Class A Fire Extinguisher - NOT EVALUATED" for it in items(r, "FE"))
    r2 = report(occupancy="mixed_multiple", height_m=12, mixed_occupancy_mode="most_restrictive",
                secondary_occupancies=["residential"])
    fe = [it.system for it in items(r2, "FE")]
    assert "Class A Fire Extinguisher - NOT EVALUATED" not in fe
    assert any(x.startswith("Class A") for x in fe)


def test_lpg_aboveground_only_required():
    assert _spray() == ["required"]


def test_ENG_19_rule_id_names_midlow():
    s = (ROOT / "rules" / "ch10_smoke_control.yaml").read_text(encoding="utf-8")
    assert "sc_lowrise_special_occupancy_stair" not in s
    assert "id: sc_midlow_special_occupancy_stair" in s
