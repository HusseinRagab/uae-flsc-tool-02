"""Phase 3 audit fixes, package "app" (audit 12.10.2026): one test per finding.

App inputs, save / load, occupancy definitions and engine leftovers. Code text in
the asserts is read off the pages named in each line (UAE FLSC 2018). Run with
`python -m pytest tests/test_phase3_app.py`.
"""
import ast
import json
import re
import sys
from pathlib import Path
from typing import get_args

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flsc_schema import OCCUPANCY_DEFS, Building, Occupancy  # noqa: E402
from test_phase1_findings import report, items  # noqa: E402

APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")
_TREE = ast.parse(APP_SRC)


# ---------------------------------------------------------------- helpers
def _module_ns(names, funcs=()):
    """Exec only the named module-level assignments and functions of app.py."""
    keep = [n for n in _TREE.body
            if (isinstance(n, ast.Assign) and any(getattr(t, "id", "") in names for t in n.targets))
            or (isinstance(n, ast.FunctionDef) and n.name in funcs)]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "app_part", "exec"), ns)
    return ns


def _guard():
    ns = _module_ns({"_SCENARIO_LIMITS", "OCCUPANCY_OPTIONS", "OCC_FLAT"},
                    ("_invalid_scenario_values",))
    return ns["_invalid_scenario_values"]


def _save_keys():
    ns = _module_ns({"_SCENARIO_LIMITS", "USE_AREA_MAX", "SPECIAL_ROOMS_KEYS", "VARIOUS_LOCATIONS_KEYS", "EQUIPMENT_KEYS",
                     "FE_KEYS", "ES_FEATURE_KEYS", "ES_ZONE_KEYS", "USE_AREA_KEYS"})
    node = next(n for n in ast.walk(_TREE) if isinstance(n, ast.Assign)
                and any(getattr(t, "id", "") == "_save_keys" for t in n.targets))
    return eval(compile(ast.Expression(node.value), "save_keys", "eval"), ns)


def _loader():
    ns = _module_ns({"FIRST_LOAD_DEFAULTS"}, ("_apply_loaded_scenario",))
    return ns["_apply_loaded_scenario"], ns["FIRST_LOAD_DEFAULTS"]


def _app_test(state, run=True):
    at_mod = pytest.importorskip("streamlit.testing.v1")
    at = at_mod.AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
    for k, v in state.items():
        at.session_state[k] = v
    if run:
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _occ(cat, occ):
    return {"occupancy_chosen": (cat, occ), "occupancy_category_select": cat,
            "occupancy_sub_select": occ}


def _state(at, key, default=None):
    try:
        return at.session_state[key]
    except KeyError:
        return default


def _has_state(at, key):
    try:
        at.session_state[key]
        return True
    except KeyError:
        return False


_GEO = {"height_m_input": 8.0, "floors_above_input": 2, "ground_bua_input": 1000.0,
        "gfa_input": 2000.0, "plot_area_input": 5000.0}


def fp_line(r, prefix):
    return [it for it in items(r, "FP") if it.system.startswith(prefix)]


def branches(r):
    """Every FP branch id that produced a line, plus the selected one."""
    ch = r.chapter("FP")
    return " ".join({ch.selected_branch or ""} | {it.source_rule or "" for it in items(r, "FP")})


# ---------------------------------------------------------------- ENG-02
def test_ENG_02_mercantile_group_over_3600_is_a_mall_not_mercantile():
    # Ch 1 Table 1.1 row 11 (p.50): a group of mercantile occupancies under a single roof
    # or not separated, GF BUA more than 3600 m2, irrespective of storeys = Mall.
    kw = dict(occupancy="mercantile_b", height_m=10, floors_above_grade=2, plot_area_m2=8000,
              mercantile_multi_tenant=True)
    with pytest.raises(ValueError, match="Table 1.1 row 11"):
        Building(**kw, ground_floor_bua_m2=3601)
    assert Building(**kw, ground_floor_bua_m2=3600).occupancy == "mercantile_b"
    # A single-tenant mercantile building is not a group: unchanged.
    assert Building(**{**kw, "mercantile_multi_tenant": False},
                    ground_floor_bua_m2=4000).occupancy == "mercantile_b"
    assert '"mercantile_multi_tenant"' in APP_SRC.split("_save_keys = [", 1)[1].split("]", 1)[0]
    at = _app_test({**_GEO, **_occ("Mercantile", "mercantile_b"), "ground_bua_input": 4000.0,
                    "mercantile_multi_tenant": True})
    assert any("Table 1.1 row 11" in e.value and "Mall" in e.value for e in at.error)


