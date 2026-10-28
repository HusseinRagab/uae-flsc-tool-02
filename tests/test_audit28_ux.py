"""Fix round 28.10.2026, area "ux": the ease-of-use findings UX-01..UX-27 (except UX-03,
done by the lead after the engine merge), the Ch 8 label findings CH8-05 / CH8-06 /
CH8-10, and the standing rule "a blank never counts as a pass" for the geometry.

Most tests drive the real app script headless (streamlit.testing.v1.AppTest). Code
text in the asserts is read off the pages named in each test (UAE FLSC 2018).
Run with `python -m pytest tests/test_audit28_ux.py`.
"""
import ast
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from flsc_schema import Building  # noqa: E402
from engine import evaluate  # noqa: E402

APP_SRC = (ROOT / "app.py").read_text(encoding="utf-8")
UI_SRC = (ROOT / "ui.py").read_text(encoding="utf-8")
EXPORT_SRC = (ROOT / "export.py").read_text(encoding="utf-8")
TODAY = dt.date.today().isoformat()


# ---------------------------------------------------------------- helpers
def _app(state=None, run=True):
    at_mod = pytest.importorskip("streamlit.testing.v1")
    at = at_mod.AppTest.from_file(str(ROOT / "app.py"), default_timeout=180)
    for k, v in (state or {}).items():
        at.session_state[k] = v
    if run:
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _occ(cat, occ):
    return {"occupancy_chosen": (cat, occ), "occupancy_category_select": cat,
            "occupancy_sub_select": occ}


def _get(at, key, default=None):
    try:
        return at.session_state[key]
    except KeyError:
        return default


WAREHOUSE = {**_occ("Storage / Industrial", "storage_industrial"),
             "height_m_input": 10.0, "floors_above_input": 1, "floors_below_input": 0,
             "ground_bua_input": 4000.0, "gfa_input": 4000.0, "plot_area_input": 8000.0}


def _sidebar_expanders(at) -> dict:
    return {getattr(c, "label", ""): i for i, c in at.sidebar.children.items()
            if type(c).__name__ == "Expander"}


def _docx_text(data: bytes) -> str:
    docx = pytest.importorskip("docx")
    d = docx.Document(io.BytesIO(data))
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            for c in row.cells:
                parts.append(c.text)
    for s in d.sections:
        parts += [p.text for p in s.footer.paragraphs]
    return "\n".join(parts)


def _pdf_text(data: bytes) -> str:
    pypdf = pytest.importorskip("pypdf")
    return "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(io.BytesIO(data)).pages)


def _report(**kw):
    base = dict(occupancy="residential", height_m=45, floors_above_grade=12,
                floors_below_grade=1, ground_floor_bua_m2=800, gross_floor_area_m2=8000,
                plot_area_m2=4000)
    base.update(kw)
    return evaluate(Building(**base))


# ---------------------------------------------------------------- UX-01
def test_UX01_warehouse_stop_draws_the_field_it_asks_for_and_then_evaluates():
    """A stand-alone warehouse was a dead end: the stop named 'Sum of GF BUAs (sidebar:
    FP - Settings)', a field drawn only after the stop. The field is now drawn under the
    storage hazard class, before any stop (#4.1.13, p.695; owner ruling 12.10.2026, Ch9
    Q1), and a filled-in warehouse evaluates with no stop."""
    at = _app({**WAREHOUSE, "storage_hazard_input": "OH2"})
    assert any("sum of GF BUAs" in e.value for e in at.error)
    # The field the stop asks for is on screen in the same run.
    assert at.sidebar.number_input(key="sum_gf_bua_m2_input") is not None
    at.sidebar.number_input(key="sum_gf_bua_m2_input").set_value(4000.0).run()
    assert not at.exception and not at.error
    b = json.loads(at.session_state["_building_json"])
    assert b["occupancy"] == "storage_industrial" and b["sum_gf_bua_m2"] == 4000.0
    assert [m.value for m in at.metric if m.label == "Required systems"] != []


def test_UX01_warehouse_preset_evaluates_without_a_stop():
    at = _app()
    name = next(o for o in at.sidebar.selectbox(key="archetype_preset_select").options
                if o.startswith("Warehouse"))
    at.sidebar.selectbox(key="archetype_preset_select").set_value(name)
    at.sidebar.button[0].click().run()
    assert not at.exception and not at.error, [e.value for e in at.error]
    b = json.loads(at.session_state["_building_json"])
    assert (b["occupancy"], b["hazard_class"], b["sum_gf_bua_m2"]) == (
        "storage_industrial", "OH2", 4000.0)


