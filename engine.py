"""UAE FLSC 2018 multi-chapter compliance engine.

Each chapter has its own YAML in rules/. The engine loads them all and
produces a ComplianceReport with one ChapterReport per chapter.

Currently implemented:
  MOE  - Ch 3  Means of Egress        rules/ch3_means_of_egress.yaml
  FE   - Ch 4  Fire Extinguishers     rules/ch4_fire_extinguishers.yaml
  ES   - Ch 5  Exit Signs             rules/ch5_exit_signs.yaml
  EL   - Ch 6  Emergency Lighting     rules/ch6_emergency_lighting.yaml
  EVC  - Ch 7  Voice Evacuation       rules/ch7_evc.yaml
  FA   - Ch 8  Fire Alarm             rules/ch8_fire_alarm.yaml
  FP   - Ch 9  Fire Protection        rules/ch9_fire_protection.yaml
  SC   - Ch 10 Smoke Control          rules/ch10_smoke_control.yaml
  LPG  - Ch 11 LPG Code of Practice   rules/ch11_lpg.yaml
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

import yaml

from schema import (
    Building, ChapterReport, ComplianceReport, HighCeilingSpec,
    Requirement, SectionBlock, occupancy_group,
)

RULES_DIR = Path(__file__).parent / "rules"


# ---------------------------- Condition evaluator ----------------------------

def _eval_when(when: Dict[str, Any], b: Building) -> bool:
    for key, expected in when.items():
        if key == "occupancy":
            if b.occupancy != expected: return False
        elif key == "occupancy_not":
            if b.occupancy in expected: return False
        elif key == "occupancy_in":
            if b.occupancy not in expected: return False
        elif key == "hazard_class_in":
            if b.hazard_class not in expected: return False
        elif key == "occupancy_group_is":
            g = occupancy_group(b.occupancy)
            if expected in ("midrise_public", "lowrise_public"):
                if g != "public": return False
            elif expected == "midrise_residential":
                if g != "residential": return False
            else:
                return False
        elif key == "building_category_is":
            if b.building_category != expected: return False
        elif key == "building_category_not":
            if b.building_category in expected: return False
        elif key.endswith("_gt"):
            if not (getattr(b, key[:-3]) > expected): return False
        elif key.endswith("_gte"):
            if not (getattr(b, key[:-4]) >= expected): return False
        elif key.endswith("_lt"):
            if not (getattr(b, key[:-3]) < expected): return False
        elif key.endswith("_lte"):
            if not (getattr(b, key[:-4]) <= expected): return False
        elif key.endswith("_is"):
            if getattr(b, key[:-3]) != expected: return False
        else:
            if getattr(b, key, None) != expected: return False
    return True


# ---------------------------- Pump spec resolver -----------------------------

def _resolve_pump(entry: Dict[str, Any], b: Building):
    pst = entry.get("pump_spec_type")
    if pst == "standpipe_dependent":
        n = b.wet_riser_standpipes
        gpm = 750 if n <= 2 else 1000
        return (
            f"{gpm} gpm @ 6.9 bar at most remote landing valve",
            f"Pump sized at {gpm} gpm based on {n} standpipe{'s' if n != 1 else ''} in the wet-riser system. "
            f"UL/FM listed electric or diesel-driven pump set with jockey pump and controller.",
        )
    if pst == "fixed_250":
        return ("250 gpm @ 4.5 bar at most remote hose-reel outlet valve",
                "Electric-driven UL/FM listed fire pump set with jockey pump and controller.")
    if pst == "fixed_1000":
        return ("1000 gpm @ 6.9 bar at most remote hydrant outlet valve",
                "Electric or diesel driven UL/FM listed pump set for yard hydrant network.")
    return None, None


def _as_req(entry: Dict[str, Any], branch: Optional[Dict[str, Any]] = None,
            rule_id: Optional[str] = None, b: Optional[Building] = None) -> Requirement:
    status = entry.get("required", "required")
    if status not in ("required", "recommended", "conditional", "not_required"):
        status = "required"
    spec = entry.get("spec")
    detail = entry.get("detail")
    if b and entry.get("pump_spec_type"):
        rspec, rdetail = _resolve_pump(entry, b)
        if rspec:
            spec = rspec
        if rdetail:
            detail = rdetail
    return Requirement(
        system=entry["name"], status=status, spec=spec, detail=detail,
        code_ref=entry.get("code_ref") or (branch.get("section") if branch else None),
        page_ref=entry.get("page_ref") or (branch.get("page") if branch else None),
        source_rule=rule_id or (branch.get("id") if branch else None),
    )


def _select_branches(branches_list: List[Dict[str, Any]], b: Building) -> List[Dict[str, Any]]:
    return [br for br in branches_list if _eval_when(br.get("match", {}), b)]


def _collect_general(rules: Dict[str, Any], b: Building) -> List[Requirement]:
    out = []
    for g in rules.get("general", []) or []:
        if _eval_when(g.get("when", {}), b):
            for e in g.get("systems", []):
                out.append(_as_req(e, rule_id=g["id"], b=b))
    return out


def _collect_branch(branches: List[Dict[str, Any]], b: Building):
    matched = _select_branches(branches, b)
    out = []
    selected_id = None
    selected_section = None
    for br in matched:
        if selected_id is None:
            selected_id = br["id"]
            selected_section = br.get("section")
        for e in br.get("systems", []):
            out.append(_as_req(e, branch=br, b=b))
    return out, selected_id, selected_section, matched


def _collect_flag(sec: List[Dict[str, Any]], b: Building) -> List[Requirement]:
    out = []
    for rule in sec or []:
        flag = rule.get("flag")
        if flag and getattr(b, flag, False):
            for entry in rule.get("systems", []):
                out.append(_as_req(entry, rule_id=rule["id"], b=b))
    return out


def _dedupe(items: List[Requirement]) -> List[Requirement]:
    seen, out = set(), []
    for r in items:
        k = (r.system, r.spec, r.status)
        if k not in seen:
            seen.add(k); out.append(r)
    return out


# ---------------------------- High-ceiling (FP-specific) ---------------------

def _pick_band(h: float) -> Optional[str]:
    if 10 <= h <= 13.5: return "band_10_13_5"
    if 13.5 < h <= 18: return "band_13_5_18"
    if 18 < h <= 30: return "band_18_30"
    return None


def _eval_high_ceiling(rules: Dict[str, Any], b: Building) -> Optional[HighCeilingSpec]:
    hc = rules.get("high_ceiling")
    if not hc: return None
    if not _eval_when(hc.get("trigger", {}), b): return None
    band = _pick_band(b.ceiling_height_m)
    matrix = hc.get("matrix", {}).get(b.hazard_class, {})
    if not band or band not in matrix:
        return HighCeilingSpec(
            applies=True, ceiling_height_m=b.ceiling_height_m, hazard_class=b.hazard_class,
            note="Ceiling height out of tabulated range (Table 9.29.A covers 10-30 m). Use manufacturer's listed high-ceiling design.",
            code_ref=hc.get("code_ref"), page_ref=hc.get("page_ref"),
        )
    p = matrix[band]
    return HighCeilingSpec(
        applies=True, ceiling_height_m=b.ceiling_height_m, hazard_class=b.hazard_class,
        height_range=p.get("height_range"), k_factor=p.get("k_factor"),
        min_pressure=p.get("min_pressure"), min_sprinklers=p.get("min_sprinklers"),
        density=p.get("density"), design_area=p.get("design_area"),
        pump_without_hydrant_gpm=p.get("pump_without_hydrant_gpm"),
        pump_with_hydrant_gpm=p.get("pump_with_hydrant_gpm"),
        code_ref=hc.get("code_ref"), page_ref=hc.get("page_ref"), note=hc.get("note"),
    )


# ---------------------------- Per-chapter evaluators -------------------------

def evaluate_fp(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 9 - Fire Protection."""
    blocks = []
    gen = _dedupe(_collect_general(rules, b))
    if gen:
        blocks.append(SectionBlock(title="FP - General Requirements (Ch 9, #4.1)", items=gen))

    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    if branch_items:
        blocks.append(SectionBlock(title="FP - Branch Requirements (Ch 9)", items=_dedupe(branch_items)))

    # Determine if matched FP branch + general REQUIRES (status=required) any sprinkler system.
    # Various-locations items annotated with `requires_sprinkler_system: true` are suppressed
    # when the building's branch does not mandate sprinklers (e.g. small villas where
    # sprinklers are only "recommended").
    _all_items = list(gen) + list(branch_items)
    sprinkler_required = any(
        ("sprinkler" in (it.system or "").lower())
        and it.status == "required"
        for it in _all_items
    )
    var_rules_filtered = [
        rule for rule in (rules.get("various_locations") or [])
        if (not rule.get("requires_sprinkler_system")) or sprinkler_required
    ]
    var_items = _dedupe(_collect_flag(var_rules_filtered, b))
    if var_items:
        blocks.append(SectionBlock(title="FP - Various Locations & Extensions (Table 9.29)", items=var_items))

    aux_items = _dedupe(_collect_flag(rules.get("auxiliary_rooms", []), b))
    if aux_items:
        blocks.append(SectionBlock(title="FP - Auxiliary Rooms (Table 9.30)", items=aux_items))

    eq_items = _dedupe(_collect_flag(rules.get("equipment", []), b))
    if eq_items:
        blocks.append(SectionBlock(title="FP - Equipment (Table 9.31)", items=eq_items))

    return ChapterReport(
        chapter_code="FP", chapter_title="Fire Protection (Ch 9)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


def evaluate_moe(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 3 - Means of Egress."""
    blocks = []
    gen = _dedupe(_collect_general(rules, b))
    if gen:
        blocks.append(SectionBlock(title="MOE - General Requirements (Ch 3 / Tables 3.1, 3.2, 3.14, 3.15)", items=gen))
    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    if branch_items:
        blocks.append(SectionBlock(title="MOE - Occupancy-specific (Ch 3 / Tables 3.13 + 3.16)", items=_dedupe(branch_items)))
    return ChapterReport(
        chapter_code="MOE", chapter_title="Means of Egress (Ch 3)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


def evaluate_fe(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 4 - Fire Extinguishers."""
    blocks = []
    gen = _dedupe(_collect_general(rules, b))
    if gen:
        blocks.append(SectionBlock(title="FE - Universal Class A + Residential Class K (Ch 4, Table 4.3 rows 1, 6)", items=gen))

    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    if branch_items:
        blocks.append(SectionBlock(title="FE - Occupancy-specific (Class B Wheeled, Ch 4, Table 4.3 row 3)", items=_dedupe(branch_items)))

    addons = _dedupe(_collect_flag(rules.get("addons", []), b))
    if addons:
        blocks.append(SectionBlock(title="FE - Hazard-zone Add-ons (Class B / C / D / K)", items=addons))

    return ChapterReport(
        chapter_code="FE", chapter_title="Fire Extinguishers (Ch 4)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


def evaluate_es(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 5 - Exit Signs."""
    blocks = []

    gen = _dedupe(_collect_general(rules, b))
    if gen:
        blocks.append(SectionBlock(title="ES - Universal Requirements (Ch 5, #3 / Table 5.3 items 1-5)", items=gen))

    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    if branch_items:
        blocks.append(SectionBlock(title="ES - Occupancy-specific Requirements (Ch 5 / Table 5.3)", items=_dedupe(branch_items)))

    addons = _dedupe(_collect_flag(rules.get("addons", []), b))
    if addons:
        blocks.append(SectionBlock(title="ES - Special Zones / Add-ons", items=addons))

    return ChapterReport(
        chapter_code="ES", chapter_title="Exit Signs (Ch 5)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


def evaluate_evc(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 7 - Emergency Voice Evacuation + Two-way Telephone."""
    blocks = []
    # General requirements only fire when an EVC system IS required by the branch.
    branch_items, sel_id, sel_section, matched = _collect_branch(rules.get("branches", []), b)
    evc_required = False
    for br in matched:
        if "_not_required" not in br.get("id", ""):
            evc_required = True; break
    if evc_required:
        gen = _dedupe(_collect_general(rules, b))
        if gen:
            blocks.append(SectionBlock(title="EVC - General Specifications (Ch 7, Tables 7.1 + 7.2)", items=gen))
    if branch_items:
        blocks.append(SectionBlock(title="EVC - Voice Evac + Two-way Telephone (Ch 7, Table 7.3)", items=_dedupe(branch_items)))

    return ChapterReport(
        chapter_code="EVC", chapter_title="Emergency Voice Evacuation (Ch 7)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


def evaluate_el(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 6 - Emergency Lighting."""
    blocks = []
    gen = _dedupe(_collect_general(rules, b))
    if gen:
        blocks.append(SectionBlock(title="EL - General Specs + Coverage Locations (Ch 6, Tables 6.1 + 6.6)", items=gen))

    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    if branch_items:
        blocks.append(SectionBlock(title="EL - System Type Selection (Ch 6, Table 6.5)", items=_dedupe(branch_items)))

    return ChapterReport(
        chapter_code="EL", chapter_title="Emergency Lighting (Ch 6)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


def evaluate_fa(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 8 - Fire Detection & Alarm."""
    blocks = []
    gen = _dedupe(_collect_general(rules, b))
    if gen:
        blocks.append(SectionBlock(title="FA - General Requirements (Ch 8, #3 + #4 / Table 8.1.a)", items=gen))
    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    if branch_items:
        blocks.append(SectionBlock(title="FA - Detection & Alarm by Occupancy / Height (Ch 8, Table 8.13)", items=_dedupe(branch_items)))

    aux = _dedupe(_collect_flag(rules.get("auxiliary_rooms", []), b))
    if aux:
        blocks.append(SectionBlock(title="FA - Auxiliary Rooms (Ch 8, Table 8.14)", items=aux))

    eq = _dedupe(_collect_flag(rules.get("equipment", []), b))
    if eq:
        blocks.append(SectionBlock(title="FA - Equipment (Ch 8, Table 8.15)", items=eq))

    return ChapterReport(
        chapter_code="FA", chapter_title="Fire Detection & Alarm (Ch 8)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


def evaluate_sc(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 10 - Smoke Control & Smoke Management."""
    blocks = []
    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    if branch_items:
        blocks.append(SectionBlock(title="SC - Smoke Control by Tier / Occupancy (Ch 10, Tables 10.19-10.27)", items=_dedupe(branch_items)))

    aux = _dedupe(_collect_flag(rules.get("auxiliary_rooms", []), b))
    if aux:
        blocks.append(SectionBlock(title="SC - Auxiliary Zones / Equipment (Ch 10, Table 10.27)", items=aux))

    return ChapterReport(
        chapter_code="SC", chapter_title="Smoke Control (Ch 10)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


def evaluate_lpg(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 11 - LPG Code of Practice."""
    blocks = []
    # Identify whether ANY gas system is present (skip general block when "no gas")
    has_gas = (b.has_lpg_tanks or b.has_gas_infra_connection or b.has_gas_cylinders_villa
               or b.has_lpg_cylinders_food_truck or getattr(b, "has_lpg_flame_effect", False))
    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    if has_gas:
        gen = _dedupe(_collect_general(rules, b))
        if gen:
            blocks.append(SectionBlock(title="LPG - General Universal Requirements (Ch 11, Tables 11.1, 11.2, 11.4, 11.14)", items=gen))
    if branch_items:
        blocks.append(SectionBlock(title="LPG - Base Gas-System Requirements (Ch 11, Tables 11.1, 11.4, 11.5, 11.6)", items=_dedupe(branch_items)))

    addons = _dedupe(_collect_flag(rules.get("addons", []), b))
    if addons:
        blocks.append(SectionBlock(title="LPG - Variant Add-ons (Roof / Underground / Indoor / Food Truck / PRDP)", items=addons))

    return ChapterReport(
        chapter_code="LPG", chapter_title="LPG Code of Practice (Ch 11)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


# ---------------------------- Master evaluate --------------------------------

CHAPTER_EVALUATORS: Dict[str, tuple] = {
    "FP": ("ch9_fire_protection.yaml", evaluate_fp),
    "ES": ("ch5_exit_signs.yaml",      evaluate_es),
}


_RULES_CACHE: Dict[str, Dict[str, Any]] = {}

def load_rules(filename: str) -> Dict[str, Any]:
    if filename in _RULES_CACHE:
        return _RULES_CACHE[filename]
    path = RULES_DIR / filename
    if not path.exists():
        _RULES_CACHE[filename] = {}
        return {}
    with open(path, "r", encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    _RULES_CACHE[filename] = d
    return d


def _branch_requires_wet_riser(rules: Dict[str, Any], b: Building) -> bool:
    matched = _select_branches(rules.get("branches", []), b)
    for br in matched:
        for entry in br.get("systems", []):
            if entry.get("requires_wet_riser"):
                return True
    return False


# Chapter ordering follows the UAE FLSC chapter numbering (Ch 4 -> Ch 10).
# When new chapters are added, insert them in numerical order here.
CHAPTER_ORDER = [
    # ("file", evaluator) - in UAE FLSC chapter-number order
    ("ch3_means_of_egress.yaml",    "evaluate_moe"),
    ("ch4_fire_extinguishers.yaml", "evaluate_fe"),
    ("ch5_exit_signs.yaml",         "evaluate_es"),
    ("ch6_emergency_lighting.yaml", "evaluate_el"),
    ("ch7_evc.yaml",                "evaluate_evc"),
    ("ch8_fire_alarm.yaml",         "evaluate_fa"),
    ("ch9_fire_protection.yaml",    "evaluate_fp"),
    ("ch10_smoke_control.yaml",     "evaluate_sc"),
    ("ch11_lpg.yaml",               "evaluate_lpg"),
]


def evaluate_attached_parking(b: Building) -> List[ChapterReport]:
    """Build a synthetic parking Building (preserving height / parking area) and run every
    chapter against it, returning a per-chapter list. Used to surface parking sub-occupancy
    requirements when the main occupancy is non-parking but has an in-building parking area.

    The PARKING AREA (parking_area_m2) drives Ch 10 SC area-based thresholds (e.g. 3600 m^2
    make-up-air exception for enclosed parking; 4000 m^2 small-vs-large open parking split).
    Falls back to basement BUA or ground-floor BUA when not set explicitly.
    """
    synth_occ = "parking_open" if b.attached_parking_kind == "open" else "parking_enclosed"
    parking_area = b.parking_area_m2 or b.basement_bua_m2 or b.ground_floor_bua_m2 or 0.0
    # Re-create a minimal Building with parking occupancy + parking-specific area; carry over
    # flags that affect parking outputs (high ceiling, fire pump room, etc.)
    synth = Building(
        project_name=b.project_name + " (parking sub-occupancy)" if b.project_name else "",
        occupancy=synth_occ,
        height_m=b.height_m,
        floors_above_grade=b.floors_above_grade,
        floors_below_grade=b.floors_below_grade,
        depth_below_grade_m=b.depth_below_grade_m,
        gross_floor_area_m2=parking_area,
        ground_floor_bua_m2=parking_area,
        basement_bua_m2=parking_area if b.basement_bua_m2 > 0 else 0.0,
        plot_area_m2=b.plot_area_m2,
        hazard_class="OH2" if synth_occ == "parking_enclosed" else "OH1",
        has_high_ceiling=b.has_high_ceiling,
        ceiling_height_m=b.ceiling_height_m,
        has_diesel_generator_room=b.has_diesel_generator_room,
        has_fire_pump_room=b.has_fire_pump_room,
        has_main_electrical_room=b.has_main_electrical_room,
    )
    chapters = []
    moe_rules = load_rules("ch3_means_of_egress.yaml")
    fe_rules  = load_rules("ch4_fire_extinguishers.yaml")
    es_rules  = load_rules("ch5_exit_signs.yaml")
    el_rules  = load_rules("ch6_emergency_lighting.yaml")
    fa_rules  = load_rules("ch8_fire_alarm.yaml")
    fp_rules  = load_rules("ch9_fire_protection.yaml")
    sc_rules  = load_rules("ch10_smoke_control.yaml")
    if moe_rules: chapters.append(evaluate_moe(synth, moe_rules))
    if fe_rules:  chapters.append(evaluate_fe(synth, fe_rules))
    if es_rules:  chapters.append(evaluate_es(synth, es_rules))
    if el_rules:  chapters.append(evaluate_el(synth, el_rules))
    if fa_rules:  chapters.append(evaluate_fa(synth, fa_rules))
    if fp_rules:  chapters.append(evaluate_fp(synth, fp_rules))
    if sc_rules:  chapters.append(evaluate_sc(synth, sc_rules))
    return chapters


def evaluate(b: Building) -> ComplianceReport:
    chapters = []
    moe_rules = load_rules("ch3_means_of_egress.yaml")
    fe_rules  = load_rules("ch4_fire_extinguishers.yaml")
    es_rules  = load_rules("ch5_exit_signs.yaml")
    el_rules  = load_rules("ch6_emergency_lighting.yaml")
    evc_rules = load_rules("ch7_evc.yaml")
    fa_rules  = load_rules("ch8_fire_alarm.yaml")
    fp_rules  = load_rules("ch9_fire_protection.yaml")
    sc_rules  = load_rules("ch10_smoke_control.yaml")
    lpg_rules = load_rules("ch11_lpg.yaml")

    # MOE -> FE -> ES -> EL -> EVC -> FA -> FP -> SC -> LPG - chapter-number order.
    if moe_rules:
        chapters.append(evaluate_moe(b, moe_rules))
    if fe_rules:
        chapters.append(evaluate_fe(b, fe_rules))
    if es_rules:
        chapters.append(evaluate_es(b, es_rules))
    if el_rules:
        chapters.append(evaluate_el(b, el_rules))
    if evc_rules:
        chapters.append(evaluate_evc(b, evc_rules))
    if fa_rules:
        chapters.append(evaluate_fa(b, fa_rules))
    if fp_rules:
        chapters.append(evaluate_fp(b, fp_rules))
    if sc_rules:
        chapters.append(evaluate_sc(b, sc_rules))
    if lpg_rules:
        chapters.append(evaluate_lpg(b, lpg_rules))

    # Attached parking sub-evaluation: when the main occupancy is NOT itself parking
    # but the building has an in-building parking area, run a parallel evaluation
    # using a synthetic parking Building so all parking-specific requirements surface.
    attached = []
    if b.has_parking_area and b.occupancy not in ("parking_enclosed", "parking_open", "infrastructure"):
        try:
            attached = evaluate_attached_parking(b)
        except Exception:
            attached = []

    return ComplianceReport(
        building=b,
        chapters=chapters,
        requires_wet_riser=_branch_requires_wet_riser(fp_rules, b),
        high_ceiling=_eval_high_ceiling(fp_rules, b),
        attached_parking_chapters=attached,
    )


# ---------------------------- Markdown renderer ------------------------------

def report_to_markdown(r: ComplianceReport) -> str:
    b = r.building
    L = []
    L.append("# UAE FLSC 2018 - Fire & Life Safety Requirements")
    if b.project_name:
        L.append(f"**Project:** {b.project_name}")
    L.append("")
    L.append("## Building profile")
    L.append(f"- Occupancy: `{b.occupancy}`")
    L.append(f"- Height: {b.height_m} m  ->  class: **{b.height_class}**")
    L.append(f"- Storeys: {b.floors_above_grade} above + {b.floors_below_grade} basement")
    L.append(f"- Plot area: {b.plot_area_m2} m²  |  GF BUA: {b.ground_floor_bua_m2} m²  |  Basement BUA: {b.basement_bua_m2} m²")
    L.append(f"- Total GFA: {b.gross_floor_area_m2} m²  |  Hazard class: {b.hazard_class}")
    if b.has_high_ceiling:
        L.append(f"- High ceiling: {b.ceiling_height_m} m")
    if r.requires_wet_riser:
        L.append(f"- Wet riser standpipes: {b.wet_riser_standpipes}")
    L.append("")

    for ch in r.chapters:
        L.append(f"# {ch.chapter_code} - {ch.chapter_title}")
        if ch.selected_branch:
            L.append(f"_Matched branch: `{ch.selected_branch}` - {ch.selected_branch_section}_")
            L.append("")
        for block in ch.blocks:
            L.append(f"## {block.title}")
            for req in block.items:
                tag = "" if req.status == "required" else f" _[{req.status}]_"
                L.append(f"- **{req.system}**{tag}")
                if req.spec:
                    L.append(f"  - Spec: {req.spec}")
                if req.detail:
                    L.append(f"  - {req.detail}")
                cite = [p for p in (req.code_ref, req.page_ref) if p]
                if cite:
                    L.append(f"  - _Ref: {' - '.join(cite)}_")
            L.append("")

    # Attached parking sub-occupancy
    if r.attached_parking_chapters:
        L.append("")
        L.append("# ATTACHED PARKING AREA - Sub-occupancy requirements")
        L.append(f"_Synthetic occupancy: `{('parking_open' if r.building.attached_parking_kind == 'open' else 'parking_enclosed')}` driven by `has_parking_area=True`_")
        L.append("")
        for ch in r.attached_parking_chapters:
            L.append(f"## P-{ch.chapter_code} - {ch.chapter_title}")
            for block in ch.blocks:
                L.append(f"### {block.title}")
                for req in block.items:
                    tag = "" if req.status == "required" else f" _[{req.status}]_"
                    L.append(f"- **{req.system}**{tag}")
                    if req.spec:
                        L.append(f"  - Spec: {req.spec}")
                    if req.detail:
                        L.append(f"  - {req.detail}")
                    cite = [p for p in (req.code_ref, req.page_ref) if p]
                    if cite:
                        L.append(f"  - _Ref: {' - '.join(cite)}_")
                L.append("")

    if r.high_ceiling and r.high_ceiling.applies:
        hc = r.high_ceiling
        L.append("## FP - High Ceiling Sprinkler Protection (Table 9.29.A)")
        L.append(f"- Ceiling height: **{hc.ceiling_height_m} m** | Hazard: **{hc.hazard_class}** | Band: {hc.height_range or 'out of range'}")
        if hc.k_factor:
            L.append(f"- K-factor: {hc.k_factor} | Pressure: {hc.min_pressure} | Sprinklers: {hc.min_sprinklers}")
            if hc.density: L.append(f"- Density: {hc.density}")
            if hc.design_area: L.append(f"- Design area: {hc.design_area}")
            L.append(f"- Pump (no hydrant): {hc.pump_without_hydrant_gpm} gpm | Pump (w/ hydrant): {hc.pump_with_hydrant_gpm} gpm")
        if hc.note:
            L.append(f"- _Note: {hc.note}_")
        if hc.code_ref:
            L.append(f"- _Ref: {hc.code_ref} - {hc.page_ref}_")
        L.append("")

    return "\n".join(L)


if __name__ == "__main__":
    b = Building(occupancy="hotel_a", height_m=55, floors_above_grade=18,
                 floors_below_grade=2, ground_floor_bua_m2=1200, plot_area_m2=5000,
                 hazard_class="LH", wet_riser_standpipes=3,
                 has_main_electrical_room=True, has_diesel_generator_room=True,
                 has_amusement_confounding=False)
    print(report_to_markdown(evaluate(b)))
