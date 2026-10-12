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

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

import yaml

from flsc_schema import (
    Building, ChapterReport, ComplianceReport, HighCeilingSpec,
    Requirement, SectionBlock, occupancy_group, default_hazard,
)
from occupant_load import compute_occupant_load
from fire_access import evaluate_fire_access, compute_fire_access
from accessibility import evaluate_accessibility
from eap import evaluate_eap

RULES_DIR = Path(__file__).parent / "rules"


# ---------------------------- Condition evaluator ----------------------------

def _eval_when(when: Dict[str, Any], b: Building) -> bool:
    """True when every key of `when` holds. Two combinators:
    `any_of: [{...}, {...}]` holds when at least one sub-condition holds;
    `not: {...}` holds when the sub-condition (all its keys together) fails."""
    for key, expected in when.items():
        if key == "any_of":
            if not any(_eval_when(c, b) for c in expected): return False
        elif key == "not":
            if _eval_when(expected, b): return False
        elif key == "occupancy":
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
        elif key.endswith("_in"):
            # Generic membership check against any Building scalar field.
            # `<field>_in: [a, b, c]` is equivalent to `getattr(b, field) in [a, b, c]`.
            # `occupancy_in` and `hazard_class_in` are handled above; this catches the rest
            # (e.g. `tent_marquee_kind_in: [permanent, commercial_desert]`).
            if getattr(b, key[:-3], None) not in expected: return False
        else:
            if getattr(b, key, None) != expected: return False
    return True


# ---------------------------- Pump spec resolver -----------------------------

_PUMP_SPECS_FILENAME = "pump_specs.yaml"

# Hard-coded fallback used only when pump_specs.yaml is absent — preserves
# the legacy behaviour for installations that haven't unpacked the new file.
_PUMP_FALLBACK = {
    "standpipe_dependent": {
        "source": "UAE FLSC 2018 Ch 9 Section 4 occupancy tables; Table 9.6 item 3.iii",
        "pressure_bar": 6.9,
        "pressure_note": "at most remote landing valve",
        "pump_description": "UL/FM listed electric or diesel-driven pump set "
                            "with jockey pump and controller.",
        "brackets": [{"max_standpipes": 2, "gpm": 750},
                     {"max_standpipes": 999, "gpm": 1000}],
    },
    "fixed_1000": {
        "source": "UAE FLSC 2018 Ch. 9 (yard hydrant network)",
        "pressure_bar": 6.9,
        "pressure_note": "at most remote hydrant outlet valve",
        "gpm": 1000,
        "pump_description": "Electric or diesel driven UL/FM listed pump set "
                            "for yard hydrant network.",
    },
}


def _pump_table() -> Dict[str, Any]:
    """Load the pump-spec table, falling back to the hard-coded defaults if
    the YAML is missing or malformed."""
    spec = load_rules(_PUMP_SPECS_FILENAME)
    return spec if spec else _PUMP_FALLBACK


def _resolve_pump(entry: Dict[str, Any], b: Building):
    pst = entry.get("pump_spec_type")
    table = _pump_table()
    cfg = table.get(pst)
    if cfg is None:
        # Unknown spec type — fall through to the legacy if-tree below so the
        # caller still gets a return value, never a None-from-missing-row.
        cfg = _PUMP_FALLBACK.get(pst)
    if cfg is not None and cfg.get("brackets"):
        # Count-dependent duty: standpipes (most tables) or exit stairs
        # (Table 9.24.C.2). `max_standpipes` is the older bracket key.
        field = cfg.get("count_field", "wet_riser_standpipes")
        label = cfg.get("count_label", "standpipe")
        n = getattr(b, field)
        gpm = next((br["gpm"] for br in cfg["brackets"]
                    if n <= br.get("max_count", br.get("max_standpipes", 999))), None)
        if gpm is None:
            gpm = cfg["brackets"][-1].get("gpm", 1000)
        bar  = cfg.get("pressure_bar", 6.9)
        note = cfg.get("pressure_note", "at most remote landing valve")
        desc = cfg.get("pump_description", "")
        cite = cfg.get("source", "")
        return (
            f"{gpm} gpm @ {bar} bar {note}",
            f"Pump sized at {gpm} gpm for {n} {label}{'s' if n != 1 else ''}. {desc}"
            + (f" [Source: {cite}]" if cite else ""),
        )
    if pst in ("fixed_250", "fixed_1000") and cfg is not None:
        gpm  = cfg.get("gpm")
        bar  = cfg.get("pressure_bar")
        note = cfg.get("pressure_note", "")
        desc = cfg.get("pump_description", "")
        return (f"{gpm} gpm @ {bar} bar {note}".strip(), desc)
    # Backward-compatibility fallback - older pump_specs.yaml without `fixed_250`.
    if pst == "fixed_250":
        return ("250 gpm @ 4.5 bar at most remote hose-reel outlet valve",
                "Electric-driven UL/FM listed fire pump set with jockey pump and controller.")
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
            if not detail:
                detail = rdetail
            elif rdetail not in detail:
                detail = f"{detail} {rdetail}"
    return Requirement(
        system=entry["name"], status=status, spec=spec, detail=detail,
        code_ref=entry.get("code_ref") or (branch.get("section") if branch else None),
        page_ref=entry.get("page_ref") or (branch.get("page") if branch else None),
        source_rule=rule_id or (branch.get("id") if branch else None),
        duty=entry.get("duty"),
    )


def _select_branches(branches_list: List[Dict[str, Any]], b: Building) -> List[Dict[str, Any]]:
    """Matching branches, minus any branch that a more specific matching
    branch names in its `suppresses:` list (e.g. Table 9.20.c single-exit
    suppresses the generic Table 9.20.b row for the same building)."""
    matched = [br for br in branches_list if _eval_when(br.get("match", {}), b)]
    suppressed = {sid for br in matched for sid in (br.get("suppresses") or [])}
    return [br for br in matched if br.get("id") not in suppressed]


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
    return _merge_duties(out), selected_id, selected_section, matched


_NUM = r"(\d[\d,]*(?:\.\d+)?)"


def _max_num(text: Optional[str], unit: str) -> float:
    vals = [float(m.group(1).replace(",", ""))
            for m in re.finditer(_NUM + r"\s*" + unit, text or "", re.I)]
    return max(vals) if vals else 0.0


