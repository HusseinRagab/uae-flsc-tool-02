"""Phase 2 Ch 3 owner answers (decision cards, 12.10.2026): Ch3 Q1-Q9.

One test per answer (test_CH3_Qn_...), with negative checks where useful. Code
values were read off the rendered pages in audit/shots: Ch 2 p.213, 214, 215, 217,
219, 220; Ch 3 p.283, 285-288, 293-295, 323.
"""
import ast
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import engine  # noqa: E402
from fire_access import compute_fire_access  # noqa: E402
from flsc_schema import Building  # noqa: E402
from occupant_load import TABLE_3_13_ROWS, mall_factor  # noqa: E402
from test_phase1_findings import items, report  # noqa: E402


def names(r, code, status=None):
    return [it.system for it in items(r, code) if status is None or it.status == status]


def one(r, code, prefix):
    hits = [it for it in items(r, code) if it.system.startswith(prefix)]
    assert len(hits) == 1, [(h.system, h.status) for h in hits]
    return hits[0]


def _master_exits(area, factor):
    """Master f6ae7bb: floor(GFA / factor) on the whole GFA, then Table 3.14."""
    ol = max(1, math.floor(area / factor))
    return 4 if ol > 1000 else 3 if ol >= 500 else 2


# ------------------------------------------------------------------ Q1
def test_CH3_Q1_largest_storey_area_drives_table_3_14_blank_is_whole_gfa():
    """#4.3.1 p.288, #4.1.3 p.283. 30 floors x 1,500 m2 residential (18.6 m2, row 6.i)."""
    kw = dict(occupancy="residential", height_m=95, floors_above_grade=30,
              gross_floor_area_m2=45000, ground_floor_bua_m2=1500)
    ol = report(**kw).occupant_load
    # Blank: the whole GFA (master behaviour), said so in the line; 45,000 / 18.6 -> 2,420.
    assert ol.storey_occupant_load == 2420 and ol.min_exits == 4
    assert "whole GFA" in ol.exit_ref and "Ch3 Q1" in ol.exit_ref
    assert "at least" not in ol.exit_ref and "up to" not in ol.exit_ref
    # Never less onerous than master when the input is blank.
    assert ol.min_exits >= _master_exits(45000, 18.6)
    # Entered: 1,500 / 18.6 -> 81 -> 2 exits; the total is not used.
    ol = report(largest_storey_area_m2=1500, **kw).occupant_load
    assert ol.storey_occupant_load == 81 and ol.min_exits == 2 and ol.occupant_load == 2420
    assert "largest storey OL 81" in ol.exit_ref and "Ch3 Q1" in ol.exit_ref


def test_CH3_Q1_largest_storey_area_settles_villa_table_3_27_item_2_iii():
    """Table 3.27 item 2.iii p.323: a floor over 400 m2 -> two primary means of escape."""
    kw = dict(occupancy="villa_private", height_m=7, floors_above_grade=2,
              gross_floor_area_m2=800, ground_floor_bua_m2=300)
    two = "Two Primary Means of Escape - Floor over 400 m2 (Table 3.27 item 2.iii)"
    r = report(**kw)                              # unknown: conditional check line
    assert [it.status for it in items(r, "MOE") if it.system == two] == ["conditional"]
    r = report(largest_storey_area_m2=450, **kw)  # entered over 400: required
    assert [it.status for it in items(r, "MOE") if it.system == two] == ["required"]
    r = report(largest_storey_area_m2=380, **kw)  # entered 400 or less: no line
    assert two not in names(r, "MOE")


