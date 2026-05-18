"""UAE FLSC 2018 - Multi-chapter Fire & Life Safety. Streamlit UI.

Chapter prefixes:
  FE  Fire Extinguishers (Ch 4)
  ES  Exit Signs (Ch 5)
  EL  Emergency Lighting (Ch 6)
  EVC Voice Evacuation (Ch 7)
  FA  Fire Detection & Alarm (Ch 8)
  FP  Fire Protection (Ch 9)
  SC  Smoke Control (Ch 10)
  LPG Liquefied Petroleum Gas (Ch 11)

Special-rooms / various-locations / equipment flags drive multiple chapters and live
in a SHARED 'Special Rooms & Equipment' master block. Per-chapter expanders carry
only items truly unique to that chapter.
"""
from __future__ import annotations

import streamlit as st

from flsc_schema import Building, OCCUPANCY_DEFS, default_hazard, DISCLAIMER
from engine import evaluate, report_to_markdown, build_rule_lookup
from export import report_to_docx_bytes, report_to_pdf_bytes


# Index of source_rule -> {file, kind, match} for the "Why triggered?" expander.
# Cached so it builds once per server start (rules YAMLs don't change at runtime).
@st.cache_data(show_spinner=False)
def _cached_rule_lookup():
    return build_rule_lookup()


# Glossary used by the sidebar "📖 Glossary" expander (Tier 2 UI #6).
# Acronyms / terms that appear in chapter outputs, ordered alphabetically.
GLOSSARY = [
    ("AFFL", "Above Finished Floor Level"),
    ("Aspiration", "Aspirating Smoke Detection — drawn-air analyser; very early warning (e.g. VESDA). Used in cold storage, server rooms, very high ceilings."),
    ("BUA", "Built-Up Area — the floor area enclosed by a building's exterior walls."),
    ("CD", "Civil Defence — the UAE federal authority enforcing the Fire & Life Safety Code."),
    ("CDGH-OP-25", "Operational reference of the UAE FLSC 2018 edition (Civil Defence Guideline Handbook, Operational Procedure 25)."),
    ("EH1 / EH2", "Extra Hazard Group 1 / 2 — sprinkler hazard classification (NFPA 13). EH1 = significant Class A/B combustibles; EH2 = quantities of flammable/combustible liquids."),
    ("ESFR", "Early Suppression Fast Response (sprinkler) — high-flow head designed to control + suppress a developing fire, common in rack storage."),
    ("ESV", "Emergency Shut-off Valve — required on LPG, gas, and some chemical lines, accessible from outside the protected area."),
    ("EVC", "Emergency Voice Communication / Voice-Evacuation system — programmable PA + tone system (Ch 7)."),
    ("FACP", "Fire Alarm Control Panel — the master detection/notification controller."),
    ("FCC", "Fire Command Centre — purpose-built control room with FACP, EVC, sprinkler annunciation, generator status, etc."),
    ("FFE", "Final Floor Elevation."),
    ("FHC", "Fire Hose Cabinet — wall-mounted cabinet containing a hose reel and (often) extinguishers."),
    ("GFA", "Gross Floor Area — total floor area summed across all storeys."),
    ("HC", "High Challenge (wall / fire wall) — enhanced fire-resistance assembly per code Ch 1."),
    ("HE", "Horizontal Exit — passage through a fire-rated wall into another fire compartment on the same level."),
    ("HH", "High Hazard — sprinkler hazard classification with rapidly developing fires (e.g. flammable liquid warehouse)."),
    ("HoE", "House of Expertise — UAE Civil Defence designation for an approved fire consultancy."),
    ("Hose Reel", "Manually operated water hose, typically 30 m × 19 mm, fed from a 250 gpm pump per UAE Ch 9."),
    ("IDF / MDF", "Intermediate / Main Distribution Frame — telecoms cross-connect rooms."),
    ("IS", "Intrinsically Safe — electrical equipment certified for hazardous (explosive) atmospheres."),
    ("K-factor", "Sprinkler discharge coefficient (US units): flow Q = K·√P. K11.2 / K25.2 etc."),
    ("KG", "Kindergarten (educational Group A in UAE FLSC)."),
    ("LEL", "Lower Explosive Limit — minimum gas concentration in air that will ignite. UAE LPG code sets gas-leak alarm at 15% LEL (low) / 30% LEL (high)."),
    ("LH", "Light Hazard — sprinkler hazard classification with limited combustibles (offices, residential, schools)."),
    ("LPG", "Liquefied Petroleum Gas (Ch 11)."),
    ("LV / MV", "Low Voltage / Medium Voltage electrical rooms."),
    ("MCP", "Manual Call Point — wall-mounted manual fire-alarm push station, 1.2 m AFFL, every 61 m."),
    ("MOE", "Means of Egress (Ch 3)."),
    ("MRI", "Magnetic Resonance Imaging room (healthcare auxiliary, Table 9.30.S)."),
    ("MRL", "Machine Room-Less elevator — has no separate machine room (uncheck `has_lift_machine_room` if applicable)."),
    ("NFPA", "National Fire Protection Association (US) — UAE FLSC defers to NFPA 10/13/14/72/96 etc. in many sections."),
    ("NS / S", "Non-Sprinklered / Sprinklered — Table 3.16 column heads (Means of Egress)."),
    ("OH1 / OH2", "Ordinary Hazard Group 1 / 2 — sprinkler hazard classifications (NFPA 13)."),
    ("OL", "Occupant Load — number of occupants used to size egress (Tables 3.13/3.14)."),
    ("OT", "Operating Theatre (healthcare auxiliary)."),
    ("Pa", "Pascals — pressure unit used for stair / lobby pressurisation (UAE Ch 10 Table 10.3.a: 12.5–45 Pa)."),
    ("PAS", "Positive Alarm Sequence — timed alarm delay (typically 15 s / 180 s / 240 s) to let staff investigate before mass notification."),
    ("PRDP", "Pressure Reducing Distribution Panel — Stage-2 regulator + ESV serving a single kitchen / apartment in central LPG distribution."),
    ("PRV", "Pressure Relief Valve — required on every LPG container; replace every 10 years per Table 11.14."),
    ("RMU", "Ring Main Unit — medium-voltage switchgear in a small dedicated room."),
    ("STI", "Speech Transmission Index — voice-evacuation intelligibility metric."),
    ("UL / FM", "Underwriters Laboratories / Factory Mutual — US product-listing bodies (FACP, sprinkler heads, fire pumps must be UL/FM listed)."),
    ("UPS", "Uninterruptible Power Supply room (electrical auxiliary, Table 9.30.U)."),
    ("VESDA", "Very Early Smoke Detection Apparatus — brand-leading aspiration smoke detector."),
    ("Wet Riser", "Vertical water-filled pipe with fire-brigade landing valves on each floor; sized 750 gpm (2 standpipes) or 1000 gpm (3+ standpipes) @ 6.9 bar."),
    ("Yard Hydrant", "External fire-brigade hydrant on a dedicated water network (not shared with irrigation). UAE typically 1000 gpm @ 6.9 bar / 90-min tank for infrastructure."),
]


# ----- Cached evaluate to remove the ~0.4 s lag on every input change -----
@st.cache_data(show_spinner=False)
def _cached_evaluate(building_json: str):
    """Cache compliance reports keyed on the JSON-serialised Building.
    Streamlit hashes the JSON string and serves the cached ComplianceReport when
    the same input recurs (very common during sidebar tweaking)."""
    return evaluate(Building.model_validate_json(building_json))


OCCUPANCY_OPTIONS = {
    "Villa": ["villa_private", "villa_commercial"],
    "Residential / Lodging": ["residential", "hotel_a", "hotel_b", "hotel_c",
                               "hostel", "labour_accommodation", "staff_accommodation"],
    "Business / Office": ["business"],
    "Assembly": ["assembly_a", "assembly_b", "assembly_c"],
    "Mall": ["mall_covered", "mall_open", "mall_mixed"],
    "Mercantile": ["mercantile_a", "mercantile_b"],
    "Education": ["education_a", "education_b", "education_c"],
    "Healthcare": ["healthcare_a", "healthcare_b", "healthcare_c"],
    "Daycare": ["daycare_a", "daycare_b", "daycare_c"],
    "Detention": ["detention_a", "detention_b", "detention_c"],
    "Parking": ["parking_enclosed", "parking_open"],
    "Storage / Industrial": ["storage_industrial", "motor_fuel_dispensing"],
    "Mixed / Underground": ["mixed_multiple", "high_depth_underground",
                            "low_depth_underground", "animal_housing"],
}
OCC_FLAT = [(g, occ) for g, items in OCCUPANCY_OPTIONS.items() for occ in items]


# ---------------- Master 'Check all' helper ----------------------------------
def _register_master(master_key: str, child_keys: list[str]):
    if master_key not in st.session_state:
        st.session_state[master_key] = False
    for k in child_keys:
        st.session_state.setdefault(k, False)

    def _cb():
        v = st.session_state[master_key]
        for k in child_keys:
            st.session_state[k] = v
    return _cb


# ----------------- SHARED Special Rooms & Equipment groups -----------------
SPECIAL_ROOMS_KEYS = [
    "has_anesthetizing_room", "has_battery_charger_room", "has_bms_room",
    "has_battery_room", "has_computer_room", "has_control_room",
    "has_diesel_generator_room", "has_main_electrical_room", "has_ahu_room",
    "has_lv_mv_room", "has_transformer_room_utility",
    "has_transformer_room_private", "has_lift_machine_room",
    "has_main_telephone_room", "has_main_server_room", "has_rmu_idf_mdf_room",
    "has_gsm_room", "has_operation_theater", "has_mri_scanning_room",
    "has_records_room", "has_ups_room", "has_cold_freezer_room",
    "has_fire_pump_room",
]
VARIOUS_LOCATIONS_KEYS = [
    "has_atrium", "has_rain_screen_glazing", "has_stairs", "has_elevator",
    "has_bathrooms_with_heaters", "has_laundry_storage_rooms", "has_pantries",
    "has_permanent_stages", "has_roof_lpg_or_restaurant", "has_garbage_chute",
    "has_high_ceiling", "has_tunnel",
]
EQUIPMENT_KEYS = [
    "has_commercial_kitchen", "has_flammable_liquid_tanks",
    "has_cable_spread_areas", "has_boilers", "has_cooling_towers",
    "has_oil_filled_transformers", "has_bulk_oil_storage",
    "has_bulk_flammable_liquid_storage", "has_bulk_flammable_gas_storage",
    "has_bulk_flammable_solid_storage", "has_high_hazard_logistics",
    "has_chemical_warehouse", "has_explosives", "has_processing_plant",
]

# Per-chapter unique groups
FE_KEYS = [
    "has_class_b_storage_zones", "has_combustible_metals",
    "has_hv_or_heavy_electrical", "has_parking_area",
]
ES_FEATURE_KEYS = ["has_evacuation_elevator", "has_horizontal_exits", "has_dead_end_paths"]
ES_ZONE_KEYS = [
    "has_amusement_confounding", "has_nightclub_disco", "has_theater_cinema",
    "has_nursery_within", "has_auditorium_within", "has_hh_storage_zones",
    "has_mall_play_food_cinema", "has_robotic_parking",
    "villa_converted_use", "fuel_dispensing_multistorey",
]

# First-load defaults
for key, default in (
    ("has_stairs", True), ("has_elevator", True),
    ("has_diesel_generator_room", True), ("has_main_electrical_room", True),
    ("has_main_telephone_room", True), ("has_lift_machine_room", True),
    ("has_fire_pump_room", True),
    ("has_parking_area", True),
    ("has_dead_end_paths", True),
    # Geometry inputs are session_state-driven so presets can write to them
    ("height_m_input", 45.0),
    ("floors_above_input", 12),
    ("floors_below_input", 1),
    ("ground_bua_input", 800.0),
    ("basement_bua_input", 0.0),
    ("gfa_input", 8000.0),
    ("plot_area_input", 4000.0),
    ("depth_below_grade_input", 0.0),
):
    st.session_state.setdefault(key, default)