def _duty_key(it: Requirement):
    if it.duty == "pump":
        return (_max_num(it.spec, "gpm"), _max_num(it.spec, "bar"))
    return (_max_num(it.spec, "min"),)


def _merge_duties(items: List[Requirement]) -> List[Requirement]:
    """One fire pump and one fire water tank per building. When branches from
    two code tables both apply (e.g. a highrise warehouse: Table 9.19 and
    Table 9.27), each emits its own `duty: pump` / `duty: tank` line. Keep
    the most onerous one (flow, then pressure; or minutes) and name the
    others in its detail as checked but not governing."""
    groups: Dict[str, List[int]] = {}
    for i, it in enumerate(items):
        if it.duty and it.status == "required":
            groups.setdefault(it.duty, []).append(i)
    drop, replace = set(), {}
    for duty, idx in groups.items():
        if len({items[i].source_rule for i in idx}) < 2:
            continue
        # A line whose flow (or minutes) is not printed as a number, e.g.
        # "2 adjacent deluge zones", cannot be ranked: keep every line.
        if any(_duty_key(items[i])[0] == 0 for i in idx):
            continue
        best = max(idx, key=lambda i: _duty_key(items[i]))
        w = items[best]
        others = [items[i] for i in idx if i != best]
        note = "; ".join(f"{o.spec or o.system} ({o.code_ref})" for o in others)
        what = "pump duty" if duty == "pump" else "tank duration"
        if all(_duty_key(o) == _duty_key(w) for o in others):
            extra = f" The same {what} is also required by: {note}."
        else:
            extra = (f" Governing {what}: more than one code table applies to this "
                     f"building and this is the most onerous. Also checked, not "
                     f"governing: {note}.")
        if duty == "pump":
            hi_bar = max((_max_num(o.spec, "bar") for o in others), default=0.0)
            if hi_bar > _max_num(w.spec, "bar"):
                extra += f" The pump must also meet {hi_bar:g} bar where that table requires it."
        replace[best] = w.model_copy(update={"detail": (w.detail or "") + extra})
        drop.update(i for i in idx if i != best)
    return [replace.get(i, it) for i, it in enumerate(items) if i not in drop]


def _collect_flag(sec: List[Dict[str, Any]], b: Building) -> List[Requirement]:
    out = []
    for rule in sec or []:
        flag = rule.get("flag")
        # A rule fires when (a) its `flag` (if any) is truthy on the building AND
        # (b) its optional `when` clause evaluates true. Rules without a `flag`
        # are skipped unless they explicitly opt in via `always_on: true` (used
        # for conditional general-style aux rules whose match condition cannot
        # be expressed as a single flag, e.g. Table 8.14 items 16/17/20).
        flag_ok = bool(flag and getattr(b, flag, False)) or bool(rule.get("always_on"))
        if not flag_ok:
            continue
        when = rule.get("when")
        if when and not _eval_when(when, b):
            continue
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
    # Table 9.29.A prints "10 m TO 13.5 m", "13.5 m TO 18 m", "18 m TO 30 m": the
    # shared edges 13.5 m and 18 m take the higher band (ruling R11, 12.10.2026).
    # Table 9.29 row M (p.750) applies where the ceiling height EXCEEDS 10 m (CH9C-19).
    if 10 < h < 13.5: return "band_10_13_5"
    if 13.5 <= h < 18: return "band_13_5_18"
    if 18 <= h <= 30: return "band_18_30"
    return None


def _sprinkler_required(items: List[Requirement]) -> bool:
    """True when the building's Ch 9 general rules or table row require an
    automatic sprinkler system (the #4.1.5 / #4.13.1 'fully protected' test)."""
    return any("sprinkler" in (it.system or "").lower() and it.status == "required"
               for it in items)


def building_sprinklered(b: Building, fp_rules: Optional[Dict[str, Any]] = None) -> bool:
    """Ch 2 'sprinkler protected' (Tables 2.3/2.4, 2.6/2.7): the building's Ch 9
    general rules or table row require an automatic sprinkler system."""
    rules = fp_rules if fp_rules is not None else load_rules("ch9_fire_protection.yaml")
    if not rules:
        return False
    gen = _collect_general(rules, b)
    branch_items = _collect_branch(rules.get("branches", []), b)[0]
    return _sprinkler_required(list(gen) + list(branch_items))


def _eval_high_ceiling(rules: Dict[str, Any], b: Building) -> Optional[HighCeilingSpec]:
    hc = rules.get("high_ceiling")
    if not hc: return None
    if not _eval_when(hc.get("trigger", {}), b): return None
    if b.ceiling_height_m <= 10:
        # Table 9.29 row M (p.750): "Where building ceiling height exceeds 10 m".
        return HighCeilingSpec(
            applies=True, not_required=True, ceiling_height_m=b.ceiling_height_m,
            hazard_class=b.hazard_class,
            note=(f"Not required: Table 9.29 row M applies where the building ceiling height "
                  f"exceeds 10 m; this ceiling is {b.ceiling_height_m:g} m."),
            code_ref="Ch 9, #4.13.1 / Table 9.29 row M", page_ref="p.750",
        )
    gen = _collect_general(rules, b)
    branch_items = _collect_branch(rules.get("branches", []), b)[0]
    if not _sprinkler_required(list(gen) + list(branch_items)):
        # Table 9.29.M is a Table 9.29 row: ruling R8 (12.10.2026).
        return HighCeilingSpec(
            applies=True, not_required=True, ceiling_height_m=b.ceiling_height_m,
            hazard_class=b.hazard_class,
            note=("Not required: Table 9.29.M / Table 9.29.A high-ceiling sprinklers extend the "
                  "building sprinkler system (#4.13.1), and this building's table row gives no "
                  "automatic sprinkler system (ruling R8, 12.10.2026)."),
            code_ref="Ch 9, #4.13.1 / Table 9.29.M", page_ref="p.749-750",
        )
    band = _pick_band(b.ceiling_height_m)
    matrix = hc.get("matrix", {}).get(b.hazard_class, {})
    if not band or band not in matrix:
        return HighCeilingSpec(
            applies=True, ceiling_height_m=b.ceiling_height_m, hazard_class=b.hazard_class,
            note="Ceiling height out of tabulated range (Table 9.29.A covers 10-30 m). Use manufacturer's listed high-ceiling design.",
            code_ref=hc.get("code_ref"), page_ref=hc.get("page_ref"),
        )
    p = matrix[band]
    note = hc.get("note")
    if b.ceiling_height_m in (13.5, 18):
        note = (f"{note} " if note else "") + (
            f"A ceiling of exactly {b.ceiling_height_m:g} m sits on a printed band edge; "
            f"the higher band ({p.get('height_range')}) is used (ruling R11, 12.10.2026).")
    return HighCeilingSpec(
        applies=True, ceiling_height_m=b.ceiling_height_m, hazard_class=b.hazard_class,
        height_range=p.get("height_range"), k_factor=p.get("k_factor"),
        min_pressure=p.get("min_pressure"), min_sprinklers=p.get("min_sprinklers"),
        density=p.get("density"), design_area=p.get("design_area"),
        pump_without_hydrant_gpm=p.get("pump_without_hydrant_gpm"),
        pump_with_hydrant_gpm=p.get("pump_with_hydrant_gpm"),
        code_ref=hc.get("code_ref"), page_ref=hc.get("page_ref"), note=note,
    )


