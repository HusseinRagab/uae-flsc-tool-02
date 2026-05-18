"""UAE FLSC 2018 compliance tool - data models (Pydantic v2). Multi-chapter."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


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
    # NOTE: Education group letters swapped 2026-05 to match UAE FLSC Ch 3 §5.3 / Table 3.13.3.
    # Per code: Group A = Nurseries / KG / Preschool (Table 3.20); Group B/C = Schools and Colleges
    # / Universities (Table 3.21). Schema IDs preserved (education_a/_b/_c) for backward compat
    # with saved scenarios; their meaning is the code's meaning, not the schema's original.
    "education_a": "Educational Group A - Nurseries, KG1/KG2, Preschool, Talent Centers (Table 3.20).",
    "education_b": "Educational Group B - Schools: Grade 1 through 12 (Table 3.21).",
    "education_c": "Educational Group C - Colleges, Universities, adult education (Table 3.21).",
    "mercantile_a": "Mercantile Group A - Retail up to 2 storeys and less than 2,800 m2. Shops, showrooms, boutiques.",
    "mercantile_b": "Mercantile Group B - Retail more than 2 storeys or exceeding 2,800 m2. Department stores, hypermarkets (stand-alone).",
    "healthcare_a": "Healthcare Group A - Hospitals, nursing homes, inpatient medical facilities where occupants require assistance for evacuation (Table 3.22).",
    "healthcare_b": "Healthcare Group B - Clinics, day-surgery and outpatient medical facilities (Table 3.22).",
    "healthcare_c": "Healthcare Group C - Ambulatory healthcare, walk-in clinics, dental/eye/diagnostic centres (Table 3.23).",
    "hotel_a": "Hotel Group A - Luxury / 4-5 star hotels.",
    "hotel_b": "Hotel Group B - Mid-range hotels (2-3 star).",
    "hotel_c": "Hotel Group C - Budget hotels, apartment hotels, furnished apartments.",
    "daycare_a": "Daycare Group A - Daycare for more than 12 clients.",
    "daycare_b": "Daycare Group B - Daycare for 7 to 12 clients.",
    # daycare_c: UAE FLSC Ch 3 §5.10 only defines Daycare Groups A and B. Schema keeps _c as a
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
    "villa_private": "Private Villa - Single-family detached dwelling for one family. G, G+1, G+2 typical.",
    "villa_commercial": "Commercial Villa - Villa used as nursery / clinic / office / salon / pharmacy / small showroom. Converted residential structure for non-residential use.",
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

HAZARD_BY_OCCUPANCY = {
    "assembly_a": "OH1", "assembly_b": "OH1", "assembly_c": "OH1",
    "business": "LH",
    "education_a": "LH", "education_b": "LH", "education_c": "LH",
    "mercantile_a": "OH1", "mercantile_b": "OH2",
    "healthcare_a": "LH", "healthcare_b": "LH", "healthcare_c": "LH",
    "hotel_a": "LH", "hotel_b": "LH", "hotel_c": "LH",
    "daycare_a": "LH", "daycare_b": "LH", "daycare_c": "LH",
    "residential": "LH",
    "labour_accommodation": "OH1", "staff_accommodation": "LH",
    "hostel": "LH", "animal_housing": "OH1",
    "detention_a": "OH1", "detention_b": "OH1", "detention_c": "OH1",
    "villa_private": "LH", "villa_commercial": "LH",
    "mall_covered": "OH2", "mall_open": "OH2", "mall_mixed": "OH2",
    "parking_enclosed": "OH2", "parking_open": "OH1",
    "storage_industrial": "OH2", "motor_fuel_dispensing": "HH", "infrastructure": "OH1",
    "mixed_multiple": "OH2",
    "high_depth_underground": "OH2", "low_depth_underground": "OH2",
}

MIDRISE_PUBLIC = {
    "assembly_a", "assembly_b", "assembly_c",
    "education_a", "education_b", "education_c",
    "healthcare_a", "healthcare_b", "healthcare_c",
    "mercantile_a", "mercantile_b",
    "hotel_a", "hotel_b", "hotel_c",
    "daycare_a", "daycare_b", "daycare_c",
    "mixed_multiple", "high_depth_underground",
}
MIDRISE_RESIDENTIAL = {
    "residential", "labour_accommodation", "staff_accommodation",
    "hostel", "business", "animal_housing",
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


class Building(BaseModel):
    project_name: str = Field("", description="Project reference")
    occupancy: Occupancy
    secondary_occupancies: List[Occupancy] = Field(default_factory=list)

    height_m: float = 0.0
    floors_above_grade: int = 1
    floors_below_grade: int = 0
    depth_below_grade_m: float = 0.0   # SC Ch 10 - >7 m underground trigger (Table 10.22)
    gross_floor_area_m2: float = 0.0
    ground_floor_bua_m2: float = 0.0
    basement_bua_m2: float = 0.0
    plot_area_m2: float = 0.0
    corridor_length_m: float = 0.0     # SC Ch 10 - >60 m enclosed-corridor trigger (Table 10.27 item 4)
    assembly_area_m2: float = 0.0      # SC Ch 10 - >2000 m² assembly hall trigger (Table 10.27 items 9-13: exhibition/assembly/sports/auditorium/stadium). If 0 and occupancy is assembly_*, falls back to gross_floor_area_m2.

    hazard_class: Literal["LH", "OH1", "OH2", "HH"] = "OH1"

    # --- FP (Ch 9) - High Ceiling
    has_high_ceiling: bool = False
    ceiling_height_m: float = 0.0
    wet_riser_standpipes: int = 2

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
    # has_lv_mv_room: code Table 8.14/9.30 item 11 mentions "LV ROOM" only; MV is treated
    # the same here as an engineering-safe interpretation. Keep the combined flag for UI
    # simplicity; surface MV in the rule detail text rather than splitting the flag.
    has_lv_mv_room: bool = False
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

    # --- FP (Ch 9) - Various Locations (Table 9.29) (balcony removed earlier)
    has_atrium: bool = False
    has_rain_screen_glazing: bool = False
    has_stairs: bool = True
    has_elevator: bool = True
    has_bathrooms_with_heaters: bool = False
    has_laundry_storage_rooms: bool = False
    has_pantries: bool = False
    has_permanent_stages: bool = False
    has_roof_lpg_or_restaurant: bool = False
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
    is_aircraft_hanger: bool = False                # Group Q - foam deluge, 1500 gpm pump
    is_cold_storage: bool = False                   # Group P - dry-pipe sprinklers (< 40 deg C)
    is_flammable_liquid_warehouse: bool = False     # Group R - foam + 120 min tank, in-rack
    is_flammable_liquid_industrial: bool = False    # Group S - foam sprinklers, processes
    is_open_yard_storage: bool = False              # Group U - outdoor/yard storage (no building envelope)
    is_plant_nursery: bool = False                  # Group V - extinguishers only
    is_single_tenant_storage: bool = False          # Groups F-J - single-tenant variants (different pump/tank than multi-tenant Groups A-E)
    is_idle_pallet_storage: bool = False            # Group K - idle wood/plastic pallet warehouse
    is_extra_hazard_2: bool = False                 # Multi-tenant HH: Group E (EH2, Definition 1.1.13.5) vs Group D (EH1, Definition 1.1.13.4 - default). Drives EH2's higher density (0.40 vs 0.30), higher pump (1000/1500 vs 750/1250 gpm), and 120-min tank.
    is_commodity_specific_storage: bool = False     # Opt-in for Table 9.27 Groups L-O (Class I-IV / plastics / rubber / tires / paper) commodity-driven design. Routes the HH match to the commodity-specific catch-all rule.
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

    @property
    def height_class(self) -> str:
        if self.height_m > 90:
            return "super_highrise"
        if self.height_m > 23:
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


class HighCeilingSpec(BaseModel):
    applies: bool
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
    attached_parking_chapters: List[ChapterReport] = Field(default_factory=list)  # parking sub-occupancy when has_parking_area + non-parking main occupancy

    def chapter(self, code: str) -> Optional[ChapterReport]:
        return next((c for c in self.chapters if c.chapter_code == code), None)

    @property
    def fp(self) -> Optional[ChapterReport]:
        return self.chapter("FP")

    @property
    def es(self) -> Optional[ChapterReport]:
        return self.chapter("ES")
