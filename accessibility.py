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
            code_ref="Ch 15, §2.2 Scope",
            page_ref="p.1088+",
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
                status="conditional",
                spec="Accessible bays + access aisles per Table 15.2 when parking is provided",
                code_ref="Ch 15, Table 15.2",
                page_ref="p.1095+",
                source_rule="acc_parking",
            ),
            Requirement(
                system="Accessible stair features",
                status="required",
                spec="Nosings, handrails, contrast, and tactile warning per Table 15.3",
                code_ref="Ch 15, Table 15.3",
                page_ref="p.1096+",
                source_rule="acc_stair",
            ),
            Requirement(
                system="Accessible AV alarms and directional signs",
                status="required",
                spec="Visual/audible alarms and directional signage to accessible elements per Table 15.4",
                code_ref="Ch 15, Table 15.4",
                page_ref="p.1098+",
                source_rule="acc_av_signs",
            ),
        ])
        if b.height_class in ("highrise", "super_highrise") or getattr(b, "has_evacuation_elevator", False):
            items.append(Requirement(
                system="Area of refuge / evacuation elevator access",
                status="required",
                spec="Areas of refuge and accessible route to evacuation elevators where provided (ties to Ch 3 §3.9 / Ch 5)",
                detail="Confirm refuge sizing (0.28 m²/person, min spaces per 200 occupants) against Ch 3.",
                code_ref="Ch 15 §3.5 · Ch 3 area of refuge",
                page_ref="p.1100+",
                source_rule="acc_refuge",
            ))

    return ChapterReport(
        chapter_code="ACC",
        chapter_title="Accessibility (Ch 15)",
        selected_branch="acc_general",
        selected_branch_section="Ch 15 Tables 15.1–15.4",
        blocks=[SectionBlock(title="ACC - Accessible routes & facilities (Ch 15)", items=items)],
    )