# =============================================================================
# Occupancy-aware flag auto-clear (silent UX, no nagging)
# =============================================================================
# When the user picks an occupancy that doesn't typically have certain rooms
# / equipment, those flags are auto-unchecked in session_state. The user can
# still tick anything manually if their specific project needs it — no
# warnings, no flags, just sensible defaults.
#
# Defined as a dict so we can mirror the same logic for villa, petrol station,
# animal housing, family daycare, etc.

# Villa-specific incompatible flag list (single-family dwellings).
VILLA_INCOMPATIBLE_FLAGS = [
    # Special Rooms — none of these are present in a typical villa
    "has_anesthetizing_room", "has_battery_charger_room", "has_bms_room",
    "has_battery_room", "has_computer_room", "has_control_room",
    "has_diesel_generator_room", "has_main_electrical_room", "has_ahu_room",
    "has_lv_mv_room", "has_transformer_room_utility",
    "has_transformer_room_private", "has_lift_machine_room",
    "has_main_telephone_room", "has_main_server_room", "has_rmu_idf_mdf_room",
    "has_gsm_room", "has_operation_theater", "has_mri_scanning_room",
    "has_records_room", "has_ups_room", "has_cold_freezer_room",
    "has_fire_pump_room",
    # Various locations — stair shaft sprinklers + elevator pit sprinklers
    # don't apply to villas (Ch 9 villa branches don't require sprinklers).
    "has_stairs", "has_elevator",
    "has_atrium", "has_rain_screen_glazing", "has_bathrooms_with_heaters",
    "has_laundry_storage_rooms", "has_pantries", "has_permanent_stages",
    "has_roof_lpg_or_restaurant", "has_garbage_chute", "has_tunnel",
    # Equipment / commercial / industrial
    "has_commercial_kitchen", "has_flammable_liquid_tanks",
    "has_cable_spread_areas", "has_boilers", "has_cooling_towers",
    "has_oil_filled_transformers", "has_bulk_oil_storage",
    "has_bulk_flammable_liquid_storage", "has_bulk_flammable_gas_storage",
    "has_bulk_flammable_solid_storage", "has_high_hazard_logistics",
    "has_chemical_warehouse", "has_explosives", "has_processing_plant",
    # FE hazard add-ons
    "has_class_b_storage_zones", "has_combustible_metals",
    "has_hv_or_heavy_electrical",
    # ES special zones
    "has_amusement_confounding", "has_nightclub_disco", "has_theater_cinema",
    "has_nursery_within", "has_auditorium_within", "has_hh_storage_zones",
    "has_mall_play_food_cinema", "has_robotic_parking",
    "fuel_dispensing_multistorey",
]


# "Infrastructure" is a yard-hydrant network only — NOT a building. Clear
# every building-level flag.
INFRASTRUCTURE_INCOMPATIBLE_FLAGS = VILLA_INCOMPATIBLE_FLAGS + [
    "has_parking_area",
]


# Animal housing — typically a single-storey stable / kennel / barn.
ANIMAL_HOUSING_INCOMPATIBLE_FLAGS = [
    "has_elevator", "has_lift_machine_room",
    "has_diesel_generator_room", "has_main_telephone_room",
    "has_fire_pump_room", "has_parking_area",
    "has_commercial_kitchen", "has_atrium", "has_garbage_chute",
    "has_anesthetizing_room", "has_operation_theater", "has_mri_scanning_room",
    "has_records_room", "has_ups_room", "has_main_server_room",
    "has_rmu_idf_mdf_room", "has_gsm_room", "has_bms_room",
    "has_battery_charger_room", "has_battery_room", "has_computer_room",
    "has_control_room", "has_cold_freezer_room",
]


# Daycare Group B (7-12 clients) — often in a villa-sized building.
DAYCARE_B_INCOMPATIBLE_FLAGS = [
    "has_elevator", "has_lift_machine_room", "has_diesel_generator_room",
    "has_main_telephone_room", "has_fire_pump_room",
    "has_commercial_kitchen", "has_atrium",
    "has_anesthetizing_room", "has_operation_theater",
    "has_mri_scanning_room", "has_main_server_room",
    "has_rmu_idf_mdf_room", "has_gsm_room",
]


# Daycare Group C (4-6 clients, family daycare) — villa-like in scale.
DAYCARE_C_INCOMPATIBLE_FLAGS = VILLA_INCOMPATIBLE_FLAGS


# Motor fuel dispensing (petrol station) — single-storey canopy + small
# kiosk. Group A may have a fire pump room; Group B/C typically don't.
PETROL_STATION_INCOMPATIBLE_FLAGS = [
    "has_stairs", "has_elevator", "has_lift_machine_room",
    "has_main_telephone_room", "has_diesel_generator_room",
    "has_atrium", "has_garbage_chute", "has_pantries",
    "has_anesthetizing_room", "has_battery_charger_room", "has_bms_room",
    "has_battery_room", "has_computer_room",
    "has_lv_mv_room", "has_transformer_room_utility",
    "has_transformer_room_private",
    "has_main_server_room", "has_rmu_idf_mdf_room", "has_gsm_room",
    "has_operation_theater", "has_mri_scanning_room",
    "has_records_room", "has_ups_room", "has_cold_freezer_room",
    "has_parking_area",
    "has_commercial_kitchen", "has_flammable_liquid_tanks",
    "has_bulk_oil_storage", "has_bulk_flammable_gas_storage",
    "has_bulk_flammable_solid_storage", "has_high_hazard_logistics",
    "has_chemical_warehouse", "has_explosives", "has_processing_plant",
    "has_permanent_stages", "has_amusement_confounding",
    "has_nightclub_disco", "has_theater_cinema",
    "has_nursery_within", "has_auditorium_within",
    "has_hh_storage_zones", "has_mall_play_food_cinema",
    "has_robotic_parking", "villa_converted_use",
]


# Small mercantile (<2 storeys, <2,800 m²) — typically no lift / diesel gen.
MERCANTILE_A_INCOMPATIBLE_FLAGS = [
    "has_elevator", "has_lift_machine_room",
    "has_diesel_generator_room",
    "has_anesthetizing_room", "has_operation_theater",
    "has_mri_scanning_room",
]


# Map every occupancy to its incompatible-flag list. Occupancies absent from
# the dict use the universal first-load defaults (typical multi-family/
# commercial building) — no auto-clear happens for them.
INCOMPATIBLE_FLAGS_BY_OCC = {
    "villa_private":          VILLA_INCOMPATIBLE_FLAGS,
    "villa_commercial":       VILLA_INCOMPATIBLE_FLAGS,
    "infrastructure":         INFRASTRUCTURE_INCOMPATIBLE_FLAGS,
    "animal_housing":         ANIMAL_HOUSING_INCOMPATIBLE_FLAGS,
    "daycare_b":              DAYCARE_B_INCOMPATIBLE_FLAGS,
    "daycare_c":              DAYCARE_C_INCOMPATIBLE_FLAGS,
    "motor_fuel_dispensing":  PETROL_STATION_INCOMPATIBLE_FLAGS,
    "mercantile_a":           MERCANTILE_A_INCOMPATIBLE_FLAGS,
    "hostel":                 ["has_parking_area"],
    "parking_enclosed":       ["has_main_telephone_room"],
    "parking_open":           ["has_diesel_generator_room",
                                "has_main_telephone_room"],
    "storage_industrial":     ["has_elevator", "has_lift_machine_room"],
}


def _apply_incompatible_flag_reset(occupancy: str) -> None:
    """Silently set incompatible flags to False for the given occupancy.
    Does NOT touch flags that are compatible — user keeps their state."""
    for flag in INCOMPATIBLE_FLAGS_BY_OCC.get(occupancy, []):
        st.session_state[flag] = False


# ---------------- Archetype presets ----------------
# A preset writes geometry + occupancy + a few common flags. Selecting "Custom" leaves
# everything as-is so the user can build from scratch.
ARCHETYPE_PRESETS = {
    "Custom (manual entry)": None,
    "Private villa G+1 (250 m² GF, 600 m² plot)": {
        "occ": "villa_private",
        "height_m_input": 6.0, "floors_above_input": 2, "floors_below_input": 0,
        "ground_bua_input": 250.0, "basement_bua_input": 0.0,
        "gfa_input": 500.0, "plot_area_input": 600.0,
        "has_parking_area": False,
        # Villas don't have these — _apply_preset() also enforces this
        # via VILLA_INCOMPATIBLE_FLAGS but listing the most-important ones
        # here makes the preset self-documenting.
        "has_diesel_generator_room": False,
        "has_main_electrical_room": False,
        "has_main_telephone_room": False,
        "has_lift_machine_room": False,
        "has_fire_pump_room": False,
        "has_stairs": False,    # Ch 9 villa branches don't require stair sprinklers
        "has_elevator": False,  # Ch 9 villa branches don't require elevator pit sprinklers
    },
    "Lowrise residential (G+3, 800 m² GF)": {
        "occ": "residential",
        "height_m_input": 14.0, "floors_above_input": 4, "floors_below_input": 1,
        "ground_bua_input": 800.0, "basement_bua_input": 800.0,
        "gfa_input": 3200.0, "plot_area_input": 2000.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
    },
    "Midrise residential (G+6, 18 m)": {
        "occ": "residential",
        "height_m_input": 21.0, "floors_above_input": 7, "floors_below_input": 1,
        "ground_bua_input": 1000.0, "basement_bua_input": 1000.0,
        "gfa_input": 7000.0, "plot_area_input": 3000.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
    },
    "Highrise residential (55 m, G+18, 2 basements)": {
        "occ": "residential",
        "height_m_input": 55.0, "floors_above_input": 18, "floors_below_input": 2,
        "ground_bua_input": 1200.0, "basement_bua_input": 1200.0,
        "gfa_input": 22000.0, "plot_area_input": 5000.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
    },
    "Super-highrise residential (120 m, 35 storeys)": {
        "occ": "residential",
        "height_m_input": 120.0, "floors_above_input": 35, "floors_below_input": 3,
        "ground_bua_input": 1800.0, "basement_bua_input": 1800.0,
        "gfa_input": 60000.0, "plot_area_input": 25000.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
    },
    "Hotel (highrise, 18 storeys, 60 m)": {
        "occ": "hotel_a",
        "height_m_input": 60.0, "floors_above_input": 18, "floors_below_input": 2,
        "ground_bua_input": 1500.0, "basement_bua_input": 1500.0,
        "gfa_input": 25000.0, "plot_area_input": 5000.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
        "has_commercial_kitchen": True,
    },
    "Hospital (lowrise, 3000 m² GF)": {
        "occ": "healthcare_a",
        "height_m_input": 12.0, "floors_above_input": 3, "floors_below_input": 1,
        "ground_bua_input": 3000.0, "basement_bua_input": 2000.0,
        "gfa_input": 9000.0, "plot_area_input": 8000.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Open parking",
        "has_anesthetizing_room": True, "has_operation_theater": True,
        "has_mri_scanning_room": True,
    },
    "Covered mall (3 floors, 25000 m² GF)": {
        "occ": "mall_covered",
        "height_m_input": 18.0, "floors_above_input": 3, "floors_below_input": 2,
        "ground_bua_input": 25000.0, "basement_bua_input": 25000.0,
        "gfa_input": 75000.0, "plot_area_input": 50000.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
        "has_atrium": True, "has_commercial_kitchen": True, "has_theater_cinema": True,
    },
    "Office (highrise, 30 m, 8 storeys)": {
        "occ": "business",
        "height_m_input": 30.0, "floors_above_input": 8, "floors_below_input": 2,
        "ground_bua_input": 800.0, "basement_bua_input": 800.0,
        "gfa_input": 6400.0, "plot_area_input": 2500.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
    },
    "Warehouse (multi-tenant OH, 4000 m²)": {
        "occ": "storage_industrial",
        "height_m_input": 10.0, "floors_above_input": 1, "floors_below_input": 0,
        "ground_bua_input": 4000.0, "basement_bua_input": 0.0,
        "gfa_input": 4000.0, "plot_area_input": 8000.0,
        "has_parking_area": False,
    },
    "Petrol station (Group A)": {
        "occ": "motor_fuel_dispensing",
        "height_m_input": 4.0, "floors_above_input": 1, "floors_below_input": 0,
        "ground_bua_input": 300.0, "basement_bua_input": 0.0,
        "gfa_input": 300.0, "plot_area_input": 2000.0,
        "has_parking_area": False,
        "motor_fuel_group_radio": "Group A - mini-marts/restaurants/retail/service as INDIVIDUAL buildings (sprinklers + 300 gpm @ 4.5 bar)",
    },
}