# ------------------------------------------------------------------ Q2
def test_CH3_Q2_blank_per_use_areas_take_densest_table_3_13_row():
    """Table 3.13 p.285-287: densest row of the occupancy."""
    cases = {"business": (3.7, "row 2.iii"), "assembly_c": (0.28, "row 1.v"),
             "healthcare_a": (9.3, "row 4.iii"), "residential": (18.6, "row 6.i"),
             "mercantile_a": (2.8, "row 13.i")}
    for occ, (f, row) in cases.items():
        ol = report(occupancy=occ, height_m=4, floors_above_grade=1,
                    gross_floor_area_m2=1000, ground_floor_bua_m2=1000).occupant_load
        assert ol.factor_m2_per_person == f and row in ol.factor_ref, occ
        assert ol.occupant_load == math.ceil(round(1000 / f, 9)), occ
    # Storage / industrial: rows 15-18 -> 9.3 m2 (industrial), never the 27.9 m2 storage row.
    ol = report(occupancy="storage_industrial", height_m=8, floors_above_grade=1,
                gross_floor_area_m2=2790, ground_floor_bua_m2=2790,
                hazard_class="OH1").occupant_load
    assert ol.factor_m2_per_person == 9.3 and ol.occupant_load == 300


def test_CH3_Q2_per_use_areas_sum_of_rounded_up_loads():
    """#1.4.5 p.242, #4.1.2 p.283: each use rounded up, then added."""
    ol = report(occupancy="business", height_m=4, floors_above_grade=1,
                gross_floor_area_m2=1100, ground_floor_bua_m2=1100,
                use_areas=[{"row": "2.i", "area_m2": 1000},     # 107.5 -> 108
                           {"row": "13.ii", "area_m2": 100}]    # 35.7 -> 36
                ).occupant_load
    assert ol.occupant_load == 144 and ol.min_exits == 2
    assert "row 2.i: 1,000 m2 / 9.3 m2 = 108" in ol.note and "Ch3 Q2" in ol.note
    # An unknown row is refused by name, not evaluated, no exit count.
    ol = report(occupancy="business", height_m=4, floors_above_grade=1,
                gross_floor_area_m2=1000, use_areas=[{"row": "99.x", "area_m2": 1000}]
                ).occupant_load
    assert not ol.evaluated and ol.min_exits == 0 and "'99.x'" in ol.note


def test_CH3_Q2_proxy_occupancies_block_moe_until_per_use_areas():
    """Table 3.13 has no row for these: MOE not evaluated, no 2-exit minimum stated."""
    for occ in ("mixed_multiple", "motor_fuel_dispensing", "infrastructure",
                "high_depth_underground", "low_depth_underground"):
        r = report(occupancy=occ, height_m=10, floors_above_grade=3,
                   gross_floor_area_m2=6000, ground_floor_bua_m2=2000)
        ol = r.occupant_load
        assert not ol.evaluated and ol.min_exits == 0 and ol.occupant_load == 0, occ
        assert "minimum 2" not in ol.exit_ref.lower() and "not evaluated" in ol.exit_ref, occ
        blk = one(r, "MOE", "Means of Egress Not Evaluated")
        assert blk.status == "required" and "No exit count is stated" in blk.spec, occ
    # With per-use areas the occupancy is evaluated.
    r = report(occupancy="mixed_multiple", height_m=10, floors_above_grade=3,
               gross_floor_area_m2=6000, ground_floor_bua_m2=2000,
               use_areas=[{"row": "13.ii", "area_m2": 2000}, {"row": "6.i", "area_m2": 4000}])
    ol = r.occupant_load
    assert ol.evaluated and ol.occupant_load == 715 + 216 and ol.min_exits == 3
    assert not [n for n in names(r, "MOE") if n.startswith("Means of Egress Not Evaluated")]
    assert one(r, "MOE", "Occupant Load by Actual Use").status == "required"