# ---------------------------------------------------------------- ENG-11
def test_ENG_11_attached_parking_only_when_ticked_with_its_area_and_user_flags():
    assert Building.model_fields["has_parking_area"].default is False
    villa = report(occupancy="villa_private", height_m=6, floors_above_grade=2,
                   ground_floor_bua_m2=250, plot_area_m2=600)
    assert villa.attached_parking_chapters == []
    ns = _module_ns({"VILLA_INCOMPATIBLE_FLAGS"})
    assert "has_parking_area" in ns["VILLA_INCOMPATIBLE_FLAGS"]
    # Blank parking area: named, never taken from the basement / GF BUA.
    blank = report(occupancy="residential", height_m=10, floors_above_grade=3,
                   ground_floor_bua_m2=1000, basement_bua_m2=1500, plot_area_m2=5000,
                   has_parking_area=True)
    assert [c.chapter_code for c in blank.attached_parking_chapters] == ["PARK"]
    ne = blank.attached_parking_chapters[0].blocks[0].items[0]
    assert ne.system == "Attached Parking Area - NOT EVALUATED" and ne.status == "not_evaluated"

    # Every user flag carries over: an unticked room is not brought back.
    def park(**kw):
        r = report(occupancy="residential", height_m=10, floors_above_grade=3,
                   ground_floor_bua_m2=1000, plot_area_m2=5000, has_parking_area=True,
                   parking_area_m2=1000, **kw)
        return {(c.chapter_code, it.system) for c in r.attached_parking_chapters
                for b in c.blocks for it in b.items if it.status != "not_required"}
    on, off = park(has_diesel_generator_room=True), park(has_diesel_generator_room=False)
    assert ("FP", "Diesel Generator Room - Foam Sprinkler System (Section 3.9)") in on
    assert not any("Diesel Generator" in s for _, s in off)


# ---------------------------------------------------------------- ENG-12
def test_ENG_12_load_sets_the_occupancy_and_replaces_the_session():
    apply, defaults = _loader()
    keys = _save_keys()
    # Save a business project from the app.
    src = _app_test({**_GEO, **_occ("Business / Office", "business"), "business_group_input": "B",
                     "project_name_input": "B-01"})
    saved = {k: (list(v) if isinstance(v, tuple) else v)
             for k in keys if _has_state(src, k) for v in [_state(src, k)]}
    saved = json.loads(json.dumps(saved, default=str))
    assert saved["occupancy_chosen"] == ["Business / Office", "business"]
    saved.pop("has_atrium", None)            # an input the file lacks takes its default
    saved["not_an_input"] = 1
    # Start from a residential session with an extra ticked flag, then load.
    state = {**_GEO, **_occ("Residential / Lodging", "residential"), "has_atrium": True,
             "_last_occupancy": "residential"}
    ignored, defaulted = apply(state, saved, keys)
    assert ignored == ["not_an_input"] and "has_atrium" in defaulted
    assert "has_atrium" not in state
    assert state["occupancy_category_select"] == "Business / Office"
    assert state["occupancy_sub_select"] == "business" and state["_last_occupancy"] == "business"
    assert state["occupancy_chosen"] == ("Business / Office", "business")
    for k, v in defaults.items():
        if k not in saved:
            assert state[k] == v
    dst = _app_test(state)
    assert json.loads(dst.session_state["_building_json"])["occupancy"] == "business"
    assert dst.session_state["_building_json"] == src.session_state["_building_json"]


# ---------------------------------------------------------------- ENG-13
def test_ENG_13_category_change_to_villa_clears_incompatible_flags():
    ns = _module_ns({"VILLA_INCOMPATIBLE_FLAGS"})
    at = _app_test({**_GEO, **_occ("Residential / Lodging", "residential"),
                    "has_lift_machine_room": True, "has_fire_pump_room": True,
                    "has_diesel_generator_room": True, "has_main_electrical_room": True,
                    "has_parking_area": True, "parking_area_m2_input": 500.0})
    at.selectbox(key="occupancy_category_select").set_value("Villa").run()
    assert not at.exception
    assert at.session_state["occupancy_sub_select"] == "villa_private"
    still_on = [f for f in ns["VILLA_INCOMPATIBLE_FLAGS"] if _state(at, f, False) is True]
    assert still_on == []
    assert json.loads(at.session_state["_building_json"])["occupancy"] == "villa_private"