def _apply_preset():
    """Callback for the Apply-preset button. Writes preset values into session_state
    BEFORE widgets render (so widgets pick them up via their `key`).

    Auto-clears any flags marked as incompatible for the target occupancy
    BEFORE applying the preset overrides — so stale first-load defaults
    (e.g. has_diesel_generator_room=True) don't leak into a villa / petrol
    station / animal-housing / family-daycare scenario."""
    name = st.session_state.get("archetype_preset_select", "Custom (manual entry)")
    cfg = ARCHETYPE_PRESETS.get(name)
    if not cfg:
        return
    # Work on a copy so we can pop("occ") without mutating ARCHETYPE_PRESETS.
    cfg = dict(cfg)
    occ_target = cfg.pop("occ", None)
    if occ_target:
        st.session_state["occupancy_chosen"] = next(
            (kv for kv in OCC_FLAT if kv[1] == occ_target), None
        )
        # Also set the two-stage picker's session-state keys so the dropdowns
        # show the new occupancy on next render.
        for cat_label, occ_list in OCCUPANCY_OPTIONS.items():
            if occ_target in occ_list:
                st.session_state["occupancy_category_select"] = cat_label
                st.session_state["occupancy_sub_select"] = occ_target
                break
        # Silent baseline reset for villa / petrol station / animal housing /
        # daycare_b/c / infrastructure / hostel / parking / small mercantile.
        _apply_incompatible_flag_reset(occ_target)
    for k, v in cfg.items():
        st.session_state[k] = v

rooms_cb = _register_master("rooms_all", SPECIAL_ROOMS_KEYS)
var_cb   = _register_master("var_all",   VARIOUS_LOCATIONS_KEYS)
eq_cb    = _register_master("eq_all",    EQUIPMENT_KEYS)
fe_cb    = _register_master("fe_all",    FE_KEYS)
es_feat_cb = _register_master("es_feat_all", ES_FEATURE_KEYS)
es_zone_cb = _register_master("es_zone_all", ES_ZONE_KEYS)


# -----------------------------------------------------------------------------
# Print-friendly mode (Tier 3 UI #15): ?print=1 hides sidebar + right TOC col
# so the main report prints cleanly to A4 from the browser.
PRINT_MODE = str(st.query_params.get("print", "0")) == "1"