def test_CH3_Q2_app_saves_and_validates_per_use_inputs():
    """BRIEF rule 5: save keys, _SCENARIO_LIMITS minimum 0, load validation."""
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    keep = [n for n in tree.body
            if (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_SCENARIO_LIMITS"
                                                 for t in n.targets))
            or (isinstance(n, ast.FunctionDef) and n.name == "_invalid_scenario_values")]
    ns = {}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "app_guard", "exec"), ns)
    check = ns["_invalid_scenario_values"]
    bad = " ".join(check({"use_area_m2_0": -5, "use_area_row_1": "99.x",
                          "use_area_count_input": 11, "largest_storey_area_m2_input": -1,
                          "mall_gla_m2_input": "big", "building_volume_m3_input": -2}))
    for frag in ("Per-use area 1 = -5", "'99.x'", "Number of per-use areas = 11",
                 "Largest storey area = -1", "Mall gross leasable area = 'big'",
                 "Building volume = -2"):
        assert frag in bad, frag
    assert check({"use_area_row_0": "2.i", "use_area_m2_0": 100.0,
                  "use_area_count_input": 1}) == []
    for key in ("largest_storey_area_m2_input", "mall_gla_m2_input", "use_area_count_input",
                "building_volume_m3_input", "is_waterfront", "is_theme_park",
                "tower_setback_over_30m", "*USE_AREA_KEYS"):
        assert f'"{key}"' in src or key in src, key
    assert set(TABLE_3_13_ROWS) >= {"1.v", "2.iii", "14", "21"}


# ------------------------------------------------------------------ Q3
def test_CH3_Q3_mall_factor_from_gla_full_increments():
    """Table 3.13 row 14 p.287: 2.8 below 14,000 m2; 3.3 + 0.1 per FULL 1,290 m2; max 5.1."""
    assert mall_factor(13999)[0] == 2.8
    assert mall_factor(14000)[0] == 3.3
    assert mall_factor(15289)[0] == 3.3          # not a full increment yet
    assert mall_factor(15290)[0] == 3.4
    assert mall_factor(37219)[0] == 5.0
    assert mall_factor(37220)[0] == 5.1
    assert mall_factor(80000)[0] == 5.1
    kw = dict(occupancy="mall_covered", height_m=10, floors_above_grade=2,
              gross_floor_area_m2=30000, ground_floor_bua_m2=15000)
    ol = report(**kw).occupant_load               # blank GLA = GFA, labelled
    assert ol.factor_m2_per_person == 4.5 and "GFA used as the GLA" in ol.factor_ref
    ol = report(mall_gla_m2=20000, **kw).occupant_load   # 6,000 / 1,290 -> 4 full -> 3.7
    assert ol.factor_m2_per_person == 3.7 and "GLA entered" in ol.factor_ref
    assert ol.occupant_load == math.ceil(30000 / 3.7) and ol.evaluated
    ol = report(mall_gla_m2=12000, **kw).occupant_load
    assert ol.factor_m2_per_person == 2.8


# ------------------------------------------------------------------ Q4
def test_CH3_Q4_table_2_7_overlap_takes_three_quarter_perimeter():
    """Table 2.7 p.215: '85,201 m3 to 113,600 m3' 1/2 and '113,001 m3 to 170,400 m2' 3/4."""
    def ext(vol):
        b = Building(occupancy="storage_industrial", height_m=10, floors_above_grade=1,
                     ground_floor_bua_m2=10000, building_volume_m3=vol)
        return compute_fire_access(b, sprinklered=True)
    assert ext(113000).extent == "1/2 perimeter"
    s = ext(113300)
    assert s.extent == "3/4 perimeter" and "Ch3 Q4" in s.extent_ref
    s = ext(113601)
    assert s.extent == "3/4 perimeter" and "Ch3 Q4" not in s.extent_ref
    # Not sprinklered: Table 2.6 has no overlap; 113,300 m3 stays 3/4 there too.
    b = Building(occupancy="storage_industrial", height_m=10, floors_above_grade=1,
                 ground_floor_bua_m2=10000, building_volume_m3=113300)
    assert compute_fire_access(b, sprinklered=False).extent == "3/4 perimeter"


