"""Phase 3 package "storey" (owner answers 12.10.2026): F6 and Ch9 Q6.

F6: optional per-storey per-use table. Each storey's occupant load is the sum of its
uses, each rounded up (#4.1.2, p.283; #1.4.5, p.242); Table 3.14 (p.288) runs per
storey (#4.3.1, #4.1.3) and the governing storey is named. Factors: Table 3.13,
p.285-287. A blank table leaves every earlier result unchanged.

Ch9 Q6: Animal Housing Groups A and C are Light Hazard (#1.1.13.1.q, r, p.528), Group B
is Ordinary Hazard Group 2 (#1.1.13.3.a, p.529). Ch 9 Tables 9.20.b row E, 9.20.c row C
and 9.21.b row D (p.701-703, 707) name "Animal Housing Group A, B, C" together, Table
3.13 row 21 (p.287) gives 11.1 m2 for all three, and Table 8.13 (p.502-508) has no
animal housing row: the group changes the hazard class only.
"""
import ast
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import engine  # noqa: E402
from flsc_schema import ANIMAL_HOUSING_GROUPS, Building, default_hazard  # noqa: E402
from test_phase1_findings import items, report  # noqa: E402

APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")


def _app_defs(*names):
    """Top-level assignments / functions of app.py by name, run on their own."""
    tree = ast.parse(APP_SRC)
    keep = [n for n in tree.body
            if (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in names
                                                 for t in n.targets))
            or (isinstance(n, ast.FunctionDef) and n.name in names)]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "app_defs", "exec"), ns)
    return ns


def _app_test(state):
    at_mod = pytest.importorskip("streamlit.testing.v1")
    at = at_mod.AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


BIZ = dict(occupancy="business", height_m=12, floors_above_grade=3,
           gross_floor_area_m2=9000, ground_floor_bua_m2=3000)
TABLE = [{"storey": "GF", "row": "2.i", "area_m2": 3000},      # 322.6 -> 323
         {"storey": "L1", "row": None, "area_m2": 2000},       # densest 2.iii 3.7: 540.5 -> 541
         {"storey": "L1", "row": "13.ii", "area_m2": 1000},    # 2.8: 357.1 -> 358
         {"storey": "L2", "row": "2.i", "area_m2": 3000}]      # 323


# ------------------------------------------------------------------ F6
def test_F6_blank_table_leaves_existing_results_unchanged():
    """Ch3 Q1 / Q2 results (tests/test_phase2_ch3_answers.py) stay as they were."""
    kw = dict(occupancy="residential", height_m=95, floors_above_grade=30,
              gross_floor_area_m2=45000, ground_floor_bua_m2=1500)
    ol = report(**kw).occupant_load
    assert (ol.occupant_load, ol.storey_occupant_load, ol.min_exits) == (2420, 2420, 4)
    assert ol.governing_storey == "" and ol.storeys == [] and ol.warnings == []
    ol = report(largest_storey_area_m2=1500, storey_uses=[], **kw).occupant_load
    assert (ol.occupant_load, ol.storey_occupant_load, ol.min_exits) == (2420, 81, 2)
    ol = report(occupancy="business", height_m=4, floors_above_grade=1,
                gross_floor_area_m2=1100, ground_floor_bua_m2=1100,
                use_areas=[{"row": "2.i", "area_m2": 1000}, {"row": "13.ii", "area_m2": 100}]
                ).occupant_load
    assert ol.occupant_load == 144 and ol.min_exits == 2 and not ol.governing_storey


