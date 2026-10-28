"""Phase 2 Ch 9 owner answers (decision cards, 12.10.2026): one test per coded answer.

Q1 plot GF BUA sum required, Q2 Groups A-C exactly 900 m2 -> row 2, Q3 Group U
non-LH yard of 1000 m2 or less -> row 3, Q5 Assembly B/C LH + OH1 caption, Q7
robotic parking HH + EH2, Q9 secondary storage hazard required. Q4, Q6 and Q8 need
no code change. Code text in the asserts is read off the pages named in each line.
Run with `python -m pytest tests/test_phase2_ch9_answers.py`.
"""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flsc_schema import Building, default_hazard  # noqa: E402
from test_phase1_findings import report, items, lines, pump  # noqa: E402

APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")


def store(**kw):
    kw.setdefault("occupancy", "storage_industrial")
    kw.setdefault("height_m", 8)
    kw.setdefault("plot_area_m2", 20000)
    # Owner ruling Q-4 (28.10.2026): tenancy is a required choice; these tests model the
    # multi-tenant groups unless they tick single tenant. A specialty-group test (K, P-V)
    # leaves it blank, so only the specialty row prints here (owner ruling R-G evaluates
    # the hazard-class rows beside it: pinned in tests/test_audit28_ch9.py).
    specialty = ("is_aircraft_hanger", "is_cold_storage", "is_flammable_liquid_warehouse",
                 "is_flammable_liquid_industrial", "is_open_yard_storage", "is_plant_nursery",
                 "is_idle_pallet_storage", "is_aboveground_tank_storage")
    if not kw.get("is_single_tenant_storage") and not any(kw.get(f) for f in specialty):
        kw.setdefault("storage_tenancy", "multi")
    return report(**kw)


def branch(r):
    return r.chapter("FP").selected_branch


def fp_line(r, prefix):
    return [it for it in items(r, "FP") if it.system.startswith(prefix)]


def _load_guard():
    tree = ast.parse(APP_SRC)
    keep = [n for n in tree.body
            if (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_SCENARIO_LIMITS"
                                                 for t in n.targets))
            or (isinstance(n, ast.FunctionDef) and n.name == "_invalid_scenario_values")]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "app_guard", "exec"), ns)
    return ns["_invalid_scenario_values"]


def _app_test(state):
    at_mod = pytest.importorskip("streamlit.testing.v1")
    at = at_mod.AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


_GEO = {"height_m_input": 8.0, "ground_bua_input": 1000.0, "gfa_input": 1000.0,
        "plot_area_input": 5000.0}


# ------------------------------------------------------------------ Q1
def test_CH9_Q1_plot_gf_bua_sum_required_blank_never_takes_a_lower_tier():
    # p.724 Group A: row 1 GF < 900 m2 AND unit < 230 m2; row 4 sum of all GF BUAs > 3600 m2.
    blank = store(ground_floor_bua_m2=800, max_unit_area_m2=100, hazard_class="LH")
    assert branch(blank) == "storage_industrial_tier4_lh"
    ne = fp_line(blank, "Sum of GF BUAs on the plot (#4.1.13) - NOT EVALUATED")
    assert ne and ne[0].status == "not_evaluated"
    assert "enter the plot GF BUA sum (#4.1.13)" in ne[0].spec
    assert "owner ruling 12.10.2026, Ch9 Q1" in ne[0].detail
    assert pump(blank).spec.startswith("750 gpm @ 6.9 bar")
    stated = store(ground_floor_bua_m2=800, max_unit_area_m2=100, sum_gf_bua_m2=800,
                   hazard_class="LH")
    assert branch(stated) == "storage_industrial_tier1_lh"
    assert not fp_line(stated, "Sum of GF BUAs")
    # GF above 3600 m2: row 4 whatever the sum, so no line.
    big = store(ground_floor_bua_m2=4000, hazard_class="OH1")
    assert branch(big) == "storage_industrial_tier4_oh" and not fp_line(big, "Sum of GF BUAs")
    # App: the input is required for storage (primary, or secondary in most-restrictive mode).
    at = _app_test({**_GEO, "occupancy_chosen": ("Storage / Industrial", "storage_industrial"),
                    "occupancy_category_select": "Storage / Industrial",
                    "occupancy_sub_select": "storage_industrial", "storage_hazard_input": "OH1"})
    assert any("sum of GF BUAs" in e.value and "Ch9 Q1" in e.value for e in at.error)
    at = _app_test({**_GEO, "occupancy_chosen": ("Storage / Industrial", "storage_industrial"),
                    "occupancy_category_select": "Storage / Industrial",
                    "occupancy_sub_select": "storage_industrial", "storage_hazard_input": "OH1",
                    "sum_gf_bua_m2_input": 1000.0,
                    "storage_tenancy_input": "multi"})   # ruling Q-4 (28.10.2026): required
    assert not at.error


