"""UAE FLSC 2018 Chapter 2 - Fire Service Vehicle and Personnel Accessibility.

Values are from the printed pages: Table 2.1 (p.206), #2.6 and Table 2.2 (p.207),
#2.8.3 and #2.8.4 (p.212), #2.8.5 / #2.8.6 and Tables 2.3 / 2.4 (p.213), #2.8.7 and
Table 2.5 (p.214), #2.8.8 / #2.8.9 and Tables 2.6 / 2.7 (p.215), #2.8.10 and Table
2.8 (p.217), #2.9.3 (p.219), #2.9.4 (p.220).

Sprinkler protection is the Ch 9 result for the building (engine passes it): the
building is "sprinkler protected" when its Ch 9 table row requires an automatic
sprinkler system.
"""
from __future__ import annotations
from typing import List, Optional, Tuple
from flsc_schema import Building, ChapterReport, FireAccessSummary, Requirement, SectionBlock

_MALLS = ("mall_covered", "mall_open", "mall_mixed")
_ORDER = ["1/6", "1/4", "1/2", "3/4", "Whole"]

# (extent text, short ref, code_ref, page_ref)
Extent = Tuple[str, str, str, str]


def _rank(extent: str) -> int:
    return next((i for i, k in enumerate(_ORDER) if k in extent), -1)


def _footprint_m2(b: Building) -> Tuple[float, str]:
    """Gross floor area of the building footprint projected onto ground level
    (#2.8.5.a / #2.8.6.a, p.213)."""
    if b.ground_floor_bua_m2 and b.ground_floor_bua_m2 > 0:
        return float(b.ground_floor_bua_m2), "ground-floor BUA"
    if b.basement_bua_m2 and b.basement_bua_m2 > 0 and (
            b.occupancy in ("high_depth_underground", "low_depth_underground")):
        return float(b.basement_bua_m2), "basement BUA (underground building)"
    if b.gross_floor_area_m2 and b.floors_above_grade:
        return (float(b.gross_floor_area_m2) / max(1, b.floors_above_grade),
                "GFA / floors above grade (no ground-floor BUA entered)")
    return 0.0, "no area entered"


def _volume_m3(b: Building, footprint: float) -> Tuple[float, str]:
    """Gross cubical extent (#2.8.8.a / #2.8.9.a, p.215): the entered building volume,
    else footprint x building height, labelled as the fallback (owner ruling
    12.10.2026, Ch3 Q5)."""
    if b.building_volume_m3 and b.building_volume_m3 > 0:
        return float(b.building_volume_m3), "building volume entered"
    return (footprint * float(b.height_m or 0),
            f"fallback, building volume not entered: {footprint:,.0f} m2 footprint x "
            f"{b.height_m:g} m height (owner ruling 12.10.2026, Ch3 Q5)")


def _table_2_3(footprint: float) -> Extent:
    cr, pg = "Ch 2, #2.8.5 / Table 2.3", "p.213"
    if footprint < 2000:
        return "Minimum 1/6 perimeter (at least 15 m)", "Table 2.3 less than 2,000 m2", cr, pg
    if footprint <= 4000:
        return "1/4 perimeter", "Table 2.3 2,000 - 4,000 m2", cr, pg
    if footprint <= 8000:
        return "1/2 perimeter", "Table 2.3 4,001 - 8,000 m2", cr, pg
    if footprint <= 16000:
        return "3/4 perimeter", "Table 2.3 8,001 - 16,000 m2", cr, pg
    return "Whole perimeter (100%)", "Table 2.3 more than 16,000 m2", cr, pg


def _table_2_4(footprint: float) -> Extent:
    # Printed "Less than 4000" and "4001 to 8000": exactly 4,000 m2 takes 1/4 (audit CH3-21).
    cr, pg = "Ch 2, #2.8.6 / Table 2.4", "p.213"
    if footprint < 4000:
        return "Minimum 1/6 perimeter (at least 15 m)", "Table 2.4 less than 4,000 m2", cr, pg
    if footprint <= 8000:
        return "1/4 perimeter", "Table 2.4 4,001 - 8,000 m2", cr, pg
    if footprint <= 16000:
        return "1/2 perimeter", "Table 2.4 8,001 - 16,000 m2", cr, pg
    if footprint <= 32000:
        return "3/4 perimeter", "Table 2.4 16,001 - 32,000 m2", cr, pg
    return "Whole perimeter (100%)", "Table 2.4 more than 32,000 m2", cr, pg


