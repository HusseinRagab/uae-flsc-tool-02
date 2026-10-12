"""Phase 3 audit fixes, package ch10 (Ch 10 smoke control): one test per finding.

Code values in the asserts were read off the rendered pages of UAE FLSC 2018
(CDGH-OP-25): Tables 10.19-10.27 (p.855-866), Annexure 1 FAQ #27-#29 (p.1282),
Ch 2 #2.9.4.a (p.220). Run with `python -m pytest tests/test_phase3_ch10.py`.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_phase1_findings import items, report  # noqa: E402


def sc(r, status=None):
    return [it for it in items(r, "SC") if status is None or it.status == status]


def names(r, status=None):
    return [it.system for it in sc(r, status)]


def one(r, prefix):
    hits = [it for it in sc(r) if it.system.startswith(prefix)]
    assert len(hits) == 1, [(h.system, h.status) for h in hits]
    return hits[0]


BASE = dict(ground_floor_bua_m2=1000)


# ------------------------------------------------------------ CH10-05
def test_CH10_05_long_corridor_applies_to_hotels_and_other_occupancies():
    """Table 10.27 item 4 (p.866): '... such as in covered mercantile spaces, staff
    accommodations, labour accommodations, residential buildings, office buildings'."""
    for occ in ("hotel_a", "hostel", "healthcare_b", "assembly_b"):
        r = report(occupancy=occ, height_m=20, corridor_length_m=80, **BASE)
        line = one(r, "Enclosed Corridor Natural Ventilation")
        assert line.status == "required" and "Section 2.15" in line.spec, occ
    # 60 m is not 'in excess of 60 m'; at 23 m the building is highrise (R1).
    assert not [n for n in names(report(occupancy="hotel_a", height_m=20, corridor_length_m=60,
                                        **BASE)) if n.startswith("Enclosed Corridor Natural")]
    assert not [n for n in names(report(occupancy="hotel_a", height_m=23, corridor_length_m=80,
                                        **BASE)) if n.startswith("Enclosed Corridor Natural")]
    # Hospitals, schools and malls keep their own corridor rows.
    for occ in ("healthcare_a", "education_b", "mall_covered"):
        r = report(occupancy=occ, height_m=12, corridor_length_m=80, **BASE)
        assert not [n for n in names(r) if n.startswith("Enclosed Corridor Natural")], occ


# ------------------------------------------------------------ CH10-14
def test_CH10_14_clinics_are_not_hospitals_and_hospital_lines_do_not_contradict():
    """Table 10.21 item 1.i (p.858) names Hospitals; Table 10.27 item 1 (p.865)."""
    r = report(occupancy="healthcare_b", height_m=12, **BASE)
    assert one(r, "Stair Pressurization").system == "Stair Pressurization NOT Required (default)"
    assert not [n for n in names(r) if n.startswith("Corridor & Open-spaces")]
    r = report(occupancy="healthcare_a", height_m=12, **BASE)
    stair = one(r, "Stair Pressurization")
    assert stair.status == "required" and "1.vi" in stair.code_ref
    corridor = [it for it in sc(r) if "Corridor" in it.system]
    assert [(c.system, c.status) for c in corridor] == [
        ("Corridor & Open-spaces Smoke Management", "required")]
    assert "two smoke zones" in corridor[0].detail


# ------------------------------------------------------------ CH10-15
def test_CH10_15_lowrise_school_stair_not_mandatory_one_corridor_line():
    """Table 10.27 item 2.2.i (p.865): 'The stair pressurization is not mandatory if
    building is not Highrise.'"""
    r = report(occupancy="education_b", height_m=12, **BASE)
    stair = one(r, "Stair Pressurization")
    assert stair.status == "not_required" and "2.2" in stair.code_ref
    corridor = [it for it in sc(r) if "Corridor" in it.system]
    assert [(c.system, c.status) for c in corridor] == [
        ("Enclosed Corridor / Circulation Smoke Management", "required")]
    # Highrise school: Table 10.20 stair only, no 'not mandatory' line.
    r = report(occupancy="education_b", height_m=30, **BASE)
    assert not [n for n in names(r) if "NOT mandatory (school" in n]
    assert "Stair Pressurization" in names(r, "required")


