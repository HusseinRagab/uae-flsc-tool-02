"""Phase 3 audit fixes, package ch47 (Ch 4 extinguishers, Ch 5 exit signs, Ch 6
emergency lighting, Ch 7 EVC). One test per finding; values quoted from the
rendered pages of UAE FLSC 2018 (CDGH-OP-25) named in each test.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_phase1_findings import report, items  # noqa: E402


def all_text(r, code):
    return " | ".join(f"{it.system} {it.spec or ''} {it.detail or ''} {it.code_ref or ''}"
                      for it in items(r, code))


def named(r, code, name):
    return [it for it in items(r, code) if it.system == name]


# ------------------------------------------------------------------ Ch 4
def test_CH47_01_class_b_row2_fires_from_occupancy():
    """Table 4.3 row 2 p.375: item 6 MALLS service corridor / cleaning solvent stores;
    item 4 HOTEL linen / waste; foam 9 L AND dry powder 4 kg, 15 m. Row 3 item 2.ii
    p.376 Group A plastics: wheeled foam 50 L."""
    mall = report(occupancy="mall_covered", height_m=12, ground_floor_bua_m2=5000)
    b = named(mall, "FE", "Class B Fire Extinguisher (Foam + Dry Powder) - Mall Areas")
    assert len(b) == 1 and b[0].status == "required"
    assert "row 2 item 6" in b[0].code_ref
    for v in ("Foam Type 9 L", "Dry Powder 2-A, 20-B, C 4 kg", "service corridors", "15 m"):
        assert v in b[0].spec
    hotel = report(occupancy="hotel_a", height_m=18, ground_floor_bua_m2=1000)
    h = named(hotel, "FE", "Class B Fire Extinguisher (Foam + Dry Powder) - Hotel Areas")
    assert len(h) == 1 and "row 2 item 4" in h[0].code_ref and "linen stores" in h[0].spec
    for occ, item in (("education_b", "item 2"), ("healthcare_a", "item 3"),
                      ("mercantile_a", "item 5"), ("storage_industrial", "item 7")):
        r = report(occupancy=occ, height_m=8, ground_floor_bua_m2=1000)
        refs = [it.code_ref for it in items(r, "FE") if "row 2 " + item in (it.code_ref or "")]
        assert refs, occ
    res = report(occupancy="residential", height_m=12)
    assert not [it for it in items(res, "FE") if "Table 4.3 row 2" in (it.code_ref or "")]
    plast = report(occupancy="storage_industrial", height_m=8, ground_floor_bua_m2=1000,
                   has_group_a_plastic_storage=True)
    p = named(plast, "FE", "Class B Wheeled Foam Extinguisher - Group A Plastic Storage / Activity")
    assert len(p) == 1 and "50 L (13 Gal)" in p[0].spec and "row 3 item 2.ii" in p[0].code_ref


def test_CH47_11_class_a_clean_agent_only_for_p374_occupancies():
    """Table 4.3 row 1: p.373 items 1-7 dry powder AND CO2; p.374 items 8-12 dry
    powder OR clean agent, AND CO2."""
    res = report(occupancy="residential", height_m=12)
    a = [it for it in items(res, "FE") if it.system.startswith("Class A")]
    assert len(a) == 1 and "Clean Agent" not in a[0].spec and "AND CO2" in a[0].spec
    assert a[0].page_ref == "p.373"
    mall = report(occupancy="mall_covered", height_m=12, ground_floor_bua_m2=5000)
    m = [it for it in items(mall, "FE") if it.system.startswith("Class A")]
    assert len(m) == 1 and "OR Clean Agent Type 4 kg" in m[0].spec and m[0].page_ref == "p.374"


def test_CH47_12_obsolete_extinguishers_should_not_shall():
    """#2.2.8.1 p.359: 'considered obsolete and should be removed from service and replaced'."""
    r = report(occupancy="business", height_m=10)
    o = named(r, "FE", "Obsolete Extinguisher Types - Removed From Service")
    assert len(o) == 1 and "should be removed" in o[0].spec and o[0].status == "recommended"
    assert "SHALL" not in o[0].spec


def test_CH47_13_fe_text_is_the_printed_text():
    """Table 4.4 item 1.xi p.379 bilingual signage; #3.4.3 serviced once every year;
    Table 4.3 row 4 p.376 item 7 RMU, item 8 switchgear."""
    r = report(occupancy="business", height_m=10, has_rmu_idf_mdf_room=True)
    text = all_text(r, "FE")
    assert "Arabic and English" in text and "once every year" in text
    for gone in ("red background", "ID label at eye level", "NEVER be placed on floor",
                 "Service tag", "registration mark"):
        assert gone not in text, gone
    rmu = named(r, "FE", "Class C Extinguisher - RMU Room")
    assert rmu and rmu[0].code_ref.endswith("row 4 items 7-8")


# ------------------------------------------------------------------ Ch 5
def test_CH47_03_education_a_gets_nursery_strip_line():
    """Table 5.3 item 8.ii p.398 'Nurseries shall be provided with Photoluminescent Exit
    Marking strips as per Table 5.1.4'; Table 1.1 p.48 Group A lists nurseries beside
    kindergartens, so the line is conditional until the nursery box is ticked."""
    name = "Photoluminescent Exit Marking Strips (Nurseries)"
    r = report(occupancy="education_a", height_m=8, ground_floor_bua_m2=800)
    s = named(r, "ES", name)
    assert len(s) == 1 and s[0].status == "conditional" and "8.ii" in s[0].code_ref
    t = report(occupancy="education_a", height_m=8, ground_floor_bua_m2=800, has_nursery_within=True)
    s = named(t, "ES", name)
    assert [x.status for x in s] == ["required"]
    assert not named(report(occupancy="education_b", height_m=8), "ES", name)


def test_CH47_14_floor_proximity_and_distance_wording():
    """Table 5.3 items 6.ii / 11.iii (p.397-398) floor proximity in assembly and hotel;
    Table 5.2 #4 p.395 rated viewing distance or 30 m, whichever is less."""
    r = report(occupancy="business", height_m=10)
    text = all_text(r, "ES")
    assert "all assembly occupancies (Table 5.3 item 6.ii" in text
    assert "all hotel occupancies (Table 5.3 item 11.iii" in text
    assert "rated viewing distance or 30 m, whichever is less" in text
    for gone in ("dance halls", "spaced further than 15 m", "line-of-sight", "~"):
        assert gone not in text, gone


def test_CH47_17_exit_sign_colours_and_spacing():
    """Table 5.1 item 1 p.388: 9.5 mm letter spacing; 'EXIT' matte White on Green;
    running man Green on White, open door background."""
    r = report(occupancy="business", height_m=10)
    s = named(r, "ES", "Exit Sign Letter Size + Bilingual EXIT (English + Arabic)")
    assert len(s) == 1
    for v in ("9.5 mm", "matte White colour on Green background",
              "Green colour on White, open door background"):
        assert v in s[0].spec, v