def _table_2_6_2_7(volume: float, sprinklered: bool) -> Extent:
    pg = "p.215"
    if not sprinklered:
        cr = "Ch 2, #2.8.8 / Table 2.6"
        if volume < 28400:
            return "Minimum 1/6 perimeter (at least 15 m)", "Table 2.6 less than 28,400 m3", cr, pg
        if volume <= 56800:
            return "1/4 perimeter", "Table 2.6 28,400 (printed '28,4001') - 56,800 m3", cr, pg
        if volume <= 85200:
            return "1/2 perimeter", "Table 2.6 56,801 - 85,200 m3", cr, pg
        if volume <= 113600:
            return "3/4 perimeter", "Table 2.6 85,201 - 113,600 m3", cr, pg
        return "Whole perimeter (100%)", "Table 2.6 more than 113,600 m3", cr, pg
    cr = "Ch 2, #2.8.9 / Table 2.7"
    if volume < 56800:
        return "Minimum 1/6 perimeter (at least 15 m)", "Table 2.7 less than 56,800 m3", cr, pg
    if volume <= 85200:
        return "1/4 perimeter", "Table 2.7 56,801 - 85,200 m3", cr, pg
    # Printed rows "85,201 m3 to 113,600 m3" (1/2) and "113,001 m3 to 170,400 m2" (3/4)
    # overlap from 113,001 to 113,600 m3: the higher band (3/4) is taken, owner ruling
    # 12.10.2026, Ch3 Q4.
    if volume <= 113000:
        return "1/2 perimeter", "Table 2.7 85,201 - 113,600 m3", cr, pg
    if volume <= 113600:
        return ("3/4 perimeter", "Table 2.7 113,001 - 170,400 m3 (113,001 - 113,600 m3 is also "
                "in the printed 85,201 - 113,600 m3 row: the higher band is taken, owner ruling "
                "12.10.2026, Ch3 Q4)", cr, pg)
    if volume <= 170400:
        return "3/4 perimeter", "Table 2.7 113,001 - 170,400 m3 (printed '170,400 m2')", cr, pg
    return "Whole perimeter (100%)", "Table 2.7 more than 170,400 m3", cr, pg


def _is_sprinklered(b: Building, sprinklered: Optional[bool]) -> bool:
    if sprinklered is not None:
        return sprinklered
    from engine import building_sprinklered  # lazy: engine imports this module
    return building_sprinklered(b)


def _compute(b: Building, sprinklered: Optional[bool]) -> Tuple[FireAccessSummary, str, str]:
    spr = _is_sprinklered(b, sprinklered)
    fp, fp_basis = _footprint_m2(b)
    notes: List[str] = [
        "Accessway minimum width 6 m; vertical clearance 4.5 m (Table 2.1, #2.6.1, #2.6.3).",
        "Maximum parking distance: 15 m from building entrance, 18 m from breeching inlet (Table 2.2).",
        "Maximum road grade 10% (Tables 2.1 / 2.2).",
    ]
    occ = b.occupancy
    is_mall = occ in _MALLS
    is_super = b.height_class == "super_highrise"
    is_theme = b.is_theme_park           # owner ruling 12.10.2026, Ch3 Q6
    is_low = b.height_m <= 15
    if occ == "storage_industrial":
        vol, vol_basis = _volume_m3(b, fp)
        ext = _table_2_6_2_7(vol, spr)
        if is_super and _rank(ext[0]) < _rank("3/4"):
            # #2.8.7.a (p.214) also covers every super highrise: Table 2.5 3/4 perimeter.
            ext = ("3/4 perimeter", f"Table 2.5 super highrise ({ext[1]} gives {ext[0]})",
                   "Ch 2, #2.8.7.a / Table 2.5", "p.214")
        short = ("entered" if b.building_volume_m3 > 0
                 else "footprint x height, fallback: building volume not entered")
        ext = (ext[0], f"{ext[1]}; volume {vol:,.0f} m3 ({short})", ext[2], ext[3])
        notes.append(f"Gross cubical extent {vol:,.0f} m3 ({vol_basis}).")
    elif is_super or is_mall or is_theme:
        # #2.8.7.a (p.214): Table 2.5 "but not less than as required in Table 2.3 or Table 2.4".
        floor = _table_2_4(fp) if spr else _table_2_3(fp)
        if _rank(floor[0]) > _rank("3/4"):
            ext = (floor[0], f"Table 2.5 3/4 perimeter raised to {floor[1]} (#2.8.7.a)",
                   "Ch 2, #2.8.7.a / Table 2.5 + " + floor[2].split("/ ")[-1], "p.214, 213")
        else:
            ext = ("3/4 perimeter", f"Table 2.5 any area or height ({floor[1]} gives "
                   f"{floor[0]})", "Ch 2, #2.8.7.a / Table 2.5", "p.214")
        why = [w for w, hit in (("super highrise", is_super), ("mall", is_mall),
                                ("theme park", is_theme)) if hit]
        notes.append(f"Table 2.5 applies: {' / '.join(why)} (#2.8.7.a).")
    elif occ == "villa_commercial" and is_low:
        ext = ("Access road within 60 m of every point",
               "#2.8.3.a commercial villa cluster: 6 m accessway within 60 m",
               "Ch 2, #2.8.3.a", "p.212")
    elif is_low:
        ext = ("Access road within 45 m of every point",
               "#2.8.4.a lowrise: accessway not required; 6 m road within 45 m",
               "Ch 2, #2.8.4.a", "p.212")
    elif not spr and b.height_class == "midrise":
        ext = _table_2_3(fp)
    else:
        ext = _table_2_4(fp)
        if not spr:
            notes.append("Table 2.4 is for sprinkler-protected midrise and highrise buildings; "
                         "Ch 9 gives this building no sprinkler system and Table 2.3 covers "
                         "midrise only.")
    extent, ref, code_ref, page_ref = ext
    notes.append(f"Footprint {fp:,.0f} m2 ({fp_basis}); sprinkler protected per Ch 9: "
                 f"{'yes' if spr else 'no'}.")
    s = FireAccessSummary(extent=extent, extent_ref=ref, footprint_m2=fp,
                          sprinklered_assumed=spr, notes=notes)
    return s, code_ref, page_ref


