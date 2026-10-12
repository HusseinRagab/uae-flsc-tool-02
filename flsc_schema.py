"""UAE FLSC 2018 compliance tool - data models (Pydantic v2). Multi-chapter."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, model_validator


# Mandatory liability / scope disclaimer shown in the UI footer and every export.
DISCLAIMER = (
    "This tool is a design-aid based on UAE Fire & Life Safety Code 2018 "
    "(CDGH-OP-25, September 2018). It does NOT replace UAE Civil Defence review "
    "or the judgement of a registered Fire Protection Engineer / Engineer-of-Record. "
    "Final compliance verification, code interpretation in edge cases, and submission "
    "to the relevant Civil Defence Department remain the responsibility of the "
    "engineer-of-record. Rule citations point at the cited code section but the user "
    "is expected to cross-check against the current edition of the code."
)


Occupancy = Literal[
    "assembly_a", "assembly_b", "assembly_c",
    "business",
    "education_a", "education_b", "education_c",
    "mercantile_a", "mercantile_b",
    "healthcare_a", "healthcare_b", "healthcare_c",
    "hotel_a", "hotel_b", "hotel_c",
    "daycare_a", "daycare_b", "daycare_c",
    "residential",
    "labour_accommodation", "staff_accommodation",
    "hostel", "animal_housing",
    "detention_a", "detention_b", "detention_c",
    "villa_private", "villa_commercial",
    "mall_covered", "mall_open", "mall_mixed",
    "parking_enclosed", "parking_open",
    "storage_industrial", "motor_fuel_dispensing", "infrastructure",
    "mixed_multiple",
    "high_depth_underground", "low_depth_underground",
]

OCCUPANCY_DEFS = {
    "assembly_a": "Assembly Group A - Occupant load > 1,000. Concert halls, large auditoriums, stadiums, arenas, exhibition halls, mosques > 1,000 capacity.",
    "assembly_b": "Assembly Group B - Occupant load 301 to 1,000. Cinemas, theatres, banquet halls, conference halls, mid-size mosques, ballrooms.",
    "assembly_c": "Assembly Group C - Occupant load 50 to 300. Restaurants, cafes, small meeting rooms, small mosques, community halls, bars, nightclubs.",
    "business": "Business - Offices, non-inpatient clinics, government offices, banks, courthouses, professional services.",
    # NOTE: Education group letters swapped 2026-05 to match UAE FLSC Ch 3 #5.3 / Table 3.13.3.
    # Per code: Group A = Nurseries / KG / Preschool (Table 3.20); Group B/C = Schools and Colleges
    # / Universities (Table 3.21). Schema IDs preserved (education_a/_b/_c) for backward compat
    # with saved scenarios; their meaning is the code's meaning, not the schema's original.
    "education_a": "Educational Group A - Nurseries, KG1/KG2, Preschool, Talent Centers (Table 3.20).",
    "education_b": "Educational Group B - Schools: Grade 1 through 12 (Table 3.21).",
    "education_c": "Educational Group C - Colleges, Universities, adult education (Table 3.21).",
    "mercantile_a": "Mercantile Group A - Retail up to 2 storeys and less than 2,800 m2. Shops, showrooms, boutiques.",
    "mercantile_b": "Mercantile Group B - Retail more than 2 storeys or exceeding 2,800 m2. Department stores, hypermarkets (stand-alone).",
    "healthcare_a": "Healthcare Group A - Hospitals, nursing homes, inpatient medical facilities where occupants require assistance for evacuation (Table 3.22).",
    "healthcare_b": "Healthcare Group B - Clinics, day-surgery and outpatient medical facilities (Table 3.22). Mid/low-rise fire protection follows Table 9.20.b / 9.21.b (with residential / business), NOT the public-assembly Table 9.20.a / 9.21.a used by Healthcare Group A hospitals.",
    "healthcare_c": "Healthcare Group C - Ambulatory healthcare, walk-in clinics, dental/eye/diagnostic centres (Table 3.23). Mid/low-rise fire protection follows Table 9.20.b / 9.21.b (with Healthcare Group B), not Table 9.20.a / 9.21.a.",
    "hotel_a": "Hotel Group A - Luxury / 4-5 star hotels.",
    "hotel_b": "Hotel Group B - Mid-range hotels (2-3 star).",
    "hotel_c": "Hotel Group C - Budget hotels, apartment hotels, furnished apartments.",
    "daycare_a": "Daycare Group A - Daycare for more than 12 clients.",
    "daycare_b": "Daycare Group B - Daycare for 7 to 12 clients.",
    # daycare_c: UAE FLSC Ch 3 #5.10 only defines Daycare Groups A and B. Schema keeps _c as a
    # UI convenience for family daycare (4-6 clients); Ch 3 rules treat it the same as Group B.
    "daycare_c": "Daycare Group C - Family daycare for 4 to 6 clients (UI category; Ch 3 falls back to Group B rules).",
    "residential": "Residential - Apartment buildings, flats, condominiums. Multi-family dwellings.",
    "labour_accommodation": "Labour Accommodation - Dormitory-style housing for construction/industrial workers with shared facilities.",
    "staff_accommodation": "Staff Accommodation - Housing for employees of a single institution (hospital/hotel/airport staff).",
    "hostel": "Hostel - Shared lodging, bunk-bed dormitories, youth hostels, pilgrim accommodation.",
    "animal_housing": "Animal Housing - Stables, kennels, veterinary boarding, livestock pens.",
    "detention_a": "Detention & Correctional Group A - Maximum security; occupants restrained and require supervised evacuation.",
    "detention_b": "Detention & Correctional Group B - Medium security correctional facilities.",
    "detention_c": "Detention & Correctional Group C - Minimum security, police holding cells, short-term detention.",
    "villa_private": "Private Villa (Ch 1 #1.7.34) - Single-family dwelling unit, generally ground with first floor, built and solely owned by an individual on an individual plot.",
    "villa_commercial": "Commercial Villa (Ch 1 #1.7.35) - One- or two-family dwelling units built in a group by a developer and sold, leased or rented to individual families. Mosques, community halls and recreation facilities may also be part of this development. NOT a private villa converted to a shop/clinic - use the 'villa converted to other use' flag for that (Table 8.13 item 14 / Table 9.21.d).",
    "mall_covered": "Covered Mall - Fully enclosed/climatised shopping mall with common internal circulation; tenants accessed from internal mall.",
    "mall_open": "Open Mall - Outdoor strip mall or open-air shopping complex. Tenants accessed from external circulation only.",
    "mall_mixed": "Mixed Mall - Development combining covered and open mall elements (covered anchor + open retail street).",
    "parking_enclosed": "Enclosed Parking (UAE FLSC Ch 1, Table 1.1, def. 15) - A parking occupancy which does NOT qualify as open parking and is enclosed on all sides.",
    "parking_open": "Open Parking (UAE FLSC Ch 1, Table 1.1, def. 15) - A parking occupancy where in each parking level, any part of the carpark is within 30 m of permanent natural ventilation wall openings open to the atmosphere; not less than 0.4 m^2 per linear meter distributed over 40 percent of the building perimeter or uniformly over two opposing sides; interior wall lines and column lines at least 20 percent open with openings distributed to provide ventilation.",
    "storage_industrial": "Storage / Warehouse / Industrial - Warehouses, logistics, manufacturing, processing, workshops. Ch 9 #4.11 (Tables 9.24-9.28).",
    "motor_fuel_dispensing": "Motor Fuel Dispensing - Petrol stations, truck fuelling, ADNOC/ENOC/EPPCO with fuel storage and dispensing pumps.",
    "infrastructure": "Infrastructure - new developments' infrastructure, marina/waterfront, theme/amusement parks, commercial developments. Ch 9 #4.10 / Table 9.26 (yard-hydrant network only).",
    "mixed_multiple": "Mixed and Multiple Occupancies - Two or more occupancies intermingled. Treated by most-restrictive occupancy unless separated per Ch 1.",
    "high_depth_underground": "High-Depth Underground - 3 or more basements.",
    "low_depth_underground": "Low-Depth Underground - 2 or fewer basements.",
}

# Ch 9 #1.1.13 (p.526-530) hazard classification for sprinkler protection.
#   LH  #1.1.13.1: Assembly C, Assembly B, Educational A/B/C, Healthcare B/C,
#       Residential A/B/C (C = labour accommodation), Daycare A/B, Detention A/B/C.
#   OH1 #1.1.13.2: Assembly A, Hotel A/B/C, Mercantile A/B, parking garages open or
#       enclosed (Storage Group C list).
#   OH2 #1.1.13.3: Animal Housing B (stables, animal sheds, livestock shelter),
#       Malls Group A (covered malls).
#   EH2 #1.1.13.5.b: robotic / mechanical parking.
# Animal Housing A and C are LH; the tool's single animal_housing occupancy takes the
# highest of its three groups (OH2) until the group is chosen (override in the app).
# Storage / industrial has no default: the app makes the user choose (Table 9.27).
# HAZARD_NOT_CLASSIFIED lists the occupancies #1.1.13 does not name; their value
# here is the tool's working default and the app says the designer must select.
HAZARD_BY_OCCUPANCY = {
    "assembly_a": "OH1", "assembly_b": "LH", "assembly_c": "LH",
    "business": "LH",
    "education_a": "LH", "education_b": "LH", "education_c": "LH",
    "mercantile_a": "OH1", "mercantile_b": "OH1",
    "healthcare_a": "LH", "healthcare_b": "LH", "healthcare_c": "LH",
    "hotel_a": "OH1", "hotel_b": "OH1", "hotel_c": "OH1",
    "daycare_a": "LH", "daycare_b": "LH", "daycare_c": "LH",
    "residential": "LH",
    "labour_accommodation": "LH", "staff_accommodation": "LH",
    "hostel": "LH", "animal_housing": "OH2",
    "detention_a": "LH", "detention_b": "LH", "detention_c": "LH",
    "villa_private": "LH", "villa_commercial": "LH",
    "mall_covered": "OH2", "mall_open": "OH2", "mall_mixed": "OH2",
    "parking_enclosed": "OH1", "parking_open": "OH1",
    "storage_industrial": "OH2", "motor_fuel_dispensing": "HH", "infrastructure": "OH1",
    "mixed_multiple": "OH2",
    "high_depth_underground": "OH2", "low_depth_underground": "OH2",
}
HAZARD_NOT_CLASSIFIED = {
    "business", "healthcare_a", "daycare_c", "villa_private", "villa_commercial",
    "mall_open", "mall_mixed", "motor_fuel_dispensing", "infrastructure",
    "mixed_multiple", "high_depth_underground", "low_depth_underground",
}

MIDRISE_PUBLIC = {
    "assembly_a", "assembly_b", "assembly_c",
    "education_a", "education_b", "education_c",
    "healthcare_a",
    "mercantile_a", "mercantile_b",
    "hotel_a", "hotel_b", "hotel_c",
    "daycare_a", "daycare_b", "daycare_c",
    "mixed_multiple", "high_depth_underground",
}
MIDRISE_RESIDENTIAL = {
    "residential", "labour_accommodation", "staff_accommodation",
    "hostel", "business", "animal_housing",
    "healthcare_b", "healthcare_c",
}
LOWRISE_PUBLIC = MIDRISE_PUBLIC | {
    "detention_a", "detention_b", "detention_c", "low_depth_underground",
}


def occupancy_group(occ: str) -> Optional[str]:
    if occ in LOWRISE_PUBLIC:
        return "public"
    if occ in MIDRISE_RESIDENTIAL:
        return "residential"
    return None


def default_hazard(occ: str) -> str:
    return HAZARD_BY_OCCUPANCY.get(occ, "OH1")


class UseArea(BaseModel):
    """One actual use of floor area (Ch 3 #1.4.5, #4.1.2): a Table 3.13 row id
    (see occupant_load.TABLE_3_13_ROWS) and the floor area assigned to it.
    Owner ruling 12.10.2026, Ch3 Q2."""
    row: str
    area_m2: float = Field(0.0, ge=0)


class StoreyUse(BaseModel):
    """One line of the per-storey table (owner answer 12.10.2026, F6): the storey it
    belongs to, a Table 3.13 row id (None = the densest row of the occupancy, Ch3 Q2)
    and the floor area of that use on that storey. Lines with the same storey name
    form one storey."""
    storey: str = ""
    row: Optional[str] = None
    area_m2: float = Field(0.0, ge=0)


class Building(BaseModel):
    project_name: str = Field("", description="Project reference")
    occupancy: Occupancy
    secondary_occupancies: List[Occupancy] = Field(default_factory=list)
    mixed_occupancy_mode: Literal["none", "most_restrictive", "separated"] = "none"

    # Impossible values are refused, never clamped: areas, depths and counts
    # cannot be negative, and a building height of 0 m is refused (see
    # _height_stated) except for infrastructure, which has no building.
    height_m: float = Field(0.0, ge=0)
    height_datum: Literal["grade", "occupiable_ceiling"] = "grade"
    floors_above_grade: int = Field(1, ge=1)
    floors_below_grade: int = Field(0, ge=0)
    depth_below_grade_m: float = Field(0.0, ge=0)   # SC Ch 10 - >7 m underground trigger (Table 10.22)
    gross_floor_area_m2: float = Field(0.0, ge=0)
    ground_floor_bua_m2: float = Field(0.0, ge=0)
    basement_bua_m2: float = Field(0.0, ge=0)
    plot_area_m2: float = Field(0.0, ge=0)
    corridor_length_m: float = Field(0.0, ge=0)     # SC Ch 10 - >60 m enclosed-corridor trigger (Table 10.27 item 4)
    assembly_area_m2: float = Field(0.0, ge=0)      # SC Ch 10 - >2000 m² assembly hall trigger (Table 10.27 items 9-13: exhibition/assembly/sports/auditorium/stadium). If 0 and occupancy is assembly_*, falls back to gross_floor_area_m2.

    # --- MOE (Ch 3) / FSA (Ch 2) inputs - owner rulings 12.10.2026, Ch3 Q1-Q6.
    # 0 / empty = not entered; each fallback is named in the report line.
    largest_storey_area_m2: float = Field(0.0, ge=0)   # Q1: Table 3.14 per storey (#4.3.1); 0 -> whole GFA
    use_areas: List[UseArea] = Field(default_factory=list)  # Q2: per-use areas (#1.4.5); empty -> densest Table 3.13 row
    storey_uses: List[StoreyUse] = Field(default_factory=list)  # F6: per-storey per-use table; empty -> the inputs above
    mall_gla_m2: float = Field(0.0, ge=0)              # Q3: mall gross leasable area (Table 3.13 row 14); 0 -> GFA
    building_volume_m3: float = Field(0.0, ge=0)       # Q5: gross cubical extent (#2.8.8.a / #2.8.9.a); 0 -> footprint x height
    is_waterfront: bool = False                        # Q6: waterfront property (#2.8.10, Table 2.8)
    is_theme_park: bool = False                        # Q6: theme / amusement park (#2.8.7, Table 2.5, #2.9.3, #2.9.4)
    tower_setback_over_30m: bool = False               # Q6: tower facade more than 30 m from the fire access road (#2.8.6.b / #2.8.7.b)

    construction_type: Literal[
        "unspecified", "type_i", "type_ii", "type_iii", "type_iv", "type_v"
    ] = "unspecified"

    hazard_class: Literal["LH", "OH1", "OH2", "HH"] = "OH1"

    # --- FP (Ch 9) - High Ceiling
    has_high_ceiling: bool = False
    ceiling_height_m: float = 0.0
    wet_riser_standpipes: int = Field(2, ge=1)
    exit_stairs: int = Field(2, ge=1)            # Table 9.24.C.2 open parking pump: 750 gpm (2 stairs) / 1000 gpm (3 or more)
    pump_room_at_grade: bool = False             # False = fire pump room at the lowest basement (Table 9.6 item 13 measures from the pump)
    gf_beyond_100m_from_hydrant: bool = False    # Ch 9 #4.1.6 second trigger (storage / industrial)
    is_covered_shaded_parking: bool = False      # Table 9.24.D - covered / shaded parking having one level only

    # --- FP (Ch 9) - Auxiliary Rooms (Table 9.30)
    has_anesthetizing_room: bool = False
    has_battery_charger_room: bool = False
    has_bms_room: bool = False
    has_battery_room: bool = False
    has_computer_room: bool = False
    has_control_room: bool = False
    has_diesel_generator_room: bool = False
    has_main_electrical_room: bool = True   # universal in any non-villa building
    has_ahu_room: bool = False
    # has_lv_mv_room = LV room (key kept so saved files still load). Ch 4 Table 4.3 names
    # LV and HV rooms only and Table 8.14 has no MV row; Table 9.30.J is printed "LV ROOMS
    # AND MV ROOMS". Ruling R12 (12.10.2026): an MV room is its own flag, treated as HV
    # for extinguishers (wheeled CO2 12 kg, labelled an engineering decision), Table 8.14
    # item 11 by analogy, and Table 9.30.J as printed.
    has_lv_mv_room: bool = False
    has_mv_room: bool = False
    has_transformer_room_utility: bool = False
    has_transformer_room_private: bool = False
    has_lift_machine_room: bool = True      # default True; uncheck for MRL elevators / no lift
    has_main_telephone_room: bool = True    # universal in any non-villa building
    has_main_server_room: bool = False
    has_rmu_idf_mdf_room: bool = False
    has_gsm_room: bool = False
    has_operation_theater: bool = False
    has_mri_scanning_room: bool = False
    has_records_room: bool = False
    has_ups_room: bool = False
    has_cold_freezer_room: bool = False

    # --- FP (Ch 9) - Various Locations (Table 9.29)
    has_exterior_balconies: bool = False    # Table 9.29 row B
    has_atrium: bool = False
    has_rain_screen_glazing: bool = False
    has_stairs: bool = True
    has_elevator: bool = True
    has_bathrooms_with_heaters: bool = False
    has_laundry_storage_rooms: bool = False
    has_pantries: bool = False
    has_permanent_stages: bool = False
    has_roof_lpg_or_restaurant: bool = False
    has_roof_restaurant_assembly: bool = False     # FA Table 8.14 item 36: roof used for restaurant seating / assembly / sheesha
    has_food_trucks: bool = False                  # FA Table 8.14 item 34: food trucks of any fuel
    has_garbage_chute: bool = False

    # --- FP (Ch 9) - Equipment (Table 9.31)
    has_commercial_kitchen: bool = False
    has_lpg_tanks: bool = False
    has_flammable_liquid_tanks: bool = False
    has_cable_spread_areas: bool = False
    has_boilers: bool = False
    has_cooling_towers: bool = False
    has_oil_filled_transformers: bool = False
    has_bulk_oil_storage: bool = False
    has_bulk_flammable_liquid_storage: bool = False
    has_bulk_flammable_gas_storage: bool = False
    has_bulk_flammable_solid_storage: bool = False
    has_high_hazard_logistics: bool = False
    has_chemical_warehouse: bool = False
    has_explosives: bool = False
    has_processing_plant: bool = False
    has_fire_pump_room: bool = True

    # --- ES (Ch 5) - Exit Sign-specific feature flags ----------------------
    has_evacuation_elevator: bool = False         # Table 5.1.6 / Ch 3 #3.9
    has_horizontal_exits: bool = False
    has_dead_end_paths: bool = True               # most buildings have likely-mistaken paths
    has_amusement_confounding: bool = False       # mazes, mirrors, play areas (assembly)
    has_nightclub_disco: bool = False
    has_theater_cinema: bool = False
    has_nursery_within: bool = False              # education sub-zone
    has_auditorium_within: bool = False           # education sub-zone
    has_hh_storage_zones: bool = False            # HH groups / robotic / cold / cable spread (storage)
    has_mall_play_food_cinema: bool = False       # mall sub-zone for photoluminescent
    has_robotic_parking: bool = False
    villa_converted_use: bool = False             # private/commercial villa converted to other use
    fuel_dispensing_multistorey: bool = False     # fuel station building > GF only

    # --- EL (Ch 6) - Egress / Coverage Features
    has_tunnel: bool = False                      # Table 6.6 item 9

    # --- FP (Ch 9) - Storage / Industrial sub-types (Table 9.27 specialty groups)
    is_aircraft_hanger: bool = False                # Group Q - aircraft hangers (group in `hangar_group`)
    is_cold_storage: bool = False                   # Group P - storage facilities below 4 deg C (dry type sprinklers)
    is_flammable_liquid_warehouse: bool = False     # Group R - foam + 120 min tank, in-rack
    is_flammable_liquid_industrial: bool = False    # Group S - foam sprinklers, processes
    is_open_yard_storage: bool = False              # Group U - outdoor/yard storage (no building envelope)
    is_plant_nursery: bool = False                  # Group V - extinguishers only
    is_single_tenant_storage: bool = False          # Groups F-J - single-tenant variants (different pump/tank than multi-tenant Groups A-E)
    is_idle_pallet_storage: bool = False            # Group K - idle wood/plastic pallet warehouse
    is_extra_hazard_2: bool = False                 # Multi-tenant HH: Group E (EH2, Definition 1.1.13.5) vs Group D (EH1, Definition 1.1.13.4 - default). Drives EH2's higher density (0.40 vs 0.30), higher pump (1000/1500 vs 750/1250 gpm), and 120-min tank.
    is_commodity_specific_storage: bool = False     # Legacy key (no longer routed): Groups L-O now follow `storage_commodity`.
    # Phase 2 (ch9): Table 9.27 inputs.
    storage_commodity: Literal["none", "class_i_iv", "plastics_rubber", "tires", "rolled_paper"] = "none"
    # Groups L (Class I-IV), M (plastic, rubber), N (tires), O (rolled paper); "none" routes by hazard class.
    max_unit_area_m2: float = Field(0.0, ge=0)      # #4.1.14 largest unit compartment area; 0 = not stated -> the ground-floor BUA (one unit)
    sum_gf_bua_m2: float = Field(0.0, ge=0)         # #4.1.13 sum of built-up ground floor areas of all buildings on the plot; 0 = not entered (owner ruling 12.10.2026, Ch9 Q1: required; blank takes Table 9.27 row 4, never a lower row)
    # Owner ruling 12.10.2026, Ch9 Q9: hazard of a storage_industrial SECONDARY occupancy
    # (R13 most-restrictive mode). None = not chosen: its Table 9.27 rows are not evaluated.
    # "EH2" = HH with Extra Hazard Group 2 (#1.1.13.5).
    secondary_storage_hazard: Optional[Literal["LH", "OH1", "OH2", "HH", "EH2"]] = None
    hangar_group: Literal["I", "II_III", "IV"] = "I"  # Table 9.27 Group Q.1 / Q.2 / Q.3; default Group I (most onerous)
    is_aboveground_tank_storage: bool = False       # Table 9.27 Group T - flammable / combustible liquids in aboveground storage tanks
    ast_storage_area_m2: float = Field(0.0, ge=0)   # Group T storage area; 0 = not stated -> row 2
    ast_tank_capacity_m3: float = Field(0.0, ge=0)  # Group T largest tank capacity; 0 = not stated -> row 2
    # --- FP (Ch 9) - Single-exit-stair / commercial-attached / tent variants
    # These drive Tables 9.20.c, 9.21.c, 9.21.e, 9.21.f branches.
    # (Table 9.21.d - villas converted to commercial - reuses the existing
    # `villa_converted_use` flag defined in the ES Ch 5 section above.)
    has_single_exit_stair: bool = False             # Tables 9.20.c, 9.21.c - building has only one exit stair
    has_attached_commercial_outlet: bool = False    # Table 9.21.e - villa/mosque/business with commercial outlet attached or in same plot
    tent_marquee_kind: Literal["none", "temporary", "permanent", "commercial_desert", "site_office_short", "site_office_long", "small_detached"] = "none"
    # Table 9.21.f - tents, marquees, site offices, site dwellings sub-types.
    # --- FP (Ch 9) - Tunnel Fire Protection (Table 9.28)
    tunnel_kind: Literal["road_rail", "cable"] = "road_rail"
    tunnel_length_m: float = 0.0


    # --- FE (Ch 4) - Hazard / Class flags
    has_class_b_storage_zones: bool = False       # chemical / linen / waste / flammable liquid / solvent / lab stores
    has_combustible_metals: bool = False          # magnesium / titanium / zirconium / sodium / lithium / potassium
    has_hv_or_heavy_electrical: bool = False      # HV room / heavy electrical machinery
    has_parking_area: bool = True                 # in-building parking area (most occupancies have one)
    attached_parking_kind: Literal["enclosed", "open"] = "enclosed"  # ATTACHED parking sub-occupancy: open vs enclosed (drives MOE/FP/FA/SC parking sub-evaluation)
    parking_area_m2: float = 0.0      # Footprint area of the attached parking - used as GFA / GF BUA in the parking sub-evaluation. If 0, falls back to basement_bua_m2 then ground_floor_bua_m2.

    # --- FP (Ch 9) - Motor Fuel Dispensing sub-group (Table 9.25 A/B/C)
    motor_fuel_group: Literal["A", "B", "C"] = "A"
    # A: petrol/gas station + mini marts/restaurants/dining/retail/business + service stations as INDIVIDUAL buildings
    #    -> Sprinklers + hose reel + 300 gpm @ 4.5 bar pump + 60 min tank
    # B: petrol/gas station + restaurants/bakeries WITHIN a single mini-mart + service/repair, fleet, marine
    #    -> Hose reel + 50 gpm @ 6.9 bar pump + 60 min tank (no sprinklers, no dry landing)
    # C: petrol/gas station with mini-marts ONLY (no service/repair) OR electric charging units
    #    -> Extinguishers per Ch 4 Table 4.3.2.8 (NO water-based fire-protection system)

    # --- LPG (Ch 11) - Gas system triggers
    has_gas_infra_connection: bool = False        # Building connected to municipal/central LPG infrastructure
    has_gas_cylinders_villa: bool = False         # Villa / domestic / small commercial LPG cylinders
    # --- LPG (Ch 11) - Add-on variants (layered on top of base gas type)
    has_lpg_tank_roof_mounted: bool = False        # Roof-mounted tanks (Tables 11.7 / 11.8)
    has_lpg_tank_underground_mounded: bool = False # Underground or mounded tanks (Tables 11.9 / 11.10)
    has_lpg_cylinders_indoor: bool = False         # Indoor cylinder room (Table 11.2)
    has_lpg_cylinders_food_truck: bool = False     # Food truck LPG (Table 11.3)
    has_lpg_flame_effect: bool = False             # Flame-effect shows in front of audience (Table 11.12)

    @property
    def building_category(self) -> str:
        if self.occupancy.startswith("villa_"):
            return "villa"
        if self.occupancy.startswith("mall_"):
            return "mall"
        if self.occupancy.startswith("parking_"):
            return "parking"
        if self.occupancy == "storage_industrial":
            return "storage_industrial"
        if self.occupancy == "motor_fuel_dispensing":
            return "fuel_dispensing"
        return "general"

    @model_validator(mode="after")
    def _height_stated(self):
        if self.height_m <= 0 and "height_m" in self.model_fields_set \
                and self.occupancy != "infrastructure":
            raise ValueError("Building height must be more than 0 m.")
        return self

    @property
    def is_high_depth(self) -> bool:
        """Ch 1 #1.7.45 (p.45): High Depth = more than 7 m below, or more than
        two basements below, the level of exit discharge."""
        return (self.occupancy == "high_depth_underground"
                or self.floors_below_grade >= 3 or self.depth_below_grade_m > 7)

    # ---- Table 9.27 tier areas (Ch 9 #4.1.11-#4.1.14, p.695) ----
    @property
    def storage_unit_area_m2(self) -> float:
        """#4.1.14 unit compartment area: the stated largest unit, else the whole
        ground floor taken as one unit (never smaller than the real unit)."""
        return self.max_unit_area_m2 if self.max_unit_area_m2 > 0 else self.ground_floor_bua_m2

    @property
    def storage_gf_bua_sum_m2(self) -> float:
        """#4.1.13 sum of built-up ground floor areas of the buildings on the plot;
        never less than this building's own ground-floor BUA. Owner ruling 12.10.2026,
        Ch9 Q1: the sum is required; when it is not entered (0) the tier is unknown, so
        it is taken above every printed tier limit (Table 9.27 row 4) and never a lower
        row. The engine prints a 'not evaluated' line naming the missing input."""
        if self.sum_gf_bua_m2 <= 0:
            return float("inf")
        return max(self.sum_gf_bua_m2, self.ground_floor_bua_m2)

    @property
    def storage_gf_bua_sum_missing(self) -> bool:
        """Owner ruling 12.10.2026, Ch9 Q1: the plot GF BUA sum (#4.1.13) is not entered."""
        return self.sum_gf_bua_m2 <= 0

    @property
    def storage_total_bua_m2(self) -> float:
        """#4.1.11 built-up area of all floors (total GFA), never less than the
        ground-floor BUA. Used where Table 9.27 prints 'total built-up floor area'."""
        return max(self.gross_floor_area_m2, self.ground_floor_bua_m2)

    @property
    def storage_compartment_floor_area_m2(self) -> float:
        """'Total built-up floor area of the compartment' (Groups N, O, R, S rows 1-2):
        the stated unit compartment area, else the building's total built-up area."""
        return self.max_unit_area_m2 if self.max_unit_area_m2 > 0 else self.storage_total_bua_m2

    @property
    def storage_has_specialty(self) -> bool:
        """True when a Table 9.27 specialty group (K, P, Q, R, S, T, U, V) is ticked."""
        return any((self.is_aircraft_hanger, self.is_cold_storage,
                    self.is_flammable_liquid_warehouse, self.is_flammable_liquid_industrial,
                    self.is_open_yard_storage, self.is_plant_nursery,
                    self.is_idle_pallet_storage, self.is_aboveground_tank_storage))

    @property
    def largest_storey_area_min_m2(self) -> float:
        """Largest storey area for Table 3.27 item 2.iii (villa floor over 400 m2):
        the entered largest storey area (owner ruling 12.10.2026, Ch3 Q1), never
        less than the ground-floor BUA; without it, a lower bound: the ground-floor
        BUA, or the GFA spread evenly over every storey above and below grade,
        whichever is larger."""
        if self.largest_storey_area_m2 > 0:
            return max(self.largest_storey_area_m2, self.ground_floor_bua_m2)
        n = self.floors_above_grade + self.floors_below_grade
        return max(self.ground_floor_bua_m2, self.gross_floor_area_m2 / n if n else 0.0)

    @property
    def use_area_total_m2(self) -> float:
        """Sum of the per-use areas entered (Ch3 Q2); 0 = none entered. When the
        per-storey table has lines it governs (owner answer 12.10.2026, F6) and its
        areas are summed instead."""
        if self.storey_uses:
            return sum(u.area_m2 for u in self.storey_uses)
        return sum(u.area_m2 for u in self.use_areas)

    @property
    def fire_lift_2_9_4_reasons(self) -> List[str]:
        """Ch 2 #2.9.4.a (p.220): at least one Fire Lift in any building which is
        'Highrise' with 23 m or more in height, 'High Depth' with more than 2
        basements, Malls and multi storey Amusement Parks. One trigger for the FSA
        Fire Lift line and the Ch 10 'NOT mandatory' line (owner ruling 12.10.2026,
        Ch3 Q9)."""
        hits = (("highrise of 23 m or more", self.height_m >= 23),
                ("high depth with more than 2 basements", self.floors_below_grade > 2),
                ("mall", self.occupancy in ("mall_covered", "mall_open", "mall_mixed")),
                ("multi storey amusement park", self.is_theme_park and self.floors_above_grade > 1))
        return [why for why, hit in hits if hit]

    @property
    def requires_fire_lift_2_9_4(self) -> bool:
        return bool(self.fire_lift_2_9_4_reasons)

    @property
    def pump_head_height_m(self) -> float:
        """Height of the most remote landing valve above the fire pump
        (Table 9.6 item 13; Table 9.19 rows A/B "from lowest pump set level").
        The pump room is taken at the lowest basement unless pump_room_at_grade."""
        return self.height_m + (0.0 if self.pump_room_at_grade else self.depth_below_grade_m)

    @property
    def height_class(self) -> str:
        # Ch 1 #1.7.39-1.7.42, Table 1.7 (p.67), FAQ Q27 (p.1282), Ch 2 #2.9.3/#2.9.4:
        #   lowrise  : height up to 15 m
        #   midrise  : more than 15 m and less than 23 m
        #   highrise : 23 m up to 90 m (ruling R1, 12.10.2026: exactly 23.0 m is highrise
        #              in every chapter; Table 1.7 prints "23 m - < 90 m")
        #   super    : more than 90 m
        if self.height_m > 90:
            return "super_highrise"
        if self.height_m >= 23:
            return "highrise"
        if self.height_m > 15:
            return "midrise"
        return "lowrise"


class Requirement(BaseModel):
    system: str
    status: Literal["required", "recommended", "conditional", "not_required"] = "required"
    spec: Optional[str] = None
    detail: Optional[str] = None
    code_ref: Optional[str] = None
    page_ref: Optional[str] = None
    source_rule: Optional[str] = None
    duty: Optional[str] = None   # "pump" / "tank": one governing line per building (engine._merge_duties)


class HighCeilingSpec(BaseModel):
    applies: bool
    not_required: bool = False      # ruling R8: building has no sprinkler system
    ceiling_height_m: float
    hazard_class: str
    height_range: Optional[str] = None
    k_factor: Optional[str] = None
    min_pressure: Optional[str] = None
    min_sprinklers: Optional[int] = None
    density: Optional[str] = None
    design_area: Optional[str] = None
    pump_without_hydrant_gpm: Optional[int] = None
    pump_with_hydrant_gpm: Optional[int] = None
    code_ref: Optional[str] = None
    page_ref: Optional[str] = None
    note: Optional[str] = None




class OccupantLoadSummary(BaseModel):
    """Table 3.13 factor → OL → Table 3.14 min exits."""
    area_m2: float = 0.0
    factor_m2_per_person: float = 0.0
    factor_ref: str = ""
    occupant_load: int = 0
    min_exits: int = 2
    exit_ref: str = ""
    note: str = ""
    # Owner rulings 12.10.2026, Ch3 Q1-Q3: evaluated=False means no exit count is
    # stated (min_exits 0); storey_* is the storey OL that Table 3.14 ran on.
    evaluated: bool = True
    storey_area_m2: float = 0.0
    storey_occupant_load: int = 0
    # Owner answer 12.10.2026, F6: per-storey table results. governing_storey is the
    # storey whose OL sets the Table 3.14 count; warnings are input checks to show.
    governing_storey: str = ""
    storeys: List["StoreyLoad"] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class StoreyLoad(BaseModel):
    """One storey of the per-storey table (F6): area, OL and Table 3.14 exits."""
    storey: str
    area_m2: float = 0.0
    occupant_load: int = 0
    min_exits: int = 0
    parts: List[str] = Field(default_factory=list)


class FireAccessSummary(BaseModel):
    """Ch 2 vehicle access extent and clearances."""
    accessway_width_m: float = 6.0
    vertical_clearance_m: float = 4.5
    max_distance_entrance_m: float = 15.0
    max_distance_breeching_m: float = 18.0
    max_road_grade_pct: float = 10.0
    extent: str = ""
    extent_ref: str = ""
    footprint_m2: float = 0.0
    sprinklered_assumed: bool = True
    notes: List[str] = Field(default_factory=list)

class SectionBlock(BaseModel):
    """One titled group of requirements in a chapter result."""
    title: str                                 # already prefix-tagged (e.g. "FP - General ...")
    items: List[Requirement] = Field(default_factory=list)


class ChapterReport(BaseModel):
    chapter_code: str                          # "FP", "ES", ...
    chapter_title: str                         # "Fire Protection (Ch 9)"
    selected_branch: Optional[str] = None
    selected_branch_section: Optional[str] = None
    blocks: List[SectionBlock] = Field(default_factory=list)
    extras: Dict[str, Any] = Field(default_factory=dict)


class ComplianceReport(BaseModel):
    building: Building
    chapters: List[ChapterReport] = Field(default_factory=list)
    requires_wet_riser: bool = False
    high_ceiling: Optional[HighCeilingSpec] = None
    attached_parking_chapters: List[ChapterReport] = Field(default_factory=list)
    occupant_load: Optional[OccupantLoadSummary] = None
    fire_access: Optional[FireAccessSummary] = None
    mixed_occupancy_note: Optional[str] = None

    def chapter(self, code: str) -> Optional[ChapterReport]:
        return next((c for c in self.chapters if c.chapter_code == code), None)

    @property
    def fp(self) -> Optional[ChapterReport]:
        return self.chapter("FP")

    @property
    def es(self) -> Optional[ChapterReport]:
        return self.chapter("ES")

    def count_status(self) -> Dict[str, int]:
        tot = {"required": 0, "recommended": 0, "conditional": 0, "not_required": 0}
        for ch in self.chapters:
            for blk in ch.blocks:
                for it in blk.items:
                    tot[it.status] = tot.get(it.status, 0) + 1
        return tot