def test_UX01_hazard_stop_also_keeps_every_storage_input_on_screen():
    at = _app(dict(WAREHOUSE))
    assert any("Select the storage hazard class" in e.value for e in at.error)
    keys = {w.key for w in at.sidebar.checkbox}
    assert {"is_single_tenant_storage", "is_cold_storage", "is_aboveground_tank_storage"} <= keys
    assert at.sidebar.number_input(key="max_unit_area_m2_input") is not None


# ---------------------------------------------------------------- UX-09
def test_UX09_a_stop_keeps_the_whole_sidebar_drawn():
    at = _app({**_occ("Business / Office", "business"), "height_m_input": 12.0,
               "ground_bua_input": 800.0, "gfa_input": 2400.0, "plot_area_input": 2000.0})
    assert any("Select the Business group" in e.value for e in at.error)
    labels = _sidebar_expanders(at)
    for lab in ("💧 FP - Settings (Ch 9)", "💨 SC - Settings (Ch 10)", "⛽ LPG - Settings (Ch 11)"):
        assert lab in labels, lab


# ---------------------------------------------------------------- blank inputs
@pytest.mark.parametrize("key,label", [("ground_bua_input", "Ground-floor BUA"),
                                       ("gfa_input", "Total GFA"),
                                       ("plot_area_input", "Plot area")])
def test_BLANK_geometry_stops_by_name(key, label):
    """Standing rule: a blank never counts as a pass. GF BUA (#4.1.12, p.695), GFA
    (Ch 3 #1.4.6, p.242) and plot area (#4.1.10, p.695) of 0 stop by name."""
    at = _app({**_occ("Residential / Lodging", "residential"), key: 0.0})
    msgs = [e.value for e in at.error]
    assert any(label in m and "Geometry" in m and "never counts as a pass" in m for m in msgs), msgs


def test_BLANK_geometry_infrastructure_and_trucks_are_exempt():
    at = _app({**_occ("Infrastructure", "infrastructure"), "height_m_input": 0.0,
               "ground_bua_input": 0.0, "gfa_input": 0.0, "plot_area_input": 0.0})
    assert not [e for e in at.error if "never counts as a pass" in e.value]
    at = _app({**_occ("Mercantile", "mercantile_c"), "mercantile_c_type_input": "food_truck",
               "height_m_input": 3.0, "floors_above_input": 1, "floors_below_input": 0,
               "ground_bua_input": 12.0, "gfa_input": 12.0, "plot_area_input": 0.0})
    assert not [e for e in at.error if "Plot area" in e.value]


def test_BLANK_every_preset_evaluates_without_a_stop():
    """Presets fill every value they need (parking area / height / levels, the office
    Business Group B, the warehouse hazard and plot GF BUA sum)."""
    at = _app()
    names = [o for o in at.sidebar.selectbox(key="archetype_preset_select").options
             if not o.startswith("Custom")]
    for name in names:
        at.sidebar.selectbox(key="archetype_preset_select").set_value(name)
        at.sidebar.button[0].click().run()
        assert not at.exception, name
        assert not at.error, (name, [e.value for e in at.error])
        b = json.loads(at.session_state["_building_json"])
        if b["has_parking_area"]:
            assert b["parking_area_m2"] > 0 and b["parking_height_m"] is not None \
                and b["parking_basement_levels"] is not None, name


# ---------------------------------------------------------------- UX-02
def test_UX02_print_layout_is_in_session_not_a_new_tab():
    assert "](?print=1)" not in APP_SRC and "st.query_params" not in APP_SRC
    at = _app({"height_m_input": 33.0})
    assert at.toggle(key="print_layout") is not None
    at.toggle(key="print_layout").set_value(True).run()
    assert not at.exception
    # Same session, same building: 33 m (not the 45 m sample), no export column.
    assert json.loads(at.session_state["_building_json"])["height_m"] == 33.0
    assert len(at.main.download_button) == 0
    assert any("display: none" in m.value and "stSidebar" in m.value for m in at.markdown)


