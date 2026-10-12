"""UAE FLSC 2018 Chapter 15 — Accessibility (light module).

Surfaces the main accessible-route, parking, stair, and refuge requirements
that always apply to non-villa buildings. Not a full Table 15.1–15.5 encoder.
"""
from __future__ import annotations
from typing import List
from flsc_schema import Building, ChapterReport, Requirement, SectionBlock

def evaluate_accessibility(b: Building) -> ChapterReport:
    items: List[Requirement] = []
    is_villa = b.occupancy.startswith("villa_")

    if is_villa:
        items.append(Requirement(
            system="Accessibility (Ch 15) — villa",
            status="conditional",
            spec="Private villas: accessible features apply where the project opts into public/visitor access or is commercial villa with common facilities",
            detail="Confirm with Civil Defence / Municipality for commercial villa clusters with shared amenities.",
            code_ref="Ch 15, #2.2 Scope",
            page_ref="p.1090",
            source_rule="acc_villa",
        ))
    else:
        items.extend([
            Requirement(
                system="Accessible route clear width",
                status="required",
                spec="Min 915 mm clear width; 180° turns and passing spaces per Table 15.1",
                detail="Passing spaces (1525×1525 mm or T-turn) at ≤ 61 m intervals where route < 1525 mm wide.",
                code_ref="Ch 15, Table 15.1",
                page_ref="p.1093",
                source_rule="acc_route_width",
            ),
            Requirement(
                system="Accessible doors",
                status="required",
                spec="Min 915 mm clear opening; maneuvering clearances Table 15.1.a / 15.1.b",
                code_ref="Ch 15, Table 15.1 · Ch 3 door rules",
                page_ref="p.1093",
                source_rule="acc_doors",
            ),
            Requirement(
                system="Accessible parking",
                status="required" if b.has_parking_area else "conditional",
                spec="Car spaces at least 2440 mm wide, van spaces 3350 mm (or 2440 mm beside a 2440 mm aisle); access aisles at least 1525 mm, adjoining an accessible route, full length of the spaces (Table 15.2)",
                detail="Spaces closest to the destination; 2490 mm vertical clearance for van spaces, their aisles and vehicular routes; Arabic and English signs at least 1525 mm above the floor of the space, measured to the bottom of the sign.",
                code_ref="Ch 15, #3.2 / Table 15.2",
                page_ref="p.1097",
                source_rule="acc_parking",
            ),
            Requirement(
                system="Accessible stair features",
                status="required" if b.has_stairs else "not_required",
                spec="Uniform risers 100-180 mm, treads at least 280 mm, no open risers; leading 51 mm of the tread in visual contrast; 108 lux (10 foot-candles) lighting; raised-character and braille stair level signs at each floor landing (Table 15.3 #1)",
                detail="Nosing radius of curvature at most 13 mm (#1.vii). Handrails on both sides of stairs and ramps, continuous, top of gripping surface 865-965 mm above nosing, 38 mm clearance to adjacent surfaces, ramp handrails extending 305 mm beyond the top and bottom (#2).",
                code_ref="Ch 15, #3.3 / Table 15.3",
                page_ref="p.1098",
                source_rule="acc_stair",
            ),
            Requirement(
                system="Accessible AV alarms and directional signs",
                status="required",
                spec="Visual/audible alarms and directional signage to accessible elements per Table 15.4",
                code_ref="Ch 15, Table 15.4",
                page_ref="p.1099-1100",
                source_rule="acc_av_signs",
            ),
            Requirement(
                system="Foldable wheelchairs (minimum 2)",
                status="required",
                spec="Foldable wheelchairs provided in every facility, stored in an easily accessible location; minimum of 2 in all occupancies (#5.2.8)",
                detail="More spare wheelchairs in accordance with the number of mobility impaired people in the building. Facility management trained in usage, maintenance and storing of the wheelchairs.",
                code_ref="Ch 15, #5.2.8",
                page_ref="p.1119",
                source_rule="acc_wheelchairs",
            ),
        ])
        if b.height_class in ("highrise", "super_highrise") or b.has_evacuation_elevator:
            items.append(Requirement(
                system="Area of refuge / evacuation elevator access",
                status="conditional",
                spec="Area of refuge is not mandated by Civil Defence; where the overall fire strategy provides one (super highrise above 90 m or large complex buildings), it complies with Ch 3 #3.8 and Table 3.10 (#3.8.1)",
                detail="Table 3.10: 1-hr fire barrier; 45 minute doors; protected stair access, stair width for the occupant load served and never less than 1200 mm; area on a clear fire strategy or the occupants of 3 floors; one 760 mm x 1220 mm wheelchair space for every 200 occupants or portion thereof; Arabic and English \"AREA OF REFUGE\" sign.",
                code_ref="Ch 3, #3.8.1 / Table 3.10",
                page_ref="p.279",
                source_rule="acc_refuge",
            ))

    return ChapterReport(
        chapter_code="ACC",
        chapter_title="Accessibility (Ch 15)",
        selected_branch="acc_general",
        selected_branch_section="Ch 15 Tables 15.1–15.4",
        blocks=[SectionBlock(title="ACC - Accessible routes & facilities (Ch 15)", items=items)],
    )
