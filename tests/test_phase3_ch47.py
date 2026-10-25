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


# ------------------------------------------------------------------ Ch 6
def el_system_types(r):
    return [it for it in items(r, "EL") if it.status == "required" and
            ("Central Battery" in it.system or it.system.startswith(("Monitored", "Stand-alone")))]


def test_CH47_07_offices_and_retail_get_one_system_type():
    """Table 6.5 p.419 items 11-12 are Business / Mercantile GROUP C; Table 1.1 p.48 offices
    are Business Group B, p.50 Mercantile Group C = kiosks / food trucks. Re-pointed
    13.10.2026 (owner ruling P4 Q1): the group is an input, so the Group C prompt is gone
    and a Business building with no group is NOT EVALUATED by name."""
    for kw, h in ((dict(occupancy="business", business_group="B"), 10),
                  (dict(occupancy="mercantile_a"), 8),
                  (dict(occupancy="business", business_group="A"), 18)):
        r = report(height_m=h, ground_floor_bua_m2=1500, **kw)
        t = el_system_types(r)
        assert [x.system for x in t] == ["Monitored Self-Contained EL (Section 3.3)"], (kw, t)
        assert not [it for it in items(r, "EL") if it.system.startswith("Stand-alone")]
    ne = [it for it in items(report(occupancy="business", height_m=10), "EL")
          if it.system.endswith("NOT EVALUATED")]
    assert len(ne) == 1 and ne[0].status == "required" and "P4 Q1" in ne[0].detail
    hi = report(occupancy="business", height_m=40)
    assert [x.system for x in el_system_types(hi)] == [
        "Central Battery (Section 3.2) OR Monitored Self-Contained (Section 3.3) Emergency Lighting"]


def test_CH47_08_fire_rated_el_wiring_only_for_central_battery():
    """Table 6.2 #8.i p.414 central battery wiring 2 hour fire rated; Table 6.3 #7.i p.416
    monitored luminaires to central monitoring unit not required to be fire rated."""
    low = report(occupancy="residential", height_m=12)
    assert not [it for it in items(low, "EL") if "Cable Fire Rating" in it.system]
    mon = el_system_types(low)[0]
    assert "not be required to be fire rated" in mon.detail
    sup = report(occupancy="residential", height_m=120)
    cb = el_system_types(sup)[0]
    assert "2 hour fire rated, throughout" in cb.detail and "#8.i" in cb.detail
    assert "EN 50200 (930" not in all_text(sup, "EL")


def test_CH47_09_el_inspection_intervals_as_printed():
    """Table 6.7 p.422 item 2.vi 15 minutes; Table 6.8 p.423 monthly 30 seconds, annual
    minimum 3 hours, batteries replaced every 4 years."""
    r = report(occupancy="business", height_m=10)
    a = named(r, "EL", "EL Acceptance Tests + Periodic Inspection")
    assert len(a) == 1
    for v in ("15-minute load test", "30 seconds", "minimum of 3 hours", "every 4 years"):
        assert v in a[0].spec, v
    assert "6-monthly" not in a[0].detail and "LED indicator" not in a[0].detail
    assert a[0].code_ref.startswith("Ch 6, #6.1 / Table 6.7")


def test_CH47_15_el_citations():
    """Table 6.1 sits under #3.1 (p.408, item 4 on p.410)."""
    r = report(occupancy="business", height_m=10)
    g = named(r, "EL", "Emergency Lighting - General Performance Specs (Table 6.1)")[0]
    assert g.code_ref == "Ch 6, #3.1 / Table 6.1" and g.page_ref == "p.408, p.410"
    p = named(r, "EL", "EL Proximity Rule (within 2m)")[0]
    assert p.code_ref.startswith("Ch 6, #3.1 / Table 6.1 item 1.v-vii")
    assert "item 5/2" not in all_text(report(occupancy="business", height_m=30), "EL")


# Table 6.1.a / 6.1.b p.410, entered a second time from the page image (double entry):
# H: (D1, D2, D3, D4, D5) in m.
SPACING_A = {"2.5": ("2.7", "7.2", "1.5", "4.6", "3.65"), "3": ("2.5", "7.3", "1.6", "4.7", "3.6"),
             "4": ("2.1", "7.5", "1.7", "4.8", "3.45"), "6": ("2", "5.3", "1.8", "3.7", "3.3")}
SPACING_B = {"2.5": ("2.5", "8.5", "2.3", "7.4", "4.95"), "3": ("2.5", "9", "1.6", "8", "6.25"),
             "4": ("2.6", "9.8", "2.3", "8.6", "3.6"), "6": ("2.4", "10.3", "1.6", "9.5", "3")}


def test_CH47_18_spacing_tables_spare_capacity_and_single_system():
    """Tables 6.1.a / 6.1.b p.410; Table 6.3 #4.ii p.416 5% spare capacity; #4.2 p.419."""
    r = report(occupancy="residential", height_m=40)
    sp = named(r, "EL", "EL Luminaire Spacing - Minimum Guideline (Tables 6.1.a / 6.1.b)")
    assert len(sp) == 1
    d = sp[0].detail
    a_part, b_part = d.split("Table 6.1.b")[0], d.split("Table 6.1.b")[1]
    for part, table in ((a_part, SPACING_A), (b_part, SPACING_B)):
        for h, row in table.items():
            assert f"{h} m = " + " / ".join(row) + " m" in part, (h, row)
    assert "5% spare capacity" in all_text(r, "EL")
    one = named(r, "EL", "One Centralized Emergency Lighting System for the Entire Facility (#4.2)")
    assert len(one) == 1 and one[0].status == "required"