# ---------------------------- Owner rulings 12.10.2026, Ch 9 Q1 / Q7 / Q9 ----

_PARKING_OCCS = ("parking_enclosed", "parking_open")


def _robotic_eh2_line() -> Requirement:
    """Owner ruling 12.10.2026, Ch9 Q7: the report states the forced classification."""
    return Requirement(
        system="Hazard Classification - Extra Hazard Group 2 (robotic / mechanical parking)",
        status="required",
        spec="HH, Extra Hazard Group 2 (#1.1.13.5.b: Parking, Group B - robotic, mechanical parking)",
        detail=("Robotic / mechanical parking is ticked. #1.1.13.5.b (p.530) lists 'Parking, "
                "Group B (Robotic, Mechanical parking)' under Extra Hazard, Group 2, so the "
                "sprinkler and storage evaluation uses hazard class HH with Extra Hazard "
                "Group 2, whatever hazard was selected (owner ruling 12.10.2026, Ch9 Q7)."),
        code_ref="Ch 9, #1.1.13.5.b", page_ref="p.530", source_rule="owner_ruling_ch9_q7",
    )


def _gf_bua_sum_not_evaluated_line() -> Requirement:
    """Owner ruling 12.10.2026, Ch9 Q1: a blank plot GF BUA sum is named, never filled."""
    return Requirement(
        system="Sum of GF BUAs on the plot (#4.1.13) - NOT EVALUATED",
        status="required",
        spec="Not evaluated: enter the plot GF BUA sum (#4.1.13)",
        detail=("Table 9.27 row 4 applies where the sum of all ground floor built-up areas "
                "on the plot is more than 3600 m2 (#4.1.13: all buildings on the same plot, "
                "excluding separated service blocks, security guard house and separated "
                "washrooms). The sum was not entered, so the tier is not evaluated: the row 4 "
                "lines below are taken so the result is never under-provided. Enter the sum "
                "(this building's GF BUA when it is the only building on the plot) to fix the "
                "tier (owner ruling 12.10.2026, Ch9 Q1)."),
        code_ref="Ch 9, #4.1.13 / Table 9.27", page_ref="p.695, p.724",
        source_rule="owner_ruling_ch9_q1",
    )


def _storage_hazard_not_evaluated(ch: ChapterReport) -> ChapterReport:
    """Owner ruling 12.10.2026, Ch9 Q9: a secondary storage occupancy with no hazard
    chosen gets no Table 9.27 rows; one required line names the missing hazard."""
    line = Requirement(
        system="Storage / Industrial (secondary occupancy) - Table 9.27 NOT EVALUATED",
        status="required",
        spec="Not evaluated: choose the storage hazard class (LH, OH1, OH2, HH or HH + EH2)",
        detail=("Storage / industrial is listed as a secondary occupancy but its hazard "
                "class was not chosen. Table 9.27 groups A-J depend on the stored materials "
                "and activities (#1.1.13, Tables 9.1 and 9.2), so the tool does not assume "
                "one: the storage Ch 9 lines are not evaluated (owner ruling 12.10.2026, "
                "Ch9 Q9)."),
        code_ref="Ch 9, #1.1.13 / #4.11 / Table 9.27", page_ref="p.526-530, p.724",
        source_rule="owner_ruling_ch9_q9",
    )
    return ch.model_copy(update={
        "blocks": [SectionBlock(title="FP - Branch Requirements (Ch 9)", items=[line])],
        "selected_branch": None, "selected_branch_section": None})


_WATER_REACTIVE_LINE = Requirement(
    system="No Water-Based System Where Water-Reactive Materials Are Stored / Handled",
    status="required",
    spec="#4.1.2: water based fire protection systems shall not be installed or used there",
    detail=("Ch 9 #4.1.2 (p.694): 'Water based fire protection systems shall not be installed "
            "or used where water reactive materials are stored and handled.' The water-based "
            "lines in this report do not apply in those areas; choose their protection from "
            "a detailed analysis of the Material Safety Data Sheet (MSDS) of the materials "
            "(#4.1.1)."),
    code_ref="Ch 9, #4.1.2 / #4.1.1", page_ref="p.694", source_rule="ch9_4_1_2_water_reactive")

_FOAM_PROHIBITED_LINE = Requirement(
    system="Medium- / High-Expansion Foam Not Used on the #4.1.3 Hazards",
    status="required",
    spec="#4.1.3 a-e: no medium- or high-expansion foam on these hazards",
    detail=("Ch 9 #4.1.3 (p.694): 'Medium- and high-expansion foam systems shall not be used "
            "on fires in the following hazards: a. Chemicals, such as cellulose nitrate, that "
            "release sufficient oxygen or other oxidizing agents to sustain combustion. "
            "b. Energized unenclosed electrical equipment c. Water-reactive metals such as "
            "sodium, potassium, and NaK (sodium-potassium alloys) d. Hazardous water-reactive "
            "materials, such as triethyl-aluminum and phosphorus pentoxide e. Liquefied "
            "flammable gas'. Printed because a foam system appears in this report."),
    code_ref="Ch 9, #4.1.3", page_ref="p.694", source_rule="ch9_4_1_3_foam")