def test_F6_per_storey_ol_and_table_3_14_name_the_governing_storey():
    """#4.1.2: each use rounded up; #4.3.1 / #4.1.3: Table 3.14 per storey (p.288:
    OL 500 - 1,000 -> not less than 3 exits; less than 500 -> minimum 2)."""
    ol = report(storey_uses=TABLE, **BIZ).occupant_load
    by = {s.storey: s for s in ol.storeys}
    assert [s.storey for s in ol.storeys] == ["GF", "L1", "L2"]
    assert (by["GF"].occupant_load, by["GF"].min_exits) == (323, 2)
    assert (by["L1"].occupant_load, by["L1"].min_exits) == (541 + 358, 3)
    assert (by["L2"].occupant_load, by["L2"].min_exits) == (323, 2)
    assert ol.evaluated and ol.governing_storey == "L1" and ol.min_exits == 3
    assert ol.storey_occupant_load == 899 and ol.storey_area_m2 == 3000
    assert ol.occupant_load == 323 + 899 + 323 and ol.area_m2 == 9000
    assert "governing storey 'L1': OL 899" in ol.exit_ref and "F6" in ol.exit_ref
    assert "Table 3.14 row iii" in ol.exit_ref
    assert "row 13.ii: 1,000 m2 / 2.8 m2 = 358" in ol.note
    assert "Table 3.13 row 2.iii" in ol.note          # the densest row used for a blank row
    assert ol.warnings == []
    # The whole-building path on the same uses would run Table 3.14 on the whole GFA
    # (OL 1,545 -> 4 exits): per storey it is 3 (LESS onerous, as #4.3.1 prints).
    whole = report(use_areas=[{"row": "2.i", "area_m2": 6000}, {"row": "2.iii", "area_m2": 2000},
                              {"row": "13.ii", "area_m2": 1000}], **BIZ).occupant_load
    assert whole.min_exits == 4
    # The same use twice on one storey is one area (#1.4.5 'the floor area assigned to
    # that use'): 50 + 50 m2 / 9.3 -> 11, not 6 + 6. (Re-pointed for P3 Storey Q1: the
    # storey stands for the 3 storeys of the building, so the counts cover them.)
    ol = report(storey_uses=[{"storey": "GF", "row": "2.i", "area_m2": 50, "count": 3},
                             {"storey": "GF", "row": "2.i", "area_m2": 50, "count": 3}],
                **BIZ).occupant_load
    assert ol.storeys[0].occupant_load == math.ceil(100 / 9.3) == 11
    assert ol.occupant_load == 3 * 11
    # A tie names the first storey listed.
    ol = report(storey_uses=[{"storey": "L3", "row": "2.i", "area_m2": 930},
                             {"storey": "L4", "row": "2.i", "area_m2": 930, "count": 2}],
                **BIZ).occupant_load
    assert ol.governing_storey == "L3"


def test_F6_table_lines_it_cannot_value_are_refused_by_name():
    bad = [{"storey": "", "row": "2.i", "area_m2": 100},
           {"storey": "L1", "row": "99.x", "area_m2": 100},
           {"storey": "L2", "row": "2.i", "area_m2": 0}]
    ol = report(storey_uses=bad, **BIZ).occupant_load
    assert not ol.evaluated and ol.min_exits == 0 and ol.occupant_load == 0
    for frag in ("line 1: no storey name", "line 2 (L1): '99.x'", "storey 'L2': no area entered"):
        assert frag in ol.note, frag
    assert "no exit count stated" in ol.exit_ref
    # Occupancies with no Table 3.13 row: a line with no row is refused (Ch3 Q2), and the
    # MOE is evaluated once every line names its use.
    kw = dict(occupancy="mixed_multiple", height_m=10, floors_above_grade=2,
              gross_floor_area_m2=4000, ground_floor_bua_m2=2000)
    ol = report(storey_uses=[{"storey": "GF", "row": None, "area_m2": 2000}], **kw).occupant_load
    assert not ol.evaluated and "no Table 3.13 row chosen" in ol.note
    r = report(storey_uses=[{"storey": "GF", "row": "13.ii", "area_m2": 2000},
                            {"storey": "L1", "row": "6.i", "area_m2": 2000}], **kw)
    ol = r.occupant_load
    assert ol.evaluated and ol.governing_storey == "GF" and ol.min_exits == 3   # 715
    names = [it.system for it in items(r, "MOE")]
    assert "Occupant Load by Actual Use (Table 3.13, #1.4.5)" in names
    assert not [n for n in names if n.startswith("Means of Egress Not Evaluated")]