# ------------------------------------------------------------ CH10-16
def test_CH10_16_assembly_purge_on_hall_area_and_cinema_theatre_split():
    """Table 10.27 items 8 (cinemas, #2.13, 6 ACH), 9-13 (halls having area more than
    2000 m2, #2.13) and 14 (theaters, #2.9) on p.866; item 2.3 (schools) on p.865."""
    purge = "Assembly Hall / Auditorium / Sports Hall / Stadium Smoke Purge"
    # 800 m2 hall in a 2500 m2 building with a stage: no purge line.
    r = report(occupancy="assembly_b", height_m=12, gross_floor_area_m2=2500,
               assembly_area_m2=800, has_permanent_stages=True, **BASE)
    assert not [n for n in names(r) if n.startswith(purge) or "Assembly Hall Smoke" in n]
    r = report(occupancy="assembly_b", height_m=12, gross_floor_area_m2=5000,
               assembly_area_m2=2500, **BASE)
    line = one(r, purge)
    assert line.status == "required" and "Section 2.13" in line.spec and "6 air changes" in line.spec
    # Hall area not entered in a building over 2000 m2: named, not defaulted to GFA.
    r = report(occupancy="assembly_b", height_m=12, gross_floor_area_m2=2500, **BASE)
    assert one(r, "Assembly Hall Smoke Purge (> 2000 m2) - NOT EVALUATED").status == "conditional"
    assert not [n for n in names(r) if n.startswith(purge)]
    # Cinema vs theatre.
    kw = dict(occupancy="assembly_b", height_m=12, gross_floor_area_m2=1500,
              has_theater_cinema=True, **BASE)
    r = report(theater_cinema_kind="cinema", **kw)
    assert one(r, "Cinema Smoke Purge").spec.startswith("Dedicated mechanical smoke purge per Section 2.13")
    assert not [n for n in names(r) if n.startswith("Theatre")]
    r = report(theater_cinema_kind="theatre", **kw)
    assert "Section 2.9" in one(r, "Theatre Smoke Management").spec
    assert not [n for n in names(r) if n.startswith("Cinema")]
    r = report(**kw)
    assert one(r, "Cinema / Theatre Smoke Control - NOT EVALUATED").status == "conditional"
    # School: stage OR area more than 2000 m2 (item 2.3).
    r = report(occupancy="education_b", height_m=12, has_permanent_stages=True, **BASE)
    assert "Section 2.13" in one(r, "School Sports Hall / Auditorium Smoke Purge").spec
    r = report(occupancy="education_b", height_m=12, has_auditorium_within=True, **BASE)
    assert one(r, "School Sports Hall / Auditorium Smoke Purge - NOT EVALUATED").status == "conditional"


def test_CH10_16_app_saves_and_validates_theatre_kind():
    """BRIEF rule 5: the new input is saved and checked on Load."""
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    keep = [n for n in tree.body
            if (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_SCENARIO_LIMITS"
                                                 for t in n.targets))
            or (isinstance(n, ast.FunctionDef) and n.name == "_invalid_scenario_values")]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "app_guard", "exec"), ns)
    check = ns["_invalid_scenario_values"]
    assert "Theatre / cinema kind = 'opera'" in " ".join(check({"theater_cinema_kind_input": "opera"}))
    for v in (None, "cinema", "theatre", "both"):
        assert check({"theater_cinema_kind_input": v}) == []
    assert '"theater_cinema_kind_input"' in src
    assert 'theater_cinema_kind=' in src


# ------------------------------------------------------------ CH10-17
def test_CH10_17_tunnel_tiers_on_length_one_line():
    """Table 10.25 (p.862): road tunnels less than 90 m natural ventilation acceptable,
    jet fan not mandatory; more than 90 m jet fan per Section 2.14."""
    kw = dict(occupancy="business", height_m=10, has_tunnel=True, **BASE)
    r = report(tunnel_length_m=50, **kw)
    line = one(r, "Tunnel Smoke Management")
    assert line.status == "required" and "less than 90 m" in line.system
    assert "jet fan system shall not be mandatory" in line.spec
    r = report(tunnel_length_m=200, **kw)
    line = one(r, "Tunnel Smoke Management")
    assert line.status == "required" and "Section 2.14" in line.spec
    r = report(tunnel_length_m=90, **kw)
    assert one(r, "Tunnel Smoke Management").status == "conditional"
    r = report(**kw)
    assert "NOT EVALUATED" in one(r, "Tunnel Smoke Management").system
    r = report(tunnel_kind="cable", tunnel_length_m=50, **kw)
    assert "Section 2.17" in one(r, "Tunnel Smoke Management").spec


