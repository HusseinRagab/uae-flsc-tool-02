"""Phase 5 Ch 9 (13.10.2026): owner cards 13.10.2026 05:45Z, all option A.

1. "Split as printed": Table 9.27 Group I (single tenant EH1, p.732) is two rows like
   Group J: row 1 total GF BUA less than 3600 m2, row 2 sum of all GF BUAs more than
   3600 m2. A blank plot sum takes row 2 with the 'not evaluated' line (Ch9 Q1).
2. "Higher row": exactly 3600 m2 takes row 2 in Groups D (p.727), E (p.728), I (p.732)
   and J (p.733); the pages print 'less than 3600' and 'more than 3600'.
3. "Keep hydrants": Group V plant nursery (p.746) keeps the #4.1.6 yard hydrant lines
   (p.694); the 'no fixed water-based system' wording is gone.
Values read off the rendered pages named above.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_phase1_findings import items, lines, pump, report, tank  # noqa: E402

NE = "Sum of GF BUAs on the plot (#4.1.13) - NOT EVALUATED"


def store(**kw):
    kw.setdefault("occupancy", "storage_industrial")
    kw.setdefault("height_m", 8)
    kw.setdefault("plot_area_m2", 20000)
    return report(**kw)


def branch(r):
    return r.chapter("FP").selected_branch


def any_line(r, prefix):
    return [it for it in items(r, "FP") if it.system.startswith(prefix)]


def group_i(gf, total=None):
    kw = dict(ground_floor_bua_m2=gf, hazard_class="HH", is_single_tenant_storage=True)
    if total is not None:
        kw["sum_gf_bua_m2"] = total
    return store(**kw)


# ------------------------------------------------------------ 1. Group I split
def test_group_I_row_1_below_3600():
    r = group_i(2000, 2000)
    assert branch(r) == "storage_single_tenant_eh1_tier1"
    assert pump(r).spec == "750 gpm @ 4.5 bar at most remote hose-reel outlet valve"
    assert tank(r).spec == "60 minutes duration"
    assert "breeching" not in tank(r).spec + (tank(r).detail or "")
    assert "low water level detection and instantaneous refilling" in tank(r).detail.lower()
    spr = lines(r, "FP", "Automatic Sprinkler System (Extra Hazard Group 1)")
    assert spr and "0.30 gpm / 232 m2 (2500 ft2)" in spr[0].spec
    foam = any_line(r, "Foam Sprinklers")
    assert foam and foam[0].status == "conditional" and "Section 3.9" in foam[0].spec
    assert lines(r, "FP", "Hose Reel System")
    dlv = any_line(r, "Dry Landing Valves")
    assert dlv and dlv[0].status == "not_required"
    assert not any_line(r, "Yard Fire Hydrants (loop")
    assert not any_line(r, NE)


def test_group_I_row_2_above_3600():
    r = group_i(5000, 5000)
    assert branch(r) == "storage_single_tenant_eh1_tier2"
    assert pump(r).spec == "1250 gpm @ 6.9 bar at most remote landing valve"
    assert tank(r).spec == "90 minutes with dedicated direct breeching inlet"
    assert "low water level detection" in tank(r).detail.lower()
    assert lines(r, "FP", "Yard Fire Hydrants (loop covering entire facility)")
    risers = any_line(r, "Dry Riser and Wet Riser System")
    assert risers and risers[0].status == "not_required"
    foam = any_line(r, "Foam Sprinklers")
    assert foam and foam[0].status == "conditional"
    assert lines(r, "FP", "Hose Reel System")
    assert not any_line(r, NE)


@pytest.mark.parametrize("total,row", [(3599, "storage_single_tenant_eh1_tier1"),
                                       (3600, "storage_single_tenant_eh1_tier2"),
                                       (3601, "storage_single_tenant_eh1_tier2")])
def test_group_I_3600_edge(total, row):
    r = group_i(total, total)
    assert branch(r) == row
    if row.endswith("tier1"):
        assert pump(r).spec.startswith("750 gpm @ 4.5 bar")
    else:
        assert pump(r).spec.startswith("1250 gpm @ 6.9 bar")
        assert tank(r).spec.startswith("90 minutes")
    if total == 3600:
        spr = lines(r, "FP", "Automatic Sprinkler System (Extra Hazard Group 1)")[0]
        assert "Exactly 3600 m2" in spr.detail and "owner ruling 13.10.2026" in spr.detail


def test_group_I_blank_sum_takes_row_2_and_is_named_not_evaluated():
    r = group_i(2000)            # plot GF BUA sum not entered
    assert branch(r) == "storage_single_tenant_eh1_tier2"
    ne = any_line(r, NE)
    assert ne and ne[0].status == "required"
    assert pump(r).spec.startswith("1250 gpm @ 6.9 bar")
    assert lines(r, "FP", "Yard Fire Hydrants (loop covering entire facility)")
    # Same handling as Group J (owner ruling 12.10.2026, Ch9 Q1).
    j = store(ground_floor_bua_m2=2000, hazard_class="HH", is_extra_hazard_2=True,
              is_single_tenant_storage=True)
    assert branch(j) == "storage_single_tenant_eh2_tier2" and any_line(j, NE)


def test_group_I_old_combined_rule_is_gone():
    for r in (group_i(2000, 2000), group_i(5000, 5000)):
        text = " ".join((it.spec or "") for it in items(r, "FP"))
        assert "->" not in text and "(<=3600 m2)" not in text
        assert not any_line(r, "Fire Pump (Single-Tenant Extra Hazard)")


# ------------------------------------------------------------ 2. 3600 m2 edge D, E, J
@pytest.mark.parametrize("single,eh2,row1,row2", [
    (False, False, "storage_industrial_eh1_tier1", "storage_industrial_eh1_tier2"),       # D
    (False, True, "storage_industrial_eh2_tier1", "storage_industrial_eh2_tier2"),        # E
    (True, True, "storage_single_tenant_eh2_tier1", "storage_single_tenant_eh2_tier2"),   # J
])
def test_groups_D_E_J_exactly_3600_take_row_2(single, eh2, row1, row2):
    kw = dict(hazard_class="HH", is_extra_hazard_2=eh2, is_single_tenant_storage=single)
    below = store(ground_floor_bua_m2=3599, sum_gf_bua_m2=3599, **kw)
    assert branch(below) == row1
    at = store(ground_floor_bua_m2=3600, sum_gf_bua_m2=3600, **kw)
    assert branch(at) == row2
    assert lines(at, "FP", "Yard Fire Hydrants (loop covering entire facility)")
    spr = [it for it in lines(at, "FP", "Automatic Sprinkler System")
           if "Exactly 3600 m2" in (it.detail or "")]
    assert spr and "owner ruling 13.10.2026" in spr[0].detail
    # A smaller building on a plot whose sum is exactly 3600 m2 also takes row 2.
    plot = store(ground_floor_bua_m2=2000, sum_gf_bua_m2=3600, **kw)
    assert branch(plot) == row2 and not any_line(plot, NE)
    # Blank sum: still row 2 with the 'not evaluated' line (Ch9 Q1).
    blank = store(ground_floor_bua_m2=2000, **kw)
    assert branch(blank) == row2 and any_line(blank, NE)


# ------------------------------------------------------------ 3. Group V nursery
def _nursery(gf, **kw):
    return store(ground_floor_bua_m2=gf, hazard_class="LH", is_plant_nursery=True,
                 sum_gf_bua_m2=gf, **kw)


def test_nursery_above_3600_keeps_hydrant_line_without_contradiction():
    r = _nursery(4000)
    assert branch(r) == "storage_plant_nursery"
    hyd = lines(r, "FP", "Yard Fire Hydrant System")
    assert hyd and hyd[0].code_ref == "Ch 9, #4.1.6"
    ext = lines(r, "FP", "Portable Fire Extinguishers")
    assert ext and "Table 9.27 Group V" in ext[0].detail
    assert "owner ruling 13.10.2026" in ext[0].detail
    text = " ".join((it.detail or "") + " " + (it.spec or "") for it in items(r, "FP")).lower()
    assert "no fixed water-based" not in text
    assert "garden centres" not in text


def test_nursery_below_3600_has_no_hydrant_line():
    r = _nursery(2000, gross_floor_area_m2=2000)
    assert branch(r) == "storage_plant_nursery"
    assert not any_line(r, "Yard Fire Hydrant System")
    ext = lines(r, "FP", "Portable Fire Extinguishers")
    assert ext and "no fixed water-based" not in ext[0].detail
