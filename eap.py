"""UAE FLSC 2018 Chapter 19 — Emergency Action Plans (light module).

Every non-villa building gets the written EAP (Table 19.2 #3.1.i, p.1246; owner ruling
12.10.2026, P3 Ch11 Q1), the evacuation strategy (Table 19.1 item 3, p.1236-1237), the
Table 19.1 item 4.2.i command roles (p.1237), the item 9 vests (p.1244), the item 8
assembly point (p.1243) and the Table 19.2 drills, occupancy by occupancy (p.1245-1248)
(audit 28.10.2026, EAP-01 to EAP-05). Villas (lowrise): every line conditional; the scope
page p.1233 (#2.1.1) prints neither a villa exclusion nor a villa inclusion, so the owner
rulings P3 Ch11 Q2 and F-a1-2 (conditional) stand until the owner closes them (EAP-04).
"""
from __future__ import annotations
from typing import List, Optional, Tuple
from flsc_schema import Building, ChapterReport, Requirement, SectionBlock

_HIGHRISE = ("highrise", "super_highrise")
_RESIDENTIAL = ("residential", "labour_accommodation", "staff_accommodation", "hostel")

# Table 19.2 #3.1 (p.1246): the facility management team drill of every building.
_FM_DRILL = ("Facility management team of every building conducts and practices fire drills as "
             "per the building emergency action plan every 6 months (Table 19.2 #3.1.ii); such a "
             "fire drill shall be only for facility management team and shall not be for the "
             "occupants (#3.1.iii)")


def _occupancy_drill(b: Building) -> Optional[Tuple[str, str]]:
    """The Table 19.2 #3.2-#3.9 row of this occupancy (p.1246-1248), as (row, text)."""
    occ, tall = b.occupancy, b.height_class in _HIGHRISE
    if occ.startswith("assembly_"):
        return ("#3.2", "Assembly occupancy management team shall conduct and practice fire drill "
                "twice every 6 months (Table 19.2 #3.2.ii); drills shall not be required to involve "
                "general public of the assembly occupancy (#3.2.iii)")
    if occ.startswith("education_"):
        return ("#3.3", "Educational occupancy management team shall conduct and practice fire drill "
                "once every 6 months (Table 19.2 #3.3.ii); drills shall involve entire school "
                "occupants, with total evacuation alarm (#3.3.iii)")
    if occ == "business" and tall:
        return ("#3.4", "Highrise business occupancy management team shall conduct and practice fire "
                "drill once every 6 months (Table 19.2 #3.4.ii); Drills shall involve entire "
                "occupants, with total evacuation alarm (#3.4.iii)")
    if occ.startswith("hotel_") and tall:
        return ("#3.5", "Highrise hotel occupancy management team shall conduct and practice fire "
                "drill every 6 months (Table 19.2 #3.5.ii); Drills shall not be required to involve "
                "Hotel guests and visitors (#3.5.iii)")
    if occ in _RESIDENTIAL and tall:
        return ("#3.6", "Highrise residential occupancy management team shall conduct and practice "
                "fire drill once every 6 months (Table 19.2 #3.6.ii); Drills shall involve entire "
                "occupants, with total evacuation alarm (#3.6.iii); drills shall be scheduled on a "
                "non-working day so that most of the residents can take part (#3.6.iv)")
    if occ.startswith("healthcare_"):
        return ("#3.7", "Healthcare occupancy management team shall conduct and practice fire drill "
                "once every 6 months (Table 19.2 #3.7.ii); Drills shall not be required to involve "
                "occupants, patients or visitors (#3.7.iii); scheduled at non-visiting hours (#3.7.iv)")
    if occ.startswith("detention_"):
        return ("#3.8", "Detention and correctional occupancy management team shall conduct and "
                "practice fire drill once every 6 months (Table 19.2 #3.8.ii); drills shall not be "
                "required to involve occupants, patients or visitors (#3.8.iii); scheduled at "
                "non-visiting hours (#3.8.iv)")
    if occ.startswith("mall_"):
        return ("#3.9", "Mall management team shall conduct and practice fire drill once every 6 "
                "months (Table 19.2 #3.9.ii); Drills shall not be required to involve public "
                "(#3.9.iii); scheduled at non-visiting hours with volunteers as public (#3.9.iv)")
    return None


