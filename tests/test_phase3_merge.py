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


def test_lpg_underground_only_stays_conditional():
    assert _spray(has_lpg_tank_underground_mounded=True) == ["conditional"]


def test_lpg_aboveground_only_required():
    assert _spray() == ["required"]


def test_ENG_19_rule_id_names_midlow():
    s = (ROOT / "rules" / "ch10_smoke_control.yaml").read_text(encoding="utf-8")
    assert "sc_lowrise_special_occupancy_stair" not in s
    assert "id: sc_midlow_special_occupancy_stair" in s