# ---------------------------------------------------------------- ENG-16
def test_ENG_16_definitions_follow_table_1_1_use_lists():
    # Table 1.1 row 11 (p.50); row 2 (p.48); row 5 (p.49).
    m_a = OCCUPANCY_DEFS["mercantile_a"]
    assert "Table 1.1 row 11 (p.50)" in m_a
    assert ("hardware stores, paint stores, chemical stores, furniture stores, motor vehicle "
            "showrooms, restaurants with less than 50 people") in m_a
    assert "#1.7.9 Class A/B/C" in m_a and "2800" not in m_a and "2 storeys" not in m_a
    assert "Table 1.1 row 2 (p.48)" in OCCUPANCY_DEFS["business"]
    assert "offices, modular site offices, banks" in OCCUPANCY_DEFS["business"]
    assert "Table 1.1 row 5 (p.49)" in OCCUPANCY_DEFS["residential"]
    for occ in ("assembly_a", "hotel_a", "detention_a"):
        assert "Table 1.1" in OCCUPANCY_DEFS[occ], occ
        assert "star" not in OCCUPANCY_DEFS[occ].lower()
        assert "occupant load" not in OCCUPANCY_DEFS[occ].lower()


# ---------------------------------------------------------------- ENG-17
def test_ENG_17_underground_definitions_quote_1_7_44_and_1_7_45():
    # #1.7.45 / #1.7.44 (p.45).
    assert ("An underground structure or a building more than 7 m below or having more than "
            "two basements below the level of exit discharge."
            in OCCUPANCY_DEFS["high_depth_underground"])
    assert ("An underground structure or a building up to 7 m below or having up to two "
            "basements below the level of exit discharge."
            in OCCUPANCY_DEFS["low_depth_underground"])


# ---------------------------------------------------------------- ENG-21
def test_ENG_21_height_datum_states_the_printed_definition_and_warns():
    base = {**_GEO, **_occ("Business / Office", "business"), "business_group_input": "B"}
    at = _app_test({**base, "height_datum_input": "occupiable_ceiling"})
    assert any("FAQ Annexure 1 Q2-Q5, p.1273" in w.value and "#1.7.39-#1.7.42" in w.value
               for w in at.warning)
    at = _app_test({**base, "height_datum_input": "grade"})
    assert not any("FAQ Annexure 1 Q2-Q5" in w.value for w in at.warning)
    assert any("Ch 1 #1.7.39-" in c.value for c in at.caption)


# ---------------------------------------------------------------- ENG-22
def test_ENG_22_every_schema_occupancy_can_be_picked():
    ns = _module_ns({"OCCUPANCY_OPTIONS"})
    ui = {o for opts in ns["OCCUPANCY_OPTIONS"].values() for o in opts}
    assert ui == set(get_args(Occupancy))
    at = _app_test({**_GEO, **_occ("Infrastructure", "infrastructure"), "height_m_input": 0.0})
    assert json.loads(at.session_state["_building_json"])["occupancy"] == "infrastructure"


# ---------------------------------------------------------------- ENG-23
def test_ENG_23_every_input_is_keyed_saved_and_type_checked_on_load():
    keys = _save_keys()
    for k in ("project_name_input", "corridor_length_m", "height_datum_input",
              "mixed_occupancy_mode_input", "construction_type_input", "hazard_override_input",
              "has_water_reactive_materials", "has_attached_commercial_outlet",
              "commercial_outlet_gf_bua_m2_input", "tent_marquee_kind_input"):
        assert k in keys, k
    assert 'key="project_name_input"' in APP_SRC and 'key="corridor_length_m"' in APP_SRC
    assert 'key="hazard_override_input"' in APP_SRC
    guard = _guard()
    assert guard({"has_atrium": True, "occupancy_chosen": ["Business / Office", "business"],
                  "hazard_override_input": "HH", "project_name_input": "X"}) == []
    bad = " ".join(guard({"has_atrium": "false", "is_extra_hazard_2": 1,
                          "hazard_override_input": "EH", "height_datum_input": "roof",
                          "occupancy_chosen": ["Business / Office", "warehouse"],
                          "project_name_input": 5, "commercial_outlet_gf_bua_m2_input": -1}))
    for frag in ("has_atrium = 'false' (not true / false)", "is_extra_hazard_2 = 1",
                 "Hazard class override = 'EH'", "Height datum = 'roof'", "Occupancy = ",
                 "project_name_input = 5", "Commercial outlet GF BUA = -1"):
        assert frag in bad, frag
    # Round trip: an HH override and the other new inputs come back with the same Building.
    apply, _ = _loader()
    a = _app_test({**_GEO, **_occ("Business / Office", "business"), "business_group_input": "B",
                   "hazard_override_input": "HH", "height_datum_input": "occupiable_ceiling",
                   "construction_type_input": "type_ii", "corridor_length_m": 12.0,
                   "project_name_input": "Round trip"})
    b_a = json.loads(a.session_state["_building_json"])
    assert b_a["hazard_class"] == "HH" and b_a["height_datum"] == "occupiable_ceiling"
    saved = json.loads(json.dumps({k: _state(a, k) for k in keys if _has_state(a, k)},
                                  default=str))
    assert guard(saved) == []
    state = {}
    apply(state, saved, keys)
    b = _app_test(state)
    assert b.session_state["_building_json"] == a.session_state["_building_json"]
    assert b.session_state["project_name_input"] == "Round trip"