# ------------------------------------------------------------------ Q5
def test_CH3_Q5_building_volume_input_and_labelled_fallback():
    """#2.8.8.a / #2.8.9.a p.215: gross cubical extent. Table 2.6 (not sprinklered)."""
    kw = dict(occupancy="storage_industrial", height_m=12, floors_above_grade=1,
              gross_floor_area_m2=5000, ground_floor_bua_m2=5000)
    s = compute_fire_access(Building(**kw), sprinklered=False)   # 60,000 m3 fallback
    assert s.extent == "1/2 perimeter"
    assert "fallback" in s.extent_ref and "60,000 m3" in s.extent_ref
    s = compute_fire_access(Building(building_volume_m3=30000, **kw), sprinklered=False)
    assert s.extent == "1/4 perimeter" and "entered" in s.extent_ref
    assert "fallback" not in s.extent_ref


# ------------------------------------------------------------------ Q6
def test_CH3_Q6_site_flags_print_required_lines_only_when_ticked():
    """Table 2.8 p.217; Table 2.5 p.214; #2.9.3.a p.219; #2.9.4.a p.220; #2.8.6.b p.213."""
    base = dict(occupancy="business", height_m=40, floors_above_grade=10,
                gross_floor_area_m2=10000, ground_floor_bua_m2=1000)
    r = report(**base)
    for n in ("Waterfront property fire access", "Theme park fire access",
              "Tower set back more than 30 m"):
        assert not [x for x in names(r, "FSA") if x.startswith(n)], n
    assert not [it for it in items(r, "FSA") if it.status == "conditional"]
    r = report(is_waterfront=True, tower_setback_over_30m=True, **base)
    wf = one(r, "FSA", "Waterfront property fire access")
    assert wf.status == "required" and "Table 2.3 and Table 2.4" in wf.spec
    assert one(r, "FSA", "Tower set back").status == "required"
    r = report(occupancy="villa_commercial", height_m=7, floors_above_grade=2,
               gross_floor_area_m2=600, ground_floor_bua_m2=300, is_waterfront=True)
    assert "60 m" in one(r, "FSA", "Waterfront property fire access").spec
    # Theme park: Table 2.5 extent, ECC, and a Fire Lift only when multi storey.
    tp = dict(occupancy="assembly_a", height_m=12, gross_floor_area_m2=6000,
              ground_floor_bua_m2=3000, is_theme_park=True)
    r = report(floors_above_grade=2, **tp)
    assert one(r, "FSA", "Theme park fire access").status == "required"
    assert r.fire_access.extent == "3/4 perimeter" and "Table 2.5" in r.fire_access.extent_ref
    assert "amusement park" in one(r, "FSA", "Emergency Command Centre").detail
    assert "multi storey amusement park" in one(r, "FSA", "Fire Lift").detail
    r = report(floors_above_grade=1, **tp)
    assert "Fire Lift" not in names(r, "FSA")
    # Tower box ticked below 23 m: stated not applicable, not required.
    r = report(occupancy="business", height_m=20, floors_above_grade=5,
               gross_floor_area_m2=5000, ground_floor_bua_m2=1000, tower_setback_over_30m=True)
    assert one(r, "FSA", "Tower set back").status == "not_required"


# ------------------------------------------------------------------ Q7
def test_CH3_Q7_villas_get_tables_3_1_3_2_3_4_not_3_14_or_3_15_a():
    """#5.6.1 p.323: Table 3.27 along with all other sections; it prevails on conflict."""
    for occ in ("villa_private", "villa_commercial"):
        r = report(occupancy=occ, height_m=7, floors_above_grade=2,
                   gross_floor_area_m2=600, ground_floor_bua_m2=300)
        req = names(r, "MOE", "required")
        for n in ("Means of Egress - General Performance", "Door Assembly Minimums (Table 3.2)",
                  "Stair Geometry (Ch 3, #3.3)"):
            assert n in req, (occ, n)
        prec = one(r, "MOE", "Villa: General Ch 3 Items")
        assert "Table 3.27 prevails" in prec.spec and "#5.6.1" in prec.code_ref
        assert "p.255" in prec.detail and "Ch3 Q7" in prec.detail
        assert "Number of Means of Egress (Table 3.14)" not in names(r, "MOE"), occ
        assert not [n for n in names(r, "MOE") if n.startswith("Exit Remoteness")], occ
        assert not r.occupant_load.evaluated and r.occupant_load.min_exits == 0


