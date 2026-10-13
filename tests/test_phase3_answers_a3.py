"""Phase 3 owner answers, package a3 (owner rulings 12.10.2026, P3 cards).

One test per answer coded:
- Storey Q1: "identical storeys" count on the per-storey table; the counts must cover the
  floors above grade plus the basements, else no exit count (NOT EVALUATED, gap named).
- Storey Q4: a secondary animal housing (R13 most restrictive) needs its group, as the
  secondary storage hazard of Ch9 Q9; hazard per #1.1.13 (A LH, B OH2, C LH, p.528-529).
- App Q1: a converted villa takes Table 9.21.d alone (#4.5.4, p.710); the Table 9.23 villa
  rows (#4.7.1, p.716) are suppressed.
- App Q2: the attached parking's own height above the fire access level and basement
  levels; blank = the lines keyed on them NOT EVALUATED, never the tower height; Ch 9
  sprinklers still follow the host table (Table 9.19 "throughout including basements").
- App Q6: a parking building above 23 m prints one sprinkler, wet riser, pump and tank
  line, the most onerous, citing Table 9.19 and Table 9.24 (as ruling R6).
"""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import engine  # noqa: E402
from flsc_schema import Building, StoreyUse  # noqa: E402
from test_phase1_findings import items, lines, pump, tank, report  # noqa: E402

APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")
_TREE = ast.parse(APP_SRC)


def _app_defs(names, funcs=()):
    keep = [n for n in _TREE.body
            if (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in names for t in n.targets))
            or (isinstance(n, ast.FunctionDef) and n.name in funcs)]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "app_part", "exec"), ns)
    return ns


def _guard():
    return _app_defs({"_SCENARIO_LIMITS", "OCCUPANCY_OPTIONS", "OCC_FLAT"},
                     ("_invalid_scenario_values",))["_invalid_scenario_values"]


def _save_keys_src():
    return APP_SRC.split("_save_keys = [", 1)[1].split("]", 1)[0]


def _app_test(state):
    at_mod = pytest.importorskip("streamlit.testing.v1")
    at = at_mod.AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _occ(cat, occ):
    return {"occupancy_chosen": (cat, occ), "occupancy_category_select": cat,
            "occupancy_sub_select": occ}


def _all(chapters, code):
    ch = next(c for c in chapters if c.chapter_code == code)
    return [it for b in ch.blocks for it in b.items]


# ------------------------------------------------------------------ Storey Q1
TOWER = dict(occupancy="business", height_m=30, floors_above_grade=10, floors_below_grade=1,
             gross_floor_area_m2=31500, ground_floor_bua_m2=3000)
TYPICAL = [{"storey": "B1", "row": "19.i", "area_m2": 3000},      # 3000 / 27.9 -> 108
           {"storey": "GF", "row": "13.ii", "area_m2": 1500},     # 1500 / 2.8 -> 536
           {"storey": "Typ", "row": "2.i", "area_m2": 3000, "count": 9}]   # 3000 / 9.3 -> 323