# ------------------------------------------------------------ CH10-27
def test_CH10_27_basement_count_trigger_cites_faq_29_and_2_9_4_a():
    """Table 10.22 items 1.i and 3.i (p.859) print only 'depth of more than 7 m'.
    FAQ #29.i (p.1282): basement-only stairs of more than 2 levels shall be pressurized.
    Ch 2 #2.9.4.a (p.220): Fire Lift for High Depth with more than 2 basements."""
    r = report(occupancy="business", height_m=20, floors_below_grade=3,
               depth_below_grade_m=6.5, **BASE)
    stair = one(r, "Stair Pressurization (basement")
    assert stair.status == "required" and "FAQ #29.i" in stair.code_ref
    lift = one(r, "Firefighting Lift")
    assert lift.status == "required" and lift.code_ref == "Ch 2 #2.9.4.a"
    assert "Table 10.22 item 3" in lift.detail and "not triggered" in lift.detail
    # depth more than 7 m: the Table 10.22 rows, once each.
    r = report(occupancy="business", height_m=20, floors_below_grade=3,
               depth_below_grade_m=10.5, **BASE)
    assert "Table 10.22" in one(r, "Stair Pressurization (basement").code_ref
    assert one(r, "Firefighting Lift").system == "Firefighting Lift (depth more than 7 m)"
    # depth not entered with basements: named, not assumed.
    r = report(occupancy="residential", height_m=14, floors_below_grade=2, **BASE)
    assert one(r, "Basement Stair / Firefighting Lift by Depth - NOT EVALUATED").status == "conditional"


# ------------------------------------------------------------ CH10-28
def test_CH10_28_mall_and_parking_stair_citations():
    """Table 10.24 (p.861) has no stair item; Table 10.21 item 1.i (p.858) excludes
    malls from the exemption. Table 10.22 is 'other than Parking usage' (p.859)."""
    r = report(occupancy="mall_covered", height_m=12, gross_floor_area_m2=20000,
               ground_floor_bua_m2=10000)
    stair = one(r, "Stair Pressurization")
    assert stair.code_ref == "Ch 10, #3.3 / Table 10.21 item 1.i"
    assert "inference" in stair.detail
    assert not [n for n in names(r) if n.startswith("Mall Stair")]
    r = report(occupancy="parking_enclosed", height_m=12, floors_below_grade=3, **BASE)
    stair = one(r, "Stair Pressurization (basement parking")
    assert stair.code_ref == "Annexure 1 FAQ #29.i" and "Table 10.22" not in stair.code_ref


# ------------------------------------------------------------ CH10-35
def test_CH10_35_stack_effect_options_are_considered_not_mandatory():
    """Table 10.19 item 1.iv (p.855): 'the designer shall consider the following options'."""
    r = report(occupancy="residential", height_m=120, **BASE)
    st = one(r, "Stair Pressurization (multi-injection")
    text = st.detail + st.spec
    assert "shall consider" in text and "mandatory" not in text.lower()


# ------------------------------------------------------------ CH10-38
def test_CH10_38_mall_atrium_line_only_with_atrium():
    """Table 10.24 item 2 (p.861): the atrium row applies where an atrium exists."""
    kw = dict(occupancy="mall_covered", height_m=12, gross_floor_area_m2=20000,
              ground_floor_bua_m2=10000)
    assert not [n for n in names(report(**kw)) if "Atrium" in n]
    assert "Atrium Smoke Management System" in names(report(has_atrium=True, **kw), "required")


# ------------------------------------------------------------ CH10-39
def test_CH10_39_parking_stair_evaluated_against_height():
    """Table 10.23 items 1.iv / 2.2.ii / 2.3.ii (p.860): more than 23 m; FAQ #27 (p.1282)
    and ruling R1 at 23.0 m."""
    for occ in ("parking_enclosed", "parking_open"):
        r = report(occupancy=occ, height_m=12, gross_floor_area_m2=3000, **BASE)
        assert one(r, "Stair Pressurization").status == "not_required", occ
        for h in (23.0, 30.0):
            r = report(occupancy=occ, height_m=h, gross_floor_area_m2=3000, **BASE)
            assert one(r, "Stair Pressurization (parking").status == "required", (occ, h)
            assert not [it for it in sc(r) if it.status == "conditional"
                        and it.system.startswith("Stair Pressurization")]


# ----------------------------------------------- phase 1 fixes still hold
def test_CH10_03_23_m_is_highrise_for_stairs():
    """Ruling R1; FAQ #27 (p.1282): 23 m or more."""
    assert "Stair Pressurization" in names(report(occupancy="residential", height_m=23.0, **BASE),
                                           "required")
    r = report(occupancy="residential", height_m=22.9, **BASE)
    assert one(r, "Stair Pressurization").status == "not_required"
