"""UAE FLSC 2018 Annexure 2 — Drawing submission checklist (design-aid).

Follows Table A2.1 (p.1284-1288; audit CH10-25, audit 28.10.2026 A2-01 / A2-02): file
format and size (#1), 4 to 6 separate files (#2.i), file names (#3), drawings not to be
submitted (#4), the reasons for rejection of applications (#5.i) and of each discipline's
drawings (#5.ii-#5.vii), and the legends (#6). Only items printed in Table A2.1 are listed.
"""
from __future__ import annotations
from typing import List, Tuple
from flsc_schema import ComplianceReport

ChecklistItem = Tuple[str, str, bool]

_STORAGE_INDUSTRIAL = ("storage_industrial",)


def build_submission_checklist(r: ComplianceReport) -> List[ChecklistItem]:
    required_codes = set()
    for ch in r.chapters:
        for blk in ch.blocks:
            for it in blk.items:
                if it.status == "required":
                    required_codes.add(ch.chapter_code)
                    break
    b = r.building
    occs = {b.occupancy, *getattr(b, "secondary_occupancies", [])}
    storage = any(o in _STORAGE_INDUSTRIAL for o in occs)
    has_lpg = "LPG" in required_codes
    tall = b.height_class in ("highrise", "super_highrise")
    superh = b.height_class == "super_highrise"
    fa = "FA" in required_codes or "EVC" in required_codes
    fp = "FP" in required_codes or "FE" in required_codes
    el = "EL" in required_codes or "ES" in required_codes
    sc = "SC" in required_codes
    items: List[ChecklistItem] = [
        ("File format and size (Table A2.1 #1)",
         "pdf / dwf as the Emirate portal requires; each file at most 50 MB, total at most 200 MB; "
         "a file over 50 MB split into Part 1, Part 2, Part 3; no .zip, files with errors or "
         "password protected files", True),
        ("Number of files (Table A2.1 #2.i)",
         "4 to 6 separate files as the project needs: a) Architecture and Life Safety, b) Fire "
         "Detection and Alarm, c) Fire Protection and suppression, d) Emergency Lighting and Signage, "
         "e) Smoke Control and management, f) LPG System (if applicable)", True),
        ("File names (Table A2.1 #3)",
         "#3.i: a) XXXXX (Application number)_LIFE SAFETY; b) XXXXX (Application number)_FIRE ALARM "
         "SYSTEM; c) XXXXX (Application number)_FIRE PROTECTION SYSTEM; d) XXXX (Application "
         "number)_EMERGENCY LIGHTING SYSTEM; e) XXXXX (Application number)_SMOKE CONTROL SYSTEM; "
         "f) XXXXX (Application number)_LPG SYSTEM. #3.ii letters: MATERIAL AND ACTIVITY LETTER; "
         "SCOPE OF WORK; LPG NOT REQUIRED; UNDERTAKING (for any client undertakings). #3.iii: file "
         "names such as Fire, Civil Defence, Residential, Project, Untitled, FF, Approval, "
         "2December, Tiltlepage, Groundfloor shall not be acceptable and drawings will not be "
         "reviewed", True),
        ("Drawings not to be submitted (Table A2.1 #4)",
         "Civil Defence does not review any aspect other than fire and life safety; do not include "
         "HVAC, Drainage, Lighting, Plumbing, Structural Details, Floor tiling, Ceiling tiles, "
         "Electrical distribution, Landscaping (#4.i); no product details with brand names, product "
         "catalogues or product brand specifications: such submissions will not be reviewed and "
         "stamped (#4.ii)", True),
        ("File a) Architecture and Life Safety",
         "Means of egress, exit routes, travel distances, stair details, occupant load, sections, all "
         "floor plans", True),
        ("Fire access road layout (Table A2.1 #5.ii.a)",
         "In the Architecture and Life Safety file; drawings without it are rejected", True),
        ("Architecture / Life Safety rejection checks (Table A2.1 #5.ii.b-h, l-n)",
         "Rejected without review if: b) without sections with dimensions; c) without all floor "
         "plans; d) without 1/3 of building diagonal distance between stairs in sprinklered "
         "buildings; e) without 1/2 of building diagonal distance between stairs in non-sprinklered "
         "buildings; f) without separation at discharge level stair between typical floor discharge "
         "and lower level or basement discharges; g) without direct discharge through protected "
         "corridor for half the number of building stairs; h) without stair details, step details "
         "in dedicated page; l) without pump room and water tank locations, sections and details; "
         "m) with underground pump room having hatch entry, cat ladder and spiral stair access; "
         "n) without required fire rating of corridors, stairs, LV room, substations, generator "
         "rooms, plant rooms, hazardous storage rooms, pump rooms etc.", True),
        ("Fire lift in dedicated shaft (Table A2.1 #5.ii.i)",
         "Highrise buildings: drawings without fire lift in dedicated shaft are rejected", tall),
        ("Fire lift lobby (Table A2.1 #5.ii.j)",
         "Superhighrise buildings: drawings without fire lift lobby are rejected", superh),
        ("Generator room (Table A2.1 #5.ii.k)",
         "Highrise and Superhighrise buildings: drawings without generator room are rejected", tall),
        ("File b) Fire Detection and Alarm System",
         "FACP, detectors, MCP, notification, zoning; voice evacuation where required", fa),
        ("Fire Detection and Alarm rejection checks (Table A2.1 #5.iii)",
         "Rejected without review if: a) superimposed on life safety details; b) without legend; "
         "c) without wiring distribution; d) without all floor plans; e) without sounder based "
         "detectors at bedrooms; f) without above false ceiling detectors with remote response "
         "indicators; g) without sounders / speakers having flashers at parking, basements, plant "
         "rooms and outdoor areas; h) without control panel (FACP / FARP) locations; i) without "
         "riser diagrams; j) without voice speakers for highrise and Superhighrise buildings", fa),
        ("File c) Fire Protection and suppression systems",
         "Sprinklers, risers, pumps, tanks, hose reels, suppression; fire extinguishers per the "
         "discipline legends", fp),
        ("Fire Protection rejection checks (Table A2.1 #5.v)",
         "Rejected without review if: a) superimposed on life safety details; b) without legend "
         "and sprinkler types; c) without piping distribution; d) without all floor plans; "
         "e) without pipe sizes; f) without fire pump and water tank capacities on riser diagrams; "
         "g) without riser diagrams; h) without vertical turbine type pumps for negative suction "
         "water tank arrangements", fp),
        ("File d) Emergency Lighting and Signage systems",
         "Emergency lighting coverage and exit signs in one file", el),
        ("Emergency Lighting rejection checks (Table A2.1 #5.iv)",
         "Rejected without review if: a) superimposed on life safety details; b) without legend; "
         "c) without wiring distribution; d) without all floor plans; e) without cross zoning for "
         "central battery systems; f) without control panel locations; g) without riser diagrams",
         el),
        ("File e) Smoke Control and management systems",
         "Pressurization, exhaust, FF lift, fans", sc),
        ("Smoke Control rejection checks (Table A2.1 #5.vi)",
         "Rejected without review if: a) With HVAC drawings or details; b) superimposed on life "
         "safety details; c) without legend; d) without ducting distribution; e) without all floor "
         "plans; f) without arrow marks for supply and return indications; g) without control "
         "panel locations; h) without riser diagrams; i) without typical details and "
         "specifications for fans, ducts and curtains, if any", sc),
        ("File f) LPG System (if applicable)",
         "Tank / cylinder locations, piping, detection", has_lpg),
        ("LPG / Natural gas rejection checks (Table A2.1 #5.vii)",
         "Rejected without review if: a) superimposed on life safety details; b) without legend; "
         "c) without piping distribution; d) LPG piping crossing through stairs, lift lobbies, "
         "garbage rooms; e) without tank locations, sizes, capacity and separation dimensions; "
         "f) without fill line location; g) without PRDP location; h) without all floor plans; "
         "i) without typical tank installation details; j) without gas detectors and control panel "
         "locations; k) without riser diagrams", has_lpg),
        ("Clarifying letter of LPG / natural gas usage (Table A2.1 #5.i.i)",
         "Every submission; state that no LPG / natural gas is used where none is" if not has_lpg
         else "Every submission; describes the LPG / natural gas usage", True),
        ("Material / activity / storage method letter (Table A2.1 #5.i.h)",
         "Storage and industrial projects; submissions without it are rejected", storage),
        ("Rejection checks (Table A2.1 #5.i)",
         "Required number of files, file names, scale, check marking, coverpage, room and occupancy "
         "names, colour coding and format, yellow / red clouds on modification jobs; no product "
         "catalogues, brochures or company licences", True),
        ("Legends per discipline (Table A2.1 #6)",
         "Symbols and legend per Figure A2.1.1 (Life Safety), A2.1.2 (Fire Alarm), A2.1.3 (Fire "
         "Protection), A2.1.4 (Emergency Lighting), A2.1.5 (Smoke Control), A2.1.6 (LPG)", True),
    ]
    return [(pkg, note, bool(req)) for pkg, note, req in items]


def checklist_markdown(r: ComplianceReport) -> str:
    lines = ["## Civil Defence drawing submission checklist (Annexure 2)", "",
             "_Design-aid only — confirm against current CD portal requirements._", ""]
    for pkg, note, req in build_submission_checklist(r):
        lines.append(f"- {'☑' if req else '☐'} **{pkg}** — {note}")
    return "\n".join(lines)