def test_P3_STOREY_Q1_identical_storeys_count_covers_every_storey():
    """Owner ruling 12.10.2026, P3 Storey Q1. A storey counts 'count' times in the total
    OL; the governing storey is still the highest OL (#4.3.1 / #4.1.3, Table 3.14 p.288:
    OL 500 - 1,000 -> 3 exits). The counts must add up to floors above grade + basements."""
    ol = report(storey_uses=TYPICAL, **TOWER).occupant_load
    assert ol.evaluated and ol.governing_storey == "GF" and ol.min_exits == 3
    assert ol.occupant_load == 108 + 536 + 9 * 323
    assert [s.count for s in ol.storeys] == [1, 1, 9]
    assert "Typ (x9 identical storeys)" in ol.note and "P3 Storey Q1" in ol.note
    # One storey short (8 typical + B1 + GF = 10 of 11): no exit count, the gap named.
    short = [dict(ln) for ln in TYPICAL]
    short[2]["count"] = 8
    ol = report(storey_uses=short, **TOWER).occupant_load
    assert not ol.evaluated and ol.min_exits == 0 and ol.occupant_load == 0
    assert "1 storey(s) not covered" in ol.exit_ref and "no exit count stated" in ol.exit_ref
    assert "add up to 10 storey(s), the building has 11" in ol.note
    # One too many is refused the same way.
    over = [dict(ln) for ln in TYPICAL]
    over[2]["count"] = 10
    assert "1 storey(s) more than the building has" in report(storey_uses=over, **TOWER).occupant_load.exit_ref
    # Lines of one storey with different counts are refused by name.
    mixed = TYPICAL + [{"storey": "Typ", "row": "13.v", "area_m2": 100, "count": 2}]
    ol = report(storey_uses=mixed, **TOWER).occupant_load
    assert not ol.evaluated and "storey 'Typ': its lines give different identical-storey counts (9, 2)" in ol.note
    # The count is a whole number of at least 1: bool, fraction, 0 and negative refused.
    for bad in (True, 2.5, 2.0, 0, -1, "2"):
        with pytest.raises(ValueError):
            StoreyUse(storey="L1", row="2.i", area_m2=10, count=bad)
    assert StoreyUse(storey="L1").count == 1          # a line saved before the column
    # App: column, save key, Load validation, old lines load as 1.
    assert '"count": st.column_config.NumberColumn(' in APP_SRC and "Identical storeys" in APP_SRC
    assert '"storey_table_input"' in _save_keys_src()
    check = _guard()
    bad = " ".join(check({"storey_table_input": [
        {"storey": "L1", "row": "2.i", "area_m2": 10, "count": True},
        {"storey": "L2", "row": "2.i", "area_m2": 10, "count": 1.5},
        {"storey": "L3", "row": "2.i", "area_m2": 10, "count": -2},
        {"storey": "L4", "row": "2.i", "area_m2": 10, "count": 0},
        {"storey": "L5", "row": "2.i", "area_m2": 10, "count": "3"}]}))
    for i, v in enumerate(("True", "1.5", "-2", "0", "'3'"), 1):
        assert f"line {i} identical storeys = {v} (a whole number of at least 1)" in bad, v
    assert check({"storey_table_input": [{"storey": "L1", "row": "2.i", "area_m2": 10},
                                         {"storey": "L2", "row": "2.i", "area_m2": 10, "count": 4}]}) == []
    ns = _app_defs({"_STOREY_COLS"}, ("_storey_count", "_storey_table_frame", "_storey_table_records"))
    assert [ns["_storey_count"](c) for c in (None, 3, 3.0)] == [1, 3, 3]
    assert ns["_storey_count"](2.5) == 2.5 and ns["_storey_count"](True) is True
    df = ns["_storey_table_frame"]([{"storey": "GF", "row": "2.i", "area_m2": 100},
                                    {"storey": "L1", "row": "2.i", "area_m2": 100, "count": 4}])
    assert [ln["count"] for ln in ns["_storey_table_records"](df)] == [1, 4]


# ------------------------------------------------------------------ Storey Q4
MIXED = dict(occupancy="business", hazard_class="LH", height_m=10, floors_above_grade=3, gross_floor_area_m2=6000,
             ground_floor_bua_m2=2000, plot_area_m2=8000, mixed_occupancy_mode="most_restrictive",
             secondary_occupancies=["animal_housing"])


def test_P3_STOREY_Q4_secondary_animal_housing_group_is_required():
    """Owner ruling 12.10.2026, P3 Storey Q4: the group of a secondary animal housing sets
    its #1.1.13 hazard (A LH #1.1.13.1.q, C LH #1.1.13.1.r, p.528; B OH2 #1.1.13.3.a,
    p.529); no group = its Ch 9 lines NOT EVALUATED, never the OH2 default (as Ch9 Q9).
    Groups A and C are LESS onerous than the OH2 used before."""
    hz = {g: report(secondary_animal_housing_group=g, **MIXED).building.hazard_class for g in "ABC"}
    assert hz == {"A": "LH", "B": "OH2", "C": "LH"}
    r = report(secondary_animal_housing_group="B", **MIXED)
    assert "Group B, OH2 (#1.1.13.3.a, p.529" in r.mixed_occupancy_note
    blank = report(**MIXED)
    assert blank.building.hazard_class == "LH"         # business LH; animal brings nothing
    ne = lines(blank, "FP", "Animal Housing (secondary occupancy) - Ch 9 NOT EVALUATED")
    assert ne and "P3 Storey Q4" in ne[0].detail and ne[0].code_ref == "Ch 9, #1.1.13"
    assert "Animal housing group not chosen" in blank.mixed_occupancy_note
    with pytest.raises(ValueError):
        Building(secondary_animal_housing_group="D", **MIXED)
    # App: selector, save key, Load validation and a stop until it is chosen.
    assert '"secondary_animal_housing_group_input"' in _save_keys_src()
    check = _guard()
    assert check({"secondary_animal_housing_group_input": "C"}) == []
    assert "Secondary animal housing group = 'D'" in " ".join(
        check({"secondary_animal_housing_group_input": "D"}))
    state = {**_occ("Business / Office", "business"), "business_group_input": "B", "height_m_input": 10.0,
             "floors_above_input": 3, "floors_below_input": 0, "gfa_input": 6000.0,
             "ground_bua_input": 2000.0, "plot_area_input": 8000.0,
             "mixed_occupancy_mode_input": "most_restrictive",
             "secondary_occupancies_input": ["animal_housing"]}
    at = _app_test(state)
    assert any("Select the group of the animal housing occupancy" in e.value
               and "P3 Storey Q4" in e.value for e in at.error)
    at = _app_test({**state, "secondary_animal_housing_group_input": "A"})
    assert not at.error