def _drill_spec(b: Building) -> str:
    row = _occupancy_drill(b)
    if row is None:
        return _FM_DRILL
    return f"{row[1]}. Also: {_FM_DRILL}"


_VILLA_SCOPE_NOTE = (
    "Villa: conditional. Ch 19 #2.1.1 (p.1233, now read) sets 'minimum guidelines on preparation "
    "of emergency action plans and procedures to ensure the safe and efficient evacuation of all "
    "occupants'; it prints no villa exclusion and no villa inclusion. Table 19.1 item 8.1.i "
    "(p.1243) reads 'Each building shall have an assembly point' and Table 19.2 #3.1.ii (p.1246) "
    "the facility management team of 'every building'. Whether private / commercial villas fall "
    "in scope stays an owner call; conditional per owner ruling 12.10.2026, P3 Ch11 Q2 (audit "
    "EAP-04: needs ruling). ")


_VILLA_EAP_NOTE = (
    "Villa: conditional. Table 19.2 #3.1.i (p.1246) reads 'Facility management shall have "
    "emergency action plan in accordance with Chapter 19' and #3.1.ii names the facility "
    "management team of 'every building'; Ch 19 #2.1.1 (p.1233, now read) prints no villa "
    "exclusion and no villa inclusion, so whether private / commercial villas fall in scope "
    "stays an owner call (owner ruling 12.10.2026, P3 follow-up F-a1-2, as P3 Ch11 Q2 for the "
    "assembly point and drills; audit EAP-04: needs ruling). ")


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
                "Content (Table 19.1 item 2.1, p.1234): emergency plans and procedures shall be "
                "primarily in Arabic and English, and translated into the language the building "
                "occupant understands (iii); personnel designated and appointed with their names, "
                "contact details and specific responsibilities (iv); a clear building evacuation "
                "plan, prepared in accordance with Chapter 5. Table 5.1.8. (v); the latest Civil "
                "Defence and Municipality approved floor plans with locations of the main "
                "electrical switch board, fire fighting equipment and building services control "
                "system (vi); fire scenarios and evacuation strategies per Table 19.1.3 (vii); "
                "other emergencies such as earthquakes, floods, power outages (viii) (audit EAP-05)."),
        code_ref="Ch 19, Table 19.1 items 1-4",
        page_ref="p.1234-1237",
        source_rule="eap_table_19_1",
    )


def _strategy(b: Building) -> Requirement:
    partial = b.height_class in _HIGHRISE or b.occupancy == "healthcare_a"
    if partial:
        spec = ("Partial evacuation would be a suitable strategy for highrise, super highrise "
                "buildings and hospitals, where total evacuation upon contained fire incidents "
                "may be impractical and unnecessary (Table 19.1 item 3.3.i); the EAP shall address "
                "the fire scenarios and evacuation strategies per Table 19.1 item 3 (item 2.1.vii)")
    else:
        spec = ("The EAP shall address the fire scenarios and evacuation strategies as per Table "
                "19.1 item 3 (item 2.1.vii): no evacuation (remain in place), partial evacuation, "
                "total evacuation, or move occupants to a refuge area, specific to the building "
                "(item 5.ii)")
    return Requirement(
        system="Evacuation strategy",
        status="required",
        spec=spec,
        detail=("Any 'No Evacuation (Remain in place)' strategies shall be evaluated and certified "
                "by Civil Defence (Table 19.1 item 3.2.i); remain in place may not be suitable for "
                "a factory, warehouse or commercial unit fire (3.2.ii.b). Total evacuation where "
                "the emergency management team assesses the situation as out of control or where "
                "full evacuation is the best option (3.4.i). Any 'Move occupants to Refuge Area' "
                "strategies shall be evaluated and certified by Civil Defence (3.5.i). Coordinate "
                "with the FA / EVC zoning (audit EAP-03: the code prints no 'total evacuation for "
                "low / midrise' rule)."),
        code_ref="Ch 19, Table 19.1 item 3",
        page_ref="p.1236-1237",
        source_rule="eap_strategy",
    )


