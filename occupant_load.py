"""UAE FLSC 2018 Table 3.13 occupant-load factors and Table 3.14 exit counts.

Uses gross floor area by default (code allows net for some assembly/education
uses). Factor is the area per person; OL = floor(area / factor), minimum 1
when area > 0.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

from flsc_schema import Building, OccupantLoadSummary

# Primary Table 3.13 factor (m2 per person) by schema occupancy.
# Prefer the most representative / conservative row for each occupancy class.
_OL_FACTOR_M2: dict[str, Tuple[float, str]] = {
    "assembly_a": (0.65, "Table 3.13 item 1.i concentrated (ballroom / dance)"),
    "assembly_b": (0.65, "Table 3.13 item 1.i concentrated"),
    "assembly_c": (1.4, "Table 3.13 item 1.ii less concentrated (restaurant / meeting)"),
    "business": (9.3, "Table 3.13 item 2.i regular office"),
    "education_a": (1.9, "Table 3.13 item 3.i classroom (net)"),
    "education_b": (1.9, "Table 3.13 item 3.i classroom (net)"),
    "education_c": (1.9, "Table 3.13 item 3.i classroom (net)"),
    "mercantile_a": (2.8, "Table 3.13 item 13.ii sales on street floor"),
    "mercantile_b": (2.8, "Table 3.13 item 13.ii sales on street floor"),
    "healthcare_a": (22.3, "Table 3.13 item 4.i inpatient treatment"),
    "healthcare_b": (9.3, "Table 3.13 item 4.iv clinics"),
    "healthcare_c": (13.0, "Table 3.13 item 5.i ambulatory healthcare"),
    "hotel_a": (18.6, "Table 3.13 item 11 hotel guest rooms / apartments"),
    "hotel_b": (18.6, "Table 3.13 item 11 hotel guest rooms"),
    "hotel_c": (18.6, "Table 3.13 item 11 hotel guest rooms"),
    "daycare_a": (3.3, "Table 3.13 item 12 day care (net)"),
    "daycare_b": (3.3, "Table 3.13 item 12 day care (net)"),
    "daycare_c": (3.3, "Table 3.13 item 12 day care (net)"),
    "residential": (18.6, "Table 3.13 item 6.i apartments"),
    "labour_accommodation": (18.6, "Table 3.13 item 7 staff / hostel-style"),
    "staff_accommodation": (18.6, "Table 3.13 item 7 staff accommodation"),
    "hostel": (18.6, "Table 3.13 item 7 hostels"),
    "animal_housing": (11.1, "Table 3.13 item 21 animal housing"),
    "detention_a": (11.1, "Table 3.13 item 10 detention"),
    "detention_b": (11.1, "Table 3.13 item 10 detention"),
    "detention_c": (11.1, "Table 3.13 item 10 detention"),
    "villa_private": (0.0, "Table 3.13 item 8 private villa — OL factor not tabulated"),
    "villa_commercial": (0.0, "Table 3.13 item 9 commercial villa — OL factor not tabulated"),
    "mall_covered": (2.8, "Table 3.13 item 14.i mall GLA < 14,000 m2"),
    "mall_open": (2.8, "Table 3.13 item 14.i mall GLA < 14,000 m2"),
    "mall_mixed": (2.8, "Table 3.13 item 14.i mall GLA < 14,000 m2"),
    "parking_enclosed": (27.9, "Table 3.13 item 19.i enclosed parking"),
    "parking_open": (27.9, "Table 3.13 item 19.ii open parking"),
    "storage_industrial": (27.9, "Table 3.13 item 16 low/ordinary hazard storage"),
    "motor_fuel_dispensing": (9.3, "Table 3.13 business / mercantile proxy for station building"),
    "infrastructure": (9.3, "Table 3.13 business proxy"),
    "mixed_multiple": (2.8, "Most restrictive mixed-use default (mercantile / assembly tier)"),
    "high_depth_underground": (9.3, "Table 3.13 business / parking hybrid proxy"),
    "low_depth_underground": (9.3, "Table 3.13 business / parking hybrid proxy"),
}


def _area_for_ol(b: Building) -> float:
    """Prefer GFA; fall back to GF BUA when GFA is zero."""
    if b.gross_floor_area_m2 and b.gross_floor_area_m2 > 0:
        return float(b.gross_floor_area_m2)
    if b.ground_floor_bua_m2 and b.ground_floor_bua_m2 > 0:
        return float(b.ground_floor_bua_m2)
    return 0.0


def min_exits_for_ol(occupant_load: int, outdoor: bool = False) -> Tuple[int, str]:
    """Table 3.14 required number of means of egress."""
    if outdoor:
        if occupant_load > 9000:
            return 4, "Table 3.14 item vii outdoor OL > 9,000 → ≥ 4 exits"
        if occupant_load > 6000:
            return 3, "Table 3.14 item vi outdoor OL > 6,000 → ≥ 3 exits"
    if occupant_load > 1000:
        return 4, "Table 3.14 item iv OL > 1,000 → ≥ 4 exits"
    if occupant_load >= 500:
        return 3, "Table 3.14 item iii OL 500–1,000 → ≥ 3 exits"
    return 2, "Table 3.14 items i–ii minimum 2 means of egress per storey"


def compute_occupant_load(b: Building) -> OccupantLoadSummary:
    factor, factor_ref = _OL_FACTOR_M2.get(
        b.occupancy, (9.3, "Table 3.13 default (business-tier proxy)")
    )
    area = _area_for_ol(b)
    if factor <= 0 or area <= 0:
        ol = 0
        note = (
            "Occupant load not auto-calculated for this occupancy/area "
            "(villa or missing GFA). Enter design OL manually if needed."
        )
    else:
        ol = max(1, int(math.floor(area / factor)))
        note = (
            f"OL = floor({area:g} m² / {factor:g} m²/person) = {ol}. "
            "Uses gross area; switch to net factors on drawings where Table 3.13 requires net."
        )
    exits, exit_ref = min_exits_for_ol(ol)
    return OccupantLoadSummary(
        area_m2=area,
        factor_m2_per_person=factor,
        factor_ref=factor_ref,
        occupant_load=ol,
        min_exits=exits,
        exit_ref=exit_ref,
        note=note,
    )