st.set_page_config(
    page_title="UAE FLSC 2018 - Fire & Life Safety",
    page_icon="FP",
    layout="wide",
    initial_sidebar_state="collapsed" if PRINT_MODE else "expanded",
)
if PRINT_MODE:
    # Hide the sidebar entirely + tighten margins for print.
    st.markdown(
        """
        <style>
          [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
          .main .block-container { max-width: 950px; padding-top: 1rem; }
          @media print {
            .stExpander { page-break-inside: avoid; }
            .stDownloadButton, .stButton { display: none !important; }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
st.markdown(
    """
    <div style="font-size:1.05rem; margin-bottom:0.5rem;">
      Created by <strong>Hussein Ragab</strong> ·
      <a href="https://www.linkedin.com/in/husseinragab" target="_blank"
         style="text-decoration:none; vertical-align:middle;">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
             width="22" height="22" fill="#0A66C2"
             style="vertical-align:-5px; margin:0 4px;">
          <path d="M20.45 20.45h-3.55v-5.57c0-1.33-.02-3.04-1.85-3.04-1.86 0-2.14 1.45-2.14 2.95v5.66H9.36V9h3.41v1.56h.05c.48-.9 1.65-1.85 3.4-1.85 3.64 0 4.31 2.4 4.31 5.51v6.23zM5.34 7.43a2.06 2.06 0 1 1 0-4.12 2.06 2.06 0 0 1 0 4.12zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.22.79 24 1.77 24h20.45c.98 0 1.78-.78 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/>
        </svg>
        LinkedIn
      </a>
    </div>
    """,
    unsafe_allow_html=True,
)
st.title("UAE FLSC 2018 - Fire & Life Safety Requirements")
st.caption("CDGH-OP-25, September 2018  |  Chapters loaded: MOE (Ch 3), FE (Ch 4), ES (Ch 5), EL (Ch 6), EVC (Ch 7), FA (Ch 8), FP (Ch 9), SC (Ch 10), LPG (Ch 11)")


with st.sidebar:
    # ----- Quick start: archetype presets -----
    with st.expander("⚡ Quick start - load an archetype", expanded=False):
        st.selectbox(
            "Archetype preset",
            options=list(ARCHETYPE_PRESETS.keys()),
            index=0,
            key="archetype_preset_select",
            help="Pick a typical UAE building archetype, then click Apply to fill geometry + occupancy + common flags. "
                 "Then customize as needed.",
        )
        st.button("Apply preset", on_click=_apply_preset, use_container_width=True)
        st.caption("'Custom' leaves your current inputs untouched.")

    with st.expander("💾 Save / Load scenario", expanded=False):
        # ----- Save -----
        import json as _json
        _save_keys = [
            # Geometry
            "height_m_input", "floors_above_input", "floors_below_input",
            "ground_bua_input", "basement_bua_input", "gfa_input",
            "plot_area_input", "depth_below_grade_input",
            # Project
            "project_notes_input",
            # Hazard / occupancy
            "occupancy_chosen",
            # Parking
            "has_parking_area", "attached_parking_kind_radio", "parking_area_m2_input",
            # Special rooms / various / equipment / FE / ES / Gas / FP / SC
            *SPECIAL_ROOMS_KEYS, *VARIOUS_LOCATIONS_KEYS, *EQUIPMENT_KEYS,
            *FE_KEYS, *ES_FEATURE_KEYS, *ES_ZONE_KEYS,
            "ceiling_height_m_input", "corridor_length_m",
            "assembly_area_m2_input",
            "gas_system_radio",
            "has_lpg_tank_roof_mounted", "has_lpg_tank_underground_mounded",
            "has_lpg_cylinders_indoor", "has_lpg_cylinders_food_truck", "has_lpg_flame_effect",
            "wet_riser_radio", "motor_fuel_group_radio",
            "is_single_tenant_storage", "is_idle_pallet_storage",
            "is_cold_storage", "is_aircraft_hanger",
            "is_flammable_liquid_warehouse", "is_flammable_liquid_industrial",
            "is_open_yard_storage", "is_plant_nursery",
            "tunnel_kind_radio", "tunnel_length_m_input",
        ]
        def _serializable(v):
            # Convert tuple to list for JSON; passthrough rest
            if isinstance(v, tuple):
                return list(v)
            return v
        _scenario = {k: _serializable(st.session_state.get(k)) for k in _save_keys
                     if k in st.session_state}
        _scenario_json = _json.dumps(_scenario, indent=2, default=str)
        _stem = (st.session_state.get("project_name", "scenario") or "scenario").replace(" ", "_")
        st.download_button(
            "Save current inputs (JSON)",
            data=_scenario_json,
            file_name=f"{_stem or 'scenario'}_FLSC_inputs.json",
            mime="application/json",
            use_container_width=True,
        )
        # ----- Load -----
        _uploaded = st.file_uploader("Load scenario JSON", type=["json"], key="scenario_uploader")
        if _uploaded is not None and not st.session_state.get("_scenario_loaded_marker"):
            try:
                _data = _json.loads(_uploaded.read().decode("utf-8"))
                for k, v in _data.items():
                    # occupancy_chosen was serialised as list (from tuple); restore tuple
                    if k == "occupancy_chosen" and isinstance(v, list) and len(v) == 2:
                        v = tuple(v)
                    st.session_state[k] = v
                st.session_state["_scenario_loaded_marker"] = True
                st.success("Scenario loaded - sidebar widgets refreshed.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load: {e}")
        elif _uploaded is None:
            # Reset marker so a future upload re-applies
            st.session_state["_scenario_loaded_marker"] = False

    with st.expander("📖 Glossary (acronyms & terms)", expanded=False):
        _gloss_q = st.text_input(
            "Filter glossary",
            value="",
            placeholder="e.g. PAS, ESFR, K-factor, Pa, hazard…",
            help="Case-insensitive match on term or definition.",
            key="glossary_filter",
        )
        _q = (_gloss_q or "").strip().lower()
        for term, defn in GLOSSARY:
            if _q and _q not in term.lower() and _q not in defn.lower():
                continue
            st.markdown(f"**{term}** — {defn}")
        if not _q:
            st.caption(
                f"{len(GLOSSARY)} terms. Type to filter. "
                "Items here are the acronyms most likely to appear in the report."
            )

    with st.expander("📍 Jump to OUTPUT section", expanded=False):
        st.markdown(
            "Click to scroll the main report:\n\n"
            "- [MOE - Means of Egress](#ch-moe)\n"
            "- [FE - Fire Extinguishers](#ch-fe)\n"
            "- [ES - Exit Signs](#ch-es)\n"
            "- [EL - Emergency Lighting](#ch-el)\n"
            "- [EVC - Voice Evacuation](#ch-evc)\n"
            "- [FA - Fire Detection & Alarm](#ch-fa)\n"
            "- [FP - Fire Protection](#ch-fp)\n"
            "- [SC - Smoke Control](#ch-sc)\n"
            "- [LPG - LPG Code](#ch-lpg)\n"
            "- [⮕ Attached parking](#attached-parking)\n"
            "- [FP High Ceiling Design](#high-ceiling)",
            unsafe_allow_html=True,
        )

    st.header("🏢 Building profile")
    project_name = st.text_input("Project name", "")
    project_notes = st.text_area(
        "Project notes (included in exports)",
        height=70,
        placeholder="Client / consultant / reviewer / design version.",
        key="project_notes_input",
    )

    # Set initial selectbox value if not already in session_state
    # ----- Two-stage occupancy picker (Tier 3 UI #11) -----
    # Stage 1: pick the broad category (Villa / Residential / Hotel / ...)
    # Stage 2: pick the specific occupancy within that category.
    # The legacy `occupancy_chosen` (category, occupancy) tuple is kept as the
    # source of truth so all downstream code, scenario save/load, and presets
    # continue to work unchanged.
    if "occupancy_chosen" not in st.session_state:
        st.session_state["occupancy_chosen"] = next(kv for kv in OCC_FLAT if kv[1] == "residential")
    _cur_cat, _cur_occ = st.session_state["occupancy_chosen"]
    _categories = list(OCCUPANCY_OPTIONS.keys())
    _cat_idx = _categories.index(_cur_cat) if _cur_cat in _categories else 0
    _chosen_cat = st.selectbox(
        "1. Category",
        _categories,
        index=_cat_idx,
        key="occupancy_category_select",
        help="Pick the broad occupancy family. The sub-occupancy list updates below.",
    )
    _options_in_cat = OCCUPANCY_OPTIONS[_chosen_cat]
    # If the user changed category, default to the first occupancy in the new
    # category. Otherwise keep their current sub-occupancy if still valid.
    _sub_idx = _options_in_cat.index(_cur_occ) if _cur_occ in _options_in_cat else 0
    def _on_occupancy_sub_change():
        # When the user changes specific occupancy, auto-clear flags that
        # don't apply (silent — no warnings). User can still tick anything
        # manually if their project needs it.
        new_occ = st.session_state.get("occupancy_sub_select")
        if new_occ:
            _apply_incompatible_flag_reset(new_occ)

    _chosen_sub = st.selectbox(
        "2. Specific occupancy (UAE FLSC classification)",
        _options_in_cat,
        index=_sub_idx,
        format_func=lambda code: code,
        key="occupancy_sub_select",
        on_change=_on_occupancy_sub_change,
    )
    # Persist back to the canonical tuple consumed by the rest of the app.
    st.session_state["occupancy_chosen"] = (_chosen_cat, _chosen_sub)
    occupancy = _chosen_sub
    st.info(OCCUPANCY_DEFS.get(occupancy, ""))
    if occupancy in INCOMPATIBLE_FLAGS_BY_OCC:
        st.caption(
            "💡 Special Rooms / Equipment that typically don't apply to this "
            "occupancy were auto-cleared. Tick anything below if your "
            "specific project needs it."
        )

    st.subheader("📐 Geometry")
    st.caption("Above-grade left, below-grade + plot right.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Above-grade**")
        height_m = st.number_input("Building height (m)", min_value=0.0, step=1.0, key="height_m_input")
        floors_above = st.number_input("Floors above grade", min_value=1, step=1, key="floors_above_input")
        ground_bua = st.number_input("Ground-floor BUA (m²)", min_value=0.0, step=50.0, key="ground_bua_input")
        gfa = st.number_input("Total GFA (m²)", min_value=0.0, step=100.0, key="gfa_input")
    with c2:
        st.markdown("**Below-grade + plot**")
        plot_area = st.number_input("Plot area (m²)", min_value=0.0, step=100.0, key="plot_area_input")
        floors_below = st.number_input("Basements (below grade)", min_value=0, step=1, key="floors_below_input")
        if int(floors_below) > 0:
            basement_bua = st.number_input("Basement BUA (m²)", min_value=0.0, step=50.0, key="basement_bua_input")
            depth_below_grade = st.number_input(
                "Depth below grade (m)", min_value=0.0, step=0.5,
                help="Distance from level of exit discharge to lowest basement floor. "
                     "If > 7 m, triggers Ch 10 Table 10.22 (deep-underground smoke control) "
                     "even when basement count <= 2.",
                key="depth_below_grade_input",
            )
        else:
            # Reset and disable when no basements
            st.session_state["basement_bua_input"] = 0.0
            st.session_state["depth_below_grade_input"] = 0.0
            basement_bua = 0.0
            depth_below_grade = 0.0
            st.caption("_Basement BUA + Depth N/A (no basements)._")

    # ---- Soft validation warnings (UX #6) ----
    _warnings = []
    if int(floors_below) > 0 and float(basement_bua) <= 0:
        _warnings.append("⚠ Basement floor count > 0 but Basement BUA = 0 - check basement area")
    if int(floors_below) == 0 and float(basement_bua) > 0:
        _warnings.append("⚠ Basement BUA entered but basement count = 0")
    if float(height_m) > 0 and int(floors_above) > 0 and float(height_m) / int(floors_above) < 2.5:
        _warnings.append(f"⚠ Implied storey height {height_m/floors_above:.1f} m looks low - verify height vs floor count")
    if float(depth_below_grade) > 7 and int(floors_below) <= 2:
        _warnings.append("ℹ Depth > 7 m with <=2 basements still triggers Ch 10 Table 10.22 (deep-underground SC) - intended.")
    for w in _warnings:
        st.caption(w)

    derived_hazard = default_hazard(occupancy)
    st.caption(f"Hazard class (auto-derived from occupancy): **{derived_hazard}**")
    with st.expander("Override hazard class (advanced)"):
        hazard = st.selectbox("Hazard class", ["LH", "OH1", "OH2", "HH"],
                              index=["LH", "OH1", "OH2", "HH"].index(derived_hazard))

    # =========================================================================
    # SHARED: Special Rooms & Equipment (drives FE / FA / FP / SC / LPG / EL)
    # =========================================================================
    st.markdown("---")
    st.markdown("### 🅿️ Spaces, equipment & gas")
    st.caption("Flags shared across FE / FA / FP / SC / LPG / EL chapters.")

    with st.expander("🅿️ Parking & special rooms", expanded=False):
        # ----- Attached parking sub-occupancy (drives MOE/FE/FP/FA/SC parking sub-evaluation) -----
        st.markdown("**Attached parking area**")
        st.checkbox("Building has parking",
                    key="has_parking_area",
                    help="If checked, the tool runs a parallel evaluation as if the building's parking area is its own occupancy and surfaces all parking-specific requirements from MOE / FE / FP / FA / SC chapters under an 'Attached Parking Area' section.")
        if st.session_state.get("has_parking_area"):
            parking_kind = st.radio(
                "Parking type",
                options=["Enclosed parking", "Open parking"],
                index=0, key="attached_parking_kind_radio",
            )
            attached_parking_kind_val = "open" if parking_kind == "Open parking" else "enclosed"
            # Show the verbatim UAE code definition for the selected parking type
            _key = "parking_open" if attached_parking_kind_val == "open" else "parking_enclosed"
            st.info(OCCUPANCY_DEFS.get(_key, ""))
            parking_area_m2_val = st.number_input(
                "Parking footprint area (m²)",
                min_value=0.0, value=0.0, step=100.0,
                key="parking_area_m2_input",
                help="Total parking footprint - drives Ch 10 SC area thresholds: enclosed parking 3,600 m² make-up-air exception (single-basement); open parking 4,000 m² small-vs-large split (>4,000 m² requires mechanical smoke purging or jet-fan system). If 0, defaults to basement BUA or ground-floor BUA.",
            )
        else:
            attached_parking_kind_val = "enclosed"
            parking_area_m2_val = 0.0
        st.markdown("---")
        st.markdown("**Special rooms checklist**")
        st.checkbox("Check all", key="rooms_all", on_change=rooms_cb)
        ca, cb = st.columns(2)
        with ca:
            st.checkbox("Anesthetizing room (A)", key="has_anesthetizing_room")
            st.checkbox("Battery charger room (B)", key="has_battery_charger_room")
            st.checkbox("BMS room (C)", key="has_bms_room")
            st.checkbox("Battery room (D)", key="has_battery_room")
            st.checkbox("Computer room (E)", key="has_computer_room")
            st.checkbox("Control / Fire command centre (F)", key="has_control_room")
            st.checkbox("Diesel generator [FOAM] (G)", key="has_diesel_generator_room")
            st.checkbox("Main electrical room (H)", key="has_main_electrical_room")
            st.checkbox("AHU room (I)", key="has_ahu_room")
            st.checkbox("LV / MV room (J)", key="has_lv_mv_room")
            st.checkbox("Transformer - utility (K)", key="has_transformer_room_utility")
            st.checkbox("Fire pump room", key="has_fire_pump_room")
        with cb:
            st.checkbox("Transformer - private (L)", key="has_transformer_room_private")
            st.checkbox("Lift machine room (M)", key="has_lift_machine_room")
            st.checkbox("Main telephone room (N)", key="has_main_telephone_room")
            st.checkbox("Main server room (O)", key="has_main_server_room")
            st.checkbox("RMU / IDF / MDF / CDF / MMR (P)", key="has_rmu_idf_mdf_room")
            st.checkbox("GSM room (Q)", key="has_gsm_room")
            st.checkbox("Operation theatre (R)", key="has_operation_theater")
            st.checkbox("MRI / Scanning room (S)", key="has_mri_scanning_room")
            st.checkbox("Records room (T)", key="has_records_room")
            st.checkbox("UPS room (U)", key="has_ups_room")
            st.checkbox("Cold / Freezer room (V)", key="has_cold_freezer_room")

    with st.expander("🛗 Various locations & spaces", expanded=False):
        st.checkbox("Check all", key="var_all", on_change=var_cb)
        st.checkbox("Atrium", key="has_atrium")
        st.checkbox("Rain-screen / glazed envelope", key="has_rain_screen_glazing")
        st.checkbox("Stairs (shaft sprinklers + smoke detector at top)", key="has_stairs")
        st.checkbox("Elevator (pit sprinklers + smoke detector at top of shaft)", key="has_elevator")
        st.checkbox("Bathrooms with heaters above false ceiling", key="has_bathrooms_with_heaters")
        st.checkbox("Residential laundry / storage rooms", key="has_laundry_storage_rooms")
        st.checkbox("Pantries (business/commercial)", key="has_pantries")
        st.checkbox("Permanent stages (assembly)", key="has_permanent_stages")
        st.checkbox("Roof LPG / restaurant / assembly / sheesha", key="has_roof_lpg_or_restaurant")
        st.checkbox("Garbage chute", key="has_garbage_chute")
        st.checkbox("High ceiling (> 10 m)", key="has_high_ceiling")
        if st.session_state.get("has_high_ceiling"):
            ceiling_height_m = st.number_input(
                "Ceiling height (m)", min_value=10.0, max_value=30.0, value=12.0, step=0.5,
                help="Triggers Table 9.29.A high-ceiling sprinkler design + FA beam smoke detection.",
                key="ceiling_height_m_input",
            )
        else:
            ceiling_height_m = 0.0
        st.checkbox("Tunnel inside building (Table 6.6 #9 / Ch 10 #3.7)", key="has_tunnel")

    with st.expander("🔥 Gas systems (Ch 11 LPG)", expanded=False):
        st.markdown("**Gas system type - one type only**")
        gas_choice = st.radio(
            "Select the building's gas-system type",
            options=[
                "No gas system",
                "LPG tanks (aboveground / roof / podium)",
                "Gas infrastructure connection (central piped supply)",
                "Gas cylinders (villa / domestic / small commercial)",
            ],
            index=0,
            key="gas_system_radio",
            help="Single mutually-exclusive choice. Triggers Ch 11 LPG requirements per type, or 'No Gas System' note.",
        )
        # Set the three underlying flags to match the radio choice
        st.session_state["has_lpg_tanks"] = gas_choice.startswith("LPG tanks")
        st.session_state["has_gas_infra_connection"] = gas_choice.startswith("Gas infrastructure")
        st.session_state["has_gas_cylinders_villa"] = gas_choice.startswith("Gas cylinders")

        # ----- Add-on variants (layer additional Ch 11 requirements) -----
        if gas_choice.startswith("LPG tanks"):
            st.markdown("*LPG tank variants (tick all that apply):*")
            st.checkbox("Roof-mounted tank (Tables 11.7/11.8 - max 2,000 Gal)",
                        key="has_lpg_tank_roof_mounted",
                        help="Layered requirements: stricter separation distances, 2,000 Gal aggregate cap (or 1,000 Gal if construction does not comply with Table 11.7.2.i).")
            st.checkbox("Underground / mounded tank (Tables 11.9/11.10)",
                        key="has_lpg_tank_underground_mounded",
                        help="Different rule set: ASME container, cathodic protection, separation measured from PRV / fill connections (not tank surface). ASME-listed containers may qualify for separation reduction per Table 11.10.b.")
        else:
            st.session_state["has_lpg_tank_roof_mounted"] = False
            st.session_state["has_lpg_tank_underground_mounded"] = False

        if gas_choice.startswith("Gas cylinders"):
            st.markdown("*Cylinder variants (tick all that apply):*")
            st.checkbox("Indoor cylinder room (Table 11.2)",
                        key="has_lpg_cylinders_indoor",
                        help="Layered requirements: dedicated room with mechanical ventilation, gas-leak detection, ESVs, 1-hr fire-rated separation. Stricter quantity limits than outdoor.")
        else:
            st.session_state["has_lpg_cylinders_indoor"] = False

        # Food truck is independent from the radio (mobile food truck is a separate scenario)
        st.markdown("*Food truck (independent option):*")
        st.checkbox("Food truck LPG cylinders (Table 11.3)",
                    key="has_lpg_cylinders_food_truck",
                    help="Mobile food truck LPG installation - dedicated ventilated cylinder compartment, secure mounting, suppression over cooking surface.")
        st.markdown("*Flame effect (assembly / entertainment):*")
        st.checkbox("Flame-effect LPG installation (Table 11.12)",
                    key="has_lpg_flame_effect",
                    help="LPG used for indoor / outdoor flame-effect entertainment shows. Triggers strict separation distances (6 m to exits, 3 m to ignition), dedicated extinguishers, fixed FP per risk assessment + Civil Defence approval.")

    with st.expander("⚙️ Equipment (FP Table 9.31 + FA Table 8.15)", expanded=False):
        st.checkbox("Check all", key="eq_all", on_change=eq_cb)
        st.checkbox("Commercial kitchen 3+ burners (A)", key="has_commercial_kitchen")
        st.checkbox("Flammable liquid tanks (C)", key="has_flammable_liquid_tanks")
        st.checkbox("Cable spread areas (D)", key="has_cable_spread_areas")
        st.checkbox("Boilers / boiler rooms (F)", key="has_boilers")
        st.checkbox("Cooling towers - combustible (G)", key="has_cooling_towers")
        st.checkbox("Oil-filled transformers (H)", key="has_oil_filled_transformers")
        st.checkbox("Bulk oil storage (I)", key="has_bulk_oil_storage")
        st.checkbox("Bulk flammable liquid storage (J)", key="has_bulk_flammable_liquid_storage")
        st.checkbox("Bulk flammable gas storage (K)", key="has_bulk_flammable_gas_storage")
        st.checkbox("Bulk flammable solid storage (L)", key="has_bulk_flammable_solid_storage")
        st.checkbox("High-hazard logistics (M)", key="has_high_hazard_logistics")
        st.checkbox("Chemical warehouse (N)", key="has_chemical_warehouse")
        st.checkbox("Arms / ammunition / explosives (O)", key="has_explosives")
        st.checkbox("Processing / generating plant (P)", key="has_processing_plant")

    # =========================================================================
    # PER-CHAPTER expanders (only chapter-unique inputs)
    # =========================================================================
    st.markdown("---")
    st.markdown("### ⚙️ Chapter-specific inputs")

    # ----- MOE (Ch 3) -----
    with st.expander("🚶 MOE - Settings (Ch 3 Means of Egress)", expanded=False):
        st.info("MOE auto-derives from occupancy + geometry + hazard class (Tables 3.13 / 3.14 / 3.15 / 3.16). "
                "No additional inputs needed - travel distance, common-path, dead-end, exit count and stair "
                "capacity all come from the building profile above.")

    # ----- FE (Ch 4) -----
    with st.expander("🧯 FE - Settings (Ch 4)", expanded=False):
        st.checkbox("Check all", key="fe_all", on_change=fe_cb)
        st.checkbox(
            "Class B storage zones (chemical / linen / waste / flammable / solvent / lab stores)",
            key="has_class_b_storage_zones")
        st.checkbox(
            "Combustible metals storage / activity (Class D)",
            key="has_combustible_metals")
        st.checkbox(
            "HV room or heavy electrical machinery",
            key="has_hv_or_heavy_electrical")
        # has_parking_area moved to "Special rooms and usage" - removed from here

    # ----- ES (Ch 5) - merged single expander -----
    with st.expander("🚪 ES - Settings (Ch 5 Exit Signs)", expanded=False):
        st.markdown("**Egress features**")
        st.checkbox("Check all - features", key="es_feat_all", on_change=es_feat_cb)
        st.checkbox("Evacuation elevator (designated egress lift)", key="has_evacuation_elevator")
        st.checkbox("Horizontal exits", key="has_horizontal_exits")
        st.checkbox("Dead-end / mistakable paths present", key="has_dead_end_paths")
        st.markdown("---")
        st.markdown("**Special zones / add-ons (Table 5.3)**")
        st.checkbox("Check all - zones", key="es_zone_all", on_change=es_zone_cb)
        st.checkbox("Amusement / mazes / mirrors / play areas (assembly)", key="has_amusement_confounding")
        st.checkbox("Night club / disco", key="has_nightclub_disco")
        st.checkbox("Theatre / cinema", key="has_theater_cinema")
        st.checkbox("Nursery (inside education)", key="has_nursery_within")
        st.checkbox("Auditorium (inside education)", key="has_auditorium_within")
        st.checkbox("HH storage / robotic / cold / cable spread / industrial basement", key="has_hh_storage_zones")
        st.checkbox("Mall play / food court / cinema zones", key="has_mall_play_food_cinema")
        st.checkbox("Robotic / mechanical parking", key="has_robotic_parking")
        st.checkbox("Villa converted to other use", key="villa_converted_use")
        st.checkbox("Fuel dispensing multi-storey", key="fuel_dispensing_multistorey")

    # ----- EL (Ch 6) -----
    with st.expander("💡 EL - Settings (Ch 6 Emergency Lighting)", expanded=False):
        st.info("EL auto-derives from height tier + occupancy + special-room flags above. "
                "No EL-specific inputs needed (the only EL-tied flag is `has_tunnel`, set in Various locations).")

    # ----- EVC (Ch 7) -----
    with st.expander("📢 EVC - Settings (Ch 7 Voice Evacuation)", expanded=False):
        st.info("EVC + Two-way Telephone auto-derive from height tier and occupancy class. "
                "No EVC-specific inputs needed - required for super-highrise / highrise / mall / assembly / "
                "amusement / education / hotel / detention / storage > 5,000 m². Lowrise residential / "
                "business / villa / parking / fuel dispensing are not required.")

    # ----- FA (Ch 8) -----
    with st.expander("🚨 FA - Settings (Ch 8 Fire Detection & Alarm)", expanded=False):
        st.info("FA auto-derives from height tier, occupancy and the Special Rooms / Various Locations / "
                "Equipment flags above (Tables 8.13 / 8.14 / 8.15). No FA-specific inputs needed.")


# ---------- Pre-evaluate to detect wet riser requirement ---------------------
prelim = _cached_evaluate(Building(
    project_name=project_name, occupancy=occupancy, height_m=height_m,
    floors_above_grade=int(floors_above), floors_below_grade=int(floors_below),
    depth_below_grade_m=float(depth_below_grade),
    gross_floor_area_m2=gfa, ground_floor_bua_m2=ground_bua,
    basement_bua_m2=basement_bua, plot_area_m2=plot_area, hazard_class=hazard,
).model_dump_json())

with st.sidebar:
    # ----- FP (Ch 9) - wet riser sizing + motor-fuel sub-group -----
    with st.expander("💧 FP - Settings (Ch 9)", expanded=False):
        # Motor fuel dispensing sub-group selector (Table 9.25 A/B/C) - only when relevant
        if occupancy == "motor_fuel_dispensing":
            mfg_choice = st.radio(
                "Motor fuel dispensing sub-group (Table 9.25)",
                options=[
                    "Group A - mini-marts/restaurants/retail/service as INDIVIDUAL buildings (sprinklers + 300 gpm @ 4.5 bar)",
                    "Group B - restaurants/bakeries WITHIN single mini-mart, fleet, marine (hose reel only + 50 gpm @ 6.9 bar)",
                    "Group C - mini-mart ONLY without service/repair, OR EV charging (extinguishers only - no water-based system)",
                ],
                index=0, key="motor_fuel_group_radio",
                help="Three groups in Table 9.25 with very different system requirements. Pick the one matching the facility.",
            )
            motor_fuel_group_val = mfg_choice[6]  # 'A', 'B', or 'C'
        else:
            motor_fuel_group_val = "A"

        # Storage / Industrial specialty (Table 9.27 specialty groups F-V)
        if occupancy == "storage_industrial":
            st.markdown("**Storage / Industrial specialty (Table 9.27 - tick if applicable, leave blank for default multi-tenant hazard-tier rules):**")
            st.checkbox("Single-tenant variant (Groups F-J - distinct pump/tank from multi-tenant)",
                        key="is_single_tenant_storage",
                        help="Single tenant. Group F (LH) / G (OH1) / H (OH2 - 350 gpm) / I (EH1 - 750/1250 gpm) / J (EH2 - 1000/1500 gpm, 120-min tank).")
            st.checkbox("Idle wood / plastic pallet warehouse (Group K - high-challenge fire load)",
                        key="is_idle_pallet_storage",
                        help="ESFR preferred for stacks > 3.7 m; density per Tables 9.7.X / 9.7.AA.")
            st.checkbox("Cold storage facility (< 40 deg C - Group P, dry-pipe sprinklers)",
                        key="is_cold_storage")
            st.checkbox("Aircraft hanger (Group Q - foam deluge, 1500 gpm pump)",
                        key="is_aircraft_hanger")
            st.checkbox("Flammable / combustible liquid WAREHOUSE (Group R - foam, 120-min tank)",
                        key="is_flammable_liquid_warehouse")
            st.checkbox("Flammable / combustible liquid INDUSTRIAL process (Group S - foam per Table 9.11.C)",
                        key="is_flammable_liquid_industrial")
            st.checkbox("Open yard storage / no building envelope (Group U)",
                        key="is_open_yard_storage")
            st.checkbox("Plant nursery (Group V - extinguishers only)",
                        key="is_plant_nursery")

        # Tunnel Fire Protection (Table 9.28) - shown when has_tunnel ticked
        if st.session_state.get("has_tunnel"):
            st.markdown("**Tunnel Fire Protection (Table 9.28):**")
            tunnel_kind_choice = st.radio(
                "Tunnel kind",
                options=["Road / Rail tunnel", "Cable tunnel"],
                index=0, key="tunnel_kind_radio",
                help="Cable: deluge water spray OR water mist. Road/rail: depends on length tier.",
            )
            tunnel_kind_val = "cable" if tunnel_kind_choice.startswith("Cable") else "road_rail"
            tunnel_length_m_val = st.number_input(
                "Tunnel length (m)", min_value=0.0, value=0.0, step=10.0,
                help="Cable: < 60 m vs >= 60 m. Road/rail: < 90 m (no FP), 90-1000 m, > 1000 m.",
                key="tunnel_length_m_input",
            )
        else:
            tunnel_kind_val = "road_rail"
            tunnel_length_m_val = 0.0

        if prelim.requires_wet_riser:
            st.markdown("**Wet riser sizing** — required because the matched FP branch emits a wet-riser system.")
            standpipe_choice = st.radio(
                "Number of standpipes in the wet-riser system",
                options=["2 standpipes (Fire pump 750 gpm @ 6.9 bar)",
                         "3 or more standpipes (Fire pump 1000 gpm @ 6.9 bar)"],
                index=0,
                help="Per Table 9.19 / 9.20 pump-sizing notes. The choice resolves the Fire Pump entry under FP Branch Requirements.",
                key="wet_riser_radio",
            )
            wet_riser_standpipes = 2 if standpipe_choice.startswith("2 ") else 3
        else:
            wet_riser_standpipes = 2
            st.info("Wet-riser sizing N/A - the matched FP branch does not require a wet-riser system.")
        st.caption("All other FP outputs auto-derived from occupancy + geometry + Special Rooms / Various Locations / Equipment flags above.")

    # ----- SC (Ch 10) -----
    with st.expander("💨 SC - Settings (Ch 10)", expanded=False):
        corridor_length_m = st.number_input(
            "Longest enclosed corridor length (m)",
            min_value=0.0, value=0.0, step=5.0,
            help="If > 60 m at lowrise/midrise (residential/office/hotel/mercantile/staff "
                 "accommodation), Ch 10 Table 10.27 item 4 requires natural ventilation per "
                 "Section 2.15 where exterior façade / roof accessible.",
        )
        # Assembly-area trigger for Table 10.27 items 9-13 (>2000 m² exhibition/sports/auditorium/stadium).
        # Only relevant for assembly_* occupancies; for others the field is left at 0 and ignored.
        if occupancy.startswith("assembly_"):
            assembly_area_m2 = st.number_input(
                "Largest assembly-hall area (m²)",
                min_value=0.0, value=0.0, step=100.0,
                key="assembly_area_m2_input",
                help="Triggers Ch 10 Table 10.27 items 9–13 (exhibition / assembly / sports / "
                     "auditorium / stadium) smoke management when > 2,000 m². If left at 0, "
                     "falls back to total GFA for area-based triggering.",
            )
        else:
            assembly_area_m2 = 0.0
        st.caption("Other SC outputs (Tables 10.19-10.27) auto-derive from height tier, occupancy, "
                   "depth below grade and Special Rooms / Various Locations / Equipment flags.")

    # ----- LPG (Ch 11) -----
    with st.expander("⛽ LPG - Settings (Ch 11)", expanded=False):
        st.info("LPG output auto-derived from the THREE gas-system flags in the Equipment + Gas Systems group above:\n\n"
                "- **LPG tanks** (aboveground / roof / podium)\n"
                "- **Gas infrastructure connection** (municipal / central piped supply)\n"
                "- **Gas cylinders** (villa / domestic / small commercial)\n\n"
                "If none are ticked, the LPG section reports 'No Gas System Present'.")


def gs(k):
    return bool(st.session_state.get(k, False))

building = Building(
    project_name=project_name, occupancy=occupancy, height_m=height_m,
    floors_above_grade=int(floors_above), floors_below_grade=int(floors_below),
    depth_below_grade_m=float(depth_below_grade),
    gross_floor_area_m2=gfa, ground_floor_bua_m2=ground_bua,
    basement_bua_m2=basement_bua, plot_area_m2=plot_area, hazard_class=hazard,
    corridor_length_m=float(corridor_length_m),
    assembly_area_m2=float(assembly_area_m2),
    has_high_ceiling=gs("has_high_ceiling"), ceiling_height_m=ceiling_height_m,
    wet_riser_standpipes=int(wet_riser_standpipes),
    motor_fuel_group=motor_fuel_group_val,
    # Storage / Industrial specialty (Table 9.27 specialty groups)
    is_aircraft_hanger=gs("is_aircraft_hanger"),
    is_cold_storage=gs("is_cold_storage"),
    is_flammable_liquid_warehouse=gs("is_flammable_liquid_warehouse"),
    is_flammable_liquid_industrial=gs("is_flammable_liquid_industrial"),
    is_open_yard_storage=gs("is_open_yard_storage"),
    is_plant_nursery=gs("is_plant_nursery"),
    is_single_tenant_storage=gs("is_single_tenant_storage"),
    is_idle_pallet_storage=gs("is_idle_pallet_storage"),
    tunnel_kind=tunnel_kind_val,
    tunnel_length_m=float(tunnel_length_m_val),
    # Special rooms
    has_anesthetizing_room=gs("has_anesthetizing_room"),
    has_battery_charger_room=gs("has_battery_charger_room"),
    has_bms_room=gs("has_bms_room"), has_battery_room=gs("has_battery_room"),
    has_computer_room=gs("has_computer_room"), has_control_room=gs("has_control_room"),
    has_diesel_generator_room=gs("has_diesel_generator_room"),
    has_main_electrical_room=gs("has_main_electrical_room"),
    has_ahu_room=gs("has_ahu_room"), has_lv_mv_room=gs("has_lv_mv_room"),
    has_transformer_room_utility=gs("has_transformer_room_utility"),
    has_transformer_room_private=gs("has_transformer_room_private"),
    has_lift_machine_room=gs("has_lift_machine_room"),
    has_main_telephone_room=gs("has_main_telephone_room"),
    has_main_server_room=gs("has_main_server_room"),
    has_rmu_idf_mdf_room=gs("has_rmu_idf_mdf_room"),
    has_gsm_room=gs("has_gsm_room"), has_operation_theater=gs("has_operation_theater"),
    has_mri_scanning_room=gs("has_mri_scanning_room"),
    has_records_room=gs("has_records_room"), has_ups_room=gs("has_ups_room"),
    has_cold_freezer_room=gs("has_cold_freezer_room"),
    has_fire_pump_room=gs("has_fire_pump_room"),
    # Various locations
    has_atrium=gs("has_atrium"), has_rain_screen_glazing=gs("has_rain_screen_glazing"),
    has_stairs=gs("has_stairs"), has_elevator=gs("has_elevator"),
    has_bathrooms_with_heaters=gs("has_bathrooms_with_heaters"),
    has_laundry_storage_rooms=gs("has_laundry_storage_rooms"),
    has_pantries=gs("has_pantries"),
    has_permanent_stages=gs("has_permanent_stages"),
    has_roof_lpg_or_restaurant=gs("has_roof_lpg_or_restaurant"),
    has_garbage_chute=gs("has_garbage_chute"),
    has_tunnel=gs("has_tunnel"),
    # Equipment + Gas
    has_commercial_kitchen=gs("has_commercial_kitchen"),
    has_lpg_tanks=gs("has_lpg_tanks"),
    has_gas_infra_connection=gs("has_gas_infra_connection"),
    has_gas_cylinders_villa=gs("has_gas_cylinders_villa"),
    has_lpg_tank_roof_mounted=gs("has_lpg_tank_roof_mounted"),
    has_lpg_tank_underground_mounded=gs("has_lpg_tank_underground_mounded"),
    has_lpg_cylinders_indoor=gs("has_lpg_cylinders_indoor"),
    has_lpg_cylinders_food_truck=gs("has_lpg_cylinders_food_truck"),
    has_lpg_flame_effect=gs("has_lpg_flame_effect"),
    has_flammable_liquid_tanks=gs("has_flammable_liquid_tanks"),
    has_cable_spread_areas=gs("has_cable_spread_areas"),
    has_boilers=gs("has_boilers"),
    has_cooling_towers=gs("has_cooling_towers"),
    has_oil_filled_transformers=gs("has_oil_filled_transformers"),
    has_bulk_oil_storage=gs("has_bulk_oil_storage"),
    has_bulk_flammable_liquid_storage=gs("has_bulk_flammable_liquid_storage"),
    has_bulk_flammable_gas_storage=gs("has_bulk_flammable_gas_storage"),
    has_bulk_flammable_solid_storage=gs("has_bulk_flammable_solid_storage"),
    has_high_hazard_logistics=gs("has_high_hazard_logistics"),
    has_chemical_warehouse=gs("has_chemical_warehouse"),
    has_explosives=gs("has_explosives"),
    has_processing_plant=gs("has_processing_plant"),
    # FE chapter-specific
    has_class_b_storage_zones=gs("has_class_b_storage_zones"),
    has_combustible_metals=gs("has_combustible_metals"),
    has_hv_or_heavy_electrical=gs("has_hv_or_heavy_electrical"),
    has_parking_area=gs("has_parking_area"),
    attached_parking_kind=attached_parking_kind_val,
    parking_area_m2=float(parking_area_m2_val),
    # ES chapter-specific
    has_evacuation_elevator=gs("has_evacuation_elevator"),
    has_horizontal_exits=gs("has_horizontal_exits"),
    has_dead_end_paths=gs("has_dead_end_paths"),
    has_amusement_confounding=gs("has_amusement_confounding"),
    has_nightclub_disco=gs("has_nightclub_disco"),
    has_theater_cinema=gs("has_theater_cinema"),
    has_nursery_within=gs("has_nursery_within"),
    has_auditorium_within=gs("has_auditorium_within"),
    has_hh_storage_zones=gs("has_hh_storage_zones"),
    has_mall_play_food_cinema=gs("has_mall_play_food_cinema"),
    has_robotic_parking=gs("has_robotic_parking"),
    villa_converted_use=gs("villa_converted_use"),
    fuel_dispensing_multistorey=gs("fuel_dispensing_multistorey"),
)
report = _cached_evaluate(building.model_dump_json())


# ---------- Top summary ------------------------------------------------------
def _branch(ch_code):
    ch = report.chapter(ch_code)
    return (ch.selected_branch if ch else None,
            ch.selected_branch_section if ch else None)

moe_b, moe_s = _branch("MOE")
fe_b, fe_s   = _branch("FE")
es_b, es_s   = _branch("ES")
el_b, el_s   = _branch("EL")
evc_b, evc_s = _branch("EVC")
fa_b, fa_s   = _branch("FA")
fp_b, fp_s   = _branch("FP")
sc_b, sc_s   = _branch("SC")
lpg_b, lpg_s = _branch("LPG")

st.markdown(
    f"""### Building classification
| Class | Cat | MOE | FE | ES | EL | EVC | FA | FP | SC | LPG |
|---|---|---|---|---|---|---|---|---|---|---|
| **{building.height_class}** | {building.building_category} | `{moe_b or '-'}` | `{fe_b or '-'}` | `{es_b or '-'}` | `{el_b or '-'}` | `{evc_b or '-'}` | `{fa_b or '-'}` | `{fp_b or '-'}` | `{sc_b or '-'}` | `{lpg_b or '-'}` |
""", unsafe_allow_html=True
)
st.caption(f"**Occupancy:** `{occupancy}` - {OCCUPANCY_DEFS.get(occupancy, '')}  |  **Hazard class:** {building.hazard_class}")

# ---------- Special-rooms / flags summary chip strip (Tier 3 UI #12) ---------
# Shows at a glance which Special Rooms / Various Locations / Equipment flags
# the user has ticked. Makes it easy to confirm the input set without scrolling
# the sidebar.
def _ticked_chips(building_obj: Building) -> str:
    _LABELS = {
        # Special rooms
        "has_anesthetizing_room": "Anesthetizing",
        "has_battery_charger_room": "Battery charger",
        "has_bms_room": "BMS",
        "has_battery_room": "Battery",
        "has_computer_room": "Computer",
        "has_control_room": "Control / FCC",
        "has_diesel_generator_room": "Diesel gen",
        "has_main_electrical_room": "Main electrical",
        "has_ahu_room": "AHU",
        "has_lv_mv_room": "LV/MV",
        "has_transformer_room_utility": "Transformer (utility)",
        "has_transformer_room_private": "Transformer (private)",
        "has_lift_machine_room": "Lift machine",
        "has_main_telephone_room": "Main telephone",
        "has_main_server_room": "Main server",
        "has_rmu_idf_mdf_room": "RMU/IDF/MDF",
        "has_gsm_room": "GSM",
        "has_operation_theater": "OT",
        "has_mri_scanning_room": "MRI",
        "has_records_room": "Records",
        "has_ups_room": "UPS",
        "has_cold_freezer_room": "Cold/Freezer",
        "has_fire_pump_room": "Fire pump",
        # Various locations
        "has_atrium": "Atrium",
        "has_rain_screen_glazing": "Rain-screen",
        "has_stairs": "Stairs",
        "has_elevator": "Elevator",
        "has_bathrooms_with_heaters": "Bathrooms+heaters",
        "has_laundry_storage_rooms": "Laundry/storage",
        "has_pantries": "Pantries",
        "has_permanent_stages": "Permanent stages",
        "has_roof_lpg_or_restaurant": "Roof LPG/restaurant",
        "has_garbage_chute": "Garbage chute",
        "has_high_ceiling": "High ceiling",
        "has_tunnel": "Tunnel",
        # Equipment
        "has_commercial_kitchen": "Commercial kitchen",
        "has_flammable_liquid_tanks": "Flammable liquid tanks",
        "has_cable_spread_areas": "Cable spread",
        "has_boilers": "Boilers",
        "has_cooling_towers": "Cooling towers",
        "has_oil_filled_transformers": "Oil-filled transformers",
        "has_bulk_oil_storage": "Bulk oil",
        "has_bulk_flammable_liquid_storage": "Bulk flammable liquid",
        "has_bulk_flammable_gas_storage": "Bulk flammable gas",
        "has_bulk_flammable_solid_storage": "Bulk flammable solid",
        "has_high_hazard_logistics": "HH logistics",
        "has_chemical_warehouse": "Chemical warehouse",
        "has_explosives": "Explosives",
        "has_processing_plant": "Processing plant",
        # Gas
        "has_lpg_tanks": "LPG tanks",
        "has_gas_infra_connection": "Gas-infra connection",
        "has_gas_cylinders_villa": "Gas cylinders (villa)",
        "has_lpg_tank_roof_mounted": "LPG roof tank",
        "has_lpg_tank_underground_mounded": "LPG UG/mounded",
        "has_lpg_cylinders_indoor": "LPG indoor cyl",
        "has_lpg_cylinders_food_truck": "Food-truck LPG",
        "has_lpg_flame_effect": "Flame-effect LPG",
        # ES feature/zone
        "has_evacuation_elevator": "Evac. elevator",
        "has_horizontal_exits": "Horizontal exits",
        "has_dead_end_paths": "Dead-ends",
        "has_amusement_confounding": "Amusement",
        "has_nightclub_disco": "Nightclub",
        "has_theater_cinema": "Theatre/cinema",
        "has_nursery_within": "Nursery within",
        "has_auditorium_within": "Auditorium within",
        "has_hh_storage_zones": "HH storage zones",
        "has_mall_play_food_cinema": "Mall play/food/cinema",
        "has_robotic_parking": "Robotic parking",
        "villa_converted_use": "Villa converted",
        "fuel_dispensing_multistorey": "Fuel multi-storey",
        # FE-specific
        "has_class_b_storage_zones": "Class B storage",
        "has_combustible_metals": "Combustible metals",
        "has_hv_or_heavy_electrical": "HV/heavy electrical",
        "has_parking_area": "Parking area",
    }
    ticked = [lab for attr, lab in _LABELS.items()
              if getattr(building_obj, attr, False)]
    if not ticked:
        return ""
    return " ".join(f"`{t}`" for t in ticked)

_chip_str = _ticked_chips(building)
if _chip_str:
    _n = _chip_str.count("`") // 2
    with st.expander(f"🔧 Inputs summary — {_n} flag(s) ticked",
                      expanded=False):
        st.markdown(_chip_str)

# ---------- Expanded soft-validation warnings (Tier 2 UI #9) -----------------

def _sanity_check_inputs(b: Building) -> tuple[list[str], list[str], list[str]]:
    """Look at the full Building model + session_state flags and return three lists:
    (errors, warnings, info). Errors are hard rule conflicts (e.g. LPG roof tank
    on super-highrise); warnings flag unusual combinations a designer should
    confirm; info is FYI traceability. Filtering / display is the caller's job."""
    errs: list[str] = []
    warns: list[str] = []
    info: list[str] = []

    def gs(k):  # session-state shorthand
        return bool(st.session_state.get(k, False))

    # --- Hard errors ---
    if gs("has_lpg_tank_roof_mounted") and b.height_m > 90:
        errs.append(
            "🚫 **LPG roof tank on super-highrise (>90 m) is PROHIBITED.** "
            "UAE Ch 11 §2.5.1.3 (p.900) bans roof LPG installations on buildings "
            "taller than 90 m. Either lower the building, change to a podium / "
            "ground tank, or uncheck the roof-mounted flag."
        )

    # --- Unusual / suspicious combinations ---
    if b.occupancy == "storage_industrial" and b.hazard_class == "LH":
        warns.append(
            "⚠ Storage / industrial occupancy is rarely LH (Light Hazard). "
            "Most warehouses are OH1/OH2/EH per the commodity (Table 9.27). "
            "Confirm hazard class is intentional."
        )

    if b.occupancy == "mall_covered" and not b.has_atrium:
        warns.append(
            "⚠ `mall_covered` selected without `has_atrium`. Most covered malls "
            "have at least one atrium, which triggers additional Ch 9/10 atrium "
            "requirements. Confirm intentional."
        )

    if b.occupancy == "healthcare_a" and not (b.has_operation_theater
                                              or b.has_mri_scanning_room
                                              or b.has_anesthetizing_room):
        warns.append(
            "⚠ Inpatient hospital (`healthcare_a`) without OT / MRI / "
            "Anesthetizing room ticked. Confirm the project scope — most "
            "inpatient hospitals have at least one of these."
        )

    if b.height_m > 23 and not b.has_evacuation_elevator:
        warns.append(
            "⚠ Highrise (>23 m) without a designated `evacuation_elevator`. "
            "Civil Defence often expects at least one designated firefighter / "
            "evacuation lift on highrise. Confirm with the AHJ if absent."
        )

    if (b.occupancy.startswith("hotel_")
            and not b.has_commercial_kitchen
            and b.height_m > 15):
        info.append(
            "ℹ Hotel without `has_commercial_kitchen` ticked. Most hotels have "
            "a kitchen (triggers Ch 9 wet chemical + Ch 8 fusible-link). "
            "Confirm intentional."
        )

    if (b.occupancy in ("assembly_a", "assembly_b", "assembly_c")
            and b.gross_floor_area_m2 > 2000
            and b.assembly_area_m2 == 0):
        info.append(
            "ℹ Assembly occupancy with GFA > 2,000 m² but no explicit "
            "`assembly_area_m2` value entered. Ch 10 Table 10.27 items 9-13 "
            "triggers on the assembly-hall area; set the value in SC settings "
            "to ensure the right smoke-purge rule fires."
        )

    if (b.occupancy.startswith("residential")
            and b.floors_above_grade >= 4
            and not b.has_garbage_chute):
        info.append(
            "ℹ G+4 residential without `has_garbage_chute` ticked. Most UAE "
            "residential buildings of this size have a chute (Ch 9 Table 9.29). "
            "Confirm intentional."
        )

    if b.has_lpg_tanks and b.height_m > 23:
        info.append(
            "ℹ LPG tanks declared on a highrise. Per Ch 11 §2.5.1 the tanks "
            "must be on the roof or podium only (never inside the building). "
            "Verify location."
        )

    if b.has_diesel_generator_room and not b.has_main_electrical_room:
        warns.append(
            "⚠ Diesel generator room ticked but `main_electrical_room` is not. "
            "Diesel gen rooms almost always accompany a main electrical room — "
            "verify the building has neither."
        )

    if b.has_high_ceiling and b.ceiling_height_m < 10:
        warns.append(
            "⚠ `has_high_ceiling` is ticked but ceiling height is < 10 m. "
            "Ch 9 Table 9.29.A high-ceiling design starts at 10 m. Untick the "
            "flag or raise the height."
        )

    if b.depth_below_grade_m > 7 and b.floors_below_grade <= 2:
        info.append(
            "ℹ Depth > 7 m with ≤ 2 basements — Ch 10 Table 10.22 deep-"
            "underground SC still triggers via the depth threshold (intended)."
        )

    # NOTE: villa / petrol-station / animal-housing / daycare_c / etc. used
    # to get a "flags ticked that don't apply" warning here. That's been
    # replaced by silent auto-clear at occupancy-change time (see
    # `_on_occupancy_sub_change` + `_apply_incompatible_flag_reset`). The
    # user can still tick anything manually — no nagging.

    return errs, warns, info


# ---------- Sanity-check banner (Tier 2 UI #9) -------------------------------
_errs, _warns, _info = _sanity_check_inputs(building)
if _errs:
    for e in _errs:
        st.error(e)
if _warns:
    with st.expander(f"⚠ Sanity checks — {len(_warns)} warning(s)", expanded=True):
        for w in _warns:
            st.warning(w)
if _info:
    with st.expander(f"ℹ Sanity checks — {len(_info)} info note(s)", expanded=False):
        for i in _info:
            st.info(i)


_STATUS_BADGE = {
    "required":     ("🔴", "REQUIRED"),
    "recommended":  ("🔵", "RECOMMENDED"),
    "conditional":  ("🟡", "CONDITIONAL"),
    "not_required": ("⚪", "NOT REQUIRED"),
}

_STATUS_ORDER = ["required", "recommended", "conditional", "not_required"]


def _filter_items(items, allowed_statuses: set, text_q: str):
    """Apply the global status + text filter to a list of Requirements."""
    text_q = (text_q or "").strip().lower()
    out = []
    for r in items:
        if allowed_statuses and r.status not in allowed_statuses:
            continue
        if text_q:
            hay = " ".join(filter(None, [r.system, r.spec, r.detail,
                                          r.code_ref])).lower()
            if text_q not in hay:
                continue
        out.append(r)
    return out


def _chapter_counts(ch):
    """Return {status -> count} totals across all blocks in a chapter, plus 'total'."""
    counts = {s: 0 for s in _STATUS_ORDER}
    for blk in ch.blocks:
        for it in blk.items:
            counts[it.status] = counts.get(it.status, 0) + 1
    counts["total"] = sum(counts[s] for s in _STATUS_ORDER)
    return counts


_RULE_LOOKUP = _cached_rule_lookup()


# ---------- Code-excerpt lookup (Tier 3 UI #14) ------------------------------
# Optional feature: if the user has populated `data/code_excerpts/chXX.txt` or
# the original `_extracted/chXX.txt` folder is reachable, the citation expander
# can pull a short excerpt around the cited page so designers can verify the
# rule against the actual code text without flipping to the PDF.
#
# The data files are NOT bundled in the repo (Civil Defence text — leave
# distribution to the user). The helper degrades silently when files are absent.

import re as _re
from pathlib import Path as _Path


@st.cache_data(show_spinner=False)
def _load_chapter_text(chapter_code: str) -> str:
    """Read the extracted chapter text. Returns '' if unavailable."""
    chapter_num_map = {
        "MOE": "03", "FE": "04", "ES": "05", "EL": "06",
        "EVC": "07", "FA": "08", "FP": "09", "SC": "10", "LPG": "11",
    }
    ch_num = chapter_num_map.get(chapter_code)
    if not ch_num:
        return ""
    here = _Path(__file__).parent
    candidates = [
        here / "data" / "code_excerpts" / f"ch{ch_num}.txt",
        here / ".." / "_extracted" / f"ch{ch_num}.txt",
    ]
    for cand in candidates:
        try:
            if cand.is_file():
                return cand.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
    return ""


def _excerpt_around_page(chapter_code: str, page_ref: str,
                         max_chars: int = 800) -> str:
    """Try to pull a short excerpt around the cited page. page_ref is text
    like 'p.713' or 'p.713-715' or 'pp.713-715'. Returns '' if not found."""
    text = _load_chapter_text(chapter_code)
    if not text or not page_ref:
        return ""
    m = _re.search(r"(\d{2,4})", page_ref)
    if not m:
        return ""
    page = int(m.group(1))
    marker = f"===== PAGE {page} ====="
    idx = text.find(marker)
    if idx < 0:
        return ""
    start = idx + len(marker)
    end = text.find("===== PAGE", start)
    page_body = text[start:end if end > 0 else len(text)].strip()
    if len(page_body) > max_chars:
        page_body = page_body[:max_chars].rstrip() + " […]"
    return page_body


# ---------- Audit-traceability index (Tier 3 UI #17) -------------------------
# Scans every chapter YAML for lines containing TODO / "needs verification" /
# "not located" markers (added by the audit-fix campaign) so designers can see
# the open items at a glance and verify them against the code themselves.

@st.cache_data(show_spinner=False)
def _scan_audit_notes() -> list[dict]:
    """Return a list of {file, line, text} dicts for every audit-style note
    found in the rule YAML files. Markers covered:
      - '# TODO' / 'TODO'
      - 'needs verification' / 'needs human verification'
      - 'claim not located'
      - 'not encoded'
      - 'verify against'
    """
    notes = []
    rules_dir = _Path(__file__).parent / "rules"
    patterns = _re.compile(
        r"(TODO|needs (?:human )?verification|claim not located|not encoded|verify against)",
        _re.IGNORECASE,
    )
    for yf in sorted(rules_dir.glob("ch*.yaml")):
        try:
            with open(yf, encoding="utf-8") as fh:
                for i, line in enumerate(fh, start=1):
                    if patterns.search(line):
                        notes.append({
                            "file": yf.name,
                            "line": i,
                            "text": line.strip().lstrip("#").strip(),
                        })
        except Exception:
            continue
    return notes


def render_block(title, items, allowed_statuses: set, text_q: str,
                  chapter_code: str = ""):
    items = _filter_items(items, allowed_statuses, text_q)
    if not items:
        return
    st.subheader(title)
    for req in items:
        emoji, label = _STATUS_BADGE.get(req.status, _STATUS_BADGE["required"])
        with st.container(border=True):
            st.markdown(f"{emoji} `{label}` **{req.system}**")
            if req.spec:
                st.markdown(f"**Spec:** {req.spec}")
            if req.detail:
                st.markdown(req.detail)
            cite = [p for p in (req.code_ref, req.page_ref) if p]
            if cite:
                st.caption("📖 " + " · ".join(cite))
            # Citation excerpt (Tier 3 UI #14) — pulls a short slice of the
            # cited PDF page if the user has the extracted text bundled.
            if chapter_code and req.page_ref:
                excerpt = _excerpt_around_page(chapter_code, req.page_ref)
                if excerpt:
                    with st.expander(
                        f"📖 Code excerpt — {req.page_ref}", expanded=False
                    ):
                        st.text(excerpt)
                        st.caption(
                            "Auto-extracted from UAE FLSC 2018 PDF. "
                            "Always verify against the official current edition."
                        )
            # "Why triggered?" — surface the rule ID + the match conditions from
            # the source YAML so designers can verify why this requirement appeared.
            if req.source_rule:
                info = _RULE_LOOKUP.get(req.source_rule)
                with st.expander(
                    f"🔍 Why triggered — rule `{req.source_rule}`", expanded=False
                ):
                    if info:
                        st.caption(
                            f"Source: `rules/{info['file']}` · kind: `{info['kind']}`"
                        )
                        if info["match"]:
                            st.code(_format_match_yaml(info["match"]),
                                     language="yaml")
                        else:
                            st.caption("(Universal rule — fires for every building)")
                    else:
                        st.caption("(Match conditions not located in YAML index.)")


def _format_match_yaml(match: dict) -> str:
    """Pretty-print a match/when dict as a small YAML snippet."""
    import yaml as _y
    return _y.safe_dump(match, sort_keys=False, default_flow_style=False).strip()


_OP_SUFFIX_LABEL = {
    "_gt": ">", "_gte": "≥", "_lt": "<", "_lte": "≤",
    "_is": "=", "_not": "≠ (not in)", "_in": "∈",
}


def _human_match(match: dict) -> str:
    """Translate a YAML match/when dict into a plain-English fragment for the
    branch-rationale caption. Examples:
      {occupancy: hotel_a, height_m_gt: 23, height_m_lte: 90, plot_area_m2_lte: 3000}
      -> "Hotel Group A, 23 < height ≤ 90 m (highrise), plot ≤ 3,000 m²"
    """
    if not match:
        return ""
    parts: list[str] = []

    # Occupancy slot
    if "occupancy" in match:
        defn = OCCUPANCY_DEFS.get(match["occupancy"], match["occupancy"])
        parts.append(defn.split(" - ")[0])
    elif "occupancy_in" in match:
        parts.append("any of: " + ", ".join(match["occupancy_in"]))
    if "occupancy_not" in match:
        parts.append("not: " + ", ".join(match["occupancy_not"]))
    if "occupancy_group_is" in match:
        parts.append(f"occupancy group = {match['occupancy_group_is']}")

    # Height tier
    h_gt = match.get("height_m_gt")
    h_gte = match.get("height_m_gte")
    h_lt = match.get("height_m_lt")
    h_lte = match.get("height_m_lte")
    h_lo = h_gt if h_gt is not None else h_gte
    h_hi = h_lt if h_lt is not None else h_lte
    if h_lo is not None and h_hi is not None:
        op_lo = ">" if h_gt is not None else "≥"
        op_hi = "<" if h_lt is not None else "≤"
        parts.append(f"{h_lo} {op_lo} height {op_hi} {h_hi} m")
    elif h_lo is not None:
        op = ">" if h_gt is not None else "≥"
        parts.append(f"height {op} {h_lo} m")
    elif h_hi is not None:
        op = "<" if h_lt is not None else "≤"
        parts.append(f"height {op} {h_hi} m")

    # Hazard class
    if "hazard_class" in match:
        parts.append(f"hazard class = {match['hazard_class']}")
    if "hazard_class_is" in match:
        parts.append(f"hazard class = {match['hazard_class_is']}")
    if "hazard_class_in" in match:
        parts.append("hazard class ∈ " + ", ".join(match["hazard_class_in"]))

    # Building category
    if "building_category_is" in match:
        parts.append(f"category = {match['building_category_is']}")

    # Anything else (areas, floors, flags) — generic fallback rendering
    skip_keys = {
        "occupancy", "occupancy_in", "occupancy_not", "occupancy_group_is",
        "height_m_gt", "height_m_gte", "height_m_lt", "height_m_lte",
        "hazard_class", "hazard_class_is", "hazard_class_in",
        "building_category_is",
    }
    for k, v in match.items():
        if k in skip_keys:
            continue
        # Translate suffix → human op
        for suf, label in _OP_SUFFIX_LABEL.items():
            if k.endswith(suf):
                field = k[: -len(suf)]
                # Pretty number with thousands separator if numeric
                v_str = f"{v:,}" if isinstance(v, (int, float)) else str(v)
                parts.append(f"{field} {label} {v_str}")
                break
        else:
            # No suffix → plain equality
            parts.append(f"{k} = {v}")

    return ", ".join(parts)


# ---------- Status legend (Tier-1 UI #1) -------------------------------------
st.markdown(
    "**Status legend:** "
    "🔴 `REQUIRED` (code 'shall') · "
    "🔵 `RECOMMENDED` (code 'should') · "
    "🟡 `CONDITIONAL` (subject to project context) · "
    "⚪ `NOT REQUIRED` (exemption captured for traceability)"
)

# ---------- Filter bar (Tier-1 UI #2) ----------------------------------------
_filt_c1, _filt_c2 = st.columns([2, 3])
with _filt_c1:
    _allowed = st.multiselect(
        "Filter by status",
        options=_STATUS_ORDER,
        default=_STATUS_ORDER,
        format_func=lambda s: f"{_STATUS_BADGE[s][0]} {_STATUS_BADGE[s][1]}",
        help="Narrow the report by status. Default = show all.",
        key="filter_status",
    )
with _filt_c2:
    _text_q = st.text_input(
        "Search requirements",
        value="",
        placeholder="e.g. 'Sprinkler', 'Pa', 'Civil Defence', 'Section 4.6' …",
        help="Case-insensitive substring match against system name, spec, detail, and code-ref.",
        key="filter_text",
    )
_allowed_set = set(_allowed)

if PRINT_MODE:
    # Single full-width column for print; create a dummy right column we just
    # don't render into.
    col_left = st.container()
    col_right = st.container()
else:
    col_left, col_right = st.columns([2, 1])

with col_left:
    for ch in report.chapters:
        # Skip the entire chapter heading if no items pass the filter — keeps
        # the report tight when the user is searching for a specific term.
        if not any(_filter_items(blk.items, _allowed_set, _text_q)
                   for blk in ch.blocks):
            continue
        st.markdown(f"<a name='ch-{ch.chapter_code.lower()}'></a>", unsafe_allow_html=True)
        st.markdown(f"## {ch.chapter_code} - {ch.chapter_title}")
        if ch.selected_branch:
            _human = _human_match(
                (_RULE_LOOKUP.get(ch.selected_branch) or {}).get("match", {})
            )
            st.caption(
                f"Matched branch: `{ch.selected_branch}` · {ch.selected_branch_section}"
                + (f"\n\n**Why this branch:** {_human}" if _human else "")
            )
        for block in ch.blocks:
            render_block(block.title, block.items, _allowed_set, _text_q,
                         chapter_code=ch.chapter_code)

    # ---------- Attached parking sub-occupancy section ----------
    if report.attached_parking_chapters:
        st.markdown("---")
        st.markdown("<a name='attached-parking'></a>", unsafe_allow_html=True)
        kind = report.building.attached_parking_kind
        synth_occ = "parking_open" if kind == "open" else "parking_enclosed"
        st.markdown(f"# ATTACHED PARKING AREA")
        st.caption(f"Sub-occupancy evaluation as `{synth_occ}` (driven by **Building has parking** in Special rooms and usage). "
                   "All parking-specific requirements from MOE / FE / ES / EL / FA / FP / SC are surfaced here.")
        for ch in report.attached_parking_chapters:
            if not any(_filter_items(blk.items, _allowed_set, _text_q)
                       for blk in ch.blocks):
                continue
            st.markdown(f"## P-{ch.chapter_code} - {ch.chapter_title}")
            if ch.selected_branch:
                _human = _human_match(
                    (_RULE_LOOKUP.get(ch.selected_branch) or {}).get("match", {})
                )
                st.caption(
                    f"Matched parking branch: `{ch.selected_branch}` - {ch.selected_branch_section}"
                    + (f"\n\n**Why this branch:** {_human}" if _human else "")
                )
            for block in ch.blocks:
                render_block(block.title, block.items, _allowed_set, _text_q,
                             chapter_code=ch.chapter_code)
        st.markdown("---")

    if report.high_ceiling and report.high_ceiling.applies:
        hc = report.high_ceiling
        st.markdown("<a name='high-ceiling'></a>", unsafe_allow_html=True)
        st.subheader("FP - High Ceiling Sprinkler Design (Table 9.29.A)")
        with st.container(border=True):
            if hc.height_range:
                st.table({
                    "Ceiling height": f"{hc.ceiling_height_m} m",
                    "Hazard class": hc.hazard_class,
                    "Height band": hc.height_range,
                    "K-factor": hc.k_factor or "-",
                    "Min pressure": hc.min_pressure or "-",
                    "Min sprinklers": hc.min_sprinklers,
                    "Density": hc.density or "-",
                    "Design area": hc.design_area or "-",
                    "Pump (no hydrant)": f"{hc.pump_without_hydrant_gpm} gpm" if hc.pump_without_hydrant_gpm else "-",
                    "Pump (with hydrant)": f"{hc.pump_with_hydrant_gpm} gpm" if hc.pump_with_hydrant_gpm else "-",
                })
            if hc.note:
                st.caption(hc.note)

with col_right:
  if not PRINT_MODE:
    # ----- Table of contents with per-chapter status counts (Tier-1 UI #3) -----
    st.subheader("📑 Table of contents")
    _toc = []
    for ch in report.chapters:
        anchor = ch.chapter_code.lower()
        _short = ch.chapter_title.split("(")[0].strip()
        c = _chapter_counts(ch)
        # Build a compact suffix: "(14 items · 🔴9 · 🔵3 · 🟡2)" — non-zero only
        bits = [f"{c['total']} items"]
        for s in _STATUS_ORDER:
            if c[s]:
                bits.append(f"{_STATUS_BADGE[s][0]}{c[s]}")
        suffix = " · ".join(bits)
        _toc.append(f"- [{ch.chapter_code} - {_short}](#ch-{anchor}) — _{suffix}_")
    if report.attached_parking_chapters:
        ap_total = sum(_chapter_counts(c)["total"]
                       for c in report.attached_parking_chapters)
        _toc.append(f"- [⮕ ATTACHED PARKING AREA](#attached-parking) — _{ap_total} items_")
    if report.high_ceiling and report.high_ceiling.applies:
        _toc.append("- [FP - High Ceiling Sprinkler Design](#high-ceiling)")
    st.markdown("\n".join(_toc))
    st.caption("Click a chapter to jump. Counts ignore the filter bar.")

    # Print-friendly view link (Tier 3 UI #15)
    st.markdown(
        "[📄 Open print-friendly view](?print=1) "
        "<small>(hides sidebar + this column; use browser Print to PDF)</small>",
        unsafe_allow_html=True,
    )

    # ----- Audit-traceability expander (Tier 3 UI #17) -----
    _audit_notes = _scan_audit_notes()
    if _audit_notes:
        with st.expander(
            f"🔬 Audit notes — {len(_audit_notes)} item(s)", expanded=False
        ):
            st.caption(
                "Markers left in the YAML by the audit-fix campaign — items "
                "the audit flagged as 'needs verification', 'not encoded', or "
                "'TODO'. Cross-check these against the UAE FLSC PDF."
            )
            # Group by file for readability
            _by_file: dict[str, list[dict]] = {}
            for n in _audit_notes:
                _by_file.setdefault(n["file"], []).append(n)
            for fname in sorted(_by_file.keys()):
                st.markdown(f"**`{fname}`** — {len(_by_file[fname])} note(s)")
                for n in _by_file[fname]:
                    st.markdown(f"- L{n['line']}: {n['text']}")

    st.markdown("---")
    with st.expander("📤 Copy / Export", expanded=False):
        md_base = report_to_markdown(report)
        # Prepend project notes if any
        _notes = st.session_state.get("project_notes_input", "").strip()
        md = (f"## Project notes\n\n{_notes}\n\n---\n\n" + md_base) if _notes else md_base
        st.code(md, language="markdown")
    fname_stem = (project_name or "building").replace(" ", "_")

    st.download_button("Download Markdown (.md)", data=md,
                       file_name=f"{fname_stem}_FLSC_requirements.md",
                       mime="text/markdown", use_container_width=True)
    try:
        st.download_button("Download Word (.docx)",
                           data=report_to_docx_bytes(report),
                           file_name=f"{fname_stem}_FLSC_requirements.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           use_container_width=True)
    except Exception as e:
        st.warning(f"Word export needs python-docx: {e}")
    try:
        st.download_button("Download PDF (.pdf)",
                           data=report_to_pdf_bytes(report),
                           file_name=f"{fname_stem}_FLSC_requirements.pdf",
                           mime="application/pdf", use_container_width=True)
    except Exception as e:
        st.warning(f"PDF export needs reportlab: {e}")

st.caption(
    "All UAE FLSC life-safety chapters loaded: MOE (Ch 3), FE (Ch 4), ES (Ch 5), EL (Ch 6), "
    "EVC (Ch 7), FA (Ch 8), FP (Ch 9), SC (Ch 10), LPG (Ch 11)."
)

# ---------- Disclaimer footer (Tier-1 UI #4) ---------------------------------
st.markdown("---")
with st.container(border=True):
    st.markdown(f"⚖️ **Disclaimer.** {DISCLAIMER}")
