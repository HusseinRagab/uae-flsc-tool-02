"""UAE FLSC 2018 Chapter 2 - Fire Service Vehicle and Personnel Accessibility.

Values are from the printed pages: Table 2.1 (p.206), #2.6 and Table 2.2 (p.207),
#2.8.3 and #2.8.4 (p.212), #2.8.5 / #2.8.6 and Tables 2.3 / 2.4 (p.213), #2.8.7 and
Table 2.5 (p.214), #2.8.8 / #2.8.9 and Tables 2.6 / 2.7 (p.215), #2.8.10 and Table
2.8 (p.217), #2.9.3 (p.219), #2.9.4 (p.220); #2.6.6-#2.6.8 (p.208), #2.7 and Figures
2.5-2.7 (p.209-210), #2.8.1-#2.8.2 (p.211), #2.9.5-#2.9.6 (p.221), #3.2 and Table 2.9
(p.225).

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


def _section_2_10(b: Building, wet_riser: bool, spr: bool) -> List[Requirement]:
    """Ch 2 #2.10.1-#2.10.4 (p.222-224), audit CH123-12: access to fire fighting equipment.
    Ch 9 sets where yard hydrants, risers, hose cabinets and pumps are needed (Section 3.11 /
    Table 9.13 and the occupancy tables); these lines give only the Ch 2 location, access and
    configuration items and do not repeat the Ch 9 duty lines."""
    water = wet_riser or spr
    out = [
        _req("Yard fire hydrants for fire fighters",
             "Where yard fire hydrants are provided: located along the Fire Accessway, for fire "
             "fighters to refill the fire vehicle water tank or fight fire from the hydrant hose "
             "connection; capable of delivering 500 gpm through a single hydrant with two "
             "outlets, i.e., 250 gpm per outlet; minimum pressure 6.9 bars; two such hydrants "
             "considered for the hydraulic calculations; design, calculations, pipe sizes, pump "
             "and tank capacities, tests, distance between hydrants and materials per Ch 9",
             "Ch 2, #2.10.1", "p.222", "fsa_yard_hydrants", status="conditional",
             detail=("Where yard hydrants are needed is set in Ch 9 (Section 3.11, Table 9.13 item 2, "
                     "p.673, and the Ch 9 occupancy table rows: see the Ch 9 section). OPEN "
                     "QUESTION (needs owner ruling): #2.10.1.a (p.222) prints 'Civil Defence makes "
                     "it mandatory to provide Yard Fire Hydrants in all developments', wider than "
                     "the Ch 9 triggers; the tool keeps the Ch 9 triggers (audit CH123-12).")),
        _req("Breeching inlets (Civil Defence connections)",
             "On the street side of the building, near the building entrance and on the Fire "
             "Accessway, within 18 m from the fire vehicle parking slot; arranged so hose lines "
             "can be readily attached without interference from nearby objects; four 65 mm "
             "(4-Way) direct coupling fittings for the wet riser, two 65 mm (2-Way) for the "
             "sprinkler riser, two 65 mm (2-Way) for the dry riser; caps against debris; not less "
             "than 457 mm nor more than 1219 mm above the finished ground level; each connection "
             "designated by a sign with raised or engraved letters at least 25.4 mm in height, in "
             "English and Arabic, naming the service (e.g. WATER TANK / SPRINKLER / WETRISER / "
             "DRYRISER); design per Ch 9",
             "Ch 2, #2.10.2", "p.223", "fsa_breeching_inlets",
             status="required" if water else "conditional",
             detail=(("Required: Ch 9 gives this building a sprinkler system or wet riser. "
                      if water else
                      "Conditional: Ch 9 gives this building no sprinkler system or wet riser; "
                      "applies to any riser or tank connection provided. ")
                     + "Points to Ponder (p.223): two sets of breeching inlets at two separate "
                       "and remote locations should be considered (audit CH123-12).")),
        _req("Fire hose cabinets for fire fighters",
             "Next to the exit stairs and distributed in the corridors and circulation areas on "
             "every floor, clearly visible; within 6 m from the stair door and not inside the "
             "stair core (a landing valve alone in the stair is not an alternative); on both "
             "sides of horizontal exits next to the door; on the roof where LPG tanks, air "
             "conditioning equipment, heaters or gymnasium are located; each cabinet: 65 mm "
             "landing valve outlet, 40/25 mm outlet with hose reel / hose rack, CO2 fire "
             "extinguisher, dry chemical powder fire extinguisher, 65 mm 30 m fire hose with "
             "nozzle; design and installation per Ch 9",
             "Ch 2, #2.10.3", "p.223-224", "fsa_hose_cabinets",
             status="required" if wet_riser else "conditional",
             detail=(("Required: Ch 9 gives this building a wet riser. " if wet_riser else
                      "Conditional: Ch 9 gives this building no wet riser; applies to the hose "
                      "cabinets provided. ")
                     + "OPEN QUESTION (needs owner ruling): #2.10.3.a (p.223) prints 'Fire Hose "
                       "Cabinets (Hose Stations) complying to Chapter 9, shall be available in all "
                       "buildings for Fire Fighters', wider than the Ch 9 rows. Ch 3 Table 3.4 "
                       "item 8.iv (p.259): hose reel and landing valve cabinets are not located in "
                       "the stair enclosure (audit CH123-12).")),
        _req("Fire pump room access for fire fighters",
             "Fire pump room, irrespective of its location, accessible for fire fighters; a clear "
             "visual layout showing the location of and the way to the pump room posted in the "
             "Emergency Command Center and Reception; a dedicated fire pump room housing the "
             "main electrical fire pump, standby diesel fire pump, jockey pump, controller, "
             "diesel fuel tank etc. as required by Ch 9; sufficient space around the "
             "installations to access the valves, controllers and gauges",
             "Ch 2, #2.10.4", "p.224", "fsa_pump_room_access",
             status="required" if (water and b.has_fire_pump_room) else "conditional",
             detail=(("Required: Ch 9 gives this building a sprinkler system or wet riser and a "
                      "fire pump room is ticked. " if (water and b.has_fire_pump_room) else
                      "Conditional: applies where a fire pump room is provided. ")
                     + "Pump room location, size and access stair per Ch 1 Table 1.9 item 2 "
                       "(p.73) (audit CH123-12).")),
    ]
    return out


def evaluate_fire_access(b: Building, requires_wet_riser: bool = False,
                         sprinklered: Optional[bool] = None) -> ChapterReport:
    s, ext_code, ext_page = _compute(b, sprinklered)
    occ = b.occupancy
    h = b.height_m
    is_mall = occ in _MALLS
    # Audit CH123-21: #2.8.4.a (p.212) lowrise: "accessway will not be required", only a
    # 6 m fire engine access ROAD within 45 m; the line says road there.
    road_only = s.extent.startswith("Access road within 45 m")
    exempt_2_3_1 = (" #2.3.1 (p.205): fire access roadways are provided to every facility, "
                    "structure and under construction building, except detached retail units, "
                    "kiosks, store rooms, snack bars, rest rooms which are less than 100 m2 and "
                    "are remotely located from predominant occupancy.")
    items = [
        _req("Fire access road width + clearance" if road_only
             else "Fire vehicle accessway width + clearance",
             (f"Fire engine access road minimum width 6 m (road width between kerbs 6 m); "
              f"vertical clearance {s.vertical_clearance_m:g} m for any grade; a fire accessway "
              "is not required for this lowrise building (#2.8.4.a)") if road_only else
             (f"Minimum unobstructed width {s.accessway_width_m:g} m (road width between kerbs "
              f"6 m); vertical clearance {s.vertical_clearance_m:g} m for any grade"),
             ("Ch 2, Table 2.1 / #2.8.4.a" if road_only
              else "Ch 2, Table 2.1 / #2.6.1 / #2.6.3"),
             "p.206, 212" if road_only else "p.206-207", "fsa_table_2_1",
             detail=(("#2.8.4.a (p.212): for lowrise buildings not exceeding the habitable height "
                      "of 15 m, accessway will not be required; a fire engine access road of "
                      "minimum 6 m width is required within 45 m of every point on the projected "
                      "plan area of the building (audit CH123-21)." if road_only else
                      "#2.8.1 (p.211): minimum width of 6 m throughout; the accessway must "
                      "accommodate the entry and maneuvering of fire engine, extended ladders, "
                      "pumping appliances, aerial appliances, turntable and / or hydraulic "
                      "platforms.") +
                     " #2.6.6 (p.208): accessway and fire engine access road kept clear "
                     "of obstructions and protruded parts of the building, plants, trees or other "
                     "fixtures between the accessway and the access openings. #2.6.8 (p.208): fire "
                     "hydrants, where required by Ch 9, located along the Fire Access Road and "
                     "Fire Accessway." + exempt_2_3_1)),
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
        _req("Access road dead end",
             "Maximum dead end 45 m; where a Fire Accessway dead end exceeds 45 m a turning "
             "facility shall be provided: U-turn, Y-turn, T-turn or roundabout",
             "Ch 2, Table 2.1 / #2.7.1", "p.206, 209", "fsa_dead_end"),
        _req("Access road gateways",
             "Minimum width of gateways 4.5 m (gate width 4500 mm); electric / automatic gates "
             "with a manual override for Civil Defence; locks not installed on fire access road "
             "gates unless the gate is attended continuously by security guards or the keys are "
             "located on-site and the gates may be readily unlocked (#2.4.4)",
             "Ch 2, Table 2.1 / #2.4.1 / #2.4.3 / #2.4.4", "p.206", "fsa_gateways"),
        _req("Access road turning circle",
             "Minimum turning circle (roundabout) radius 12 m; U-turn and roundabout per "
             "Figure 2.5: clearance radius (R3) 12000 mm, outer radius (R2) 11000 mm, inner "
             "radius (R1) 7000 mm, lane dimension 6000 mm",
             "Ch 2, Table 2.1 / #2.7.2 / Figure 2.5", "p.206, 209", "fsa_turning_circle",
             detail=("T-turn per #2.7.3 / Figure 2.6 (p.209), dimensions as printed: 6000, 36000, "
                     "20000, 11000, 6000 and R 7000 mm. Y-turn per #2.7.4 / Figure 2.7 (p.210), "
                     "dimensions as printed: 20000, 19000, 6000 and R 7000 mm. The figures do not "
                     "name what each T-turn / Y-turn dimension measures: check the layout against "
                     "the figure.")),
        _req("Fire lane signage",
             "'NO PARKING, FIRE LANE' and 'PARKING RESERVED OF CIVIL DEFENCE' signs; wording "
             "not less than 50 mm; roadways and accessways free of obstruction",
             "Ch 2, #2.5.1", "p.206", "fsa_signage"),
        _req("Firefighter inspection pathway",
             "A suitable access pathway (paved or gravel path) so fire-fighters can inspect all "
             "elevations of the building during or after a fire; minimum 1 m wide, not impeded "
             "by plants, bushes, walls or other features (width and obstruction printed as "
             "'should')",
             "Ch 2, #2.6.7", "p.208", "fsa_inspection_pathway"),
        # Audit CH123-20: #2.6.4 / #2.6.5 (p.207), design features with no input.
        _req("Security barriers and turfed accessways",
             "Where a security barrier or guard house is on the accessway: the security barrier, "
             "when lifted up, shall not obstruct the fire engine accessway, and eaves of the "
             "security post or guard house shall not project into the fire engine accessway "
             "(#2.6.4). Where the accessway is on a turfed area (synthetic grass, composite "
             "material, sports surfaces): marked with contrasting objects (preferably reflective) "
             "visible at night, at an interval not more than 3 meters apart, on both sides of "
             "the accessway (#2.6.5)",
             "Ch 2, #2.6.4 / #2.6.5", "p.207", "fsa_barrier_turf", status="conditional",
             detail="Conditional: no input says the accessway has a security barrier, guard house "
                    "or turfed surface (audit CH123-20)."),
    ]
    if h > 15:
        items.append(_req(
            "Accessway within 18 m of breeching inlet",
            "Required for midrise and highrise buildings exceeding 15 m habitable height",
            "Ch 2, #2.6.2", "p.207", "fsa_breeching_18m"))
    # #2.8.2 applies wherever an accessway is required: not the #2.8.3.a / #2.8.4.a
    # "Access road within 60 / 45 m" cases (owner card 13.10.2026 05:45Z, G2).
    if not s.extent.startswith("Access road within"):
        items.append(_req(
            "Accessway position from the building",
            "Nearer edge of the accessway not less than 2 m or more than 10 m from the "
            "building, measured horizontally",
            "Ch 2, #2.8.2", "p.211", "fsa_accessway_offset",
            detail=("#2.6.6 Note / Figure 2.4 (p.208): the fire engine shall be located at least "
                    "2 m from the building, but not more than 10 m away from the external wall or "
                    "facade (including any overhead obstruction). A public road may be used as "
                    "hard standing by fire engine, provided the edge of the public road to the "
                    "facade where access openings are located is not exceeding 10 m.")))
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
        elif b.height_class == "lowrise":
            # Audit CH123-19: the Table 2.8 lowrise row (p.217) prints no villa exclusion.
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
        # Ch 2 #3.2 (p.225) on the same tick (owner card 13.10.2026 05:45Z, G7).
        items.append(_req(
            "Fireboat access from the water front",
            "Fire access for Civil Defence Fire Boats irrespective of the fire access road on "
            "land: dedicated berth for docking during emergencies, minimum unobstructed length "
            "15 m, width 5 m, vertical clearance 6 m (Table 2.9); mooring facility complete with "
            "approved ropes and fixed fittings on the deck and platform; mooring bitts or cleats "
            "corrosion resistant, secured to a foundation tied into an underdeck structure and "
            "of adequate strength to carry the mooring loads; docking facility within 45 m from "
            "any building and structure to be attended to, on the shore",
            "Ch 2, #3.2.1-#3.2.5 / Table 2.9", "p.225", "fsa_fireboat",
            detail=("Ticked: waterfront property (owner card 13.10.2026 05:45Z). #3.2.1: on all "
                    "water front developments, so that Fire Boats can approach from the "
                    "waterside.")))
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
        # Owner ruling R-A (28.10.2026), audit H2 / CH123-02: 1 h if the building is
        # sprinklered, 2 h if not (Ch 1 Table 1.9 item 1, p.73; FAQ Q8, p.1273).
        spr = s.sprinklered_assumed
        rating = ("separated by a 1-hour fire barrier (building sprinkler protected per Ch 9)"
                  if spr else
                  "separated by a 2-hour fire barrier (building not sprinkler protected per Ch 9)")
        items.append(_req(
            "Emergency Command Centre",
            "On the building front side along the Fire Accessway (not below grade or above the "
            "discharge level); minimum 19 m2 with minimum dimension 3 m on any side; entrance "
            "from the exterior along the Fire Accessway (else at the main entrance lobby); "
            f"{rating}; mechanical ventilation per Ch 10",
            "Ch 2, #2.9.3.a-e; Ch 1, Table 1.9 item 1; Annexure 1, Table A.1.2 Q8",
            "p.219, 73, 1273", "fsa_ecc",
            detail=f"#2.9.3.a: required in any building which is {' / '.join(ecc)}. "
                   "Fire rating: Ch 1 Table 1.9 item 1 EMERGENCY COMMAND CENTER (p.73) prints "
                   "'1 Hour' with automatic fixed fire protection and '2 Hour' without; Annexure 1 "
                   "FAQ Table A.1.2 Q8 (p.1273): 'minimum of 1 hour fire resistance rated with "
                   "sprinkler protection and 2 hour fire resistance rated without sprinkler "
                   "protection'. CODE CONFLICT: Ch 2 #2.9.3.c (p.219) prints 'not less than a "
                   "1-hour fire barrier' with no sprinkler condition; owner ruling R-A "
                   "(28.10.2026): 1 h sprinklered, 2 h not. "
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
               "storey" if b.height_class == "super_highrise" else "")
            + "; in a fire emergency, when a fire detection device or the fire alarm system is "
              "activated and the ground floor is compromised with fire, all the passenger lifts "
              "brought to the ground floor or egress level or alternative floor, lift doors "
              "remaining open (#2.9.4.i); water management, protection of electrical equipment "
              "against water, control and power supplies, and Civil Defence communications "
              "systems in accordance with sections 5.3 and 5.6-5.12 of BS EN 81-72 current "
              "edition (#2.9.4.l)",
            "Ch 2, #2.9.4.a-l", "p.220", "fsa_fire_lift",
            detail=f"#2.9.4.a: required in any building which is {' / '.join(lift)}. "
                   "#2.9.4.k: elevators used for evacuation have the features of Ch 3 Section "
                   "3.9 (Table 3.11). Items i and l added (audit CH123-11)."))
        # #2.9.6 (p.221) only where the Fire Lift is required (owner card 13.10.2026
        # 05:45Z "Fire lift buildings", G6).
        items.append(_req(
            "Fire Exit Stair for fire fighters",
            "2 hour rated Fire Exit enclosure for the fire fighters to access the interior and "
            "upper floors; the exit stair a fully enclosed smoke proof space; number of such "
            "stairs per Ch 3, construction per Ch 1; the Fire Exit Stair connects every "
            "habitable floor, and not less than one stair provides access to the roof where "
            "LPG tanks are located",
            "Ch 2, #2.9.6.a-b", "p.221", "fsa_fire_exit_stair",
            detail=(f"Stated where the Fire Lift is required (#2.9.4.a: {' / '.join(lift)}); "
                    "#2.9.5.b: the Fire Lift Lobby is where both the fire exit stair and the fire "
                    "lift can be accessed."
                    + (" Ticked: roof-mounted LPG tanks (Ch 11)." if b.has_lpg_tank_roof_mounted
                       else ""))))
    if b.height_class == "super_highrise":
        items.append(_req(
            "Firefighter's Lift Lobby (super highrise)",
            "Fire Fighter's Lift Lobby per Ch 1 Table 1.9.38, where both the fire exit stair "
            "and the fire lift can be accessed; enclosed with a smoke barrier of minimum 1-hour "
            "fire-resistance rating; clear floor area not less than 9 m2 with a minimum "
            "dimension of 2440 mm; doorway protected with a 60 minutes fire door assembly; free "
            "of combustible materials and ignition sources",
            "Ch 2, #2.9.5.a-e / Figure 2.15", "p.221", "fsa_fire_lift_lobby",
            detail=("#2.9.5.a: all super highrise buildings (height greater than 90 m from the "
                    "fire access level). #2.9.5.f: no requirement for the fire lift lobby or the "
                    "fire lift shaft to be pressurized when this lobby is provided.")))
    items += _section_2_10(b, requires_wet_riser, s.sprinklered_assumed)
    return ChapterReport(
        chapter_code="FSA", chapter_title="Fire Service Access (Ch 2)",
        selected_branch="fsa_auto", selected_branch_section=f"{ext_code} ({ext_page})",
        blocks=[SectionBlock(title="FSA - Vehicle access & extent (Ch 2)", items=items)],
        extras={"fire_access": s.model_dump()},
    )