# ---------------------------------------------------------------- UX-04
def test_UX04_executive_has_one_governing_line_per_chapter_never_truncated():
    import export
    r = _report(has_fire_pump_room=True)
    rows = export.governing_rows(r)
    codes = [c for c, *_ in rows]
    assert len(codes) == len(set(codes))
    req_chapters = [ch.chapter_code for ch in r.chapters
                    if any(it.status == "required" for b in ch.blocks for it in b.items)]
    assert codes == req_chapters
    by = {c: (s, spec) for c, s, spec, _cite, _n in rows}
    assert by["FP"][0].startswith("Automatic Sprinkler System")
    assert "Fire Pump: 750 gpm @ 6.9 bar" in by["FP"][1] and "Fire Water Tank" in by["FP"][1]
    assert by["FA"][0].startswith("Smoke Detection and Alarm System")
    assert by["FSA"][1] == r.fire_access.extent
    # The specification is printed in full (the old export cut it at 80 / 90 characters).
    data = export.report_to_docx_bytes(r, "executive")
    text = _docx_text(data)
    for _c, system, spec, _cite, _n in rows:
        assert spec in text and system in text
    assert "[:60]" not in EXPORT_SRC and "[:80]" not in EXPORT_SRC and "[:90]" not in EXPORT_SRC


# ---------------------------------------------------------------- UX-05
def test_UX05_flags_cleared_by_villa_are_restored_on_return():
    at = _app({**_occ("Residential / Lodging", "residential")})
    on_before = {k for k in ("has_stairs", "has_elevator", "has_main_electrical_room",
                             "has_main_telephone_room", "has_lift_machine_room",
                             "has_fire_pump_room") if _get(at, k)}
    assert len(on_before) == 6
    at.sidebar.selectbox(key="occupancy_category_select").set_value("Villa").run()
    assert not any(_get(at, k) for k in on_before)
    assert any("Cleared" in c.value and "Stairs" in c.value for c in at.sidebar.caption)
    at.sidebar.selectbox(key="occupancy_category_select").set_value("Residential / Lodging").run()
    assert {k for k in on_before if _get(at, k)} == on_before
    assert any("Restored 6 input(s)" in c.value for c in at.sidebar.caption)


def test_UX05_a_preset_or_a_load_never_restores_an_older_project_s_flags():
    ns = {}
    tree = ast.parse(APP_SRC)
    keep = [n for n in tree.body if isinstance(n, ast.FunctionDef)
            and n.name in ("_incompatible_flags", "_apply_incompatible_flag_reset")]
    keep += [n for n in tree.body if isinstance(n, ast.Assign) and any(
        getattr(t, "id", "") in ("OCC_ONLY_FLAGS", "VILLA_INCOMPATIBLE_FLAGS",
                                 "INCOMPATIBLE_FLAGS_BY_OCC", "ANIMAL_HOUSING_INCOMPATIBLE_FLAGS",
                                 "DAYCARE_B_INCOMPATIBLE_FLAGS", "PETROL_STATION_INCOMPATIBLE_FLAGS",
                                 "MERCANTILE_A_INCOMPATIBLE_FLAGS", "INFRASTRUCTURE_INCOMPATIBLE_FLAGS",
                                 "DAYCARE_C_INCOMPATIBLE_FLAGS") for t in n.targets)]
    keep.sort(key=lambda n: n.lineno)
    exec(compile(ast.Module(body=keep, type_ignores=[]), "app_part", "exec"), ns)
    reset = ns["_apply_incompatible_flag_reset"]
    state = {"has_stairs": True}
    reset("villa_private", state=state)
    assert state["has_stairs"] is False and state["_cleared_flags"] == {"has_stairs": True}
    reset("villa_private", remember=False, state=state)
    reset("residential", remember=False, state=state)
    assert state["has_stairs"] is False and state["_cleared_flags"] == {}


# ---------------------------------------------------------------- UX-06
def test_UX06_sidebar_sections_keep_their_place_when_inputs_appear_or_go():
    """Every expander keeps its position (so an open one stays open) when the
    basements, the depth warning or the occupancy-specific inputs appear or go."""
    base = {**_occ("Residential / Lodging", "residential"), "floors_below_input": 1,
            "basement_bua_input": 0.0, "depth_below_grade_input": 8.0}
    ref = _sidebar_expanders(_app(base))
    for change in ({"floors_below_input": 0}, {"basement_bua_input": 500.0},
                   {"depth_below_grade_input": 3.0}, {"has_robotic_parking": True},
                   {**_occ("Business / Office", "business"), "business_group_input": "B"},
                   {**_occ("Storage / Industrial", "storage_industrial")}):
        got = _sidebar_expanders(_app({**base, **change}))
        common = set(ref) & set(got)
        assert {k: got[k] for k in common} == {k: ref[k] for k in common}, change


