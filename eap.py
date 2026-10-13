"""UAE FLSC 2018 Chapter 19 — Emergency Action Plans (light module).

Every non-villa building gets the Table 19.1 item 8 assembly point and the
Table 19.2 drills (audit CH10-12, 12.10.2026), and the written EAP document
(Table 19.2 #3.1.i, p.1246; owner ruling 12.10.2026, P3 Ch11 Q1). The
evacuation strategy and response team lines stay with midrise+ and high-risk
occupancies. Villas: written EAP, assembly point and drills conditional until
the Ch 19 scope page p.1233 is read (owner ruling 12.10.2026, P3 Ch11 Q2 and
follow-up F-a1-2). Pages:
Table 19.1 items 1-4 p.1234-1237, item 8 p.1243; Table 19.2 p.1245-1248
(drills read on p.1246).
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


_VILLA_SCOPE_NOTE = (
    "Villa: conditional. Table 19.1 item 8.1.i (p.1243) reads 'Each building shall have an "
    "assembly point' and Table 19.2 #3.1.ii (p.1246) the facility management team of 'every "
    "building'; the Ch 19 scope page (p.1233) is not yet read, so whether private / "
    "commercial villas fall in scope is not confirmed (owner ruling 12.10.2026, P3 Ch11 Q2). ")


_VILLA_EAP_NOTE = (
    "Villa: conditional. Table 19.2 #3.1.i (p.1246) reads 'Facility management shall have "
    "emergency action plan in accordance with Chapter 19' and #3.1.ii names the facility "
    "management team of 'every building'; the Ch 19 scope page (p.1233) is not yet read, so "
    "whether private / commercial villas fall in scope is not confirmed (owner ruling "
    "12.10.2026, P3 follow-up F-a1-2, as P3 Ch11 Q2 for the assembly point and drills). ")


def _written_eap(b: Building) -> Requirement:
    # Owner ruling 12.10.2026, P3 Ch11 Q1: required for every non-villa building.
    return Requirement(
        system="Written Emergency Action Plan (Table 19.1)",
        status="required",
        spec="Documented EAP covering roles, alarm response, Civil Defence call-out, assembly points",
        detail=("Facility management shall have an emergency action plan in accordance with "
                "Chapter 19 (Table 19.2 #3.1.i, p.1246), and the facility management team of "
                "every building drills as per the building emergency action plan (#3.1.ii); "
                "required for every non-villa building (owner ruling 12.10.2026, P3 Ch11 Q1). "
                "Include approved floor plans with electrical switchboard, FF equipment, and "
                "BMS/control locations."),
        code_ref="Ch 19, Table 19.1 items 1-4",
        page_ref="p.1234-1237",
        source_rule="eap_table_19_1",
    )


def _assembly_and_drills(b: Building) -> List[Requirement]:
    reqs = [
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
    if b.occupancy.startswith("villa_"):
        reqs = [r.model_copy(update={"status": "conditional",
                                     "detail": _VILLA_SCOPE_NOTE + (r.detail or "")})
                for r in reqs]
    return reqs


def evaluate_eap(b: Building) -> ChapterReport:
    items: List[Requirement] = []
    needs = (
        b.height_class in ("midrise", "highrise", "super_highrise")
        or b.occupancy.startswith(("assembly_", "healthcare_", "hotel_", "education_", "mall_"))
        or b.occupancy in ("labour_accommodation", "detention_a", "detention_b", "detention_c")
    )
    if not needs and b.occupancy.startswith("villa_"):
        # Owner ruling 12.10.2026, P3 follow-up F-a1-2: the written EAP is conditional for
        # villas, like the assembly point and drills, until p.1233 is read.
        items.append(_written_eap(b).model_copy(update={
            "status": "conditional",
            "detail": (_VILLA_EAP_NOTE + "Include approved floor plans with electrical "
                       "switchboard, FF equipment, and BMS/control locations."),
            "source_rule": "eap_villa_written",
        }))
        items.extend(_assembly_and_drills(b))
    elif not needs:
        items.append(_written_eap(b))
        items.extend(_assembly_and_drills(b))
    else:
        partial = b.height_class in ("highrise", "super_highrise") or b.occupancy == "healthcare_a"
        items.extend([
            _written_eap(b),
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
