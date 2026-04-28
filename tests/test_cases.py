"""Verification - archetype cases for FP (Ch 9) and ES (Ch 5)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schema import Building
from engine import evaluate


def _items(report, chapter_code: str, title_substr: str = ""):
    """Flatten requirements from the named chapter (optionally a block whose title contains substr)."""
    ch = report.chapter(chapter_code)
    if not ch:
        return []
    out = []
    for block in ch.blocks:
        if title_substr and title_substr not in block.title:
            continue
        out.extend(block.items)
    return out


def _names(items):
    return [r.system for r in items]


CASES = [
    # ---- FP archetypes ----
    dict(name="FP: Private villa < 1500 m² (recommended sprinkler)",
         inputs=dict(occupancy="villa_private", height_m=6, floors_above_grade=2,
                     ground_floor_bua_m2=250, plot_area_m2=600),
         expect_fp_branch="villa_private_base"),

    dict(name="FP: Private villa GF > 1500 m²",
         inputs=dict(occupancy="villa_private", height_m=6, floors_above_grade=2,
                     floors_below_grade=1, ground_floor_bua_m2=1600,
                     basement_bua_m2=1200, plot_area_m2=2200),
         expect_fp_systems=["Hose Reel System (basement + ground floor)",
                            "Fire Pump", "Fire Water Tank"]),

    dict(name="FP: Covered Mall",
         inputs=dict(occupancy="mall_covered", height_m=18,
                     floors_above_grade=3, floors_below_grade=2,
                     ground_floor_bua_m2=25000, plot_area_m2=50000),
         expect_fp_branch="mall_covered",
         expect_fp_systems=["Wet Riser System (interconnected at highest level)",
                            "Yard Fire Hydrants",
                            "ESFR Sprinklers (supermarket / hypermarket / large clothing storage)"]),

    dict(name="FP: 55 m residential highrise",
         inputs=dict(occupancy="residential", height_m=55,
                     floors_above_grade=18, floors_below_grade=2,
                     ground_floor_bua_m2=1200, plot_area_m2=5000,
                     wet_riser_standpipes=3),
         expect_fp_branch="highrise_45_90_small_plot"),

    dict(name="FP: Super-highrise 120 m large plot",
         inputs=dict(occupancy="residential", height_m=120,
                     floors_above_grade=35, floors_below_grade=3,
                     ground_floor_bua_m2=1800, plot_area_m2=25000),
         expect_fp_branch="superhighrise_large_plot",
         expect_fp_systems=["Multi-level Pump Set (every 90 m from lowest level)"]),

    dict(name="FP: Healthcare lowrise 3000 m² GF",
         inputs=dict(occupancy="healthcare_a", height_m=12, floors_above_grade=3,
                     ground_floor_bua_m2=3000, plot_area_m2=8000),
         expect_fp_branch="lowrise_public_501_3600"),

    dict(name="FP: Diesel generator -> FOAM Sprinkler",
         inputs=dict(occupancy="healthcare_a", height_m=12, floors_above_grade=3,
                     ground_floor_bua_m2=1000, plot_area_m2=2000,
                     has_diesel_generator_room=True),
         expect_fp_aux_systems=["Foam Sprinkler System (Section 3.9)"]),

    dict(name="FP: Warehouse with 15 m ceiling triggers high-ceiling design",
         inputs=dict(occupancy="storage_industrial", height_m=14,
                     has_high_ceiling=True, ceiling_height_m=15.0,
                     hazard_class="OH2", floors_above_grade=1,
                     ground_floor_bua_m2=5000, plot_area_m2=10000),
         expect_high_ceiling_band="13.5 m to 18 m"),

    dict(name="FP: Mall with atrium",
         inputs=dict(occupancy="mall_covered", height_m=18, floors_above_grade=3,
                     ground_floor_bua_m2=10000, plot_area_m2=25000,
                     has_atrium=True),
         expect_fp_var_systems=["Atrium Sprinklers (ceiling + adjacent to opening)"]),

    dict(name="FP: Commercial kitchen -> Wet Chemical",
         inputs=dict(occupancy="business", height_m=10, floors_above_grade=2,
                     ground_floor_bua_m2=500, plot_area_m2=1000,
                     has_commercial_kitchen=True),
         expect_fp_eq_systems=["Automatic Wet Chemical System (Section 3.12) + Grease Filters"]),


    # ---- EL archetypes (Ch 6) ----
    dict(name="EL: Super-highrise -> Central Battery EL",
         inputs=dict(occupancy="residential", height_m=120,
                     floors_above_grade=35, ground_floor_bua_m2=1800,
                     plot_area_m2=25000),
         expect_el_branch="el_super_highrise",
         expect_el_systems=["Central Battery Emergency Lighting (Section 3.2)"]),

    dict(name="EL: Mall -> Central Battery (with monitored alternative)",
         inputs=dict(occupancy="mall_covered", height_m=18,
                     floors_above_grade=3, ground_floor_bua_m2=10000,
                     plot_area_m2=25000),
         expect_el_branch="el_mall",
         expect_el_systems=[
             "Central Battery Emergency Lighting (Section 3.2)",
             "Monitored Self-Contained EL (Section 3.3) - alternative",
         ]),

    dict(name="EL: Lowrise hospital -> Monitored Self-Contained",
         inputs=dict(occupancy="healthcare_a", height_m=12,
                     floors_above_grade=3, ground_floor_bua_m2=3000,
                     plot_area_m2=8000),
         expect_el_branch="el_lowrise_general",
         expect_el_systems=["Monitored Self-Contained EL (Section 3.3)"]),

    dict(name="EL: Small business lowrise -> Stand-alone Self-Contained",
         inputs=dict(occupancy="business", height_m=10,
                     floors_above_grade=2, ground_floor_bua_m2=400,
                     plot_area_m2=1000),
         expect_el_branch="el_business_lowrise",
         expect_el_systems=["Stand-alone Self-Contained EL (Section 3.4)"]),

    dict(name="EL: Mercantile Group A -> Stand-alone",
         inputs=dict(occupancy="mercantile_a", height_m=8,
                     floors_above_grade=2, ground_floor_bua_m2=1500,
                     plot_area_m2=2000),
         expect_el_branch="el_mercantile_small",
         expect_el_systems=["Stand-alone Self-Contained EL (Section 3.4)"]),

    dict(name="EL: Fuel station -> Stand-alone",
         inputs=dict(occupancy="motor_fuel_dispensing", height_m=4,
                     floors_above_grade=1, ground_floor_bua_m2=300,
                     plot_area_m2=2000),
         expect_el_branch="el_fuel_dispensing",
         expect_el_systems=["Stand-alone Self-Contained EL (Section 3.4)"]),

    dict(name="EL: Private villa -> Not mandatory",
         inputs=dict(occupancy="villa_private", height_m=6,
                     floors_above_grade=2, ground_floor_bua_m2=300,
                     plot_area_m2=600),
         expect_el_branch="el_villa_above_grade",
         expect_el_status={"Emergency Lighting (above-grade levels)": "not_required"}),

    dict(name="EL: Villa with basement -> Stand-alone for basement",
         inputs=dict(occupancy="villa_private", height_m=6,
                     floors_above_grade=2, floors_below_grade=1,
                     ground_floor_bua_m2=400, basement_bua_m2=300,
                     plot_area_m2=800),
         expect_el_systems=["Stand-alone Self-Contained EL (basement only)"]),

    dict(name="EL: Hotel -> general specs include guest-room luminaire",
         inputs=dict(occupancy="hotel_a", height_m=18,
                     floors_above_grade=5, ground_floor_bua_m2=1000,
                     plot_area_m2=2000),
         expect_el_general=["EL inside Hotel Guest Rooms"]),

    dict(name="EL: Assembly with amusement -> Central Battery",
         inputs=dict(occupancy="assembly_b", height_m=12,
                     floors_above_grade=2, ground_floor_bua_m2=2000,
                     plot_area_m2=5000, has_amusement_confounding=True),
         expect_el_branch="el_assembly_amusement",
         expect_el_systems=["Central Battery Emergency Lighting (Section 3.2)"]),


    # ---- FE archetypes (Ch 4) ----
    dict(name="FE: Hotel highrise -> universal Class A + residential Class K + commercial kitchen Class K",
         inputs=dict(occupancy="hotel_a", height_m=55, floors_above_grade=18,
                     ground_floor_bua_m2=1200, plot_area_m2=5000,
                     has_commercial_kitchen=True, has_main_electrical_room=True),
         expect_fe_general=[
             "Class A Fire Extinguisher (Multi-purpose Dry Powder OR Clean Agent) + CO2",
             "Class K Fire Extinguisher (Residential Kitchen)",
         ],
         expect_fe_addons=[
             "Class K Fire Extinguisher (Commercial Kitchen)",
             "Class C Extinguisher - Main Electrical Room",
         ]),

    dict(name="FE: Petrol station -> Class B Wheeled Foam",
         inputs=dict(occupancy="motor_fuel_dispensing", height_m=4,
                     floors_above_grade=1, ground_floor_bua_m2=300,
                     plot_area_m2=2000),
         expect_fe_branch="fe_fuel_dispensing",
         expect_fe_branch_systems=["Class B Wheeled Foam Extinguisher"]),

    dict(name="FE: Diesel generator -> Wheeled Foam (add-on)",
         inputs=dict(occupancy="business", height_m=10, floors_above_grade=2,
                     ground_floor_bua_m2=400, plot_area_m2=1000,
                     has_diesel_generator_room=True),
         expect_fe_addons=["Class B Wheeled Foam Extinguisher - Diesel Generator Room"]),

    dict(name="FE: Class B storage zones flag -> Foam + Dry Powder",
         inputs=dict(occupancy="storage_industrial", height_m=12,
                     floors_above_grade=2, ground_floor_bua_m2=2000,
                     plot_area_m2=4000, has_class_b_storage_zones=True),
         expect_fe_addons=["Class B Fire Extinguisher (Foam + Dry Powder) - Storage Zones"]),

    dict(name="FE: Combustible metals -> Class D Wheeled",
         inputs=dict(occupancy="storage_industrial", height_m=12,
                     floors_above_grade=2, ground_floor_bua_m2=3000,
                     plot_area_m2=5000, has_combustible_metals=True),
         expect_fe_addons=["Class D Wheeled Extinguisher (Combustible Metals)"]),

    dict(name="FE: Private villa -> Class A recommended only",
         inputs=dict(occupancy="villa_private", height_m=6, floors_above_grade=2,
                     ground_floor_bua_m2=300, plot_area_m2=600),
         expect_fe_general=["Class A Fire Extinguisher (recommended for villas)",
                            "Class K Fire Extinguisher (Residential Kitchen)"],
         expect_fe_status={"Class A Fire Extinguisher (recommended for villas)": "recommended"}),


    # ---- EVC archetypes (Ch 7) ----
    dict(name="EVC: Hotel highrise -> EVC + Two-way required",
         inputs=dict(occupancy="hotel_a", height_m=55, floors_above_grade=18,
                     ground_floor_bua_m2=1200, plot_area_m2=5000),
         expect_evc_branch="evc_highrise",
         expect_evc_systems=[
             "Emergency Voice Evacuation or Communication System (EVC)",
             "Two-way Telephone Communication System",
         ]),

    dict(name="EVC: Mall -> EVC + Two-way",
         inputs=dict(occupancy="mall_covered", height_m=18,
                     floors_above_grade=3, ground_floor_bua_m2=10000,
                     plot_area_m2=25000),
         expect_evc_branch="evc_mall",
         expect_evc_systems=[
             "Emergency Voice Evacuation or Communication System (EVC)",
             "Two-way Telephone Communication System",
         ]),

    dict(name="EVC: Small office lowrise -> NOT required",
         inputs=dict(occupancy="business", height_m=10, floors_above_grade=2,
                     ground_floor_bua_m2=400, plot_area_m2=1000),
         expect_evc_branch="evc_business_not_required",
         expect_evc_status={"Emergency Voice Evacuation (EVC) - business under highrise": "not_required"}),

    dict(name="EVC: Residential lowrise -> NOT required",
         inputs=dict(occupancy="residential", height_m=12, floors_above_grade=4,
                     ground_floor_bua_m2=600, plot_area_m2=1500),
         expect_evc_branch="evc_residential_not_required",
         expect_evc_status={"Emergency Voice Evacuation (EVC) - residential occupancies up to highrise threshold": "not_required"}),

    dict(name="EVC: Storage 6000 m² -> required",
         inputs=dict(occupancy="storage_industrial", height_m=10,
                     floors_above_grade=2, gross_floor_area_m2=6000,
                     ground_floor_bua_m2=4000, plot_area_m2=8000),
         expect_evc_branch="evc_storage_industrial_large",
         expect_evc_systems=["Emergency Voice Evacuation or Communication System (EVC)"]),

    dict(name="EVC: Storage 3000 m² -> NOT required",
         inputs=dict(occupancy="storage_industrial", height_m=10,
                     floors_above_grade=2, gross_floor_area_m2=3000,
                     ground_floor_bua_m2=2500, plot_area_m2=5000),
         expect_evc_branch="evc_storage_industrial_small",
         expect_evc_status={"Emergency Voice Evacuation (EVC) - small storage/industrial": "not_required"}),

    dict(name="EVC: Villa -> NOT required",
         inputs=dict(occupancy="villa_private", height_m=6, floors_above_grade=2,
                     ground_floor_bua_m2=300, plot_area_m2=600),
         expect_evc_branch="evc_villa_not_required"),


    # ---- FA archetypes (Ch 8) ----
    dict(name="FA: Highrise -> sub-FACPs every 45m + 5-floor PAS",
         inputs=dict(occupancy="hotel_a", height_m=55, floors_above_grade=18,
                     ground_floor_bua_m2=1200, plot_area_m2=5000),
         expect_fa_branch="fa_highrise",
         expect_fa_systems=[
             "Smoke Detection and Alarm System (entire building)",
             "Sub-FACPs / Annunciators every 45 m",
             "5-Floor Phased Evacuation Alarm",
         ]),

    dict(name="FA: Mall -> networked sub-FACPs + per-tenant PAS",
         inputs=dict(occupancy="mall_covered", height_m=18,
                     floors_above_grade=3, ground_floor_bua_m2=10000,
                     plot_area_m2=25000),
         expect_fa_branch="fa_mall",
         expect_fa_systems=[
             "Smoke Detection and Alarm System (entire mall)",
             "Networked Sub-FACPs (per fire-evacuation zone)",
         ]),

    dict(name="FA: Healthcare -> nurse-station annunciators + critical care visual",
         inputs=dict(occupancy="healthcare_a", height_m=18, floors_above_grade=4,
                     ground_floor_bua_m2=4000, plot_area_m2=8000,
                     has_operation_theater=True),
         expect_fa_branch="fa_healthcare",
         expect_fa_systems=[
             "Annunciators at Nurse Stations (strategic locations)",
             "Visual Notification Devices in Critical Care (in lieu of audible)",
         ],
         expect_fa_aux=["Aspiration Air Sampling (Operation Theatre)"]),

    dict(name="FA: Detention -> aspiration in cells",
         inputs=dict(occupancy="detention_a", height_m=12, floors_above_grade=3,
                     ground_floor_bua_m2=2000, plot_area_m2=4000),
         expect_fa_branch="fa_detention",
         expect_fa_systems=["Aspiration Type Air Sampling (Inmate Cells / Sleeping Areas)"]),

    dict(name="FA: Atrium triggers Beam Smoke",
         inputs=dict(occupancy="mall_covered", height_m=18, floors_above_grade=3,
                     ground_floor_bua_m2=10000, plot_area_m2=25000,
                     has_atrium=True),
         expect_fa_aux=["Beam Smoke Detection (Atrium)"]),

    dict(name="FA: Battery room -> Heat + Flame + Hydrogen",
         inputs=dict(occupancy="business", height_m=10, floors_above_grade=2,
                     ground_floor_bua_m2=500, plot_area_m2=1000,
                     has_battery_room=True),
         expect_fa_aux=["Heat + Flame + Hydrogen Detection (Battery Room)"]),

    dict(name="FA: Diesel generator + Commercial kitchen -> Heat + Fusible-link",
         inputs=dict(occupancy="hotel_a", height_m=18, floors_above_grade=5,
                     ground_floor_bua_m2=1000, plot_area_m2=2000,
                     has_diesel_generator_room=True, has_commercial_kitchen=True),
         expect_fa_aux=["Heat Detection (Diesel Generator Room)"],
         expect_fa_eq=["Fusible-Link Heat Detection (Kitchen Hood)",
                       "Heat Detection (Diesel Generator Area)"]),

    dict(name="FA: Open parking -> Manual only",
         inputs=dict(occupancy="parking_open", height_m=12, floors_above_grade=3,
                     ground_floor_bua_m2=3000, plot_area_m2=5000),
         expect_fa_branch="fa_parking_open",
         expect_fa_systems=["Manual Fire Detection and Alarm System"]),

    dict(name="FA: Villa -> Smoke OR Wireless RF + external A/V",
         inputs=dict(occupancy="villa_private", height_m=6, floors_above_grade=2,
                     ground_floor_bua_m2=400, plot_area_m2=800),
         expect_fa_branch="fa_villa_private",
         expect_fa_systems=[
             "Smoke Detection and Alarm System (each villa)",
             "External Audio-Visual Notification Devices",
         ]),


    # ---- SC archetypes (Ch 10) ----
    dict(name="SC: Super-highrise -> stair pressurization + lobby + firefighting lift",
         inputs=dict(occupancy="residential", height_m=120, floors_above_grade=35,
                     ground_floor_bua_m2=1800, plot_area_m2=25000),
         expect_sc_branch="sc_super_highrise",
         expect_sc_systems=[
             "Stair Pressurization (multi-injection, all levels including basements)",
             "Passenger Elevator Lobby (1-hr fire rated, smoke barrier)",
             "Firefighting Lift + Firefighting Lobby (mandatory)",
         ]),

    dict(name="SC: Lowrise office -> stair pressurization NOT required",
         inputs=dict(occupancy="business", height_m=10, floors_above_grade=2,
                     ground_floor_bua_m2=400, plot_area_m2=1000),
         expect_sc_branch="sc_midrise_lowrise_default",
         expect_sc_status={"Stair Pressurization NOT Required (default)": "not_required"}),

    dict(name="SC: Lowrise hospital -> special-occupancy stair pressurization required",
         inputs=dict(occupancy="healthcare_a", height_m=12, floors_above_grade=3,
                     ground_floor_bua_m2=3000, plot_area_m2=8000),
         expect_sc_systems=["Stair Pressurization (special occupancy override)"]),

    dict(name="SC: Enclosed parking -> mechanical purging via dedicated ducting",
         inputs=dict(occupancy="parking_enclosed", height_m=12, floors_above_grade=3,
                     ground_floor_bua_m2=3000, plot_area_m2=5000),
         expect_sc_branch="sc_parking_enclosed",
         expect_sc_systems=["Mechanical Smoke Purging via Dedicated Ducting"]),

    dict(name="SC: Open parking <=4000 m² -> no purging required",
         inputs=dict(occupancy="parking_open", height_m=10, floors_above_grade=2,
                     gross_floor_area_m2=3000, ground_floor_bua_m2=3000,
                     plot_area_m2=5000),
         expect_sc_branch="sc_parking_open_small",
         expect_sc_status={"Smoke Purging / Ventilation NOT Required": "not_required"}),

    dict(name="SC: Open parking >4000 m² -> mechanical purging or jet fan",
         inputs=dict(occupancy="parking_open", height_m=10, floors_above_grade=2,
                     gross_floor_area_m2=6000, ground_floor_bua_m2=6000,
                     plot_area_m2=8000),
         expect_sc_branch="sc_parking_open_large",
         expect_sc_systems=["Mechanical Smoke Purging OR Jet Fan System"]),

    dict(name="SC: Mall -> circulation + atrium + tenant >1000 m²",
         inputs=dict(occupancy="mall_covered", height_m=18, floors_above_grade=3,
                     ground_floor_bua_m2=10000, plot_area_m2=25000,
                     has_atrium=True),
         expect_sc_branch="sc_mall",
         expect_sc_systems=[
             "Mall Circulation Smoke Control",
             "Anchor / Hypermarket / Tenant > 1000 m² Smoke Management",
         ]),

    dict(name="SC: Storage 6000 m² -> mechanical roof exhaust",
         inputs=dict(occupancy="storage_industrial", height_m=10,
                     floors_above_grade=2, ground_floor_bua_m2=6000,
                     gross_floor_area_m2=6000, plot_area_m2=10000),
         expect_sc_branch="sc_storage_industrial_over_2000",
         expect_sc_systems=["Mechanical Roof Exhaust Fans (with engineering analysis if natural)"]),

    dict(name="SC: Atrium -> atrium smoke management",
         inputs=dict(occupancy="mall_covered", height_m=18, floors_above_grade=3,
                     ground_floor_bua_m2=10000, plot_area_m2=25000,
                     has_atrium=True),
         expect_sc_aux=["Atrium Smoke Management System"]),

    dict(name="SC: Diesel generator + commercial kitchen -> mech ventilation + cooking ventilation",
         inputs=dict(occupancy="hotel_a", height_m=18, floors_above_grade=5,
                     ground_floor_bua_m2=1000, plot_area_m2=2000,
                     has_diesel_generator_room=True, has_commercial_kitchen=True),
         expect_sc_aux=[
             "Diesel Generator Room - Dedicated Mechanical Ventilation",
             "Kitchen Cooking Operation Ventilation",
         ]),

    dict(name="SC: Tunnel flag -> tunnel smoke management",
         inputs=dict(occupancy="business", height_m=10, floors_above_grade=2,
                     ground_floor_bua_m2=2000, plot_area_m2=5000,
                     has_tunnel=True),
         expect_sc_aux=["Tunnel Smoke Management"]),

    dict(name="SC: Deep basement (4 levels below) -> underground stair pressurization",
         inputs=dict(occupancy="mall_covered", height_m=18, floors_above_grade=3,
                     floors_below_grade=4, ground_floor_bua_m2=8000,
                     basement_bua_m2=8000, plot_area_m2=15000),
         expect_sc_systems=["Stair Pressurization (deep basements - > 7 m below OR > 2 basements)"]),

    # AUDIT Ch 10 Table 10.22 - depth-only trigger (1 basement, 8 m deep)
    dict(name="AUDIT SC: Single deep basement (8m, 1 level) -> Table 10.22 by depth",
         inputs=dict(occupancy="business", height_m=20, floors_above_grade=5,
                     floors_below_grade=1, depth_below_grade_m=8.0,
                     ground_floor_bua_m2=800, plot_area_m2=2000),
         expect_sc_systems=["Stair Pressurization (deep basements - > 7 m below OR > 2 basements)"]),

    # AUDIT Ch 10 Table 10.27 item 4 - lowrise corridor > 60 m
    dict(name="AUDIT SC: Hotel lowrise corridor 80m -> long-corridor natural ventilation (Table 10.27 item 4)",
         inputs=dict(occupancy="hotel_b", height_m=18, floors_above_grade=5,
                     corridor_length_m=80, ground_floor_bua_m2=800, plot_area_m2=2000),
         expect_sc_systems=["Enclosed Corridor Natural Ventilation (corridor length > 60 m, lowrise/midrise)"]),


    # ---- LPG archetypes (Ch 11) ----
    dict(name="LPG: No gas system -> Chapter 11 not applicable",
         inputs=dict(occupancy="residential", height_m=12, floors_above_grade=4,
                     ground_floor_bua_m2=600, plot_area_m2=1500),
         expect_lpg_branch="lpg_no_gas_system",
         expect_lpg_status={"No Gas System Present": "not_required"}),

    dict(name="LPG: Villa cylinders -> outdoor cylinder install",
         inputs=dict(occupancy="villa_private", height_m=6, floors_above_grade=2,
                     ground_floor_bua_m2=300, plot_area_m2=600,
                     has_gas_cylinders_villa=True),
         expect_lpg_branch="lpg_cylinders_villa",
         expect_lpg_systems=[
             "Outdoor LPG Cylinder Installation Location",
             "Outdoor Cylinder Separation Distances",
             "Cylinder Quantity Limits",
         ]),

    dict(name="LPG: Gas infrastructure connection -> central distribution requirements",
         inputs=dict(occupancy="hotel_a", height_m=55, floors_above_grade=18,
                     ground_floor_bua_m2=1200, plot_area_m2=5000,
                     has_gas_infra_connection=True),
         expect_lpg_branch="lpg_central_distribution",
         expect_lpg_systems=[
             "LPG Piping Distribution",
             "Dedicated Fire-Rated LPG Shafts",
             "Emergency Shut-off Valves (ESV)",
         ]),

    dict(name="LPG: Aboveground tanks -> Table 11.5 + 11.6",
         inputs=dict(occupancy="business", height_m=12, floors_above_grade=3,
                     ground_floor_bua_m2=2000, plot_area_m2=8000,
                     has_lpg_tanks=True),
         expect_lpg_branch="lpg_aboveground_tank",
         expect_lpg_systems=[
             "Aboveground LPG Tank Installation",
             "Maximum Quantity (72,000 Gal per location)",
             "Tank Separation Distances",
             "Two-Stage Pressure Regulation",
         ]),


    # ---- AUDIT-DERIVED archetypes (gap-fill tests) ----
    dict(name="AUDIT FP: Residential lowrise 4-storey 800m² GF -> hose reel only (Table 9.21.b.1)",
         inputs=dict(occupancy="residential", height_m=12, floors_above_grade=4,
                     ground_floor_bua_m2=800, plot_area_m2=2000),
         expect_fp_branch="lowrise_residential_upto_3600",
         expect_fp_systems=["Hose Reel System (throughout)",
                            "Fire Pump", "Fire Water Tank"]),

    dict(name="AUDIT FP: Labour accommodation lowrise 4500m² GF -> sprinkler + wet riser (Table 9.21.b.2)",
         inputs=dict(occupancy="labour_accommodation", height_m=14, floors_above_grade=4,
                     ground_floor_bua_m2=4500, plot_area_m2=8000, wet_riser_standpipes=3),
         expect_fp_branch="lowrise_residential_over_3600",
         expect_fp_systems=["Automatic Sprinkler System (full coverage incl. basements & podiums)",
                            "Wet Riser System (interconnected at highest level)"]),

    dict(name="AUDIT FP: Hostel lowrise large plot >20,000m² (Table 9.21.b.3)",
         inputs=dict(occupancy="hostel", height_m=12, floors_above_grade=3,
                     ground_floor_bua_m2=2000, plot_area_m2=25000),
         expect_fp_branch="lowrise_residential_large_plot",
         expect_fp_systems=["Yard Fire Hydrants", "Fire Pump", "Fire Water Tank"]),

    # ---- AUDIT FP: Tables 9.26 + 9.27 (Infrastructure + Storage/Industrial) ----
    dict(name="AUDIT FP: Infrastructure -> dedicated 1000 gpm yard hydrant + 90-min tank (Table 9.26)",
         inputs=dict(occupancy="infrastructure", height_m=0,
                     plot_area_m2=20000),
         expect_fp_branch="infrastructure_general",
         expect_fp_systems=[
             "Yard Fire Hydrants - Dedicated Network (NOT shared with irrigation)",
             "Fire Pump (Infrastructure)",
             "Fire Water Tank (Infrastructure)",
         ]),

    dict(name="AUDIT FP: Storage LH 500 m2 -> Tier 2 LH (Table 9.27 A.2 - 250 gpm pump)",
         inputs=dict(occupancy="storage_industrial", height_m=8, ground_floor_bua_m2=500,
                     plot_area_m2=2000, hazard_class="LH"),
         expect_fp_branch="storage_industrial_tier2_lh",
         expect_fp_systems=[
             "Automatic Sprinkler System (full coverage)",
             "Fire Pump (Tier 2 LH)",
             "MSDS Review (DESIGNER OBLIGATION)",
         ]),

    dict(name="AUDIT FP: Storage OH 4000 m2 -> Tier 4 OH (Table 9.27 B.4 - 750 gpm @ hydrant)",
         inputs=dict(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=4000,
                     plot_area_m2=10000, hazard_class="OH1"),
         expect_fp_branch="storage_industrial_tier4_oh",
         expect_fp_systems=[
             "Yard Fire Hydrants (loop covering entire facility)",
             "Fire Pump (Tier 4 OH)",
         ]),

    dict(name="AUDIT FP: Aircraft hanger -> foam deluge + 1500 gpm (Table 9.27 Group Q)",
         inputs=dict(occupancy="storage_industrial", height_m=12, ground_floor_bua_m2=4000,
                     plot_area_m2=10000, hazard_class="OH2", is_aircraft_hanger=True),
         expect_fp_branch="storage_aircraft_hanger",
         expect_fp_systems=[
             "Foam-Water Deluge System",
             "Fire Pump (Aircraft Hanger)",
             "Fire Water Tank + Foam Concentrate",
         ]),

    dict(name="AUDIT FP: Cold storage -> dry-pipe sprinklers (Table 9.27 Group P)",
         inputs=dict(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000,
                     plot_area_m2=5000, hazard_class="OH1", is_cold_storage=True),
         expect_fp_branch="storage_cold_storage",
         expect_fp_systems=[
             "Automatic DRY-Pipe Sprinkler System (NOT wet pipe)",
         ]),

    dict(name="AUDIT FP: Flammable liquid warehouse -> foam + 120-min tank (Table 9.27 Group R)",
         inputs=dict(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=2000,
                     plot_area_m2=5000, hazard_class="HH", is_flammable_liquid_warehouse=True),
         expect_fp_branch="storage_flammable_liquid_warehouse",
         expect_fp_systems=[
             "Sprinkler OR Foam-Water Sprinkler System",
             "Fire Water Tank + Foam Reserve",
         ]),

    dict(name="AUDIT FP: Plant nursery -> extinguishers only (Table 9.27 Group V)",
         inputs=dict(occupancy="storage_industrial", height_m=4, ground_floor_bua_m2=300,
                     plot_area_m2=1000, hazard_class="LH", is_plant_nursery=True),
         expect_fp_branch="storage_plant_nursery",
         expect_fp_systems=[
             "Portable Fire Extinguishers (only)",
         ]),

    # ---- AUDIT FA: Ch 8 patches (general + CD/HoE gating) ----
    dict(name="AUDIT FA: Universal General entries fire (Table 8.1.a + addressable FACP)",
         inputs=dict(occupancy="residential", height_m=20,
                     ground_floor_bua_m2=600, plot_area_m2=2000),
         expect_fa_general=[
             "Visible (Strobe) Notification Device Spacing - Table 8.1.a",
             "Addressable Fire Detection & Alarm Control Panel (FACP)",
             "FACP Interface to Civil Defence Receiving Station",
         ]),

    dict(name="AUDIT FA: Bulk flammable liquid storage -> CD/HoE gating spec/detail",
         inputs=dict(occupancy="storage_industrial", height_m=8, ground_floor_bua_m2=4000,
                     plot_area_m2=10000, hazard_class="HH",
                     has_bulk_flammable_liquid_storage=True),
         expect_fa_eq=["IS Flame + IS Linear Heat (Bulk Flammable Liquid Storage)"]),

    # ---- AUDIT EVC: Ch 7 General Specifications (Tables 7.1 + 7.2) ----
    dict(name="AUDIT EVC: Super-highrise -> EVC General specs (jacks, voice msg pattern, 2-hr wiring)",
         inputs=dict(occupancy="residential", height_m=120, floors_above_grade=35,
                     ground_floor_bua_m2=1800, plot_area_m2=25000),
         expect_evc_general=[
             "EVC Control Unit Location",
             "Voice Message Pattern + Pre-recorded Content",
             "Two-way Telephone Jack Locations (Fireman's Phone)",
             "Two-way Telephone System Features",
             "Circuits + Wiring (Class A, addressable, 2-hr fire rated)",
         ]),

    dict(name="AUDIT EVC: Lowrise residential -> NO EVC General block (system not required)",
         inputs=dict(occupancy="residential", height_m=10, floors_above_grade=3,
                     ground_floor_bua_m2=400, plot_area_m2=1000),
         expect_evc_general_absent=True),

    # ---- AUDIT EL: Ch 6 patches (corrected lux values + 2m proximity + cable fire rating) ----
    dict(name="AUDIT EL: General specs include 0.65 lux floor + 10.8 lux average + 40:1 ratio",
         inputs=dict(occupancy="residential", height_m=20, floors_above_grade=6,
                     ground_floor_bua_m2=600, plot_area_m2=2000),
         expect_el_general=[
             "Emergency Lighting - General Performance Specs (Table 6.1)",
             "EL Proximity Rule (within 2m)",
             "EL Cable Fire Rating",
             "EL Acceptance Tests + Periodic Inspection",
         ]),

    # ---- AUDIT ES: Ch 5 universal sign specs (size, bilingual, photolum, tactile, placement) ----
    dict(name="AUDIT ES: Hotel -> universal sign specs (150 mm letters, bilingual, tactile, photolum)",
         inputs=dict(occupancy="hotel_a", height_m=18, floors_above_grade=5,
                     ground_floor_bua_m2=1000, plot_area_m2=2000),
         expect_es_universal=[
             "Exit Sign Letter Size + Bilingual EXIT (English + Arabic)",
             "Sign Illumination - External vs Internal",
             "Photoluminescent Sign Specifications (UL 1994)",
             "Tactile Sign at Every Exit (Braille + Raised Characters)",
             "Directional Exit Sign Placement Rules",
             "Floor Proximity Sign Mounting (150-455 mm above floor)",
         ]),

    # ---- AUDIT FE: Ch 4 patches (universal mounting/CD/inspection + Class C 9m travel) ----
    dict(name="AUDIT FE: Universal entries fire (Civil Defence + mounting + inspection)",
         inputs=dict(occupancy="business", height_m=10, ground_floor_bua_m2=500, plot_area_m2=1000),
         expect_fe_general=[
             "Civil Defence Approval + Licensed Contractor",
             "Mounting Heights + Cabinet + Signage",
             "Inspection + Testing Intervals",
         ]),

    # ---- AUDIT MOE: Ch 3 Table 3.16 patches (7 branches gained Travel/Common-path/Dead-end) ----
    dict(name="AUDIT MOE: Mercantile -> Table 3.16 row 13 travel/commonpath/dead-end",
         inputs=dict(occupancy="mercantile_a", height_m=8, ground_floor_bua_m2=600, plot_area_m2=2000),
         expect_moe_branch="moe_mercantile"),

    dict(name="AUDIT MOE: Mall -> Table 3.16 rows 14-15 (covered/open)",
         inputs=dict(occupancy="mall_covered", height_m=18, floors_above_grade=3,
                     ground_floor_bua_m2=10000, plot_area_m2=25000),
         expect_moe_branch="moe_mall"),

    dict(name="AUDIT MOE: Daycare -> Table 3.16 row 12 + 10 mm/person stair",
         inputs=dict(occupancy="daycare_b", height_m=8, ground_floor_bua_m2=400, plot_area_m2=1000),
         expect_moe_branch="moe_daycare"),

    dict(name="AUDIT MOE: Detention -> Table 3.16 row 10 (Type II/III/IV vs V)",
         inputs=dict(occupancy="detention_b", height_m=10, ground_floor_bua_m2=800, plot_area_m2=2000),
         expect_moe_branch="moe_detention"),

    dict(name="AUDIT MOE: Storage HH -> 0m commonpath/dead-end + 23m travel (Table 3.16 row 16/18)",
         inputs=dict(occupancy="storage_industrial", height_m=8, ground_floor_bua_m2=4000,
                     plot_area_m2=10000, hazard_class="HH"),
         expect_moe_branch="moe_storage_industrial_high_hazard"),

    dict(name="AUDIT MOE: Storage LH/OH -> 122/61 m travel (Table 3.16 rows 17, 19)",
         inputs=dict(occupancy="storage_industrial", height_m=8, ground_floor_bua_m2=2000,
                     plot_area_m2=5000, hazard_class="OH1"),
         expect_moe_branch="moe_storage_industrial_ordinary"),

    dict(name="AUDIT MOE: Animal Housing -> Table 3.16 row 22 (91/61 m travel)",
         inputs=dict(occupancy="animal_housing", height_m=6, ground_floor_bua_m2=400, plot_area_m2=1500),
         expect_moe_branch="moe_animal_housing"),

    # ---- AUDIT LPG: Ch 11 patches (general universal block + flame effect addon) ----
    dict(name="AUDIT LPG: Hotel with LPG tanks -> universal general block fires",
         inputs=dict(occupancy="hotel_a", height_m=18, ground_floor_bua_m2=1000,
                     plot_area_m2=2000, has_lpg_tanks=True),
         expect_lpg_general=[
             "Civil Defence Listing + Approved Contractor (Universal)",
             "Gas-Leak Detection + Interfaced ESV (Universal)",
             "Ignition-Source Clearance + Electrical Hazard Class",
             "Inspection + Maintenance Checklist (Table 11.14)",
         ]),

    dict(name="AUDIT LPG: Flame effect (Table 11.12) -> dedicated addon fires",
         inputs=dict(occupancy="assembly_b", height_m=10, ground_floor_bua_m2=600,
                     plot_area_m2=1500, has_lpg_flame_effect=True),
         expect_lpg_addons=["Flame Effect LPG Installation (Table 11.12)"]),

    dict(name="AUDIT LPG: No gas system -> NO general universal block",
         inputs=dict(occupancy="residential", height_m=10, ground_floor_bua_m2=400, plot_area_m2=1000),
         expect_lpg_general_absent=True),

    # ---- AUDIT Attached Parking sub-evaluation ----
    dict(name="AUDIT Parking: Hotel + enclosed attached parking -> 7 parking sub-chapters",
         inputs=dict(occupancy="hotel_a", height_m=18, floors_above_grade=5,
                     ground_floor_bua_m2=1000, plot_area_m2=2000,
                     has_parking_area=True, attached_parking_kind="enclosed"),
         expect_attached_parking_count=7,
         expect_attached_parking_branch_for=("FP", "parking_enclosed")),

    dict(name="AUDIT Parking: Residential + open attached parking -> sub-evaluation parking_open",
         inputs=dict(occupancy="residential", height_m=20, floors_above_grade=6,
                     ground_floor_bua_m2=600, plot_area_m2=2000,
                     has_parking_area=True, attached_parking_kind="open"),
         expect_attached_parking_count=7,
         expect_attached_parking_branch_for=("MOE", "moe_parking_open")),

    dict(name="AUDIT Parking: Building IS parking_enclosed -> NO attached parking sub-evaluation (avoid recursion)",
         inputs=dict(occupancy="parking_enclosed", height_m=15, floors_above_grade=4,
                     ground_floor_bua_m2=4000, plot_area_m2=6000),
         expect_attached_parking_count=0),

    dict(name="AUDIT Parking: has_parking_area=False -> NO attached parking sub-evaluation",
         inputs=dict(occupancy="residential", height_m=10, floors_above_grade=3,
                     ground_floor_bua_m2=400, plot_area_m2=1000,
                     has_parking_area=False),
         expect_attached_parking_count=0),

    # ---- AUDIT FP: Single-tenant variants (Groups F-J) ----
    dict(name="AUDIT FP: Single-tenant LH 600 m2 -> Group F Tier 1 (45-min tank)",
         inputs=dict(occupancy="storage_industrial", is_single_tenant_storage=True,
                     height_m=8, ground_floor_bua_m2=600, plot_area_m2=2000, hazard_class="LH"),
         expect_fp_branch="storage_single_tenant_lh_tier1",
         expect_fp_systems=["Fire Pump (Single-Tenant LH Tier 1)"]),

    dict(name="AUDIT FP: Single-tenant OH2 1500 m2 -> 350 gpm pump (Group H Tier 2)",
         inputs=dict(occupancy="storage_industrial", is_single_tenant_storage=True,
                     height_m=10, ground_floor_bua_m2=1500, plot_area_m2=4000, hazard_class="OH2"),
         expect_fp_branch="storage_single_tenant_oh2_tier2",
         expect_fp_systems=["Fire Pump (Single-Tenant OH2 Tier 2)"]),

    dict(name="AUDIT FP: Single-tenant Extra Hazard (Groups I + J)",
         inputs=dict(occupancy="storage_industrial", is_single_tenant_storage=True,
                     height_m=10, ground_floor_bua_m2=2000, plot_area_m2=5000, hazard_class="HH"),
         expect_fp_branch="storage_single_tenant_extra_hazard",
         expect_fp_systems=["Fire Pump (Single-Tenant Extra Hazard)"]),

    dict(name="AUDIT FP: Idle pallet warehouse (Table 9.27 Group K)",
         inputs=dict(occupancy="storage_industrial", is_idle_pallet_storage=True,
                     height_m=10, ground_floor_bua_m2=2000, plot_area_m2=5000, hazard_class="OH2"),
         expect_fp_branch="storage_idle_pallet_warehouse",
         expect_fp_systems=["Fire Pump (Idle Pallet Storage)"]),

    # ---- AUDIT FP: Tunnel (Table 9.28) ----
    dict(name="AUDIT FP: Cable tunnel 40m -> deluge + dry riser at entry (Table 9.28 A < 60 m)",
         inputs=dict(occupancy="business", has_tunnel=True, tunnel_kind="cable",
                     tunnel_length_m=40, height_m=20, ground_floor_bua_m2=1000, plot_area_m2=2000),
         expect_fp_systems=[
             "Automatic Deluge Water Spray OR Water Mist System",
             "Dry Riser at Tunnel Entry Points",
             "Fire Pump (Cable Tunnel < 60 m)",
         ]),

    dict(name="AUDIT FP: Cable tunnel 100m -> deluge + wet riser throughout (Table 9.28 A >= 60 m)",
         inputs=dict(occupancy="business", has_tunnel=True, tunnel_kind="cable",
                     tunnel_length_m=100, height_m=20, ground_floor_bua_m2=1000, plot_area_m2=2000),
         expect_fp_systems=[
             "Automatic Deluge Water Spray OR Water Mist System",
             "Fire Pump (Cable Tunnel >= 60 m)",
         ]),

    dict(name="AUDIT FP: Road/rail tunnel 50m -> NO FP system (Table 9.28 B < 90 m)",
         inputs=dict(occupancy="business", has_tunnel=True, tunnel_kind="road_rail",
                     tunnel_length_m=50, height_m=20, ground_floor_bua_m2=1000, plot_area_m2=2000),
         expect_fp_systems=["No Tunnel Fire Protection System Required"]),

    dict(name="AUDIT FP: Road/rail tunnel 500m -> 750 gpm wet riser (Table 9.28 B 90-1000 m)",
         inputs=dict(occupancy="business", has_tunnel=True, tunnel_kind="road_rail",
                     tunnel_length_m=500, height_m=20, ground_floor_bua_m2=1000, plot_area_m2=2000),
         expect_fp_systems=["Fire Pump (Road/Rail Tunnel 90-1000 m)"]),

    dict(name="AUDIT FP: Road/rail tunnel 1500m -> Class III wet riser + deluge (Table 9.28 B > 1000 m)",
         inputs=dict(occupancy="business", has_tunnel=True, tunnel_kind="road_rail",
                     tunnel_length_m=1500, height_m=20, ground_floor_bua_m2=1000, plot_area_m2=2000),
         expect_fp_systems=[
             "Class III Wet Riser System (throughout)",
             "Fire Pump (Road/Rail Tunnel > 1000 m)",
         ]),

    dict(name="AUDIT FP: Motor fuel Group A -> sprinklers + 300 gpm pump (Table 9.25 A)",
         inputs=dict(occupancy="motor_fuel_dispensing", motor_fuel_group="A",
                     height_m=4, floors_above_grade=1,
                     ground_floor_bua_m2=300, plot_area_m2=2000),
         expect_fp_branch="motor_fuel_dispensing_group_a",
         expect_fp_systems=[
             "Automatic Sprinkler System (Group A - service station with individual buildings)",
             "Hose Reel System (throughout)",
             "Fire Pump (Group A)",
         ]),

    dict(name="AUDIT FP: Motor fuel Group B -> hose reel only + 50 gpm @ 6.9 bar (Table 9.25 B)",
         inputs=dict(occupancy="motor_fuel_dispensing", motor_fuel_group="B",
                     height_m=4, floors_above_grade=1,
                     ground_floor_bua_m2=300, plot_area_m2=2000),
         expect_fp_branch="motor_fuel_dispensing_group_b",
         expect_fp_systems=[
             "Hose Reel System (throughout)",
             "Fire Pump (Group B)",
         ]),

    dict(name="AUDIT FP: Motor fuel Group C -> extinguishers only, no water-based system (Table 9.25 C)",
         inputs=dict(occupancy="motor_fuel_dispensing", motor_fuel_group="C",
                     height_m=4, floors_above_grade=1,
                     ground_floor_bua_m2=300, plot_area_m2=2000),
         expect_fp_branch="motor_fuel_dispensing_group_c",
         expect_fp_systems=[
             "Portable Fire Extinguishers (only)",
         ]),

    dict(name="AUDIT MOE: Open parking 122m travel (Table 3.15.b)",
         inputs=dict(occupancy="parking_open", height_m=10, floors_above_grade=2,
                     ground_floor_bua_m2=4000, plot_area_m2=6000, hazard_class="OH1"),
         expect_moe_branch="moe_parking_open"),

    dict(name="AUDIT MOE: Enclosed parking 61m sprinklered / 46m non-sprinklered",
         inputs=dict(occupancy="parking_enclosed", height_m=12, floors_above_grade=3,
                     ground_floor_bua_m2=3000, plot_area_m2=5000, hazard_class="OH2"),
         expect_moe_branch="moe_parking_enclosed"),

    dict(name="AUDIT MOE: HH storage uses 18mm/person stair capacity",
         inputs=dict(occupancy="storage_industrial", height_m=8, floors_above_grade=1,
                     ground_floor_bua_m2=2000, plot_area_m2=5000, hazard_class="HH"),
         expect_moe_branch="moe_storage_industrial_high_hazard"),

    # ---- ES archetypes (Ch 5) ----
    dict(name="ES: Hotel needs Tactile + Floor Proximity + per-guest-room plan",
         inputs=dict(occupancy="hotel_a", height_m=18, floors_above_grade=5,
                     ground_floor_bua_m2=1000, plot_area_m2=2000),
         expect_es_branch="es_hotel",
         expect_es_systems=["Tactile Signs at Every Exit",
                            "Floor Proximity Signs",
                            "Per-Guest-Room Evacuation Plan"]),

    dict(name="ES: Private villa - signs not required",
         inputs=dict(occupancy="villa_private", height_m=6, floors_above_grade=2,
                     ground_floor_bua_m2=300, plot_area_m2=600),
         expect_es_branch="es_villa_private",
         expect_es_status={"Exit Signs Not Required": "not_required"}),

    dict(name="ES: Mall with theatre/cinema -> photoluminescent",
         inputs=dict(occupancy="mall_covered", height_m=18, floors_above_grade=3,
                     ground_floor_bua_m2=10000, plot_area_m2=25000,
                     has_theater_cinema=True, has_mall_play_food_cinema=True),
         expect_es_addons=[
             "Photoluminescent Exit Marking Strips (Theatres / Cinemas)",
             "Photoluminescent Exit Marking Strips (Mall Play / Food Court / Cinema zones)",
         ]),

    dict(name="ES: Education with nursery + auditorium photoluminescent",
         inputs=dict(occupancy="education_b", height_m=12, floors_above_grade=3,
                     ground_floor_bua_m2=2000, plot_area_m2=5000,
                     has_nursery_within=True, has_auditorium_within=True),
         expect_es_addons=[
             "Photoluminescent Exit Marking Strips (Nurseries)",
             "Photoluminescent Exit Marking Strips (Auditoriums)",
         ]),

    dict(name="ES: Storage with HH zones -> photoluminescent",
         inputs=dict(occupancy="storage_industrial", height_m=12,
                     floors_above_grade=2, ground_floor_bua_m2=3000,
                     plot_area_m2=5000, has_hh_storage_zones=True),
         expect_es_addons=[
             "Photoluminescent Exit Marking Strips (HH / Robotic / Cold / Cable Spread / Industrial Basements)",
         ]),

    dict(name="ES: Evacuation elevator + horizontal exits -> universal additions",
         inputs=dict(occupancy="healthcare_a", height_m=18, floors_above_grade=4,
                     ground_floor_bua_m2=4000, plot_area_m2=8000,
                     has_evacuation_elevator=True, has_horizontal_exits=True),
         expect_es_universal=["Evacuation Elevator Signs",
                              "Exit Signs at Horizontal Exit Doors"]),
]


def run_all():
    passed = failed = 0
    for case in CASES:
        b = Building(project_name=case["name"], **case["inputs"])
        r = evaluate(b)
        ok = True
        reasons = []

        # ----- FP checks -----
        fp = r.fp
        if "expect_fp_branch" in case:
            if not fp or fp.selected_branch != case["expect_fp_branch"]:
                ok = False
                reasons.append(f"FP branch: expected {case['expect_fp_branch']}, got {fp.selected_branch if fp else None}")
        for s in case.get("expect_fp_systems", []):
            if s not in _names(_items(r, "FP", "Branch Requirements")):
                ok = False
                reasons.append(f"missing FP branch system: {s}")
        for s in case.get("expect_fp_aux_systems", []):
            if s not in _names(_items(r, "FP", "Auxiliary Rooms")):
                ok = False
                reasons.append(f"missing FP aux system: {s}")
        for s in case.get("expect_fp_var_systems", []):
            if s not in _names(_items(r, "FP", "Various Locations")):
                ok = False
                reasons.append(f"missing FP various system: {s}")
        for s in case.get("expect_fp_eq_systems", []):
            if s not in _names(_items(r, "FP", "Equipment")):
                ok = False
                reasons.append(f"missing FP equipment system: {s}")
        if "expect_high_ceiling_band" in case:
            hc = r.high_ceiling
            if not hc or hc.height_range != case["expect_high_ceiling_band"]:
                ok = False
                reasons.append(f"high-ceiling band: expected {case['expect_high_ceiling_band']}, got {hc.height_range if hc else None}")

        # ----- ES checks -----
        es = r.es
        if "expect_es_branch" in case:
            if not es or es.selected_branch != case["expect_es_branch"]:
                ok = False
                reasons.append(f"ES branch: expected {case['expect_es_branch']}, got {es.selected_branch if es else None}")
        for s in case.get("expect_es_systems", []):
            if s not in _names(_items(r, "ES", "Occupancy-specific")):
                ok = False
                reasons.append(f"missing ES branch system: {s}")
        for s in case.get("expect_es_addons", []):
            if s not in _names(_items(r, "ES", "Special Zones")):
                ok = False
                reasons.append(f"missing ES add-on system: {s}")
        for s in case.get("expect_es_universal", []):
            if s not in _names(_items(r, "ES", "Universal")):
                ok = False
                reasons.append(f"missing ES universal system: {s}")
        for sname, want in case.get("expect_es_status", {}).items():
            es_items = _items(r, "ES")
            got = next((rq.status for rq in es_items if rq.system == sname), None)
            if got != want:
                ok = False
                reasons.append(f"ES status for '{sname}': expected {want}, got {got}")

        # ----- EL checks -----
        el = r.chapter("EL")
        if "expect_el_branch" in case:
            if not el or el.selected_branch != case["expect_el_branch"]:
                ok = False
                reasons.append(f"EL branch: expected {case['expect_el_branch']}, got {el.selected_branch if el else None}")
        for s in case.get("expect_el_systems", []):
            if s not in _names(_items(r, "EL", "System Type Selection")):
                ok = False
                reasons.append(f"missing EL system: {s}")
        for s in case.get("expect_el_general", []):
            if s not in _names(_items(r, "EL", "General Specs")):
                ok = False
                reasons.append(f"missing EL general entry: {s}")
        for sname, want in case.get("expect_el_status", {}).items():
            el_items = _items(r, "EL")
            got = next((rq.status for rq in el_items if rq.system == sname), None)
            if got != want:
                ok = False
                reasons.append(f"EL status for '{sname}': expected {want}, got {got}")

        # ----- FE checks -----
        fe = r.chapter("FE")
        if "expect_fe_branch" in case:
            if not fe or fe.selected_branch != case["expect_fe_branch"]:
                ok = False
                reasons.append(f"FE branch: expected {case['expect_fe_branch']}, got {fe.selected_branch if fe else None}")
        for s in case.get("expect_fe_general", []):
            if s not in _names(_items(r, "FE", "Universal Class A")):
                ok = False
                reasons.append(f"missing FE general entry: {s}")
        for s in case.get("expect_fe_branch_systems", []):
            if s not in _names(_items(r, "FE", "Occupancy-specific")):
                ok = False
                reasons.append(f"missing FE branch system: {s}")
        for s in case.get("expect_fe_addons", []):
            if s not in _names(_items(r, "FE", "Hazard-zone Add-ons")):
                ok = False
                reasons.append(f"missing FE addon: {s}")
        for sname, want in case.get("expect_fe_status", {}).items():
            fe_items = _items(r, "FE")
            got = next((rq.status for rq in fe_items if rq.system == sname), None)
            if got != want:
                ok = False
                reasons.append(f"FE status for '{sname}': expected {want}, got {got}")

        # ----- EVC checks -----
        evc = r.chapter("EVC")
        for s in case.get("expect_evc_general", []):
            if s not in _names(_items(r, "EVC", "General Specifications")):
                ok = False
                reasons.append(f"missing EVC general system: {s}")
        if case.get("expect_evc_general_absent"):
            if any("General Specifications" in blk.title for blk in (evc.blocks if evc else [])):
                ok = False
                reasons.append("EVC general block present but should be absent (lowrise residential)")
        if "expect_evc_branch" in case:
            if not evc or evc.selected_branch != case["expect_evc_branch"]:
                ok = False
                reasons.append(f"EVC branch: expected {case['expect_evc_branch']}, got {evc.selected_branch if evc else None}")
        for s in case.get("expect_evc_systems", []):
            if s not in _names(_items(r, "EVC")):
                ok = False
                reasons.append(f"missing EVC system: {s}")
        for sname, want in case.get("expect_evc_status", {}).items():
            evc_items = _items(r, "EVC")
            got = next((rq.status for rq in evc_items if rq.system == sname), None)
            if got != want:
                ok = False
                reasons.append(f"EVC status for '{sname}': expected {want}, got {got}")
        # ----- FA checks -----
        fa = r.chapter("FA")
        if "expect_fa_branch" in case:
            if not fa or fa.selected_branch != case["expect_fa_branch"]:
                ok = False
                reasons.append(f"FA branch: expected {case['expect_fa_branch']}, got {fa.selected_branch if fa else None}")
        for s in case.get("expect_fa_general", []):
            if s not in _names(_items(r, "FA", "General Requirements")):
                ok = False
                reasons.append(f"missing FA general system: {s}")
        for s in case.get("expect_fa_systems", []):
            if s not in _names(_items(r, "FA", "Detection & Alarm by Occupancy")):
                ok = False
                reasons.append(f"missing FA branch system: {s}")
        for s in case.get("expect_fa_aux", []):
            if s not in _names(_items(r, "FA", "Auxiliary Rooms")):
                ok = False
                reasons.append(f"missing FA aux system: {s}")
        for s in case.get("expect_fa_eq", []):
            if s not in _names(_items(r, "FA", "Equipment")):
                ok = False
                reasons.append(f"missing FA equipment system: {s}")

        # ----- SC checks -----
        sc = r.chapter("SC")
        if "expect_sc_branch" in case:
            if not sc or sc.selected_branch != case["expect_sc_branch"]:
                ok = False
                reasons.append(f"SC branch: expected {case['expect_sc_branch']}, got {sc.selected_branch if sc else None}")
        for s in case.get("expect_sc_systems", []):
            if s not in _names(_items(r, "SC", "Smoke Control by Tier")):
                ok = False
                reasons.append(f"missing SC system: {s}")
        for s in case.get("expect_sc_aux", []):
            if s not in _names(_items(r, "SC", "Auxiliary Zones")):
                ok = False
                reasons.append(f"missing SC aux system: {s}")
        for sname, want in case.get("expect_sc_status", {}).items():
            sc_items = _items(r, "SC")
            got = next((rq.status for rq in sc_items if rq.system == sname), None)
            if got != want:
                ok = False
                reasons.append(f"SC status for '{sname}': expected {want}, got {got}")

        # ----- LPG checks -----
        lpg = r.chapter("LPG")
        if "expect_lpg_branch" in case:
            if not lpg or lpg.selected_branch != case["expect_lpg_branch"]:
                ok = False
                reasons.append(f"LPG branch: expected {case['expect_lpg_branch']}, got {lpg.selected_branch if lpg else None}")
        for s in case.get("expect_lpg_systems", []):
            if s not in _names(_items(r, "LPG")):
                ok = False
                reasons.append(f"missing LPG system: {s}")
        for s in case.get("expect_lpg_general", []):
            if s not in _names(_items(r, "LPG", "General Universal")):
                ok = False
                reasons.append(f"missing LPG general system: {s}")
        for s in case.get("expect_lpg_addons", []):
            if s not in _names(_items(r, "LPG", "Variant Add-ons")):
                ok = False
                reasons.append(f"missing LPG addon system: {s}")
        if case.get("expect_lpg_general_absent"):
            if any("General Universal" in blk.title for blk in (lpg.blocks if lpg else [])):
                ok = False
                reasons.append("LPG general block present but should be absent (no gas system)")
        for sname, want in case.get("expect_lpg_status", {}).items():
            lpg_items = _items(r, "LPG")
            got = next((rq.status for rq in lpg_items if rq.system == sname), None)
            if got != want:
                ok = False
                reasons.append(f"LPG status for '{sname}': expected {want}, got {got}")

        # ----- Attached Parking checks -----
        if "expect_attached_parking_count" in case:
            n = len(r.attached_parking_chapters)
            if n != case["expect_attached_parking_count"]:
                ok = False
                reasons.append(f"attached parking chapter count: expected {case['expect_attached_parking_count']}, got {n}")
        if "expect_attached_parking_branch_for" in case:
            code, expected_branch = case["expect_attached_parking_branch_for"]
            ch = next((c for c in r.attached_parking_chapters if c.chapter_code == code), None)
            if not ch or ch.selected_branch != expected_branch:
                ok = False
                reasons.append(f"attached parking {code} branch: expected {expected_branch}, got {ch.selected_branch if ch else None}")

        # ----- MOE checks -----
        moe = r.chapter("MOE")
        if "expect_moe_branch" in case:
            if not moe or moe.selected_branch != case["expect_moe_branch"]:
                ok = False
                reasons.append(f"MOE branch: expected {case['expect_moe_branch']}, got {moe.selected_branch if moe else None}")

        tag = "PASS" if ok else "FAIL"
        print(f"[{tag}] {case['name']}")
        if not ok:
            for reason in reasons:
                print(f"   - {reason}")
        passed += int(ok)
        failed += int(not ok)

    print()
    print(f"{passed} passed, {failed} failed")
    return failed


if __name__ == "__main__":
    import sys
    sys.exit(1 if run_all() else 0)