# ---------------------------------------------------------------- UX-07
def test_UX07_exports_are_built_on_click_and_do_not_rerun():
    tree = ast.parse(APP_SRC)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and n.func.attr == "download_button"]
    assert len(calls) >= 8
    for c in calls:
        kw = {k.arg: k.value for k in c.keywords}
        assert isinstance(kw.get("on_click"), ast.Constant) and kw["on_click"].value == "ignore"
    exports = [c for c in calls if any(k.arg == "key" and isinstance(k.value, ast.Constant)
                                       and str(k.value.value).startswith("dl_") for k in c.keywords)]
    assert len(exports) == 6
    for c in exports:
        data = next(k.value for k in c.keywords if k.arg == "data")
        assert isinstance(data, ast.Call) and getattr(data.func, "id", "") == "_export_data"
    assert "@st.cache_resource" in APP_SRC and "def _export_store" in APP_SRC


# ---------------------------------------------------------------- UX-08
def test_UX08_assumptions_box_names_sample_preticks_and_defaults():
    at = _app()
    box = " ".join(m.value for m in at.markdown)
    assert "Assumptions used in this report" in box
    assert "Sample building" in box
    assert "Ticked on first load and never changed" in box and "Stairs" in box
    assert "Wet riser: 2 standpipes (the first option" in box
    assert any("Sample building" in i.value for i in at.info)
    # Unticking and re-ticking a box is the user's own choice: it leaves the list.
    at.sidebar.checkbox(key="has_stairs").uncheck().run()
    at.sidebar.checkbox(key="has_stairs").check().run()
    line = next(m.value for m in at.markdown if "Ticked on first load" in m.value)
    assert "Stairs," not in line.split("Ticked on first load")[1].split("\n")[0]


def test_UX08_motor_fuel_group_left_on_its_default_is_listed():
    at = _app({**_occ("Storage / Industrial", "motor_fuel_dispensing"), "height_m_input": 5.0,
               "floors_above_input": 1, "floors_below_input": 0, "ground_bua_input": 300.0,
               "gfa_input": 300.0, "plot_area_input": 2000.0, "_profile_source": "user"})
    box = " ".join(m.value for m in at.markdown)
    assert "Motor fuel dispensing Group A (the first option" in box


# ---------------------------------------------------------------- UX-10
def test_UX10_save_name_follows_the_project_name_until_typed():
    at = _app()
    assert at.session_state["save_as_filename"] == f"project_{TODAY}"
    at.sidebar.text_input(key="project_name_input").input("Tower A - Dubai Marina").run()
    assert at.session_state["save_as_filename"] == f"Tower A - Dubai Marina_{TODAY}"
    at.sidebar.text_input(key="save_as_filename").input("my_copy").run()
    at.sidebar.text_input(key="project_name_input").input("Tower B").run()
    assert at.session_state["save_as_filename"] == "my_copy"


# ---------------------------------------------------------------- UX-11 / UX-12
def test_UX11_UX12_notes_date_revision_inputs_and_status_in_every_export():
    import export
    r = _report(project_name="Tower A", has_parking_area=True, parking_area_m2=900.0)
    meta = {"notes": "Rev B for CD review", "assumptions": ["Wet riser: 2 standpipes"]}
    for kind in ("compact", "detailed", "executive"):
        t = _docx_text(export.report_to_docx_bytes(r, kind, meta=meta))
        assert "Rev B for CD review" in t and "Generated " in t and "FLSC tool revision" in t, kind
        p = _pdf_text(export.report_to_pdf_bytes(r, kind, meta=meta))
        assert "Rev B for CD review" in p and "FLSC tool revision" in p, kind
    det = _docx_text(export.report_to_docx_bytes(r, "detailed", meta=meta))
    assert "INPUTS USED" in det.upper() and "Parking footprint area (m2)" in det
    assert "Parking basement levels" in det and "not entered" in det
    assert "Status" in det and "REQUIRED" in det
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(io.BytesIO(export.report_to_xlsx_bytes(r, meta=meta)))
    assert "Inputs" in wb.sheetnames
    prof = {row[0].value: row[1].value for row in wb["Profile"].iter_rows()}
    assert prof["Project notes"] == "Rev B for CD review" and prof["FLSC tool revision"]
    assert export.export_file_name("Tower A - Dubai", "detailed", "pdf", "2026-10-28") == \
        "Tower_A_-_Dubai_FLSC_detailed_2026-10-28.pdf"
    # A project name with markup characters no longer breaks the PDF.
    assert export.report_to_pdf_bytes(_report(project_name="Tower <A> & B"), "compact")


