"""UAE FLSC 2018 Chapter 19 — Emergency Action Plans (light module).

Every non-villa building gets the Table 19.1 item 8 assembly point and the
Table 19.2 drills (audit CH10-12, 12.10.2026). The full written EAP document
stays tiered: required for midrise+ and high-risk occupancies, recommended
otherwise (owner question open). Pages: Table 19.1 items 1-4 p.1234-1237,
item 8 p.1243; Table 19.2 p.1245-1248 (drills read on p.1246).
"""
from __future__ import annotations
from typing import List
from flsc_schema import Building, ChapterReport, Requirement, SectionBlock


def _drill_spec(b: Building) -> str:
    occ = b.occupancy
    if occ.startswith("assembly_"):
        return ("Assembly occupancy management team conducts and practices a fire drill twice "
                "every 6 months (Table 19.2 #3.2.ii); the general public need not be involved (#3.2.iii)")
    if occ.startswith("education_"):
        return ("Educational occupancy management team conducts and practices a fire drill once "
                "every 6 months (Table 19.2 #3.3.ii), involving the entire school occupants with a "
                "total evacuation alarm (#3.3.iii)")
    return ("Facility management team conducts and practices fire drills per the building emergency "
            "action plan every 6 months (Table 19.2 #3.1.ii); this drill is for the facility "
            "management team only, not the occupants (#3.1.iii)")


def _assembly_and_drills(b: Building) -> List[Requirement]:
    return [
        Requirement(
            system="Assembly point",
            status="required",
            spec=("Each building shall have an assembly point, predetermined and designated with a sign, "
                   "at least 15 m from the building or, alternatively, at a distance not less than the "
                   "height of the building (Table 19.1 item 8)"),
            detail=("Easily accessible; safe from fire heat radiation and falling debris; away from the "
                    "fire access road and fire truck parking areas (8.2). Large enough for the building "
                    "occupants; multiple points permitted where space is a constraint; a public large open "
                    "space within 100 m may be a common assembly point for a group of buildings (8.3). "
                    "Large and distributed occupancies (malls, theme parks, hospitals, schools) have "
                    "multiple assembly points; consider sheltered points (8.1). Green Arabic and English "
                    "sign per Figure 19.1 (8.4)."),
            code_ref="Ch 19, Table 19.1 item 8",
            page_ref="p.1243",
            source_rule="eap_assembly",
        ),
        Requirement(
            system="Drills and training",
            status="required",
            spec=_drill_spec(b),
            detail=("All building occupants shall participate in an emergency evacuation drill, with "
                    "emphasis on orderly evacuation rather than speed (Table 19.2 #2.3). Owner / facility "
                    "management notify Civil Defence of a planned drill 48 hours before and again 1 hour "
                    "before, and notify the neighbouring building facility management (#2.4). Drill "
                    "frequencies for other occupancy groups are on Table 19.2 p.1247-1248."),
            code_ref="Ch 19, Table 19.2",
            page_ref="p.1245-1248",
            source_rule="eap_drills",
        ),
    ]


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
            code_ref="Ch 19, #2",
            page_ref="p.1233",
            source_rule="eap_villa_na",
        ))
    elif not needs:
        items.append(Requirement(
            system="Emergency Action Plan",
            status="recommended",
            spec="Prepare a basic EAP aligned with Table 19.1 even where not strictly mandated",
            code_ref="Ch 19, Table 19.1",
            page_ref="p.1234-1237",
            source_rule="eap_recommended",
        ))
        items.extend(_assembly_and_drills(b))
    else:
        partial = b.height_class in ("highrise", "super_highrise") or b.occupancy == "healthcare_a"
        items.extend([
            Requirement(
                system="Written Emergency Action Plan (Table 19.1)",
                status="required",
                spec="Documented EAP covering roles, alarm response, Civil Defence call-out, assembly points",
                detail="Include approved floor plans with electrical switchboard, FF equipment, and BMS/control locations.",
                code_ref="Ch 19, Table 19.1 items 1-4",
                page_ref="p.1234-1237",
                source_rule="eap_table_19_1",
            ),
            Requirement(
                system="Evacuation strategy",
                status="required",
                spec=(
                    "Partial evacuation for highrise, super-highrise and hospital buildings "
                    "(Table 19.1 item 3.3); total evacuation for low/midrise as practical"
                    if partial
                    else "Evacuation strategy per occupancy and height; coordinate with FA/EVC zoning"
                ),
                code_ref="Ch 19, Table 19.1 item 3.3",
                page_ref="p.1236-1237",
                source_rule="eap_strategy",
            ),
            Requirement(
                system="Emergency response team & fire wardens",
                status="required",
                spec="Response Team of minimum 4 personnel, named with contacts and duties (Table 19.1 item 4)",
                code_ref="Ch 19, Table 19.1 item 4",
                page_ref="p.1237",
                source_rule="eap_team",
            ),
        ])
        items.extend(_assembly_and_drills(b))
    return ChapterReport(
        chapter_code="EAP",
        chapter_title="Emergency Action Plans (Ch 19)",
        selected_branch="eap_auto",
        selected_branch_section="Ch 19 Tables 19.1 and 19.2",
        blocks=[SectionBlock(title="EAP - Emergency action plan (Ch 19)", items=items)],
    )
