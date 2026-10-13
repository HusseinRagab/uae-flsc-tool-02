"""UAE FLSC 2018 Annexure 2 — Drawing submission checklist (design-aid).

Follows Table A2.1 (p.1284-1286, audit CH10-25): 4 to 6 separate files (#2.i),
the file format and size limits (#1), the letters whose absence rejects a
submission (#5.i.h-i) and the fire access road layout (#5.ii.a).
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
    items: List[ChecklistItem] = [
        ("File format and size (Table A2.1 #1)",
         "pdf / dwf as the Emirate portal requires; each file at most 50 MB, total at most 200 MB; "
         "a file over 50 MB split into Part 1, Part 2, Part 3; no .zip, files with errors or "
         "password protected files", True),
        ("Number of files (Table A2.1 #2.i)",
         "4 to 6 separate files as the project needs: a) Architecture and Life Safety, b) Fire "
         "Detection and Alarm, c) Fire Protection and suppression, d) Emergency Lighting and Signage, "
         "e) Smoke Control and management, f) LPG System (if applicable)", True),
        ("File a) Architecture and Life Safety",
         "Means of egress, exit routes, travel distances, stair details, occupant load, sections, all "
         "floor plans", True),
        ("Fire access road layout (Table A2.1 #5.ii.a)",
         "In the Architecture and Life Safety file; drawings without it are rejected", True),
        ("File b) Fire Detection and Alarm System",
         "FACP, detectors, MCP, notification, zoning; voice evacuation where required",
         "FA" in required_codes or "EVC" in required_codes),
        ("File c) Fire Protection and suppression systems",
         "Sprinklers, risers, pumps, tanks, hose reels, suppression; fire extinguishers per the "
         "discipline legends", "FP" in required_codes or "FE" in required_codes),
        ("File d) Emergency Lighting and Signage systems",
         "Emergency lighting coverage and exit signs in one file",
         "EL" in required_codes or "ES" in required_codes),
        ("File e) Smoke Control and management systems",
         "Pressurization, exhaust, FF lift, fans", "SC" in required_codes),
        ("File f) LPG System (if applicable)",
         "Tank / cylinder locations, piping, detection", has_lpg),
        ("Clarifying letter of LPG / natural gas usage (Table A2.1 #5.i.i)",
         "Every submission; state that no LPG / natural gas is used where none is" if not has_lpg
         else "Every submission; describes the LPG / natural gas usage", True),
        ("Material / activity / storage method letter (Table A2.1 #5.i.h)",
         "Storage and industrial projects; submissions without it are rejected", storage),
        ("Rejection checks (Table A2.1 #5.i)",
         "Required number of files, file names, scale, check marking, coverpage, room and occupancy "
         "names, colour coding and format, yellow / red clouds on modification jobs; no product "
         "catalogues, brochures or company licences", True),
        ("Legends per discipline", "Annexure 2 standard legends for LS / FA / FP / EL / SC / LPG", True),
        ("Consultant declaration / HoE endorsement", "Where required by local Civil Defence", True),
    ]
    return [(pkg, note, bool(req)) for pkg, note, req in items]


def checklist_markdown(r: ComplianceReport) -> str:
    lines = ["## Civil Defence drawing submission checklist (Annexure 2)", "",
             "_Design-aid only — confirm against current CD portal requirements._", ""]
    for pkg, note, req in build_submission_checklist(r):
        lines.append(f"- {'☑' if req else '☐'} **{pkg}** — {note}")
    return "\n".join(lines)