# ---------------------------------------------------------------- CH9A-17
def test_CH9A_17_storage_total_bua_not_entered_is_named():
    # #4.1.6 (p.694) "more than 3600 m2 built-up area"; #4.1.11 (p.695) built-up area =
    # total floor areas of all the floors, including mezzanines.
    kw = dict(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000,
              plot_area_m2=5000, hazard_class="OH1", sum_gf_bua_m2=2000)
    blank = report(**kw, floors_above_grade=2)
    ne = fp_line(blank, "Yard Fire Hydrant System (#4.1.6 total built-up area) - NOT EVALUATED")
    assert ne and ne[0].status == "not_evaluated" and ne[0].page_ref == "p.694, p.695"
    stated = report(**kw, floors_above_grade=2, gross_floor_area_m2=4000)
    assert not fp_line(stated, "Yard Fire Hydrant System (#4.1.6 total built-up area) - NOT")
    single = report(**kw, floors_above_grade=1)
    assert not fp_line(single, "Yard Fire Hydrant System (#4.1.6 total built-up area) - NOT")


# ---------------------------------------------------------------- CH9A-19
def test_CH9A_19_midrise_low_depth_underground_not_given_a_9_20_a_row():
    # Table 9.20.a (p.700) lists no low depth underground building; row H is high depth.
    r = report(occupancy="low_depth_underground", height_m=20, floors_above_grade=5,
               floors_below_grade=1, ground_floor_bua_m2=1000, plot_area_m2=5000)
    assert "midrise_low_depth_not_in_code" in branches(r)
    assert fp_line(r, "Midrise Low Depth Underground - NOT EVALUATED")
    assert "midrise_public_" not in branches(r)
    deep = report(occupancy="low_depth_underground", height_m=20, floors_above_grade=5,
                  floors_below_grade=3, ground_floor_bua_m2=1000, plot_area_m2=5000)
    assert "midrise_low_depth_not_in_code" not in branches(deep)


# ---------------------------------------------------------------- CH9A-20
def test_CH9A_20_water_reactive_and_foam_prohibitions_are_printed():
    kw = dict(occupancy="storage_industrial", height_m=8, floors_above_grade=2,
              ground_floor_bua_m2=1000, plot_area_m2=5000, hazard_class="OH1",
              sum_gf_bua_m2=1000)
    wr = report(**kw, has_water_reactive_materials=True)
    line = fp_line(wr, "No Water-Based System Where Water-Reactive Materials Are Stored")
    assert line and line[0].page_ref == "p.694"
    assert ("Water based fire protection systems shall not be installed or used where water "
            "reactive materials are stored and handled.") in line[0].detail
    assert not fp_line(report(**kw), "No Water-Based System")
    # #4.1.3 note on any foam output (diesel generator room foam sprinklers).
    foam = report(occupancy="business", height_m=8, floors_above_grade=2,
                  ground_floor_bua_m2=1000, plot_area_m2=5000, has_diesel_generator_room=True)
    note = fp_line(foam, "Medium- / High-Expansion Foam Not Used on the #4.1.3 Hazards")
    assert note and "Liquefied flammable gas" in note[0].detail
    assert not fp_line(report(occupancy="business", height_m=8, floors_above_grade=2,
                              ground_floor_bua_m2=1000, plot_area_m2=5000,
                              has_diesel_generator_room=False), "Medium- / High-Expansion")