# ------------------------------------------------------------------ App Q1
def test_P3_APP_Q1_converted_villa_takes_table_9_21_d_alone():
    """Owner ruling 12.10.2026, P3 App Q1: #4.5.4 (p.710) Table 9.21.d alone; the Table
    9.23 rows (#4.7.1, p.716) do not print beside it. LESS onerous: a converted villa
    with GF BUA over 1,500 m2 loses the Table 9.23.A.2 sprinklers, 250 gpm pump and tank."""
    for occ in ("villa_private", "villa_commercial"):
        r = report(occupancy=occ, height_m=7, floors_above_grade=2, floors_below_grade=1,
                   ground_floor_bua_m2=1600, basement_bua_m2=1600, plot_area_m2=25000,
                   villa_converted_use=True, exit_stairs=2)
        ch = r.chapter("FP")
        assert ch.selected_branch == "lowrise_villa_converted_two_stairs"
        src = {it.source_rule for it in items(r, "FP")}
        assert not any(s and s.startswith("villa_") for s in src), src
        assert not lines(r, "FP", "Fire Pump") and not lines(r, "FP", "Automatic Sprinkler")
        assert "P3 App Q1" in lines(r, "FP", "Portable Fire Extinguishers")[0].detail
    # Not converted: Table 9.23 unchanged.
    r = report(occupancy="villa_private", height_m=7, floors_above_grade=2,
               ground_floor_bua_m2=1600, plot_area_m2=2000)
    assert "Table 9.23.A.2" in pump(r).code_ref


# ------------------------------------------------------------------ App Q2
TOWER_P = dict(occupancy="residential", height_m=60, floors_above_grade=18, floors_below_grade=2,
               depth_below_grade_m=7, ground_floor_bua_m2=2000, gross_floor_area_m2=30000,
               plot_area_m2=5000, has_parking_area=True, parking_area_m2=3000)


def test_P3_APP_Q2_attached_parking_uses_its_own_height_and_levels():
    """Owner ruling 12.10.2026, P3 App Q2. Table 10.23 item 1.iv (p.860): stairs of parking
    'having a height of more than 23 m from the fire access level' -> the parking's own
    height, not the 60 m tower (a 9 m podium is LESS onerous than before). Ch 9: the
    sprinklers follow the host table (Table 9.19, sprinklered throughout incl. basements)."""
    low = engine.evaluate(Building(parking_height_m=9, parking_basement_levels=2, **TOWER_P))
    sc = [it.system for it in _all(low.attached_parking_chapters, "SC")]
    assert "Stair Pressurization NOT Required (parking, height less than 23 m)" in sc
    assert "Stair Pressurization (parking, height 23 m or more)" not in sc
    tall = engine.evaluate(Building(parking_height_m=30, parking_basement_levels=2, **TOWER_P))
    assert "Stair Pressurization (parking, height 23 m or more)" in [
        it.system for it in _all(tall.attached_parking_chapters, "SC")]
    fp = _all(low.attached_parking_chapters, "FP")
    spr = [it for it in fp if it.system.startswith("Automatic Sprinkler System")]
    assert len(spr) == 1 and spr[0].status == "required"
    assert spr[0].system == "Automatic Sprinkler System (as the host building)"
    assert "Table 9.19" in spr[0].code_ref and "P3 App Q2" in spr[0].detail
    assert any(it.code_ref and "Table 9.24.A.2" in it.code_ref for it in fp)   # own row, 9 m
    # Blank height: the height-keyed lines are NOT EVALUATED by name (not the tower's 60 m).
    blank = engine.evaluate(Building(parking_basement_levels=2, **TOWER_P))
    sc = _all(blank.attached_parking_chapters, "SC")
    ne = [it for it in sc if it.system.endswith(" - NOT EVALUATED")]
    assert "Stair Pressurization (parking, height 23 m or more) - NOT EVALUATED" in [it.system for it in ne]
    assert all("parking height above the fire access level" in it.spec for it in ne)
    assert not any(it.status == "required" and it.system == "Stair Pressurization (parking, height 23 m or more)"
                   for it in sc)
    assert any(it.system == "Fire Pump - NOT EVALUATED" for it in _all(blank.attached_parking_chapters, "FP"))
    # Height-independent lines still print (Table 10.27 item 5 fire pump room).
    assert "Fire Pump Room - Dedicated Mechanical Ventilation" in [it.system for it in sc]
    blank_lv = engine.evaluate(Building(parking_height_m=9, **TOWER_P))
    assert any("basement levels" in it.spec for c in blank_lv.attached_parking_chapters
               for b in c.blocks for it in b.items if it.system.endswith("NOT EVALUATED"))
    # Levels within the building; negative refused.
    with pytest.raises(ValueError, match="cannot exceed the building's basements"):
        Building(parking_basement_levels=3, **TOWER_P)
    for bad in ({"parking_height_m": -1}, {"parking_basement_levels": -1}):
        with pytest.raises(ValueError):
            Building(**{**TOWER_P, **bad})
    # App: inputs with help text, saved, Load-checked, Building() fields.
    for key in ("parking_height_m_input", "parking_basement_levels_input"):
        assert f'"{key}"' in _save_keys_src()
        assert f'key="{key}"' in APP_SRC
    assert "parking_height_m=None if parking_height_m_val is None" in APP_SRC
    check = _guard()
    assert check({"parking_height_m_input": None, "parking_basement_levels_input": None}) == []
    bad = " ".join(check({"parking_height_m_input": -3.0, "parking_basement_levels_input": 1.5}))
    assert "Parking height above the fire access level = -3.0 (minimum 0.0)" in bad
    assert "Parking basement levels = 1.5 (must be a whole number)" in bad
    state = {**_occ("Residential", "residential"), "height_m_input": 60.0,
             "floors_above_input": 18, "floors_below_input": 1, "gfa_input": 30000.0,
             "ground_bua_input": 2000.0, "plot_area_input": 5000.0, "has_parking_area": True,
             "parking_area_m2_input": 3000.0, "parking_height_m_input": 9.0,
             "parking_basement_levels_input": 2}
    at = _app_test(state)
    assert any("cannot exceed the building's basements (1)" in e.value for e in at.error)
    at = _app_test({**state, "parking_basement_levels_input": 1})
    assert not at.error