def test_UX12_detailed_pdf_gives_required_lines_a_status_too():
    import export
    p = _pdf_text(export.report_to_pdf_bytes(_report(), "detailed"))
    assert "Status" in p and "REQUIRED" in p


# ---------------------------------------------------------------- UX-13 / UX-22
def test_UX13_table_view_default_and_UX22_no_match_message():
    at = _app()
    assert at.radio(key="report_view").value == "Table"
    assert "not_required" not in at.multiselect(key="filter_status").value
    assert any("flsc-rtable" in m.value for m in at.markdown)
    at.text_input(key="filter_text").input("zzqqxx-no-such-thing").run()
    assert any("No requirements match 'zzqqxx-no-such-thing'" in i.value for i in at.info)


# ---------------------------------------------------------------- UX-14
def test_UX14_readable_branch_labels_and_rule_ids_behind_a_toggle():
    at = _app()
    strip = next(m.value for m in at.markdown if 'class="flsc-class"' in m.value)
    assert "Table 9.19.B" in strip and "highrise_45_90_small_plot" not in strip
    assert "general rules" in strip                     # FE: no branch row, no empty chip
    caps = " ".join(c.value for c in at.caption)
    assert "**Occupancy:** Residential Group A - Table 1.1 row 5" in caps
    assert "`residential`" not in caps
    at.toggle(key="show_rule_ids").set_value(True).run()
    strip = next(m.value for m in at.markdown if 'class="flsc-class"' in m.value)
    assert "highrise_45_90_small_plot" in strip


# ---------------------------------------------------------------- UX-15 / UX-17
def test_UX15_robotic_parking_with_parking_and_UX17_one_column_rooms():
    src = APP_SRC.split('with st.expander("🅿️ Parking & special rooms"', 1)[1].split(
        'with st.expander("🛗 Various locations', 1)[0]
    assert 'key="has_robotic_parking"' in src
    assert "st.columns" not in src.split("Special rooms checklist", 1)[1]
    es = APP_SRC.split('with st.expander("🚪 ES - Settings', 1)[1].split("# ----- EL (Ch 6)", 1)[0]
    assert 'key="has_robotic_parking"' not in es and 'key="theater_cinema_kind_input"' in es


# ---------------------------------------------------------------- UX-16
def test_UX16_every_input_has_help_without_tilde_approx_or_section_sign():
    tree = ast.parse(APP_SRC)
    widgets = {"checkbox", "number_input", "selectbox", "radio", "text_input", "text_area",
               "multiselect", "toggle", "file_uploader", "button", "download_button"}
    missing = []
    for n in ast.walk(tree):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in widgets and getattr(n.func.value, "id", "") == "st"):
            if "help" not in {k.arg for k in n.keywords}:
                missing.append(n.lineno)
    assert missing == []
    for m in re.finditer(r'help="([^"]*)"', APP_SRC):
        assert not re.search("[~≈§]", m.group(1))