# ------------------------------------------------------------------ Q8
def test_CH3_Q8_table_3_16_prints_one_named_column():
    """Table 3.16 row 2.i p.293: S 30 / 15 / 91 m, NS 23 / 6.1 / 61 m."""
    b = Building(occupancy="business", height_m=12, floors_above_grade=3,
                 gross_floor_area_m2=3000, ground_floor_bua_m2=1000)
    rules = engine.load_rules("ch3_means_of_egress.yaml")

    def travel(spr):
        ch = engine.evaluate_moe(b, rules, sprinklered=spr)
        (t,) = [it for blk in ch.blocks for it in blk.items
                if it.system == "Travel / Dead-end / Commonpath (Business)"]
        return t
    s, ns = travel(True), travel(False)
    assert s.spec.startswith("Column S (sprinklered)") and "travel 91 m" in s.spec
    assert "61 m" not in s.spec and "NS" not in s.spec
    assert ns.spec.startswith("Column NS (non-sprinklered)") and "travel 61 m" in ns.spec
    assert "91 m" not in ns.spec
    assert "Column S" in s.detail and "R8" in s.detail and "Ch3 Q8" in s.detail
    # The engine uses building_sprinklered (the R8 test).
    r = engine.evaluate(b)
    t = one(r, "MOE", "Travel / Dead-end / Commonpath (Business)")
    assert t.spec == (s if engine.building_sprinklered(b) else ns).spec
    # Enclosed parking: one Table 3.15.b travel line, the one for the Ch 9 result.
    p = Building(occupancy="parking_enclosed", height_m=12, floors_above_grade=3,
                 gross_floor_area_m2=9000, ground_floor_bua_m2=3000)
    ch = engine.evaluate_moe(p, rules, sprinklered=False)
    got = [it.system for blk in ch.blocks for it in blk.items
           if it.system.startswith("Travel Distance (Enclosed Parking")]
    assert got == ["Travel Distance (Enclosed Parking - non-sprinklered)"]


# ------------------------------------------------------------------ Q9
def test_CH3_Q9_ch10_lift_not_mandatory_only_where_2_9_4_a_does_not_require_one():
    """#2.9.4.a p.220: highrise 23 m or more, more than 2 basements, malls, multi storey
    amusement parks. Never both 'Fire Lift' required and 'NOT mandatory'."""
    nm = "Firefighting Lift (NOT mandatory)"
    cases = [
        (dict(occupancy="mall_covered", height_m=10, floors_above_grade=2,
              gross_floor_area_m2=20000, ground_floor_bua_m2=10000), True),
        (dict(occupancy="residential", height_m=12, floors_above_grade=4, floors_below_grade=3,
              gross_floor_area_m2=7000, ground_floor_bua_m2=1000), True),
        (dict(occupancy="assembly_a", height_m=12, floors_above_grade=2,
              gross_floor_area_m2=6000, ground_floor_bua_m2=3000, is_theme_park=True), True),
        (dict(occupancy="residential", height_m=12, floors_above_grade=4,
              gross_floor_area_m2=4000, ground_floor_bua_m2=1000), False),
    ]
    for kw, lift in cases:
        r = report(**kw)
        fsa_lift = "Fire Lift" in names(r, "FSA", "required")
        assert fsa_lift is lift, kw
        assert (nm in names(r, "SC")) is (not lift), kw
        assert Building(**kw).requires_fire_lift_2_9_4 is lift