def test_F6_table_input_checks_warn_by_name():
    """Storey areas above the GFA, fewer or more storeys than the building, and the
    inputs the table replaces are named; the evaluation still runs."""
    ol = report(storey_uses=TABLE + [{"storey": "L2", "row": "2.i", "area_m2": 500}],
                **BIZ).occupant_load
    assert ol.evaluated
    assert any("add up to 9,500 m2, more than the GFA of 9,000 m2" in w for w in ol.warnings)
    # Re-pointed for P3 Storey Q1 (owner ruling 12.10.2026): fewer or more storeys than
    # the building is no longer a warning but NOT EVALUATED (tests/test_phase3_answers_a3.py);
    # here the one storey stands for all 3 (identical storeys count 3).
    ol = report(storey_uses=[dict(TABLE[0], count=3)], largest_storey_area_m2=2000,
                use_areas=[{"row": "2.i", "area_m2": 9000}], **BIZ).occupant_load
    w = " ".join(ol.warnings)
    assert ol.evaluated
    assert "whole-building per-use areas are not used" in w
    assert "largest storey area input (2,000 m2) is not used" in w
    assert "a storey of 3,000 m2, larger than it" in w
    assert "Check:" in ol.note
    ol = report(storey_uses=[dict(ln, storey=f"S{i}") for i, ln in enumerate(TABLE)],
                **BIZ).occupant_load
    assert not ol.evaluated and "1 storey(s) more than the building has" in ol.exit_ref


def test_F6_app_saves_and_validates_the_table():
    """BRIEF rule 5: save key, load validation (no negative or non-numeric area)."""
    check = _app_defs("_SCENARIO_LIMITS", "_invalid_scenario_values")["_invalid_scenario_values"]
    bad = " ".join(check({"storey_table_input": [
        {"storey": "GF", "row": "2.i", "area_m2": -5},
        {"storey": "L1", "row": "2.i", "area_m2": "big"},
        {"storey": "L2", "row": "99.x", "area_m2": 10},
        {"storey": 3, "row": None, "area_m2": 10},
        {"storey": "L3", "row": None, "area_m2": True},
        ["L4", "2.i", 10],
        {"storey": "L5", "use": "2.i"}]}))
    for frag in ("line 1 area = -5 (minimum 0)", "line 2 area = 'big' (not a number)",
                 "line 3 Table 3.13 row = '99.x'", "line 4 storey = 3 (not text)",
                 "line 5 area = True (not a number)", "line 6 = ['L4', '2.i', 10]",
                 "line 7 = {'storey': 'L5', 'use': '2.i'}"):
        assert frag in bad, frag
    assert "not a list" in " ".join(check({"storey_table_input": "GF 100"}))
    assert "maximum 200" in " ".join(check({"storey_table_input": [{}] * 201}))
    assert check({"storey_table_input": TABLE + [{"storey": "", "row": None, "area_m2": None}]}) == []
    assert '"storey_table_input"' in APP_SRC and '"animal_housing_group_input"' in APP_SRC
    # Load replaces: a file saved before phase 3 clears the table and the group.
    assert 'list(_data.get("storey_table_input") or [])' in APP_SRC
    assert 'st.session_state.pop("storey_table_editor", None)' in APP_SRC
    # Editor frame -> saved lines: blank lines dropped, NaN area -> None, ids kept.
    ns = _app_defs("_STOREY_COLS", "_storey_table_frame", "_storey_table_records")
    df = ns["_storey_table_frame"](TABLE + [{"storey": None, "row": None, "area_m2": None},
                                            {"storey": " L9 ", "row": "2.i", "area_m2": None}])
    out = ns["_storey_table_records"](df)
    # (Re-pointed for P3 Storey Q1: every saved line carries its identical-storeys count.)
    assert out[:4] == [dict(ln, area_m2=float(ln["area_m2"]), count=1) for ln in TABLE]
    assert out[4:] == [{"storey": "L9", "row": "2.i", "area_m2": None, "count": 1}]