def test_UX16_generated_help_cites_the_rule_lines_each_box_switches_on():
    ns = {"_yaml": __import__("yaml"), "Path": Path, "__file__": str(ROOT / "app.py")}
    tree = ast.parse(APP_SRC)
    keep = []
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(getattr(t, "id", "") in (
                "_HELP_BANNED", "_SPECIAL_ROOM_WIDGETS", "_VARIOUS_LOCATION_WIDGETS",
                "_EQUIPMENT_WIDGETS") for t in n.targets):
            keep.append(n)
        elif isinstance(n, ast.FunctionDef) and n.name in ("_rule_refs_by_field", "_h"):
            n.decorator_list = []
            keep.append(n)
    exec(compile(ast.Module(body=keep, type_ignores=[]), "app_part", "exec"), ns)
    for tbl in ("_SPECIAL_ROOM_WIDGETS", "_VARIOUS_LOCATION_WIDGETS", "_EQUIPMENT_WIDGETS"):
        for key, _label, lead in ns[tbl]:
            h = ns["_h"](lead, key)
            assert re.search(r"p\.\d{3}", h), key
            assert not re.search("[~≈§]", h), key
    h = ns["_h"]("", "has_anesthetizing_room")
    assert "Table 8.14 item 2, p.509" in h and "Table 9.30.A, p.752" in h


# ---------------------------------------------------------------- CH8-05 / 06 / 10 labels
def test_CH8_labels_drop_conditions_the_tables_do_not_print():
    """p.512 Table 8.15 item 1 KITCHEN HOOD and item 7 COOLING TOWERS print no burner
    count and no combustibility; p.510-511 Table 8.14 items 21-25 (laundry, storage room,
    pantry, pump room, garbage room) print no occupancy, pump type or chute condition."""
    for old in ('"Cooling towers - combustible (G)"', '"Commercial kitchen 3+ burners (A)"',
                '"Residential laundry / storage rooms"', '"Pantries (business/commercial)"',
                '"Fire pump room"', '"Garbage chute"'):
        assert old not in APP_SRC, old
    for new in ('"Cooling towers (G)"', '"Commercial kitchen with cooking hood (A)"',
                '"Laundry / storage rooms"', '"Pantries"', '"Pump room (fire pump or other)"',
                '"Garbage room / chute"'):
        assert new in APP_SRC, new
    eq = APP_SRC.split('("has_cooling_towers", "Cooling towers (G)",', 1)[1].split("),", 1)[0]
    assert "Table 8.15 item 7" in eq and "Table 9.31.G" in eq and "non-combustibility" in eq
    kit = APP_SRC.split('("has_commercial_kitchen", "Commercial kitchen with cooking hood (A)",', 1)[1].split("),", 1)[0]
    assert "Table 8.15 item 1" in kit and "Table 9.31.A" in kit and "3 or more burners" in kit


# ---------------------------------------------------------------- UX-18 / UX-20 / UX-21 / UX-24
def test_UX18_UX20_UX21_UX24_layout_pin_and_dead_code():
    assert 'initial_sidebar_state="auto"' in APP_SRC
    assert "@media (max-width: 640px)" in UI_SRC and "#exports" in APP_SRC
    for src in (APP_SRC, UI_SRC, EXPORT_SRC):
        assert "use_container_width" not in src
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert "streamlit==1.66.1" in req
    assert "_excerpt_around_page" not in APP_SRC and "code_excerpts" not in APP_SRC
    assert "--flsc-muted:   #475569;" in UI_SRC


# ---------------------------------------------------------------- UX-23 / UX-25 / UX-19
def test_UX23_change_is_surfaced_and_UX25_short_fire_access_value():
    at = _app()
    assert [m.value for m in at.metric if m.label == "Fire access (perimeter)"] == ["1/6"]
    at.sidebar.number_input(key="height_m_input").set_value(95.0).run()
    exp = [e.label for e in at.expander if e.label.startswith("What changed")]
    assert exp and "added" in exp[0]
    req = next(m for m in at.metric if m.label == "Required systems")
    assert req.delta not in (None, "")
    assert any("live only in this browser tab" in c.value for c in at.caption)


# ---------------------------------------------------------------- UX-26 / UX-27
def test_UX26_advisories_are_not_styled_as_stops_and_UX27_required_in_label():
    at = _app({**_occ("Residential / Lodging", "residential"), "height_m_input": 120.0,
               "floors_above_input": 35, "gas_system_radio": "LPG tanks (aboveground / roof / podium)",
               "has_lpg_tank_roof_mounted": True})
    assert not at.error
    assert any("PROHIBITED" in w.value and "Advisory" in w.value for w in at.warning)
    assert 'with st.expander(f"⚠ Sanity checks — {len(_warns)} warning(s)", expanded=False)' in APP_SRC
    assert '"Parking height above the fire access level (m) (required)"' in APP_SRC
    assert '"Parking basement levels (required)"' in APP_SRC