# ---------------------------------------------------------------- CH9B-14
def test_CH9B_14_outlet_keyed_on_outlet_area_and_tents_replace_generic_tiers():
    # Table 9.21.e (p.711): keyed on the built-up GF area OF THE COMMERCIAL OUTLET, for
    # villas (G+1), business (A, B, C) and mosques.
    kw = dict(height_m=7, floors_above_grade=2, ground_floor_bua_m2=2000, plot_area_m2=5000,
              has_attached_commercial_outlet=True)
    small = report(occupancy="business", commercial_outlet_gf_bua_m2=900, **kw)
    assert "lowrise_commercial_outlet_attached_small" in branches(small)
    assert "lowrise_public_" not in branches(small)
    # Owner ruling R-C (28.10.2026): the host Table 9.21.b.1 row and Table 9.21.e.1 both
    # apply; one governing pump (both 50 gpm at 4.5 bar here), the other named.
    assert "lowrise_residential_upto_3600" in branches(small)
    pumps = [it for it in items(small, "FP", True) if it.system.startswith("Fire Pump")]
    assert len(pumps) == 1 and pumps[0].spec.startswith("50 gpm")
    assert "Table 9.21.e.1" in pumps[0].detail
    large = report(occupancy="business", commercial_outlet_gf_bua_m2=901, **kw)
    assert "lowrise_commercial_outlet_attached_large" in branches(large)
    missing = report(occupancy="business", **kw)
    assert fp_line(missing, "Commercial Outlet GF BUA (Table 9.21.e) - NOT EVALUATED")
    # Not a listed host occupancy: the outlet table does not apply.
    resid = report(occupancy="residential", commercial_outlet_gf_bua_m2=1500, **kw)
    assert "lowrise_commercial_outlet" not in branches(resid)
    # Table 9.21.f.A (p.712) temporary tent: extinguishers only, no generic 9.21.a tier.
    tent = report(occupancy="assembly_c", height_m=7, floors_above_grade=2,
                  ground_floor_bua_m2=1000, plot_area_m2=5000, tent_marquee_kind="temporary")
    assert "lowrise_tent_marquee_extinguishers_only" in branches(tent)
    assert "lowrise_public_" not in branches(tent)
    assert not [it for it in items(tent, "FP", True)
                if it.system.startswith(("Automatic Sprinkler", "Fire Pump", "Hose Reel"))]
    # The inputs reach Building() from the app.
    at = _app_test({**_GEO, **_occ("Business / Office", "business"), "business_group_input": "B", "height_m_input": 7.0,
                    "has_attached_commercial_outlet": True,
                    "commercial_outlet_gf_bua_m2_input": 500.0,
                    "tent_marquee_kind_input": "none"})
    bj = json.loads(at.session_state["_building_json"])
    assert bj["has_attached_commercial_outlet"] is True
    assert bj["commercial_outlet_gf_bua_m2"] == 500.0


# ---------------------------------------------------------------- Scenario B
def test_SCENB_storage_hazard_is_asked_never_defaulted():
    at = _app_test({**_GEO, **_occ("Business / Office", "business"), "business_group_input": "B"})
    at.selectbox(key="scenario_b_occ").set_value("storage_industrial").run()
    assert not at.exception
    hz = at.selectbox(key="scenario_b_storage_hazard")
    assert hz.value is None
    at.button(key="run_scenario_compare").click().run()
    assert any("Scenario B is NOT EVALUATED: select the B storage hazard class" in e.value
               for e in at.error)
    at.selectbox(key="scenario_b_storage_hazard").set_value("OH1").run()
    at.number_input(key="scenario_b_sum_gf_bua").set_value(0.0).run()
    at.button(key="run_scenario_compare").click().run()
    assert any("Scenario B is NOT EVALUATED: enter the B sum of GF BUAs" in e.value
               for e in at.error)


# ---------------------------------------------------------------- label sweep
def test_LABELS_no_tilde_approx_or_section_sign_in_package_files():
    files = ["app.py", "engine.py", "flsc_schema.py", "rules/ch9_fire_protection.yaml"]
    pat = re.compile("[~≈§]")
    hits = []
    for f in files:
        for n, line in enumerate((ROOT / f).read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line):
                hits.append(f"{f}:{n}")
    assert hits == []