def test_F6_app_table_drives_the_occupant_load_card():
    at = _app_test({"occupancy_chosen": ("Business / Office", "business"),
                    "occupancy_category_select": "Business / Office",
                    "occupancy_sub_select": "business", "business_group_input": "B",
                    "height_m_input": 12.0,
                    "floors_above_input": 3, "floors_below_input": 0,
                    "gfa_input": 9000.0, "ground_bua_input": 3000.0,
                    "plot_area_input": 9000.0, "storey_table_base": TABLE})
    caps = [c.value for c in at.caption]
    assert any("Table 3.14 on the governing storey 'L1' OL 899" in c for c in caps)
    assert at.session_state["storey_table_input"][1] == {"storey": "L1", "row": None,
                                                         "area_m2": 2000.0, "count": 1}
    assert not at.warning
    at = _app_test({"occupancy_chosen": ("Business / Office", "business"),
                    "occupancy_category_select": "Business / Office",
                    "occupancy_sub_select": "business", "business_group_input": "B",
                    "height_m_input": 12.0,
                    "floors_above_input": 3, "floors_below_input": 0,
                    "gfa_input": 5000.0, "ground_bua_input": 3000.0,
                    "plot_area_input": 9000.0, "storey_table_base": TABLE})
    assert any("more than the GFA of 5,000 m2" in w.value for w in at.warning)


# ------------------------------------------------------------------ Ch9 Q6
def test_CH9_Q6_animal_housing_groups_take_the_printed_hazard_class():
    """#1.1.13.1.q (p.528) Group A LH; #1.1.13.1.r (p.528) Group C LH; #1.1.13.3.a
    (p.529) Group B OH2. Groups A and C are LESS onerous than the phase 2 OH2."""
    assert {g: v[0] for g, v in ANIMAL_HOUSING_GROUPS.items()} == {"A": "LH", "B": "OH2", "C": "LH"}
    assert [default_hazard("animal_housing", g) for g in ("A", "B", "C")] == ["LH", "OH2", "LH"]
    assert default_hazard("animal_housing") == "OH2"   # no group: unchanged (R13 secondaries)
    kw = dict(occupancy="animal_housing", height_m=10, floors_above_grade=2,
              gross_floor_area_m2=4000, ground_floor_bua_m2=4000, plot_area_m2=8000,
              has_high_ceiling=True, ceiling_height_m=12)
    hz = {g: report(animal_housing_group=g, **kw) for g in "ABC"}
    assert {g: r.building.hazard_class for g, r in hz.items()} == {"A": "LH", "B": "OH2", "C": "LH"}
    assert hz["A"].high_ceiling.hazard_class == "LH" and hz["B"].high_ceiling.hazard_class == "OH2"
    # An explicit hazard (the app override) is kept.
    assert report(animal_housing_group="A", hazard_class="OH1", **kw).building.hazard_class == "OH1"
    # The Ch 9 table row is the same for every group (Table 9.21.b row D, p.707).
    assert len({r.chapter("FP").selected_branch for r in hz.values()}) == 1
    assert "(Group B, #1.1.13)" in engine.report_to_markdown(hz["B"])
    # The group is ignored for any other occupancy.
    assert Building(occupancy="business", height_m=10, animal_housing_group="A").hazard_class == "OH1"


def test_CH9_Q6_app_requires_the_group_and_old_files_are_stopped_by_name():
    """No default group: an old file (single animal housing value) loads, then the app
    stops with a named message until the group is chosen."""
    check = _app_defs("_SCENARIO_LIMITS", "_invalid_scenario_values")["_invalid_scenario_values"]
    assert check({"animal_housing_group_input": "B"}) == []
    assert check({"animal_housing_group_input": None}) == []
    assert "Animal housing group = 'D'" in " ".join(check({"animal_housing_group_input": "D"}))
    base = {"occupancy_chosen": ("Mixed / Underground", "animal_housing"),
            "occupancy_category_select": "Mixed / Underground",
            "occupancy_sub_select": "animal_housing", "height_m_input": 6.0,
            "floors_above_input": 1, "floors_below_input": 0, "gfa_input": 1000.0,
            "ground_bua_input": 1000.0, "plot_area_input": 5000.0}
    at = _app_test(base)
    assert any("Select the animal housing group" in e.value and "Ch9 Q6" in e.value
               for e in at.error)
    at = _app_test({**base, "animal_housing_group_input": "B"})
    assert not at.error
    assert any("Animal Housing Group B, #1.1.13.3.a, p.529): **OH2**" in c.value
               for c in at.caption)