def test_CH47_19_villa_basement_from_basement_count():
    """Table 6.5 p.419 items 9-10 'required for basements, if any'; item 14 stand-alone."""
    r = report(occupancy="villa_private", height_m=6, floors_below_grade=1, basement_bua_m2=0)
    b = named(r, "EL", "Stand-alone Self-Contained EL (basement only)")
    assert len(b) == 1 and b[0].status == "required"
    none = report(occupancy="villa_private", height_m=6, floors_below_grade=0, basement_bua_m2=0)
    assert not named(none, "EL", "Stand-alone Self-Contained EL (basement only)")


# ------------------------------------------------------------------ Ch 7
def test_CH47_04_sleeping_area_audibility_wherever_evc_required():
    """Table 7.1 #4.4 p.434: 'Voice messages in sleeping areas shall be 75 dB measured at
    the pillow level ... (dBA)'."""
    name = "Sleeping Area Audibility (75 dB at pillow level)"
    for occ in ("residential", "hostel", "healthcare_a"):
        r = report(occupancy=occ, height_m=40)
        s = named(r, "EVC", name)
        assert len(s) == 1 and s[0].status == "required" and "pillow level" in s[0].spec, occ
    det = report(occupancy="detention_a", height_m=10)
    assert [x.status for x in named(det, "EVC", name)] == ["required"]
    office = report(occupancy="business", height_m=40)
    assert [x.status for x in named(office, "EVC", name)] == ["conditional"]
    assert not named(report(occupancy="business", height_m=10), "EVC", name)


def test_CH47_05_strobes_speakers_zones_two_way_wiring_and_heights():
    """Table 7.1 #5-#6 p.434; Table 7.2 #4-#5 p.438."""
    r = report(occupancy="hotel_a", height_m=10)
    req = {it.system: it for it in items(r, "EVC", required_only=True)}
    assert "flashers or strobe light" in req[
        "Speakers with Flashers / Strobe Light (basements, plant rooms, noisy industrial areas)"].spec
    assert "dedicated, listed, approved and tested" in req["EVC Speakers - Dedicated, Listed, Approved"].spec
    assert "Table 7.1 item 6" in req["Voice Evacuation Signalling Zones"].code_ref
    assert "2 hour fire rated" in req["Two-way Telephone Circuits + Wiring (2 hour fire rated)"].spec
    h = req["Two-way Telephone Appliance / Jack Mounting Heights"].spec
    for v in ("910-1680 mm", "760 mm", "1220 mm"):
        assert v in h, v


def test_CH47_open_yard_does_not_take_warehouse_evc():
    """Table 7.3 item 9 is warehouses/factories over 5,000 m2. Group U open-yard
    storage has no building envelope, so the warehouse EVC row must not also fire."""
    kw = dict(occupancy="storage_industrial", height_m=10, floors_above_grade=1,
              ground_floor_bua_m2=4000, gross_floor_area_m2=6000, plot_area_m2=8000,
              hazard_class="LH")
    yard = report(is_open_yard_storage=True, **kw)
    assert yard.chapter("EVC").selected_branch == "evc_open_yard"
    assert not [it for it in items(yard, "EVC")
                if it.source_rule == "evc_storage_industrial_large"]
    assert not [it for it in items(yard, "EVC")
                if it.system.startswith("Emergency Voice Evacuation or Communication System")]
    assert not [it for it in items(yard, "EVC")
                if it.system.startswith("Two-way Telephone Communication System")]
    assert not any("General Specifications" in blk.title for blk in yard.chapter("EVC").blocks)
    nr = [it for it in items(yard, "EVC") if it.source_rule == "evc_open_yard"]
    assert nr and nr[0].status == "not_required"
    tall = report(is_open_yard_storage=True, occupancy="storage_industrial",
                  height_m=25, floors_above_grade=6, ground_floor_bua_m2=2500,
                  gross_floor_area_m2=2500, plot_area_m2=8000, hazard_class="LH")
    assert tall.chapter("EVC").selected_branch == "evc_open_yard"
    assert not [it for it in items(tall, "EVC")
                if it.source_rule in ("evc_highrise", "evc_storage_industrial_large")]
    small = report(is_open_yard_storage=True, occupancy="storage_industrial",
                   height_m=10, floors_above_grade=1, ground_floor_bua_m2=2500,
                   gross_floor_area_m2=3000, plot_area_m2=5000, hazard_class="LH")
    assert small.chapter("EVC").selected_branch == "evc_open_yard"
    plain = report(**kw)
    req = [it for it in items(plain, "EVC")
           if it.source_rule == "evc_storage_industrial_large"
           and it.system.startswith("Emergency Voice Evacuation or Communication System")]
    assert req and req[0].status == "required"


def test_CH47_16_evc_labels_as_printed():
    """Table 7.1 #4.4 p.434 (no 'door closed'); Table 8.1 #14.2 p.459 15 s / 180 s;
    Table 8.13 p.502 240 s; ambient levels are 'for information'."""
    hotel = all_text(report(occupancy="hotel_a", height_m=10), "EVC")
    assert "door closed" not in hotel and "hotel override 120 s" not in hotel
    assert "within 15 seconds" in hotel and "180 seconds" in hotel and "240 seconds" in hotel
    asm = all_text(report(occupancy="assembly_b", height_m=10), "EVC")
    edu = all_text(report(occupancy="education_b", height_m=10), "EVC")
    assert "ambient design level" not in asm + edu
    assert "for information" in asm and "for information" in edu
