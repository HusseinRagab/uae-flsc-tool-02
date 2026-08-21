"""UAE FLSC 2018 Annexure 2 — Drawing submission checklist (design-aid)."""
from __future__ import annotations
from typing import List, Tuple
from flsc_schema import ComplianceReport

ChecklistItem = Tuple[str, str, bool]

def build_submission_checklist(r: ComplianceReport) -> List[ChecklistItem]:
    required_codes = set()
    for ch in r.chapters:
        for blk in ch.blocks:
            for it in blk.items:
                if it.status == "required":
                    required_codes.add(ch.chapter_code)
                    break
    items: List[ChecklistItem] = [
        ("General requirements (Table A2.1)", "File format, naming, size limits, title block", True),
        ("Life Safety / Means of Egress plans", "Exit routes, travel distances, stair details, OL", "MOE" in required_codes or "FSA" in required_codes),
        ("Fire Alarm system drawings", "FACP, detectors, MCP, notification, zoning", "FA" in required_codes),
        ("Voice Evacuation drawings", "Speakers, zoning, firefighter phones", "EVC" in required_codes),
        ("Fire Protection drawings", "Sprinklers, risers, pumps, tanks, hose reels", "FP" in required_codes),
        ("Fire Extinguisher layout", "Type, rating, spacing per Ch 4", "FE" in required_codes),
        ("Exit Sign layout", "Locations, bilingual, photoluminescent", "ES" in required_codes),
        ("Emergency Lighting layout", "Coverage, central battery / self-contained", "EL" in required_codes),
        ("Smoke Control drawings", "Pressurization, exhaust, FF lift, fans", "SC" in required_codes),
        ("LPG / gas drawings", "Tank/cylinder locations, PRVs, detection", "LPG" in required_codes),
        ("Fire Service Access plan", "Access roads, hydrants, breeching inlets, turning", "FSA" in required_codes or r.building.height_m > 15),
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