# ------------------------------------------------------------------ Q2
@pytest.mark.parametrize("hz,row", [("LH", "storage_industrial_tier2_lh"),
                                    ("OH1", "storage_industrial_tier2_oh"),
                                    ("OH2", "storage_industrial_tier2_oh2")])
def test_CH9_Q2_groups_A_to_C_exactly_900_m2_take_row_2(hz, row):
    # p.724: row 1 "LESS THAN 900 m2", row 2 "MORE THAN 900 m2"; exactly 900 m2 -> row 2.
    r = store(ground_floor_bua_m2=900, sum_gf_bua_m2=900, hazard_class=hz)
    assert branch(r) == row
    spr = fp_line(r, "Automatic Sprinkler System")
    assert spr and "exactly 900 m2" in spr[0].detail
    assert "owner ruling 12.10.2026, Ch9 Q2" in spr[0].detail
    below = store(ground_floor_bua_m2=899, max_unit_area_m2=100, sum_gf_bua_m2=899, hazard_class=hz)
    assert branch(below) == row.replace("tier2", "tier1")


# ------------------------------------------------------------------ Q3
def test_CH9_Q3_group_U_non_LH_yard_1000_m2_or_less_takes_row_3():
    # p.746 Group U row 3: "MORE THAN 1000 m2 AND STORING MATERIALS OTHER THAN LIGHT HAZARD".
    r = store(ground_floor_bua_m2=800, sum_gf_bua_m2=800, hazard_class="OH1",
              is_open_yard_storage=True)
    assert branch(r) == "storage_open_yard_r3"
    hr = fp_line(r, "Hose Reel System (Open Yard)")
    assert hr and "1000 m2 or less" in hr[0].detail
    assert "owner ruling 12.10.2026, Ch9 Q3" in hr[0].detail
    assert pump(r).spec.startswith("50 gpm @ 4.5 bar")


# ------------------------------------------------------------------ Q5
def test_CH9_Q5_assembly_B_C_stay_LH_with_OH1_caption():
    # p.526-527: #1.1.13.1 a. Assembly, Group C and b. Assembly, Group B are Light Hazard.
    assert default_hazard("assembly_b") == "LH" and default_hazard("assembly_c") == "LH"
    at = _app_test({**_GEO, "occupancy_chosen": ("Assembly", "assembly_b"),
                    "occupancy_category_select": "Assembly", "occupancy_sub_select": "assembly_b"})
    cap = [c.value for c in at.caption if "Ch9 Q5" in c.value]
    assert cap, "Assembly B/C caption missing"
    assert "kitchen" in cap[0] and "stage" in cap[0] and "**OH1**" in cap[0]
    assert "#1.1.13.1" in cap[0] and "#1.1.13.2" in cap[0]
    at = _app_test({**_GEO, "occupancy_chosen": ("Assembly", "assembly_a"),
                    "occupancy_category_select": "Assembly", "occupancy_sub_select": "assembly_a"})
    assert not [c for c in at.caption if "Ch9 Q5" in c.value]