def _team_and_vests(b: Building) -> List[Requirement]:
    return [
        Requirement(
            system="Emergency response team & fire wardens",
            status="required",
            spec=("Facility management (or management under lease) appoints trained and able "
                  "personnel (Table 19.1 item 4.2.i): a. Incident Fire Commander; b. Assistant "
                  "Incident Fire Commander; c. Fire Warden; d. Assistant Fire Warden; e. Response "
                  "Team of minimum 4 personnel (Fire Responder, First Aider, Assembly Point "
                  "Coordinator, Drill observer)"),
            detail=("The emergency action plan is initiated and prepared by the owner, who appoints "
                    "the emergency management team through facility management (item 4.1.i-ii); "
                    "the team delivers its duties per Table 19.1.5 (item 4.2.ii); volunteers from "
                    "the building are permitted and encouraged (item 4.2.iii). Table 19.1 item 4.2.i "
                    "carries no height or occupancy limit: every building (audit EAP-02)."),
            code_ref="Ch 19, Table 19.1 item 4.2.i",
            page_ref="p.1237",
            source_rule="eap_team",
        ),
        Requirement(
            system="Response team vests (fluorescent, with designation)",
            status="required",
            spec=("Each member of the emergency response team shall wear a fluorescent jacket/vest "
                  "with the designation inscribed in capital letters, as INCIDENT COMMANDER, FIRE "
                  "WARDEN, FIRE RESPONDER, FIRST AIDER, ASSEMBLY POINT COORDINATOR, OBSERVER etc. "
                  "(Table 19.1 item 9.i-ii)"),
            detail=("Vests kept within reach and put on as soon as an emergency situation arises and "
                    "when emergency drills are practiced (item 9.iii); Figure 19.2 (audit EAP-05)."),
            code_ref="Ch 19, Table 19.1 item 9",
            page_ref="p.1244",
            source_rule="eap_vests",
        ),
    ]


def _assembly_and_drills(b: Building) -> List[Requirement]:
    row = _occupancy_drill(b)
    no_row = ("" if row else
              " Table 19.2 #3.2-#3.9 print no occupant drill frequency for this occupancy and "
              "height (the #3.4-#3.6 business, hotel and residential rows are for highrise and "
              "super highrise buildings), so only the #3.1 facility management team drill has a "
              "printed frequency (audit EAP-01).")
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
                    "emphasis on orderly evacuation under proper discipline rather than speed (Table "
                    "19.2 #2.3.i-ii)." + no_row + " Drills scheduled and notified to building occupants "
                    "by the Evacuation Coordinator(s) and Fire Wardens, at least one week prior to the "
                    "drill (#2.1.iii); occupant training per #2.2. Owner / facility management notify "
                    "Civil Defence of a planned drill 48 hours before and again 1 hour before, and "
                    "notify the neighbouring building facility management (#2.4)."),
            code_ref="Ch 19, Table 19.2",
            page_ref="p.1245-1248",
            source_rule="eap_drills",
        ),
    ]


def evaluate_eap(b: Building) -> ChapterReport:
    items: List[Requirement] = [_written_eap(b), _strategy(b), *_team_and_vests(b),
                                *_assembly_and_drills(b)]
    # Villas (routing unchanged from rulings P3 Ch11 Q2 / F-a1-2): the assembly point and
    # drills are conditional for every villa; the written EAP, and the strategy, team and vest
    # lines that every building now gets (EAP-02, EAP-05), are conditional for a lowrise villa.
    # A villa taller than 15 m kept the written EAP, strategy and team as required before.
    if b.occupancy.startswith("villa_"):
        low = b.height_class == "lowrise"
        out = []
        for it in items:
            if not (low or it.source_rule in ("eap_assembly", "eap_drills")):
                out.append(it)
                continue
            note = _VILLA_EAP_NOTE if it.source_rule == "eap_table_19_1" else _VILLA_SCOPE_NOTE
            upd = {"status": "conditional", "detail": note + (it.detail or "")}
            if it.source_rule == "eap_table_19_1":
                upd["source_rule"] = "eap_villa_written"
            out.append(it.model_copy(update=upd))
        items = out
    return ChapterReport(
        chapter_code="EAP",
        chapter_title="Emergency Action Plans (Ch 19)",
        selected_branch="eap_auto",
        selected_branch_section="Ch 19 Tables 19.1 and 19.2",
        blocks=[SectionBlock(title="EAP - Emergency action plan (Ch 19)", items=items)],
    )
