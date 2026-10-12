"""Phase 3 audit fixes, package ch11 (audit 12.10.2026, slice CH10):
Ch 11 LPG, Ch 15 accessibility, Ch 19 emergency action plan, Annexure 2.

One test per finding. Code values in the asserts were read off the rendered
pages in audit/shots (p.884-930 Ch 11, p.1097-1119 Ch 15, p.1243-1246 Ch 19,
p.1284-1286 Annexure 2, p.279 Ch 3).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_phase1_findings import report, items  # noqa: E402
from submission_checklist import build_submission_checklist  # noqa: E402

LPG_YAML = (ROOT / "rules" / "ch11_lpg.yaml").read_text(encoding="utf-8")
BASE = dict(ground_floor_bua_m2=1000, plot_area_m2=3000)


def lpg(r):
    return items(r, "LPG")


def get(r, code, prefix):
    out = [it for it in items(r, code) if it.system.startswith(prefix)]
    assert len(out) == 1, [(x.system, x.status) for x in items(r, code)]
    return out[0]


def names(r, code="LPG"):
    return [it.system for it in items(r, code)]


def text(r, code="LPG"):
    return " | ".join(f"{it.system} {it.spec or ''} {it.detail or ''}" for it in items(r, code))


# ------------------------------------------------------------------ Ch 11
def test_CH10_06_aboveground_tank_fixed_water_spray_no_exemption():
    for h in (12, 40):
        r = report(occupancy="residential", height_m=h, has_lpg_tanks=True, **BASE)
        fp = get(r, "LPG", "Tank Fire Protection - Fixed Water Spray System")
        assert fp.status == "required" and "item 5" in fp.code_ref
        assert "Exempt only if" not in fp.detail and "no exemption is applied" in fp.detail


def test_CH10_07_tank_project_gets_table_11_4_items():
    r = report(occupancy="residential", height_m=40, has_lpg_tanks=True, **BASE)
    shafts = get(r, "LPG", "Dedicated Fire-Rated LPG Shafts")
    assert shafts.spec.startswith("2 hour")
    assert "Pipe-in-Pipe Containment Arrangement" in names(r)
    fill = get(r, "LPG", "Fill Line and Filling Point")
    assert "7.6 m" in fill.spec and "1 m from finished ground level" in fill.spec
    fence = get(r, "LPG", "Tank Fencing and Barricades")
    assert "1.8 m high" in fence.spec and "1.2 m width" in fence.spec
    assert "800 mm x 600 mm" in get(r, "LPG", "LPG Warning Sign").spec
    low = report(occupancy="residential", height_m=12, has_lpg_tanks=True, **BASE)
    assert get(low, "LPG", "Dedicated Fire-Rated LPG Shafts").spec.startswith("1 hour")
    # a tank project still selects the aboveground branch first
    assert r.chapter("LPG").selected_branch == "lpg_aboveground_tank"


def test_CH10_08_cylinder_prohibition_and_indoor_occupancy_limit():
    r = report(occupancy="business", height_m=12, has_gas_cylinders_villa=True, **BASE)
    first = lpg(r)
    ban = get(r, "LPG", "Cylinder Installations Not Allowed in New / Modified Buildings")
    assert "#2.2.4" in ban.code_ref and "#2.2.5" in ban.spec
    base = [b for b in r.chapter("LPG").blocks if b.title.startswith("LPG - Base")][0]
    assert base.items[0].system == ban.system
    indoor = report(occupancy="business", height_m=12, has_gas_cylinders_villa=True,
                    has_lpg_cylinders_indoor=True, **BASE)
    assert "Indoor LPG Cylinders Not Allowed for this Occupancy (#2.2.6, #2.4.2.1)" in names(indoor)
    assert "Indoor LPG Cylinder Installation (Table 11.2)" not in names(indoor)
    res = report(occupancy="residential", height_m=12, has_gas_cylinders_villa=True,
                 has_lpg_cylinders_indoor=True, **BASE)
    assert "Indoor LPG Cylinder Installation (Table 11.2)" in names(res)
    assert first


def test_CH10_09_flame_effect_audience_distance_quantity_and_sprinkler_precondition():
    r = report(occupancy="business", height_m=12, has_lpg_flame_effect=True, **BASE)
    fx = get(r, "LPG", "Flame Effect LPG Installation (Table 11.12)")
    assert "6 m away from the audience and stage" in fx.spec
    assert "within 3 m of the audience" in fx.spec
    assert "exits/doors" not in fx.spec
    q = get(r, "LPG", "Flame Effect LPG Quantity")
    assert "maximum 24 kg" in q.spec and "6 m from each other" in q.spec and "single day" in q.spec
    pre = get(r, "LPG", "Indoor Flame Effect Shows")
    assert "#3.2.2" in pre.code_ref and "NOT allowed here" in pre.detail   # lowrise business: no sprinklers
    spr = report(occupancy="business", height_m=40, has_lpg_flame_effect=True, **BASE)
    assert "NOT allowed here" not in (get(spr, "LPG", "Indoor Flame Effect Shows").detail or "")


def test_CH10_10_roof_tank_location_and_construction_rules():
    r = report(occupancy="residential", height_m=40, has_lpg_tanks=True,
               has_lpg_tank_roof_mounted=True, **BASE)
    loc = get(r, "LPG", "Roof Tank Location Prohibitions").spec
    assert "helipad" in loc and "cat ladders" in loc and "lift machine room roof" in loc
    con = get(r, "LPG", "Roof Tank Building Construction").spec
    assert "Type I (443 or 332) or Type II (222)" in con and "filled with water" in con
    assert "Table 11.7 #5" in get(r, "LPG", "Roof Tank Fire Protection").code_ref


def test_CH10_11_warning_sign_and_9_kg_extinguisher():
    villa = report(occupancy="villa_private", height_m=6, ground_floor_bua_m2=300,
                   has_gas_cylinders_villa=True)
    assert "800 mm x 600 mm" in get(villa, "LPG", "LPG Warning Sign").spec
    assert "minimum capacity 9 kg" in get(villa, "LPG", "Portable Fire Extinguisher").spec
    infra = report(occupancy="hotel_a", height_m=55, has_gas_infra_connection=True, **BASE)
    ext = get(infra, "LPG", "Portable Fire Extinguisher")
    assert "Table 11.11 #6.ii" in ext.code_ref
    assert "LPG Warning Sign (minimum 800 mm x 600 mm)" in names(infra)


def test_CH10_18_roof_tank_drops_at_grade_items_and_gates_mall_line():
    r = report(occupancy="residential", height_m=40, has_lpg_tanks=True,
               has_lpg_tank_roof_mounted=True, **BASE)
    n = names(r)
    assert "Maximum Quantity (72,000 Gal per location)" not in n
    assert "Aboveground LPG Tank Installation" not in n
    assert "Mall 4,000 Gal Allowance" not in n
    assert "2000 Gal aggregate" in get(r, "LPG", "Roof-Mounted LPG Tank Maximum Quantity").spec
    # Re-pointed: owner ruling 12.10.2026, P3 Ch11 Q4 replaced the conditional line with a
    # not_required "none declared" line (tests/test_phase3_answers_a1.py).
    assert get(r, "LPG", "Aboveground (at-grade) LPG Tanks").status == "not_required"
    mall = report(occupancy="mall_covered", height_m=20, has_lpg_tanks=True,
                  has_lpg_tank_roof_mounted=True, ground_floor_bua_m2=10000, plot_area_m2=30000)
    m = get(mall, "LPG", "Mall 4,000 Gal Allowance")
    assert m.status == "conditional" and "15 m apart" in m.spec


def test_CH10_19_underground_tank_no_aboveground_cap_fire_protection_not_mandatory():
    r = report(occupancy="residential", height_m=30, has_lpg_tanks=True,
               has_lpg_tank_underground_mounded=True, **BASE)
    n = names(r)
    assert "Maximum Quantity (72,000 Gal per location)" not in n
    assert "Tank Fire Protection - Fixed Water Spray System" not in n
    assert "180,000 Gal" in get(r, "LPG", "Maximum Quantity (Underground/Mounded)").spec
    fp = get(r, "LPG", "Underground / Mounded Tank Fire Protection")
    assert fp.status == "not_required" and "Table 11.9 #5" in fp.code_ref
    # Ch 9 keeps its conditional line for any aboveground tank (CH9D-09)
    ch9 = [it for it in items(r, "FP") if it.system.startswith("LPG Tanks")]
    assert len(ch9) == 1 and ch9[0].status == "conditional"


def test_CH10_20_asme_reduction_is_15_m_to_3_m_with_table_11_10_b():
    r = report(occupancy="residential", height_m=30, has_lpg_tanks=True,
               has_lpg_tank_underground_mounded=True, **BASE)
    asme = get(r, "LPG", "ASME Container Reduction Allowance")
    assert "50%" not in asme.spec
    assert "up to 30,000 Gal" in asme.spec and "3 m separation" in asme.spec and "15 m" in asme.spec
    assert "within 4.6 m" in asme.detail and "7.6 m to 30 m" in asme.detail


def test_CH10_21_indoor_cylinders_follow_table_11_2():
    tanks = report(occupancy="residential", height_m=12, has_lpg_tanks=True, **BASE)
    assert not [x for x in names(tanks) if "Indoor Cylinder" in x]
    r = report(occupancy="residential", height_m=12, has_gas_cylinders_villa=True,
               has_lpg_cylinders_indoor=True, **BASE)
    ign = get(r, "LPG", "Indoor Cylinder - No Ignition Source within 1.5 m")
    assert ign.status == "required" and "1.5 m" in ign.spec
    cook = get(r, "LPG", "Indoor Cylinder Compartment - 3 m")
    assert cook.status == "recommended"
    t = text(r)
    assert "1-hr" not in t and "mechanical ventilation" not in t.lower() and "150 mm" not in t
    assert "30 cm above finished floor" in get(r, "LPG", "Indoor Cylinder Gas Detection").spec


def test_CH10_22_villa_cylinder_detection_where_internal_pipes_are():
    r = report(occupancy="villa_private", height_m=6, ground_floor_bua_m2=300,
               has_gas_cylinders_villa=True)
    det = get(r, "LPG", "Gas-Leak Detection where the Internal Pipes")
    assert "internal LPG/CNG pipes and fittings" in det.spec and "Table 11.1 #6" in det.code_ref
    assert "at least 3 m" in det.detail


def test_CH10_23_prdp_items_follow_table_11_11():
    r = report(occupancy="hotel_a", height_m=55, has_gas_infra_connection=True, **BASE)
    prdp = get(r, "LPG", "PRDP (Pressure Reducing Distribution Panel) Tapping")
    t = text(r)
    assert "double-block-and-bleed" not in t and "vault" not in t
    assert "2 hour" in prdp.spec and "3(4)x1.5 mm" in prdp.spec
    assert "30 cm above finished floor" in get(r, "LPG", "PRDP Stage 2 Kitchen Gas Detection").spec


def test_CH10_26_app_highrise_tank_message_names_preferred_locations():
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "must be on the roof or podium only" not in src
    assert "#2.5.1.2 (p.900)" in src and "up to \"\n            \"90 m only (#2.5.1.3)" in src
    assert "6 m to exits, 3 m to ignition" not in src
    assert "dedicated room with mechanical ventilation" not in src


def test_CH10_29_no_dead_ch11_citations():
    assert not re.search(r"Section 2\.6|#2\.1\.5|#2\.1\.7", LPG_YAML)


def test_CH10_30_ch11_references_corrected():
    r = report(occupancy="business", height_m=12, has_lpg_flame_effect=True, **BASE)
    assert get(r, "LPG", "Flame Effect LPG Installation").code_ref.startswith("Ch 11, #3 ")
    ug = report(occupancy="residential", height_m=30, has_lpg_tanks=True,
                has_lpg_tank_underground_mounded=True, **BASE)
    assert get(ug, "LPG", "Underground / Mounded LPG Tank Installation").page_ref == "p.915-917"
    res = report(occupancy="residential", height_m=12, has_gas_cylinders_villa=True,
                 has_lpg_cylinders_indoor=True, **BASE)
    assert get(res, "LPG", "Indoor Cylinder Quantity Limits").page_ref == "p.898"
    ft = report(occupancy="business", height_m=12, has_lpg_cylinders_food_truck=True, **BASE)
    assert get(ft, "LPG", "Food Truck LPG Cylinder Installation").page_ref == "p.899"
    insp = get(ug, "LPG", "Inspection + Maintenance Checklist").spec
    assert "Table 11.14 #2.ii" in insp and "shut-off valves + gauges" not in insp


def test_CH10_31_ch11_wording():
    ft = report(occupancy="business", height_m=12, has_lpg_cylinders_food_truck=True, **BASE)
    t = text(ft)
    assert "exactly" not in t and "annual" not in t.lower()
    assert "maximum 2 cylinders of 12 kg" in get(ft, "LPG", "Food Truck LPG Cylinder Installation").spec
    assert "NOC shall be obtained only after inspection" in t
    tank = report(occupancy="residential", height_m=12, has_lpg_tanks=True, **BASE)
    assert "vertical plane beneath overhead electric power lines that are over 600 volts" in \
        get(tank, "LPG", "Overhead Power Line Clearance").spec
    roof = report(occupancy="residential", height_m=40, has_lpg_tanks=True,
                  has_lpg_tank_roof_mounted=True, **BASE)
    sep = get(roof, "LPG", "Roof-Mounted LPG Tank Separation Distances")
    assert "stricter" not in (sep.detail or "") and "501-1000 Gal 4.5 m" in sep.spec


def test_CH10_32_stage_1_and_stage_2_detection_for_every_tank_installation():
    for kw in (dict(has_lpg_tanks=True), dict(has_gas_infra_connection=True)):
        r = report(occupancy="residential", height_m=12, **kw, **BASE)
        st = get(r, "LPG", "Two-Stage Gas Detection")
        assert st.status == "required" and "15% LEL" in st.detail and "30% LEL" in st.detail
        assert "LARGE" not in text(r)


def test_CH10_36_flame_effect_only_no_no_gas_line():
    r = report(occupancy="business", height_m=12, has_lpg_flame_effect=True, **BASE)
    assert "No Gas System Present" not in names(r)
    assert "Gas-Leak Detection + Interfaced ESV (Universal)" not in names(r)


def test_CH10_39_roof_super_highrise_line_only_above_90_m():
    r = report(occupancy="residential", height_m=40, has_lpg_tanks=True,
               has_lpg_tank_roof_mounted=True, **BASE)
    assert not [x for x in names(r) if "Super-Highrise" in x or "Higher than 90 m" in x]
    tall = report(occupancy="residential", height_m=95, has_lpg_tanks=True,
                  has_lpg_tank_roof_mounted=True, **BASE)
    assert get(tall, "LPG", "Roof LPG Tank Not Allowed - Building Higher than 90 m").status == "required"


# ------------------------------------------------------------------ Ch 19
def test_CH10_12_assembly_point_and_drills_for_every_non_villa_building():
    r = report(occupancy="business", height_m=12, **BASE)
    ap = get(r, "EAP", "Assembly point")
    assert ap.status == "required" and "at least 15 m" in ap.spec and "height of the building" in ap.spec
    dr = get(r, "EAP", "Drills and training")
    assert dr.status == "required" and "every 6 months" in dr.spec
    assert "48 hours" in dr.detail and "1 hour" in dr.detail
    asm = report(occupancy="assembly_b", height_m=12, **BASE)
    assert "twice every 6 months" in get(asm, "EAP", "Drills and training").spec
    edu = report(occupancy="education_b", height_m=12, **BASE)
    assert "once every 6 months" in get(edu, "EAP", "Drills and training").spec
    hosp = report(occupancy="healthcare_a", height_m=12, **BASE)
    assert get(hosp, "EAP", "Evacuation strategy").spec.startswith("Partial evacuation")
    assert "minimum 4 personnel" in get(hosp, "EAP", "Emergency response team").spec


def test_CH10_34_ch19_citations():
    r = report(occupancy="hotel_a", height_m=30, **BASE)
    refs = {it.system: (it.code_ref, it.page_ref) for it in items(r, "EAP")}
    assert refs["Assembly point"] == ("Ch 19, Table 19.1 item 8", "p.1243")
    assert refs["Drills and training"] == ("Ch 19, Table 19.2", "p.1245-1248")
    assert refs["Written Emergency Action Plan (Table 19.1)"][1] == "p.1234-1237"
    assert "\u00a7" not in str(refs) and "p.1230" not in str(refs)


# ------------------------------------------------------------------ Ch 15
def test_CH10_13_two_foldable_wheelchairs_required():
    r = report(occupancy="business", height_m=12, **BASE)
    wc = get(r, "ACC", "Foldable wheelchairs")
    assert wc.status == "required" and "minimum of 2" in wc.spec and wc.code_ref == "Ch 15, #5.2.8"


def test_CH10_24_area_of_refuge_conditional_per_ch3_3_8_1():
    r = report(occupancy="residential", height_m=40, **BASE)
    ref = get(r, "ACC", "Area of refuge")
    assert ref.status == "conditional" and ref.code_ref.startswith("Ch 3, #3.8.1")
    assert "760 mm x 1220 mm" in ref.detail and "0.28" not in ref.detail
    assert "45 minute doors" in ref.detail and "1-hr fire barrier" in ref.detail and "1200 mm" in ref.detail
    assert "#3.5" not in ref.code_ref and "occupants of 3 floors" in ref.detail


def test_CH10_33_ch15_citations_and_stair_content():
    r = report(occupancy="business", height_m=12, **BASE)
    pages = {it.source_rule: it.page_ref for it in items(r, "ACC")}
    assert pages["acc_parking"] == "p.1097" and pages["acc_stair"] == "p.1098"
    assert pages["acc_av_signs"] == "p.1099-1100"
    st = get(r, "ACC", "Accessible stair features").spec
    assert "tactile" not in st and "51 mm" in st and "108 lux" in st and "braille" in st
    villa = report(occupancy="villa_private", height_m=6, ground_floor_bua_m2=300)
    assert items(villa, "ACC")[0].page_ref == "p.1090"


# ------------------------------------------------------------ Annexure 2
def _cl(r):
    return {pkg: (note, req) for pkg, note, req in build_submission_checklist(r)}


def test_CH10_25_checklist_follows_annexure_2_files_and_letters():
    r = report(occupancy="business", height_m=12, **BASE)
    cl = _cl(r)
    assert cl["Clarifying letter of LPG / natural gas usage (Table A2.1 #5.i.i)"][1] is True
    assert "no LPG" in cl["Clarifying letter of LPG / natural gas usage (Table A2.1 #5.i.i)"][0]
    assert cl["Fire access road layout (Table A2.1 #5.ii.a)"][1] is True
    assert cl["Material / activity / storage method letter (Table A2.1 #5.i.h)"][1] is False
    assert "4 to 6 separate files" in cl["Number of files (Table A2.1 #2.i)"][0]
    assert "50 MB" in cl["File format and size (Table A2.1 #1)"][0]
    assert not [k for k in cl if k.startswith(("Voice Evacuation", "Exit Sign layout", "Fire Extinguisher layout"))]
    st = report(occupancy="storage_industrial", height_m=10, **BASE)
    assert _cl(st)["Material / activity / storage method letter (Table A2.1 #5.i.h)"][1] is True