def compute_fire_access(b: Building, requires_wet_riser: bool = False,
                        sprinklered: Optional[bool] = None) -> FireAccessSummary:
    return _compute(b, sprinklered)[0]


def _req(system, spec, code_ref, page_ref, rule, status="required", detail=None):
    return Requirement(system=system, status=status, spec=spec, detail=detail,
                       code_ref=code_ref, page_ref=page_ref, source_rule=rule)


def evaluate_fire_access(b: Building, requires_wet_riser: bool = False,
                         sprinklered: Optional[bool] = None) -> ChapterReport:
    s, ext_code, ext_page = _compute(b, sprinklered)
    occ = b.occupancy
    h = b.height_m
    is_mall = occ in _MALLS
    items = [
        _req("Fire vehicle accessway width + clearance",
             f"Minimum unobstructed width {s.accessway_width_m:g} m (road width between kerbs "
             f"6 m); vertical clearance {s.vertical_clearance_m:g} m for any grade",
             "Ch 2, Table 2.1 / #2.6.1 / #2.6.3", "p.206-207", "fsa_table_2_1"),
        _req("Parking distance to entrance / breeching inlet",
             f"Not more than {s.max_distance_entrance_m:g} m from building entrance; not more "
             f"than {s.max_distance_breeching_m:g} m from breeching inlet",
             "Ch 2, Table 2.2", "p.207", "fsa_table_2_2_distances"),
        _req("Extent of fire vehicle access around building", s.extent, ext_code, ext_page,
             "fsa_extent", detail=" ".join(s.notes[3:]) + f" {s.extent_ref}."),
        _req("Access road grade", f"Maximum road grade {s.max_road_grade_pct:g}%",
             "Ch 2, Table 2.1 / Table 2.2", "p.206-207", "fsa_grade"),
        _req("Access road load capacity",
             "All-weather driving surface to carry 41,000 kg (standard fire appliance) / "
             "81,000 kg (high reach fire appliance)",
             "Ch 2, Table 2.1", "p.206", "fsa_load_capacity"),
        _req("Access road dead end", "Maximum dead end 45 m",
             "Ch 2, Table 2.1", "p.206", "fsa_dead_end"),
        _req("Access road gateways",
             "Minimum width of gateways 4.5 m (gate width 4500 mm); electric / automatic gates "
             "with a manual override for Civil Defence",
             "Ch 2, Table 2.1 / #2.4.1 / #2.4.3", "p.206", "fsa_gateways"),
        _req("Access road turning circle", "Minimum turning circle (roundabout) radius 12 m",
             "Ch 2, Table 2.1", "p.206", "fsa_turning_circle"),
        _req("Fire lane signage",
             "'NO PARKING, FIRE LANE' and 'PARKING RESERVED OF CIVIL DEFENCE' signs; wording "
             "not less than 50 mm; roadways and accessways free of obstruction",
             "Ch 2, #2.5.1", "p.206", "fsa_signage"),
    ]
    if h > 15:
        items.append(_req(
            "Accessway within 18 m of breeching inlet",
            "Required for midrise and highrise buildings exceeding 15 m habitable height",
            "Ch 2, #2.6.2", "p.207", "fsa_breeching_18m"))
    # Site flags (owner ruling 12.10.2026, Ch3 Q6): each line is required when its box is
    # ticked and left out when it is not.
    if b.tower_setback_over_30m:
        if b.height_class in ("highrise", "super_highrise"):
            sup = b.height_class == "super_highrise"
            items.append(_req(
                "Tower set back more than 30 m from the fire access road",
                "The fire access road shall extend and reach the tower perimeter above the "
                "podium; such access a minimum of 1/4 (25 percent) of the tower perimeter; "
                "building facade per #2.8.10.b.1",
                "Ch 2, #2.8.7.b" if sup else "Ch 2, #2.8.6.b", "p.214" if sup else "p.213",
                "fsa_tower_setback",
                detail=("Ticked: the tower facade is more than 30 m of horizontal separation "
                        "distance from the fire access road (podium, parking structure or "
                        "architectural feature); owner ruling 12.10.2026, Ch3 Q6.")))
        else:
            items.append(_req(
                "Tower set back more than 30 m from the fire access road",
                "Not applicable: #2.8.6.b and #2.8.7.b cover highrise and super highrise "
                "towers only", "Ch 2, #2.8.6.b / #2.8.7.b", "p.213-214", "fsa_tower_setback",
                status="not_required",
                detail="Ticked, but the building is below 23 m (owner ruling 12.10.2026, Ch3 Q6)."))
    if b.is_waterfront:
        if occ == "villa_commercial":
            wf = "Commercial villas: maximum distance from fire access road shall not exceed 60 m"
        elif b.height_class == "lowrise" and not occ.startswith("villa_"):
            wf = "Lowrise buildings: maximum distance from fire access road shall not exceed 60 m"
        elif b.height_class == "highrise":
            wf = "Highrise buildings: shall comply with Table 2.3 and Table 2.4"
        elif b.height_class == "super_highrise":
            wf = "Superhighrise buildings: shall comply with Table 2.5"
        else:
            wf = ("Table 2.8 has no row for this building: the fire access road shall comply "
                  "with this chapter (#2.8.10.a)")
        items.append(_req(
            "Waterfront property fire access", f"{wf} (Table 2.8)",
            "Ch 2, #2.8.10.a / Table 2.8", "p.217", "fsa_waterfront",
            detail=("Ticked: waterfront property; owner ruling 12.10.2026, Ch3 Q6. #2.8.10.a: "
                    "the fire access road shall comply with this chapter and Table 2.8. Where it "
                    "does not, #2.8.10.b.1 (building facade) and #2.8.10.b.2 apply.")))
    if b.is_theme_park:
        items.append(_req(
            "Theme park fire access",
            "Accessway shall be provided irrespective of the area or height; extent 3/4 "
            "perimeter (Table 2.5), but not less than Table 2.3 or Table 2.4",
            "Ch 2, #2.8.7.a / Table 2.5", "p.214", "fsa_theme_park",
            detail="Ticked: theme / amusement park; owner ruling 12.10.2026, Ch3 Q6."))
    ecc = [why for why, hit in (("highrise of 23 m or more", h >= 23), ("mall", is_mall),
                                ("amusement park", b.is_theme_park)) if hit]
    if ecc:
        items.append(_req(
            "Emergency Command Centre",
            "On the building front side along the Fire Accessway (not below grade or above the "
            "discharge level); minimum 19 m2 with minimum dimension 3 m on any side; entrance "
            "from the exterior along the Fire Accessway (else at the main entrance lobby); "
            "separated by a 1-hour fire barrier; mechanical ventilation per Ch 10",
            "Ch 2, #2.9.3.a-e", "p.219", "fsa_ecc",
            detail=f"#2.9.3.a: required in any building which is {' / '.join(ecc)}. "
                   "Features per #2.9.3.f (plans, EVC unit, two-way telephone, FA annunciator, "
                   "lift annunciator, HVAC / smoke control panel, door unlocking, fire pump and "
                   "sprinkler status, generator status, PA, work table, lift recall)."))
    # One trigger with the Ch 10 'NOT mandatory' line (Building.fire_lift_2_9_4_reasons).
    lift = b.fire_lift_2_9_4_reasons
    if lift:
        items.append(_req(
            "Fire Lift",
            "At least one Fire Lift in a dedicated shaft, serving every habitable floor; car to "
            "take a 610 mm x 2134 mm stretcher; firefighter override, exclusive sub-main "
            "circuit, 1-hour protected wiring, 2-way communication"
            + ("; in super highrise adjacent to an exit stair and a firefighting lobby at each "
               "storey" if b.height_class == "super_highrise" else ""),
            "Ch 2, #2.9.4.a-j", "p.220", "fsa_fire_lift",
            detail=f"#2.9.4.a: required in any building which is {' / '.join(lift)}."))
    return ChapterReport(
        chapter_code="FSA", chapter_title="Fire Service Access (Ch 2)",
        selected_branch="fsa_auto", selected_branch_section=f"{ext_code} ({ext_page})",
        blocks=[SectionBlock(title="FSA - Vehicle access & extent (Ch 2)", items=items)],
        extras={"fire_access": s.model_dump()},
    )