# ------------------------------------------------------------------ Q7
def test_CH9_Q7_robotic_parking_forces_HH_with_extra_hazard_group_2():
    # p.530 #1.1.13.5 Extra Hazard, Group 2: "b. Parking, Group B (Robotic, Mechanical parking)".
    r = report(occupancy="parking_enclosed", height_m=8, ground_floor_bua_m2=1000,
               plot_area_m2=5000, hazard_class="OH1", has_robotic_parking=True,
               has_high_ceiling=True, ceiling_height_m=12)
    assert r.building.hazard_class == "HH" and r.building.is_extra_hazard_2
    assert r.high_ceiling.hazard_class == "HH"
    hz = fp_line(r, "Hazard Classification - Extra Hazard Group 2")
    assert hz and hz[0].status == "required" and "#1.1.13.5.b" in hz[0].spec
    assert "owner ruling 12.10.2026, Ch9 Q7" in hz[0].detail and hz[0].page_ref == "p.530"
    plain = report(occupancy="parking_enclosed", height_m=8, ground_floor_bua_m2=1000,
                   plot_area_m2=5000, hazard_class="OH1")
    assert plain.building.hazard_class == "OH1" and not fp_line(plain, "Hazard Classification")
    # Attached robotic parking: the parking sub-evaluation is HH + EH2, the building keeps LH.
    res = report(occupancy="residential", height_m=8, ground_floor_bua_m2=1000,
                 plot_area_m2=5000, hazard_class="LH", has_robotic_parking=True,
                 # phase 3 (ENG-11): parking is ticked and its area entered, no defaults
                 has_parking_area=True, parking_area_m2=1000)
    assert res.building.hazard_class == "LH"
    sub = [it for c in res.attached_parking_chapters if c.chapter_code == "FP"
           for b in c.blocks for it in b.items]
    assert any(it.system.startswith("Hazard Classification - Extra Hazard Group 2") for it in sub)
    # App: the hazard widget shows HH, disabled, with the caption.
    at = _app_test({**_GEO, "occupancy_chosen": ("Parking", "parking_enclosed"),
                    "occupancy_category_select": "Parking",
                    "occupancy_sub_select": "parking_enclosed", "has_robotic_parking": True})
    w = [s for s in at.selectbox if s.label == "Hazard class"]
    assert w and w[0].value == "HH" and w[0].disabled
    assert any("Extra Hazard Group 2" in c.value and "Ch9 Q7" in c.value for c in at.caption)


# ------------------------------------------------------------------ Q9
def test_CH9_Q9_secondary_storage_hazard_required_never_OH2_by_default():
    kw = dict(occupancy="business", height_m=8, ground_floor_bua_m2=1000, plot_area_m2=5000,
              hazard_class="LH", mixed_occupancy_mode="most_restrictive",
              secondary_occupancies=["storage_industrial"])
    r = report(**kw)
    ne = fp_line(r, "Storage / Industrial (secondary occupancy) - Table 9.27 NOT EVALUATED")
    assert ne and ne[0].status == "not_evaluated" and "owner ruling 12.10.2026, Ch9 Q9" in ne[0].detail
    assert r.building.hazard_class == "LH"                 # not the old silent OH2
    assert "storage_industrial" not in (r.chapter("FP").selected_branch_section or "")
    assert "Ch9 Q9" in r.mixed_occupancy_note
    # Owner ruling Q-4 (28.10.2026): the tenancy is a required choice as well.
    chosen = report(**kw, secondary_storage_hazard="OH2", sum_gf_bua_m2=1000,
                    storage_tenancy="multi")
    assert chosen.building.hazard_class == "OH2" and not fp_line(chosen, "Storage / Industrial (secondary")
    assert "storage_industrial_tier3_oh2" in chosen.chapter("FP").selected_branch_section
    eh2 = report(**kw, secondary_storage_hazard="EH2", sum_gf_bua_m2=1000,
                 storage_tenancy="multi")
    assert eh2.building.hazard_class == "HH" and eh2.building.is_extra_hazard_2
    assert "storage_industrial_eh2_tier1" in eh2.chapter("FP").selected_branch_section
    # Save key and Load check.
    assert '"secondary_storage_hazard_input",' in APP_SRC
    guard = _load_guard()
    assert guard({"secondary_storage_hazard_input": "EH2"}) == []
    assert guard({"secondary_storage_hazard_input": None}) == []
    assert any("Secondary storage hazard class" in m
               for m in guard({"secondary_storage_hazard_input": "XH"}))
    # App: stops until the secondary storage hazard is chosen.
    base = {**_GEO, "occupancy_chosen": ("Business / Office", "business"),
            "occupancy_category_select": "Business / Office", "occupancy_sub_select": "business", "business_group_input": "B",
            "mixed_occupancy_mode_input": "most_restrictive",
            "secondary_occupancies_input": ["storage_industrial"]}
    at = _app_test(base)
    assert any("Ch9 Q9" in e.value for e in at.error)
    at = _app_test({**base, "secondary_storage_hazard_input": "OH2", "sum_gf_bua_m2_input": 1000.0,
                    "storage_tenancy_input": "multi"})  # ruling Q-4: required for listed storage too
    assert not at.error