def _with_robotic_eh2(b: Building) -> Building:
    """Owner ruling 12.10.2026, Ch9 Q7: robotic / mechanical parking evaluates at HH with
    Extra Hazard Group 2 (#1.1.13.5.b, p.530)."""
    if b.has_robotic_parking and b.occupancy in _PARKING_OCCS and not (
            b.hazard_class == "HH" and b.is_extra_hazard_2):
        return b.model_copy(update={"hazard_class": "HH", "is_extra_hazard_2": True})
    return b


# ---------------------------- Per-chapter evaluators -------------------------

def evaluate_fp(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 9 - Fire Protection."""
    blocks = []
    gen = _dedupe(_collect_general(rules, b))
    branch_items, sel_id, sel_section, _matched = _collect_branch(rules.get("branches", []), b)
    # One yard hydrant line: when the occupancy table already lists yard
    # hydrants (with its own exemption text), the #4.1.4 / #4.1.6 general
    # trigger is folded into that line instead of printing a second one.
    yard = next((i for i, it in enumerate(branch_items)
                 if it.status == "required" and it.system.startswith("Yard Fire Hydrant")), None)
    gen_yard = [it for it in gen if it.system == "Yard Fire Hydrant System"]
    if yard is not None and gen_yard:
        refs = ", ".join(dict.fromkeys(f"{g.code_ref} ({g.page_ref})" for g in gen_yard))
        y = branch_items[yard]
        branch_items[yard] = y.model_copy(update={
            "detail": (y.detail or "") + f" Also triggered by {refs}."})
        gen = [it for it in gen if it not in gen_yard]
    if gen:
        blocks.append(SectionBlock(title="FP - General Requirements (Ch 9, #4.1)", items=gen))

    # Owner ruling 12.10.2026, Ch9 Q7: robotic / mechanical parking is Extra Hazard
    # Group 2 (#1.1.13.5.b, p.530); the building is evaluated at HH + EH2.
    if b.has_robotic_parking and b.occupancy in _PARKING_OCCS:
        blocks.append(SectionBlock(title="FP - Hazard Classification (Ch 9, #1.1.13)", items=[
            _robotic_eh2_line()]))

    # Owner ruling 12.10.2026, Ch9 Q1: the plot GF BUA sum (#4.1.13) is required. A blank
    # sum is taken above 3600 m2 (Table 9.27 row 4, never a lower row) and named here.
    if (b.occupancy == "storage_industrial" and b.storage_gf_bua_sum_missing
            and b.ground_floor_bua_m2 <= 3600
            and any("storage_gf_bua_sum_m2" in str(br.get("match")) for br in _matched)):
        branch_items = [_gf_bua_sum_not_evaluated_line()] + list(branch_items)

    if branch_items:
        blocks.append(SectionBlock(title="FP - Branch Requirements (Ch 9)", items=_dedupe(branch_items)))

    # Determine if matched FP branch + general REQUIRES (status=required) any sprinkler system.
    # Various-locations items annotated with `requires_sprinkler_system: true` are suppressed
    # when the building's branch does not mandate sprinklers (e.g. small villas where
    # sprinklers are only "recommended").
    sprinkler_required = _sprinkler_required(list(gen) + list(branch_items))
    # #4.13.1 (p.749): Table 9.29 extends the building sprinkler system. Ruling R8
    # (12.10.2026): gated rows print a #4.13.1 not_required note in a building whose
    # table row gives no automatic sprinkler system.
    var_rules = rules.get("various_locations") or []
    var_items = _collect_flag(
        [r for r in var_rules if (not r.get("requires_sprinkler_system")) or sprinkler_required], b)
    if not sprinkler_required:
        for it in _collect_flag([r for r in var_rules if r.get("requires_sprinkler_system")
                                 and not r.get("silent_when_unsprinklered")], b):
            var_items.append(Requirement(
                system=it.system, status="not_required",
                detail=("Not required: #4.13.1 extends the building sprinkler system to the "
                        "Table 9.29 locations, and this building's table row gives no automatic "
                        "sprinkler system (ruling R8, 12.10.2026)."),
                code_ref="Ch 9, #4.13.1 / " + (it.code_ref or "").replace("Ch 9, #4.13.1 / ", ""),
                page_ref=it.page_ref, source_rule=it.source_rule))
    var_items = _dedupe(var_items)
    if var_items:
        blocks.append(SectionBlock(title="FP - Various Locations & Extensions (Table 9.29)", items=var_items))

    # #4.1.5 (p.694): Table 9.30 systems apply only when the main building is fully
    # protected. Rooms marked `requires_sprinkler_system` (ruling R14, 12.10.2026) are
    # gated on the same test as Table 9.29 and replaced by a #4.1.5 note otherwise.
    aux_rules = rules.get("auxiliary_rooms", []) or []
    aux_items = _collect_flag(
        [r for r in aux_rules if (not r.get("requires_sprinkler_system")) or sprinkler_required], b)
    if not sprinkler_required:
        for it in _collect_flag([r for r in aux_rules if r.get("requires_sprinkler_system")
                                 and not r.get("silent_when_unsprinklered")], b):
            aux_items.append(Requirement(
                system=it.system, status="not_required",
                detail=("Not required: Table 9.30 systems apply only when the main building is "
                        "fully protected per Tables 9.18 to 9.28 (#4.1.5), and this building's "
                        "table row gives no automatic sprinkler system."),
                code_ref="Ch 9, #4.1.5 / " + (it.code_ref or "").replace("Ch 9, ", ""),
                page_ref="p.694", source_rule=it.source_rule))
    aux_items = _dedupe(aux_items)
    if aux_items:
        blocks.append(SectionBlock(title="FP - Auxiliary Rooms (Table 9.30)", items=aux_items))

    eq_items = _dedupe(_collect_flag(rules.get("equipment", []), b))
    # One room, one system (CH9D-10): a Table 9.31 line that names the same system
    # as a required Table 9.30 line (diesel generator foam sprinklers, 9.30.G = 9.31.E)
    # is already listed in the auxiliary-room block.
    aux_required = {it.system for it in aux_items if it.status == "required"}
    eq_items = [it for it in eq_items if it.system not in aux_required]
    if eq_items:
        blocks.append(SectionBlock(title="FP - Equipment (Table 9.31)", items=eq_items))

    # Audit CH9A-20: #4.1.2 / #4.1.3 prohibitions (p.694).
    prohib = []
    if b.has_water_reactive_materials:
        prohib.append(_WATER_REACTIVE_LINE)
    if any("foam" in f"{it.system} {it.spec or ''}".lower()
           for blk in blocks for it in blk.items if it.status != "not_required"):
        prohib.append(_FOAM_PROHIBITED_LINE)
    if prohib:
        blocks.append(SectionBlock(title="FP - Prohibitions (Ch 9, #4.1.2 / #4.1.3)", items=prohib))

    return ChapterReport(
        chapter_code="FP", chapter_title="Fire Protection (Ch 9)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


def _moe_sprinkler_columns(rules: Dict[str, Any], spr: bool) -> Dict[str, Any]:
    """Owner ruling 12.10.2026, Ch3 Q8 (Table 3.16) and follow-up F7 (Tables 3.15.a and
    3.15.b): a line carrying `spec_s` / `spec_ns` prints only the column of this
    building's Ch 9 result (building_sprinklered, the sprinkler test of ruling R8) and
    names it; a line tagged `sprinkler_column: S|NS` prints only in a building of that
    kind."""
    col = "S" if spr else "NS"
    why = ("Column S (sprinklered) used: Ch 9 requires an automatic sprinkler "
           "system in this building" if spr else
           "Column NS (non-sprinklered) used: Ch 9 does not require an automatic "
           "sprinkler system in this building")
    why += " (the sprinkler test of ruling R8; owner rulings 12.10.2026, Ch3 Q8 and F7)."

    def pick(systems):
        out = []
        for e in systems or []:
            if e.get("sprinkler_column") and e["sprinkler_column"] != col:
                continue
            if "spec_s" in e:
                e = dict(e)
                e["spec"] = (f"Column S (sprinklered): {e['spec_s']}" if spr
                             else f"Column NS (non-sprinklered): {e['spec_ns']}")
                e["detail"] = why + (f" {e['detail']}" if e.get("detail") else "")
            out.append(e)
        return out

    return {**rules,
            "general": [{**g, "systems": pick(g.get("systems"))} for g in rules.get("general", []) or []],
            "branches": [{**br, "systems": pick(br.get("systems"))} for br in rules.get("branches", []) or []]}


def evaluate_moe(b: Building, rules: Dict[str, Any],
                 sprinklered: Optional[bool] = None) -> ChapterReport:
    """Ch 3 - Means of Egress."""
    spr = building_sprinklered(b) if sprinklered is None else sprinklered
    rules = _moe_sprinkler_columns(rules, spr)
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
    # General requirements only fire when an EVC system IS actually required.
    # Determine that from the matched branches' system STATUSES (robust) rather
    # than from a naming convention on the branch id (fragile - a branch like
    # `evc_storage_industrial_small` emits only a not_required item but its id
    # doesn't contain "_not_required", which used to wrongly trigger the full
    # general block for a building that doesn't need EVC).
    branch_items, sel_id, sel_section, matched = _collect_branch(rules.get("branches", []), b)
    evc_required = False
    for br in matched:
        for e in br.get("systems", []):
            if e.get("required", "required") != "not_required":
                evc_required = True
                break
        if evc_required:
            break
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
    # Table 8.13 item 28 PLANT NURSERY (p.508): no FA system is required, so neither the
    # Table 8.1 system lines nor the Table 8.14 / 8.15 lines apply (owner rulings
    # 12.10.2026, Ch8 Q4 and follow-up F1).
    nursery = b.occupancy == "storage_industrial" and b.is_plant_nursery
    gen = [] if nursery else _dedupe(_collect_general(rules, b))
    if gen:
        blocks.append(SectionBlock(title="FA - General Requirements (Ch 8, #3 + #4 / Table 8.1.a)", items=gen))
    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    if branch_items:
        blocks.append(SectionBlock(title="FA - Detection & Alarm by Occupancy / Height (Ch 8, Table 8.13)", items=_dedupe(branch_items)))

    aux = [] if nursery else _dedupe(_collect_flag(rules.get("auxiliary_rooms", []), b))
    if aux:
        blocks.append(SectionBlock(title="FA - Auxiliary Rooms (Ch 8, Table 8.14)", items=aux))

    eq = [] if nursery else _dedupe(_collect_flag(rules.get("equipment", []), b))
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


def build_rule_lookup() -> Dict[str, Dict[str, Any]]:
    """Map source_rule ID -> {'file', 'kind', 'match'} for the UI 'Why triggered?'
    expander. Walks every chapter YAML and indexes general / branches /
    auxiliary_rooms / equipment / addons / various_locations by rule `id`.

    'kind' is one of: 'general' (uses `when:`), 'branch' (uses `match:`),
    'flag-rule' (uses `flag:` and/or `when:` per the engine's _collect_flag).
    """
    lookup: Dict[str, Dict[str, Any]] = {}
    for yf in sorted(RULES_DIR.glob("ch*.yaml")):
        d = load_rules(yf.name)
        for rule in (d.get("general") or []):
            rid = rule.get("id")
            if rid:
                lookup[rid] = {"file": yf.name, "kind": "general",
                               "match": rule.get("when", {}) or {}}
        for rule in (d.get("branches") or []):
            rid = rule.get("id")
            if rid:
                lookup[rid] = {"file": yf.name, "kind": "branch",
                               "match": rule.get("match", {}) or {}}
        for section_key in ("auxiliary_rooms", "equipment", "addons",
                            "various_locations"):
            for rule in (d.get(section_key) or []):
                rid = rule.get("id")
                if not rid:
                    continue
                match: Dict[str, Any] = {}
                if rule.get("flag"):
                    match["flag"] = rule["flag"]
                if rule.get("when"):
                    match["when"] = rule["when"]
                if rule.get("always_on"):
                    match["always_on"] = True
                lookup[rid] = {"file": yf.name, "kind": "flag-rule",
                               "match": match}
    return lookup


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


def _parking_area_not_evaluated() -> ChapterReport:
    """Audit ENG-11: a blank parking area is named, never filled from the basement or
    ground-floor BUA."""
    return ChapterReport(
        chapter_code="PARK", chapter_title="Attached parking (all chapters)",
        blocks=[SectionBlock(title="Attached parking - NOT EVALUATED", items=[Requirement(
            system="Attached Parking Area - NOT EVALUATED",
            status="required",
            spec="Not evaluated: enter the parking footprint area (m2)",
            detail=("'Building has parking' is ticked but the parking footprint area was not "
                    "entered. The parking area sets the Table 9.24 tier and the Ch 10 parking "
                    "area thresholds, so the attached parking is not evaluated until it is "
                    "entered (audit ENG-11: no fallback to the basement or ground-floor BUA)."),
            source_rule="audit_eng_11_parking_area")])])


def evaluate_attached_parking(b: Building) -> List[ChapterReport]:
    """Build a synthetic parking Building (preserving height / parking area) and run every
    chapter against it, returning a per-chapter list. Used to surface parking sub-occupancy
    requirements when the main occupancy is non-parking but has an in-building parking area.

    The PARKING AREA (parking_area_m2) drives Ch 10 SC area-based thresholds (e.g. 3600 m^2
    make-up-air exception for enclosed parking; 4000 m^2 small-vs-large open parking split).
    Audit ENG-11: a blank parking area is NOT EVALUATED (no fallback), and every yes/no
    flag the user set carries over, so an unticked room is never brought back by a schema
    default.
    """
    if b.parking_area_m2 <= 0:
        return [_parking_area_not_evaluated()]
    synth_occ = "parking_open" if b.attached_parking_kind == "open" else "parking_enclosed"
    parking_area = b.parking_area_m2
    # Every user flag (bool) carries over (audit ENG-11); areas, uses and mixed-occupancy
    # inputs are the parking's own.
    flags = {k: v for k, v in b.model_dump().items()
             if isinstance(v, bool) and k in Building.model_fields}
    flags.update(
        # Owner ruling 12.10.2026, Ch9 Q7: robotic / mechanical parking = HH + EH2 (#1.1.13.5.b).
        is_extra_hazard_2=b.has_robotic_parking,
        # Only the parent building's own flags that make it a different occupancy are off.
        mercantile_multi_tenant=False, villa_converted_use=False,
        has_water_reactive_materials=False,
    )
    synth = Building(
        **flags,
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
        hazard_class="HH" if b.has_robotic_parking else "OH1",   # #1.1.13.2 (p.528): parking garages, open or enclosed
        ceiling_height_m=b.ceiling_height_m,
        # Table 9.24 inputs: standpipes (A.3), exit stairs (C.2), robotic (B),
        # covered/shaded (D); pump level for Table 9.19 zoning.
        wet_riser_standpipes=b.wet_riser_standpipes,
        exit_stairs=b.exit_stairs,
        tunnel_kind=b.tunnel_kind, tunnel_length_m=b.tunnel_length_m,
    )
    chapters = []
    moe_rules = load_rules("ch3_means_of_egress.yaml")
    fe_rules  = load_rules("ch4_fire_extinguishers.yaml")
    es_rules  = load_rules("ch5_exit_signs.yaml")
    el_rules  = load_rules("ch6_emergency_lighting.yaml")
    fa_rules  = load_rules("ch8_fire_alarm.yaml")
    fp_rules  = load_rules("ch9_fire_protection.yaml")
    sc_rules  = load_rules("ch10_smoke_control.yaml")
    # Attached parking takes the S / NS column from the parent building's Ch 9 result
    # (owner ruling 12.10.2026, follow-up F8): it shares the parent's sprinkler system.
    if moe_rules: chapters.append(evaluate_moe(synth, moe_rules,
                                               sprinklered=building_sprinklered(b)))
    if fe_rules:  chapters.append(evaluate_fe(synth, fe_rules))
    if es_rules:  chapters.append(evaluate_es(synth, es_rules))
    if el_rules:  chapters.append(evaluate_el(synth, el_rules))
    if fa_rules:  chapters.append(evaluate_fa(synth, fa_rules))
    if fp_rules:  chapters.append(evaluate_fp(synth, fp_rules))
    if sc_rules:  chapters.append(evaluate_sc(synth, sc_rules))
    return chapters


# ---------------------------- Empty-chapter explanatory note -----------------
# When a chapter produces NO requirements at all (e.g. Smoke Control for a
# lowrise villa), the report section would otherwise be silently blank. Instead
# we append a single explanatory "not required" item so every section always
# states why it has nothing to show. `{tier}` / `{occ}` are filled per building.
_EMPTY_CHAPTER_NOTES = {
    "MOE": ("Means of Egress - Not Triggered",
            "No occupancy-specific means-of-egress requirements were triggered "
            "for this {tier} {occ} building. General egress provisions still "
            "apply - refer to UAE FLSC Ch 3."),
    "FE":  ("Fire Extinguishers - Not Triggered",
            "No fire-extinguisher requirements were triggered for this "
            "building configuration."),
    "ES":  ("Exit Signs Not Required",
            "Exit signs are not required for this {occ} building per UAE FLSC "
            "Ch 5 Table 5.3 - private villas are exempt unless the building is "
            "converted to another use."),
    "EL":  ("Emergency Lighting Not Required",
            "Emergency lighting is not required for this {tier} {occ} building "
            "per UAE FLSC Ch 6 Table 6.5."),
    "EVC": ("Emergency Voice Evacuation Not Required",
            "Emergency Voice Evacuation and Two-way Telephone systems are not "
            "required - UAE FLSC Ch 7 Table 7.3 does not list this occupancy "
            "or height tier."),
    "FA":  ("Fire Detection & Alarm - Not Triggered",
            "No fire detection & alarm requirements were triggered for this "
            "building configuration."),
    "FP":  ("Fire Protection - Not Triggered",
            "No fire-protection requirements were triggered for this "
            "building configuration."),
    "SC":  ("Smoke Control Not Required",
            "Smoke control / smoke management systems are NOT required for "
            "this {tier} {occ} building. UAE FLSC Ch 10 mandates smoke control "
            "only for: highrise and super-highrise buildings (23 m and above); "
            "special occupancies (hospitals, malls, educational, assembly); "
            "deep basements and underground areas (more than 7 m below grade "
            "or more than 2 basements); enclosed parking; atria; tunnels; and "
            "large assembly halls. None of these conditions apply to the "
            "current building profile, so a smoke control system is not "
            "required - natural ventilation per Ch 10 Section 2.15 applies "
            "where an accessible external facade or roof is available."),
    "LPG": ("No Gas System Present",
            "No LPG or gas-system requirements - no gas system is present in "
            "this building."),
}

_CHAPTER_CODE_REF = {
    "FSA": "UAE FLSC 2018 Ch 2",
    "MOE": "UAE FLSC 2018 Ch 3",  "FE": "UAE FLSC 2018 Ch 4",
    "ES":  "UAE FLSC 2018 Ch 5",  "EL": "UAE FLSC 2018 Ch 6",
    "EVC": "UAE FLSC 2018 Ch 7",  "FA": "UAE FLSC 2018 Ch 8",
    "FP":  "UAE FLSC 2018 Ch 9",  "SC": "UAE FLSC 2018 Ch 10",
    "LPG": "UAE FLSC 2018 Ch 11",
    "ACC": "UAE FLSC 2018 Ch 15",
    "EAP": "UAE FLSC 2018 Ch 19",
}


def _ensure_chapter_not_blank(ch: ChapterReport, b: Building) -> None:
    """If a chapter produced no requirement items, append an explanatory
    'not required' block so the report section is never silently empty."""
    if sum(len(blk.items) for blk in ch.blocks) > 0:
        return
    system, detail_tpl = _EMPTY_CHAPTER_NOTES.get(
        ch.chapter_code,
        (f"{ch.chapter_code} - Not Triggered",
         "No requirements were triggered for this building configuration."),
    )
    tier = b.height_class.replace("_", "-")
    detail = detail_tpl.format(tier=tier, occ=b.occupancy.replace("_", " "))
    ch.blocks.append(SectionBlock(
        title=f"{ch.chapter_code} - Status",
        items=[Requirement(
            system=system,
            status="not_required",
            detail=detail,
            code_ref=_CHAPTER_CODE_REF.get(ch.chapter_code),
        )],
    ))



def _mixed_occupancy_note(b: Building) -> Optional[str]:
    if not b.secondary_occupancies and b.mixed_occupancy_mode == "none":
        return None
    secs = ", ".join(b.secondary_occupancies) if b.secondary_occupancies else "(none listed)"
    if b.mixed_occupancy_mode == "separated":
        return (
            f"Mixed occupancy treated as SEPARATED (Ch 1 #2.5). Secondary: {secs}. "
            "Provide fire-barrier ratings per Table 1.2 between occupancy compartments."
        )
    if b.mixed_occupancy_mode == "most_restrictive" and b.secondary_occupancies:
        return (
            f"Mixed occupancy treated as MOST RESTRICTIVE (Ch 1 #2.4.4, p.55). Secondary: {secs}. "
            f"Every listed occupancy is evaluated and the most onerous line per system is kept; "
            f"lines brought by a secondary occupancy say so (ruling R13, 12.10.2026). "
            f"Hazard class used: {b.hazard_class} (the highest of those listed)."
        )
    if b.mixed_occupancy_mode == "most_restrictive":
        return ("Mixed occupancy mode is MOST RESTRICTIVE but no secondary occupancy is listed: "
                "the report covers the primary occupancy only. List the other occupancies to "
                "apply Ch 1 #2.4.4.")
    if b.secondary_occupancies:
        return (f"Secondary occupancies listed ({secs}) but the mixed occupancy mode is not set: "
                "they are not evaluated. Choose MOST RESTRICTIVE or SEPARATED.")
    return None


_STATUS_RANK = {"required": 3, "conditional": 2, "recommended": 1, "not_required": 0}
_HAZARD_RANK = {"LH": 0, "OH1": 1, "OH2": 2, "HH": 3}


def _merge_most_restrictive(runs: List[tuple]) -> List[ChapterReport]:
    """Ruling R13 (12.10.2026), Ch 1 #2.4.4 (p.55): a mixed occupancy takes the most
    restrictive requirements of the occupancies involved. `runs` is a list of
    (occupancy, chapters) with the primary occupancy first. Per chapter and block:
    - one line per system name at its most onerous status (required > conditional >
      recommended > not_required); lines of that status with different specs are all
      kept, each naming its occupancy, because the tool cannot rank free text (the same
      spec keeps the first occupancy's wording, primary first);
    - an occupancy whose block holds only not_required lines is dropped from that block
      when another occupancy requires something there (e.g. EVC not required for
      business, required for a hotel);
    - one governing fire pump and fire water tank line (`duty`), as for one building;
    - a line that only a secondary occupancy brings says so."""
    primary_occ, primary = runs[0]
    out = []
    for ci, ch in enumerate(primary):
        others = [(occ, chs[ci]) for occ, chs in runs[1:]]
        titles, by_title = [], {}
        for occ, c in [(primary_occ, ch)] + others:
            for blk in c.blocks:
                if blk.title not in by_title:
                    titles.append(blk.title)
                    by_title[blk.title] = []
                by_title[blk.title].append((occ, blk.items))
        blocks = []
        for t in titles:
            contrib = by_title[t]
            block_req = any(it.status != "not_required" for _, its in contrib for it in its)
            tagged = [(occ, it) for occ, its in contrib
                      if not (block_req and all(i.status == "not_required" for i in its))
                      for it in its]
            names, groups = [], {}
            for occ, it in tagged:
                if it.system not in groups:
                    names.append(it.system)
                    groups[it.system] = []
                groups[it.system].append((occ, it))
            items = []
            for n in names:
                g = groups[n]
                top = max(_STATUS_RANK[it.status] for _, it in g)
                g = [(o, it) for o, it in g if _STATUS_RANK[it.status] == top]
                specs = {}
                for o, it in g:
                    specs.setdefault(it.spec, (it, []))[1].append(o)
                for it, occs in specs.values():
                    if primary_occ not in occs or len(specs) > 1:
                        it = it.model_copy(update={"detail": (it.detail + " " if it.detail else "") + (
                            f"[Mixed occupancy, most restrictive (ruling R13): from {', '.join(occs)}.]")})
                    items.append(it)
            blocks.append(SectionBlock(title=t, items=_merge_duties(items)))
        sec = ch.selected_branch_section
        extra = "; ".join(f"{occ}: {c.selected_branch}" for occ, c in others if c.selected_branch)
        if extra:
            sec = f"{sec or ''} + most restrictive with {extra} (ruling R13)".strip()
        out.append(ch.model_copy(update={"blocks": blocks, "selected_branch_section": sec}))
    return out


def evaluate(b: Building) -> ComplianceReport:
    """Ruling R13 (12.10.2026): in most_restrictive mixed mode every listed occupancy is
    evaluated on the same building, at the highest hazard class of those listed, and the
    chapters are merged keeping the most onerous line per system."""
    if b.mixed_occupancy_mode == "most_restrictive" and b.secondary_occupancies:
        occs = [b.occupancy] + [o for o in dict.fromkeys(b.secondary_occupancies) if o != b.occupancy]
        # Owner rulings 12.10.2026: a secondary storage occupancy brings the hazard chosen
        # for it, never a default (Ch9 Q9); robotic / mechanical parking brings HH + EH2
        # (Ch9 Q7).
        sec_hz = [_secondary_hazard(o, b) for o in occs[1:]]
        hz_all = [b.hazard_class] + [h for h in sec_hz if h]
        eh2 = b.is_extra_hazard_2
        if b.has_robotic_parking and any(o in _PARKING_OCCS for o in occs):
            hz_all.append("HH")
            eh2 = True
        if "storage_industrial" in occs[1:] and b.secondary_storage_hazard == "EH2":
            eh2 = True
        hz = max(hz_all, key=lambda h: _HAZARD_RANK[h])
        base = b.model_copy(update={"hazard_class": hz, "is_extra_hazard_2": eh2 and hz == "HH"})
        single = lambda o: base.model_copy(update={"occupancy": o, "secondary_occupancies": [],
                                                   "mixed_occupancy_mode": "none"})
        reps = [_evaluate_single(single(o)) for o in occs]
        note = _mixed_occupancy_note(base)
        storage_missing = "storage_industrial" in occs[1:] and b.secondary_storage_hazard is None
        if storage_missing:
            i = occs.index("storage_industrial")
            reps[i] = reps[i].model_copy(update={"chapters": [
                _storage_hazard_not_evaluated(c) if c.chapter_code == "FP" else c
                for c in reps[i].chapters]})
            note = (note or "") + (
                f" Storage / industrial hazard class not chosen: its Table 9.27 lines are NOT "
                f"EVALUATED, and its other chapters use {hz}, the highest class of the other "
                f"occupancies (owner ruling 12.10.2026, Ch9 Q9).")
        r0 = reps[0]
        return r0.model_copy(update={
            "building": base,
            "chapters": _merge_most_restrictive([(o, r.chapters) for o, r in zip(occs, reps)]),
            "requires_wet_riser": any(r.requires_wet_riser for r in reps),
            "mixed_occupancy_note": note,
        })
    return _evaluate_single(b)


def _secondary_hazard(o: str, b: Building) -> Optional[str]:
    """Hazard class a secondary occupancy brings to the R13 most-restrictive run.
    Storage / industrial: the class chosen for it, None when not chosen (owner ruling
    12.10.2026, Ch9 Q9). Robotic / mechanical parking: HH (Ch9 Q7)."""
    if o == "storage_industrial":
        h = b.secondary_storage_hazard
        return None if h is None else ("HH" if h == "EH2" else h)
    if o in _PARKING_OCCS and b.has_robotic_parking:
        return "HH"
    return default_hazard(o)


def _evaluate_single(b: Building) -> ComplianceReport:
    b = _with_robotic_eh2(b)   # owner ruling 12.10.2026, Ch9 Q7
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

    wet = _branch_requires_wet_riser(fp_rules, b)
    spr = building_sprinklered(b, fp_rules)
    chapters.append(evaluate_fire_access(b, requires_wet_riser=wet, sprinklered=spr))

    # MOE -> FE -> ES -> EL -> EVC -> FA -> FP -> SC -> LPG - chapter-number order.
    if moe_rules:
        chapters.append(evaluate_moe(b, moe_rules, sprinklered=spr))
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

    # Ch 15 Accessibility + Ch 19 EAP (light modules)
    chapters.append(evaluate_accessibility(b))
    chapters.append(evaluate_eap(b))

    for ch in chapters:
        for blk in ch.blocks:
            blk.items = _dedupe(blk.items)

    # Attached parking sub-evaluation: when the main occupancy is NOT itself parking
    # but the building has an in-building parking area, run a parallel evaluation
    # using a synthetic parking Building so all parking-specific requirements surface.
    attached = []
    if b.has_parking_area and b.occupancy not in ("parking_enclosed", "parking_open", "infrastructure"):
        try:
            attached = evaluate_attached_parking(b)
        except ValueError as e:
            # Never dropped silently: the refusal is named (audit ENG-11).
            nev = _parking_area_not_evaluated()
            it = nev.blocks[0].items[0]
            nev.blocks[0].items[0] = it.model_copy(update={
                "spec": "Not evaluated: the parking inputs were refused",
                "detail": f"The attached parking could not be evaluated: {e}"})
            attached = [nev]

    # Never leave a report section silently blank — append an explanatory
    # "not required" note to any chapter that produced zero requirements.
    for ch in chapters:
        _ensure_chapter_not_blank(ch, b)
    for ch in attached:
        _ensure_chapter_not_blank(ch, b)

    ol = compute_occupant_load(b)
    fa_summary = compute_fire_access(b, requires_wet_riser=wet, sprinklered=spr)

    return ComplianceReport(
        building=b,
        chapters=chapters,
        requires_wet_riser=wet,
        high_ceiling=_eval_high_ceiling(fp_rules, b),
        attached_parking_chapters=attached,
        occupant_load=ol,
        fire_access=fa_summary,
        mixed_occupancy_note=_mixed_occupancy_note(b),
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
        band_txt = "not applied" if hc.not_required else (hc.height_range or "out of range")
        L.append(f"- Ceiling height: **{hc.ceiling_height_m} m** | Hazard: **{hc.hazard_class}** | Band: {band_txt}")
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

    # Mandatory disclaimer footer
    from flsc_schema import DISCLAIMER as _DISCLAIMER
    L.append("---")
    L.append("")
    L.append(f"_{_DISCLAIMER}_")
    L.append("")

    return "\n".join(L)


if __name__ == "__main__":
    b = Building(occupancy="hotel_a", height_m=55, floors_above_grade=18,
                 floors_below_grade=2, ground_floor_bua_m2=1200, plot_area_m2=5000,
                 hazard_class="LH", wet_riser_standpipes=3,
                 has_main_electrical_room=True, has_diesel_generator_room=True,
                 has_amusement_confounding=False)
    print(report_to_markdown(evaluate(b)))