# ------------------------------------------------------------------ App Q6
def test_P3_APP_Q6_parking_above_23_m_one_line_per_system_citing_both_tables():
    """Owner ruling 12.10.2026, P3 App Q6, merged as ruling R6. #4.3.1 (p.698) Table 9.19
    applies to buildings of more than 23 m 'of any occupancy'; #4.8.1 (p.718) Table 9.24 to
    parking. One sprinkler, wet riser, pump and tank line, the most onerous, both cited.
    Open parking C.3 (p.720) 1000 gpm governs Table 9.19.D 750 gpm (2 standpipes, p.699)."""
    for occ, row in (("parking_enclosed", "Table 9.24.A.3"), ("parking_open", "Table 9.24.C.3")):
        r = report(occupancy=occ, height_m=30, floors_above_grade=10, ground_floor_bua_m2=3000,
                   gross_floor_area_m2=20000, plot_area_m2=5000)
        for prefix in ("Automatic Sprinkler System", "Wet Riser System"):
            got = lines(r, "FP", prefix)
            assert len(got) == 1, (prefix, [g.system for g in got])
            assert "Table 9.19.D" in got[0].code_ref and row in got[0].code_ref
            assert "P3 App Q6" in got[0].detail and "ruling R6" in got[0].detail
        p, t = pump(r), tank(r)
        assert "Table 9.19.D" in p.code_ref and row in p.code_ref
        assert "Table 9.19.D" in t.code_ref and row in t.code_ref and t.spec.startswith("60 minutes")
    r = report(occupancy="parking_open", height_m=30, floors_above_grade=10,
               ground_floor_bua_m2=3000, gross_floor_area_m2=20000, plot_area_m2=5000)
    assert pump(r).spec.startswith("1000 gpm @ 6.9 bar") and pump(r).source_rule == "parking_open_c3"
    # Table 9.19 riser interconnection line stays (lowest + highest level of each zone).
    assert lines(r, "FP", "Wet Risers Interconnected at Lowest + Highest Level of Each Zone")
    # A parking below 23 m and a tower that is not parking are unchanged (one table).
    low = report(occupancy="parking_enclosed", height_m=20, floors_above_grade=6,
                 ground_floor_bua_m2=3000, plot_area_m2=5000)
    assert all("Table 9.19" not in (it.code_ref or "") for it in items(low, "FP"))
    biz = report(occupancy="business", height_m=30, floors_above_grade=10,
                 ground_floor_bua_m2=1000, plot_area_m2=5000)
    assert pump(biz).code_ref == "Ch 9, #4.3.1 / Table 9.19.D"
