"""UAE FLSC 2018 Chapter 19 — Emergency Action Plans (light module).

Triggers EAP documentation requirements for midrise+ and high-risk occupancies.
"""
from __future__ import annotations
from typing import List
from flsc_schema import Building, ChapterReport, Requirement, SectionBlock

def evaluate_eap(b: Building) -> ChapterReport:
    items: List[Requirement] = []
    needs = (
        b.height_class in ("midrise", "highrise", "super_highrise")
        or b.occupancy.startswith(("assembly_", "healthcare_", "hotel_", "education_", "mall_"))
        or b.occupancy in ("labour_accommodation", "detention_a", "detention_b", "detention_c")
    )
    if not needs and b.occupancy.startswith("villa_"):
        items.append(Requirement(
            system="Emergency Action Plan",
            status="not_required",
            spec="Private villa: formal EAP documentation not typically mandated at this scale",
            code_ref="Ch 19, §2",
            page_ref="p.1230+",
            source_rule="eap_villa_na",
        ))
    elif not needs:
        items.append(Requirement(
            system="Emergency Action Plan",
            status="recommended",
            spec="Prepare a basic EAP aligned with Table 19.1 even where not strictly mandated",
            code_ref="Ch 19, Table 19.1",
            page_ref="p.1233+",
            source_rule="eap_recommended",
        ))
    else:
        items.extend([
            Requirement(
                system="Written Emergency Action Plan (Table 19.1)",
                status="required",
                spec="Documented EAP covering roles, alarm response, Civil Defence call-out, assembly points",
                detail="Include approved floor plans with electrical switchboard, FF equipment, and BMS/control locations.",
                code_ref="Ch 19, Table 19.1 items 1–4",
                page_ref="p.1233–1235",
                source_rule="eap_table_19_1",
            ),
            Requirement(
                system="Evacuation strategy",
                status="required",
                spec=(
                    "Partial / phased evacuation for highrise and super-highrise; "
                    "total evacuation for low/midrise as practical"
                    if b.height_class in ("highrise", "super_highrise")
                    else "Evacuation strategy per occupancy and height; coordinate with FA/EVC zoning"
                ),
                code_ref="Ch 19, Table 19.1.3",
                page_ref="p.1236+",
                source_rule="eap_strategy",
            ),
            Requirement(
                system="Emergency response team & fire wardens",
                status="required",
                spec="Named personnel with contacts and duties per Table 19.1.5 / 19.1.6",
                code_ref="Ch 19, Table 19.1.5–19.1.6",
                page_ref="p.1237+",
                source_rule="eap_team",
            ),
            Requirement(
                system="Assembly point",
                status="required",
                spec="Designated assembly point conforming to Table 19.1.7; shown on site plan",
                code_ref="Ch 19, Table 19.1.7",
                page_ref="p.1238+",
                source_rule="eap_assembly",
            ),
            Requirement(
                system="Drills and training",
                status="required",
                spec="Periodic drills so occupants and staff are familiar with the EAP",
                code_ref="Ch 19, §2.1",
                page_ref="p.1231+",
                source_rule="eap_drills",
            ),
        ])
    return ChapterReport(
        chapter_code="EAP",
        chapter_title="Emergency Action Plans (Ch 19)",
        selected_branch="eap_auto",
        selected_branch_section="Ch 19 Table 19.1",
        blocks=[SectionBlock(title="EAP - Emergency action plan (Ch 19)", items=items)],
    )
