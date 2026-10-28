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
from contextvars import ContextVar
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Tuple

import yaml

from flsc_schema import (
    Building, ChapterReport, ComplianceReport, HighCeilingSpec,
    Requirement, SectionBlock, occupancy_group, default_hazard, ANIMAL_HOUSING_GROUPS,
    MERCANTILE_C_TYPES,
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
        "pump_description": "",
        "brackets": [{"max_standpipes": 2, "gpm": 750},
                     {"max_standpipes": 999, "gpm": 1000}],
    },
    "fixed_1000": {
        "source": "UAE FLSC 2018 Table 9.26 A.vi (p.723); Table 9.23.B.2 ii (p.717)",
        "pressure_bar": 6.9,
        "pressure_note": "at most remote hydrant outlet valve",
        "gpm": 1000,
        "pump_description": "Yard hydrant duty (Table 9.26 A.vi, p.723).",
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
                "Table 9.23 item v (p.716-717).")
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
    out, tags = [], []
    selected_id = None
    selected_section = None
    for br in matched:
        if selected_id is None:
            selected_id = br["id"]
            selected_section = br.get("section")
        for e in br.get("systems", []):
            out.append(_as_req(e, branch=br, b=b))
            tags.append((e.get("merge_system"), br.get("merge_family"))
                        if e.get("merge_system") and br.get("merge_family") else None)
    return _merge_duties(_merge_tables(out, tags)), selected_id, selected_section, matched


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


# Owner ruling 12.10.2026, P3 App Q6: a parking building of 23 m or more takes Table 9.18 /
# 9.19 (#4.2.1 / #4.3.1, "of any occupancy classification") and Table 9.24 (#4.8.1). As
# ruling R6 did for tall malls, one line per system is printed: the most onerous, citing
# both tables. Lines carry `merge_system` and their branch `merge_family` in the YAML.
_MERGE_FAMILY_RANK = {"tall": 2, "parking": 1}
_MERGE_WHY = {
    "sprinkler": ("Table 9.18 / 9.19 sprinklers run throughout the building including "
                  "basements and podiums (open as well as closed), which includes the "
                  "Table 9.24 sprinklers throughout the parking structure."),
    "wet_riser": ("Table 9.18 / 9.19 wet risers run throughout the building and are "
                  "interconnected at the lowest and the highest level of each zone (next line), "
                  "which includes the Table 9.24 interconnection at the highest level."),
}


def _merge_tables(items: List[Requirement], tags: List[Optional[tuple]]) -> List[Requirement]:
    """P3 App Q6: one sprinkler, wet riser, fire pump and fire water tank line when lines of
    both the tall-building family (Tables 9.18 / 9.19) and the parking family (Table 9.24)
    are required. Pump / tank: the most onerous flow then pressure, or minutes (ties keep
    the tall-building line); a pump whose flow is not a printed number (robotic deluge) is
    not ranked and every line stays, as in `_merge_duties`. Sprinkler / wet riser: the
    tall-building line. The kept line cites every table and quotes what the others say."""
    groups: Dict[str, List[int]] = {}
    for i, (it, tag) in enumerate(zip(items, tags)):
        if tag and it.status == "required":
            groups.setdefault(tag[0], []).append(i)
    drop, replace = set(), {}
    for kind, idx in groups.items():
        if len({tags[i][1] for i in idx}) < 2:
            continue
        numeric = kind in ("pump", "tank")
        key = (lambda i: _duty_key(items[i].model_copy(update={"duty": kind}))) if numeric \
            else (lambda i: ())
        if numeric and any(key(i)[0] == 0 for i in idx):
            continue
        best = max(idx, key=lambda i: (key(i), _MERGE_FAMILY_RANK.get(tags[i][1], 0), -i))
        w, others = items[best], [items[i] for i in idx if i != best]
        refs = list(dict.fromkeys([w.code_ref] + [o.code_ref for o in others]))
        pages = list(dict.fromkeys(p for p in [w.page_ref] + [o.page_ref for o in others] if p))
        also = " ".join(
            f"Also required by {o.code_ref}: {o.system}" + (f", {o.spec}" if o.spec else "")
            + (f" - {o.detail}" if o.detail else ".") for o in others)
        why = _MERGE_WHY.get(kind, "")
        extra = (f" One line per system (owner ruling 12.10.2026, P3 App Q6, merged as ruling "
                 f"R6 for tall malls): a parking building of 23 m or more takes Table 9.18 / "
                 f"9.19 (#4.2.1 / #4.3.1, any occupancy) and Table 9.24 (#4.8.1); this line is "
                 f"the most onerous.{(' ' + why) if why else ''} {also}")
        if kind == "pump":
            hi_bar = max((_max_num(o.spec, "bar") for o in others), default=0.0)
            if hi_bar > _max_num(w.spec, "bar"):
                extra += f" The pump must also meet {hi_bar:g} bar where that table requires it."
        replace[best] = w.model_copy(update={
            "detail": (w.detail or "") + extra, "code_ref": " + ".join(r for r in refs if r),
            "page_ref": ", ".join(pages) or w.page_ref})
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
    kiosk = _collect_flag(rules.get("kiosk_item_48", []), b)   # Table 1.9 item 48 iii
    return _sprinkler_required(list(gen) + list(branch_items) + list(kiosk))


def _fa_row_automatic_detection(b: Building, fa_rules: Dict[str, Any]) -> bool:
    """One occupancy: its Table 8.13 row (the Ch 8 branch lines) requires an automatic
    detection system. Enclosed parking (item 22, p.506, open parking by analogy, ruling
    R10): fully sprinklered = no fire detectors, a Manual Fire Detection and Alarm System
    (items i-ii); not sprinklered = a Heat Detection and Alarm System (item iii)."""
    for it in _collect_branch(fa_rules.get("branches", []), b)[0]:
        if it.status != "required":
            continue
        name = (it.system or "").lower()
        if name.startswith("conditional fa system"):
            if not building_sprinklered(b):
                return True
        elif ("detection" in name or "aspiration" in name) and "manual" not in name:
            return True
    return False


def fa_automatic_detection_required(b: Building, fa_rules: Optional[Dict[str, Any]] = None) -> bool:
    """Ch 8 result read-only (no FA line is changed): the building's Table 8.13 row
    requires an automatic fire detection and alarm system. Not required for a plant
    nursery (item 28, p.508) or a sprinklered enclosed / open parking (item 22 i-ii,
    p.506). Under ruling R13 most restrictive, any listed occupancy that requires it
    counts. Used by the Ch 11 #3.2.2 flame-effect stop (owner ruling 12.10.2026, P3
    follow-up F-a1-3)."""
    rules = fa_rules if fa_rules is not None else load_rules("ch8_fire_alarm.yaml")
    if not rules:
        return False
    occs = [b.occupancy]
    if b.mixed_occupancy_mode == "most_restrictive":
        occs += [o for o in dict.fromkeys(b.secondary_occupancies) if o != b.occupancy]
    return any(_fa_row_automatic_detection(
        b if o == b.occupancy else b.model_copy(update={
            "occupancy": o, "secondary_occupancies": [], "mixed_occupancy_mode": "none"}),
        rules) for o in occs)


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


def _animal_group_not_evaluated(ch: ChapterReport) -> ChapterReport:
    """Owner ruling 12.10.2026, P3 Storey Q4 (as Ch9 Q9 for storage): a secondary animal
    housing occupancy with no group chosen gets no Ch 9 lines of its own; one required
    line names the missing group."""
    line = Requirement(
        system="Animal Housing (secondary occupancy) - Ch 9 NOT EVALUATED",
        status="required",
        spec="Not evaluated: choose the animal housing group (A, B or C)",
        detail=("Animal housing is listed as a secondary occupancy but its group was not "
                "chosen. The group sets the hazard class (#1.1.13: Group A animal market, pet "
                "shops, bird market, veterinary clinic and Group C zoo are Light Hazard, "
                "#1.1.13.1.q, r, p.528; Group B stable, animal sheds, livestock shelter, "
                "slaughter houses is Ordinary Hazard Group 2, #1.1.13.3.a, p.529), so the tool "
                "does not assume one: the animal housing Ch 9 lines are not evaluated (owner "
                "ruling 12.10.2026, P3 Storey Q4)."),
        code_ref="Ch 9, #1.1.13", page_ref="p.528-529",
        source_rule="owner_ruling_p3_storey_q4",
    )
    return ch.model_copy(update={
        "blocks": [SectionBlock(title="FP - Branch Requirements (Ch 9)", items=[line])],
        "selected_branch": None, "selected_branch_section": None})


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

# Owner ruling 13.10.2026 (CH9D-15, "Pointer lines"): Ch 9 Section 5 (p.758-769) is
# reported as one line per required system type, naming its acceptance test, inspection
# and maintenance table; the table rows are not itemised.
_ITM_TABLES = (
    # (key, system label, table, clause, page range, standards as printed, name keywords)
    ("pump", "Fire Pumps", "Table 9.32", "#5.5.1", "p.759-761",
     "Manufacturer's instruction manual, NFPA 20 and NFPA 25", ("fire pump", "pump set")),
    ("standpipe", "Standpipe and Hose Systems (Dry/Wet Risers)", "Table 9.33", "#5.6.1",
     "p.762-763", "NFPA 14 and NFPA 25",
     ("riser", "standpipe", "landing valve", "hose reel")),
    ("sprinkler", "Sprinkler and Deluge Systems", "Table 9.34", "#5.7.1", "p.764-765",
     "NFPA 13, NFPA 15 and NFPA 25", ("sprinkler", "deluge", "water spray", "pre-action")),
    ("foam", "Foam Systems", "Table 9.35", "#5.8.1", "p.766-767",
     "NFPA 13, NFPA 11, NFPA 16 and NFPA 25", ("foam",)),
    ("clean_agent", "Clean Agent Systems", "Table 9.36", "#5.9.1", "p.768-769",
     "NFPA 2001, and Manufacturer's guidelines", ("clean agent",)),
)


def _itm_lines(blocks) -> List[Requirement]:
    """One Section 5 pointer line per system type that a required Ch 9 line names. A line
    offering alternatives ("Clean Agent OR Deluge Water Spray") points to each table, for
    the option installed."""
    names = [(it.system or "").lower() for blk in blocks for it in blk.items
             if it.status == "required"]
    out = []
    for _key, label, table, clause, pages, stds, words in _ITM_TABLES:
        hits = [n for n in names if any(w in n for w in words) and "extinguisher" not in n]
        if not hits:
            continue
        optional = all(" or " in n for n in hits)
        out.append(Requirement(
            system=f"Acceptance Test, Inspection and Maintenance - {label}",
            status="required",
            spec=(f"{clause}: inspected and maintained to {table} as the minimum guideline; "
                  f"detailed acceptance, inspection tests and maintenance per {stds}"
                  + (" (for the option installed)" if optional else "")),
            detail=(f"Ch 9 Section 5, {table} ({pages}); rows not itemised in this report "
                    "(owner ruling 13.10.2026, CH9D-15). #5.3 (p.758): inspection and "
                    "acceptance are the main consultant's responsibility. #5.4.1 (p.758): the "
                    "building owner, his appointed representative and the facility management "
                    "ensure the systems are inspected regularly, maintained and repaired."),
            code_ref=f"Ch 9, {clause} / {table}", page_ref=pages,
            source_rule=f"itm_{_key}"))
    return out


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


_P4_Q4_NOTE = (" Mercantile Group C (kiosks) is not listed in Table 9.21.b (p.707-708); this "
               "row is applied by inference from its midrise twin, Table 9.20.b row C "
               "MERCANTILE GROUP C (KIOSKS), p.701 (owner ruling 13.10.2026, P4 Q4).")


# ---------------------------- Fix round 28.10.2026 (ch9) ----------------------

# Audit CH9B2-01 / 06 / 07 (H9): every governing fire pump line states the pump set the
# code prints for every water-based system (Table 9.3, p.567-568), never "electric or
# diesel"; and #4.1.9 (audit F9A-12).
_PUMP_SET_NOTE = (
    " Fire pump set: 1 electric driven fire pump, 1 diesel driven fire pump and 1 jockey "
    "pump, complete with controllers (Table 9.3 item 1.xii, p.567; Tables 9.5 / 9.6 / 9.7 "
    "item 3.i, p.580 / p.582 / p.589); the diesel fire pump has 8 hour operating capacity "
    "(Table 9.3 item 2.iii, p.568). The pump set is located at the lowest level of the system "
    "in the building, or from the lowest level of the building to the ground floor level with "
    "fire access (Table 9.3 item 1.xv, p.568); pump room location and size per Ch 1 Table "
    "1.9.2 (items 1.xi / 1.xvi); primary power to the electric fire pump and the jockey pump "
    "directly from the power utility company, in a dedicated distribution board inside the "
    "pump room (item 2.i). Fire pumps are dedicated to and listed for fire protection "
    "service, tested as an assembly, and registered and listed by Civil Defence (Table 9.3 "
    "items 1.ii-1.iii, p.567; #6.1.1 and #6.1.3, p.770). Pump capacities in Section 4 are "
    "minimum guidelines and may vary; they shall be verified with the Civil Defence "
    "engineers (#4.1.9, p.694).")

# Audit CH9B2-21 (INFO): Dubai pump verification, not part of the 2018 code.
_ESL_NOTE = (
    " Dubai projects (not part of the 2018 code): fire pumps with a 500 US gpm capacity and "
    "above are to be certified by a UAE approved certification body and verified for the "
    "particular project by ESL (Emirates Safety Laboratory), whose verification certificate "
    "is submitted to DCD (ESL information pack 'Fire Pumps - DXB New Regulation', "
    "commencement Jan 2024; taken from a scanned copy, confirm against the issued document).")


def _with_pump_set_note(items: List[Requirement]) -> List[Requirement]:
    out = []
    for it in items:
        if it.duty == "pump" and it.status == "required" and \
                "Table 9.3 item 1.xii" not in (it.detail or ""):
            extra = _PUMP_SET_NOTE + (_ESL_NOTE if _max_num(it.spec, "gpm") >= 500 else "")
            it = it.model_copy(update={"detail": (it.detail or "") + extra})
        out.append(it)
    return out


def _system_kinds(name: Optional[str]) -> set:
    """The system kinds a line names, for the required / not-required reconciliation."""
    n = (name or "").lower()
    if "extinguisher" in n:
        return set()
    kinds = set()
    if "sprinkler" in n:
        kinds.add("sprinkler")
    if "wet riser" in n or "internal landing valve" in n:
        kinds.add("wet_riser")
    if "dry riser" in n or "dry landing valve" in n:
        kinds.add("dry_riser")
    if "hose reel" in n:
        kinds.add("hose_reel")
    if n.startswith("fire pump"):
        kinds.add("pump")
    if n.startswith("fire water tank"):
        kinds.add("tank")
    if "yard" in n and "hydrant" in n:
        kinds.add("yard_hydrant")
    return kinds


_TALL_RULES = ("superhighrise_", "highrise_")


def _reconcile_not_required(gen: List[Requirement], branch: List[Requirement]):
    """Audit CH9B2-05 and the 28.10.2026 sweep (systemic class 3): when two code tables apply
    to one building, a line one table prints 'not required' beside a required line of the
    same system from another table is dropped; the required line governs (the most onerous)
    and names it. E.g. Table 9.19 wet riser vs Table 9.27 row 4 'wet risers not required';
    a highrise or G+4 plant nursery (Group V) vs the height row or #4.1.7; the hazard-class
    rows vs a specialty group (owner ruling R-G)."""
    allitems = list(gen) + list(branch)
    notes: Dict[int, List[str]] = {}
    drop = set()
    for i, it in enumerate(allitems):
        if it.status != "not_required":
            continue
        kinds = _system_kinds(it.system)
        if not kinds:
            continue
        cover = {}
        for j, other in enumerate(allitems):
            if other.status != "required" or other.source_rule == it.source_rule:
                continue
            for k in kinds & _system_kinds(other.system):
                cover.setdefault(k, j)
        if not cover:
            continue
        drop.add(i)
        j = cover[sorted(cover)[0]]
        gov = allitems[j]
        why = ("Tables 9.18 / 9.19 apply to buildings of any occupancy of 23 m or more (#4.2.1 / "
               "#4.3.1) and govern" if (gov.source_rule or "").startswith(_TALL_RULES)
               else "the required line governs")
        notes.setdefault(j, []).append(
            f" {it.code_ref or it.source_rule} ({it.page_ref}) prints '{it.system}' as not "
            f"required; more than one code table applies to this building and {why} (the most "
            f"onerous is kept, audit CH9B2-05, 28.10.2026).")
    if not drop:
        return list(gen), list(branch)
    fixed = [it.model_copy(update={"detail": (it.detail or "") + "".join(notes[i])})
             if i in notes else it for i, it in enumerate(allitems)]
    keep = [(i, it) for i, it in enumerate(fixed) if i not in drop]
    n = len(gen)
    return [it for i, it in keep if i < n], [it for i, it in keep if i >= n]


def _high_ceiling_pump_line(b: Building, rules: Dict[str, Any],
                            items: List[Requirement]) -> Optional[Requirement]:
    """Audit CH9B2-02 (H10): the Table 9.29.A pump enters the governing pump merge. The
    'with hydrants' value is used when the building's Ch 9 result requires yard fire
    hydrants, else the 'without hydrant' value."""
    hc = _eval_high_ceiling(rules, b)
    if not hc or hc.not_required or not hc.pump_without_hydrant_gpm:
        return None
    yards = [it for it in items if it.status == "required" and "yard" in (it.system or "").lower()
             and "hydrant" in (it.system or "").lower()]
    yard = any("NOT EVALUATED" not in (it.system or "") for it in yards)
    # A yard hydrant line that is NOT EVALUATED never counts as 'no hydrants'.
    unknown = bool(yards) and not yard
    which = "with hydrants" if (yard or unknown) else "without hydrant"
    gpm = hc.pump_with_hydrant_gpm if (yard or unknown) else hc.pump_without_hydrant_gpm
    why = ("A yard fire hydrant line of this building is NOT EVALUATED, so the 'with hydrants' "
           "value is used until it is evaluated." if unknown else
           f"The building's Ch 9 result {'requires' if yard else 'does not require'} yard fire "
           f"hydrants, so the '{which}' value is used.")
    return Requirement(
        system="Fire Pump (Table 9.29.A high ceiling)", status="required",
        spec=f"{gpm} gpm ({which}; Table 9.29.A, {hc.hazard_class}, ceiling {hc.height_range})",
        detail=(f"Table 9.29.A (p.750-751), hazard {hc.hazard_class}, ceiling height "
                f"{hc.height_range}: pump capacity without hydrant "
                f"{hc.pump_without_hydrant_gpm} gpm, with hydrants {hc.pump_with_hydrant_gpm} gpm. "
                f"{why} #4.13.1 (p.749): the building "
                f"sprinkler system shall be extended to comply with Table 9.29; Table 9.29 row M "
                f"(p.750): ceilings over 10 m per Section 3.5 and Table 9.29.A. Table 9.29.A "
                f"prints no pressure for this pump (audit CH9B2-02)."),
        code_ref="Ch 9, #4.13.1 / Table 9.29.A", page_ref="p.749-751",
        source_rule="high_ceiling_9_29_A", duty="pump")


def _sprinkler_pump_warning() -> Requirement:
    """Owner ruling Q-1 (28.10.2026), audit CH9B2-03: #4.1.7 sprinklers beside a Table 9.27
    row that gives only a hose-reel pump and tank."""
    return Requirement(
        system="Sprinkler Pump / Tank Sizing (#4.1.7) - the row's hose-reel pump and tank do not size it",
        status="required",
        spec="Size the fire pump and fire water tank for the #4.1.7 sprinkler system by hydraulic "
             "calculation and verify with the Civil Defence engineers (#4.1.9)",
        detail=("#4.1.7 (p.694) requires an automatic sprinkler system, but this building's "
                "Table 9.27 row prints only a hose reel fire pump and tank (e.g. 50 gpm at "
                "4.5 bar at the most remote hose reel outlet valve), which do not size a "
                "sprinkler system. The code prints no pump for the #4.1.7 case; #4.1.9 "
                "(p.694): fire pump capacities may vary and shall be verified with the Civil "
                "Defence engineers and the relevant NFPA references (owner ruling Q-1, "
                "28.10.2026)."),
        code_ref="Ch 9, #4.1.7 / #4.1.9", page_ref="p.694", source_rule="owner_ruling_q1_pump")


_MSDS_LINE = Requirement(
    system="MSDS Review (DESIGNER OBLIGATION)", status="required", spec="Per #4.11.1 (p.724)",
    detail=("#4.11.1 (p.724): all warehouse and industrial sprinkler protection designers shall "
            "first consider and consult the relevant Material Safety Data Sheet (MSDS) before "
            "designing and proposing the sprinkler system (audit CH9B2-10)."),
    code_ref="Ch 9, #4.11.1", page_ref="p.724", source_rule="ch9_4_11_1_msds")

_RG_NOTE = (" Owner ruling R-G (28.10.2026): the Table 9.27 specialty group row and the "
            "hazard-class / commodity row are both evaluated; the most onerous pump and tank "
            "govern and the other is named.")
_BASE_STORAGE_RULES = ("storage_industrial_tier", "storage_industrial_eh", "storage_single_tenant_",
                       "storage_commodity_")


# ---------------------------- Per-chapter evaluators -------------------------

def evaluate_fp(b: Building, rules: Dict[str, Any],
                host_sprinklered: bool = False) -> ChapterReport:
    """Ch 9 - Fire Protection. `host_sprinklered`: an attached parking in a host building
    whose table requires sprinklers (owner ruling 12.10.2026, P3 App Q2); the Table 9.29 /
    9.30 #4.13.1 / #4.1.5 gate then treats the parking as sprinklered."""
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
    # Fix round 28.10.2026 (ch9): a not-required line beside a required line of the same
    # system from another table is dropped and named (CH9B2-05, sweep); #4.1.7 sprinklers
    # beside a hose-reel-only Table 9.27 row get the pump / tank sizing warning (Q-1).
    gen, branch_items = _reconcile_not_required(gen, branch_items)
    if any(it.source_rule == "g_storage_sprinkler_over_3floors" for it in gen) and not any(
            "sprinkler" in (it.system or "").lower() and it.status == "required"
            for it in branch_items):
        gen = list(gen) + [_sprinkler_pump_warning()]
    if gen:
        blocks.append(SectionBlock(title="FP - General Requirements (Ch 9, #4.1)", items=gen))

    # Owner ruling 12.10.2026, Ch9 Q7: robotic / mechanical parking is Extra Hazard
    # Group 2 (#1.1.13.5.b, p.530); the building is evaluated at HH + EH2.
    if b.has_robotic_parking and b.occupancy in _PARKING_OCCS:
        blocks.append(SectionBlock(title="FP - Hazard Classification (Ch 9, #1.1.13)", items=[
            _robotic_eh2_line()]))

    # Owner ruling 12.10.2026, Ch9 Q1: the plot GF BUA sum (#4.1.13) is required. A blank
    # sum is taken above 3600 m2 (Table 9.27 row 4, never a lower row) and named here.
    # A ground floor of exactly 3600 m2 already takes the higher row (owner ruling
    # 13.10.2026, "Higher row"), so the blank sum cannot change the row there.
    if (b.occupancy == "storage_industrial" and b.storage_gf_bua_sum_missing
            and b.ground_floor_bua_m2 < 3600
            and any("storage_gf_bua_sum_m2" in str(br.get("match")) for br in _matched)):
        branch_items = [_gf_bua_sum_not_evaluated_line()] + list(branch_items)

    # Owner ruling 13.10.2026, P4 Q4: Table 9.21.b does not list Mercantile Group C; a
    # lowrise kiosk takes it by inference from its midrise twin, Table 9.20.b row C.
    if b.occupancy == "mercantile_c" and sel_id and sel_id.startswith("lowrise_residential"):
        branch_items = [it.model_copy(update={"detail": (it.detail or "") + _P4_Q4_NOTE})
                        for it in branch_items]
        sel_section = f"{sel_section} (Mercantile Group C by inference, owner ruling 13.10.2026, P4 Q4)"

    # Audit CH9B2-02 (H10): the Table 9.29.A high-ceiling pump enters the governing merge.
    hc_pump = _high_ceiling_pump_line(b, rules, list(gen) + list(branch_items))
    if hc_pump:
        branch_items = _merge_duties(list(branch_items) + [hc_pump])
    if b.occupancy == "storage_industrial":
        # Owner ruling R-G (28.10.2026): specialty and hazard / commodity rows both apply.
        if b.storage_has_specialty and any(
                (br.get("id") or "").startswith(_BASE_STORAGE_RULES) for br in _matched):
            branch_items = [it.model_copy(update={"detail": (it.detail or "") + _RG_NOTE})
                            if it.duty in ("pump", "tank") and it.status == "required" else it
                            for it in branch_items]
        # The ticked specialty group names the selected row (the hazard / commodity row and
        # a blank-tenancy line are printed beside it, ruling R-G).
        spec_br = next((br for br in _matched if b.storage_has_specialty
                        and (br.get("id") or "").startswith("storage_")
                        and not (br.get("id") or "").startswith(_BASE_STORAGE_RULES)
                        and br.get("id") != "storage_tenancy_not_evaluated"), None)
        if spec_br and spec_br.get("id") != sel_id:
            sel_id = spec_br["id"]
            sel_section = (f"{spec_br.get('section')} (with the Table 9.27 hazard-class / "
                           f"commodity row, owner ruling R-G, 28.10.2026)")
        # Audit CH9B2-10: one #4.11.1 MSDS line for every storage group.
        if not any((it.system or "").startswith("MSDS Review") for it in branch_items):
            branch_items = list(branch_items) + [_MSDS_LINE]
    # Audit CH9B2-01 (H9): the pump set composition on the governing pump line.
    branch_items = _with_pump_set_note(branch_items)

    if branch_items:
        blocks.append(SectionBlock(title="FP - Branch Requirements (Ch 9)", items=_dedupe(branch_items)))

    # Ch 1 Table 1.9 item 48 KIOSKS (p.98), owner rulings 13.10.2026, P4 Q4-Q5.
    kiosk_items = _dedupe(_collect_flag(rules.get("kiosk_item_48", []), b))
    if kiosk_items:
        blocks.append(SectionBlock(title="FP - Kiosk (Ch 1, Table 1.9 item 48)", items=kiosk_items))

    # Determine if matched FP branch + general REQUIRES (status=required) any sprinkler system.
    # Various-locations items annotated with `requires_sprinkler_system: true` are suppressed
    # when the building's branch does not mandate sprinklers (e.g. small villas where
    # sprinklers are only "recommended").
    sprinkler_required = host_sprinklered or _sprinkler_required(
        list(gen) + list(branch_items) + list(kiosk_items))
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

    itm = _itm_lines(blocks)
    if itm:
        blocks.append(SectionBlock(
            title="FP - Testing, Inspection and Maintenance (Ch 9, Section 5)", items=itm))

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


_TRUCK_NO_ROOMS = ("has_main_electrical_room", "has_main_telephone_room", "has_lift_machine_room")


def evaluate_fe(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 4 - Fire Extinguishers."""
    blocks = []
    gen = _dedupe(_collect_general(rules, b))
    if gen:
        blocks.append(SectionBlock(title="FE - Universal Class A + Residential Class K (Ch 4, Table 4.3 rows 1, 6)", items=gen))

    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    if branch_items:
        blocks.append(SectionBlock(title="FE - Occupancy-specific (Class B Wheeled, Ch 4, Table 4.3 row 3)", items=_dedupe(branch_items)))

    # Fix round 28.10.2026 (CH04-07 L10): Table 4.3 row 4 items 1-3 (p.376) are rooms
    # (electrical / LV, telephone, lift machine). Their inputs default to ticked for any
    # building; a food truck or mercantile truck has no such room, so they are not read.
    fb = b.model_copy(update=dict.fromkeys(_TRUCK_NO_ROOMS, False)) \
        if b.is_mercantile_c_truck else b
    addons = _dedupe(_collect_flag(rules.get("addons", []), fb))
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
        blocks=_rb_yard_tank_conditional(blocks, b, 5),
    )


# Owner ruling R-B (28.10.2026): Groups T (aboveground tank storage) and U (open yard)
# keep the Ch 5 / 6 / 7 warehouse packages, as conditional, with this wording.
_RB_WORDING = ("Applies to any enclosed building on the site (warehouse, pump house, office). "
               "Ch {n} prints no row for open yards / aboveground tank farms (owner ruling R-B, "
               "28.10.2026).")


def _rb_yard_tank_conditional(blocks: List[SectionBlock], b: Building, n: int) -> List[SectionBlock]:
    """Owner ruling R-B (28.10.2026), CH04-07 M6: a storage / industrial building ticked as
    Table 9.27 Group T or Group U takes the Ch {n} warehouse lines as conditional, each
    naming the ruling; never 'not required'. NOT EVALUATED lines and not_required lines
    are left as they are."""
    if not (b.occupancy == "storage_industrial"
            and (b.is_open_yard_storage or b.is_aboveground_tank_storage)):
        return blocks
    note = _RB_WORDING.format(n=n)
    out = []
    for blk in blocks:
        its = []
        for it in blk.items:
            if it.status == "not_required" or "NOT EVALUATED" in it.system.upper():
                its.append(it)
                continue
            its.append(it.model_copy(update={
                "status": "conditional" if it.status == "required" else it.status,
                "detail": f"{note} {it.detail}" if it.detail else note}))
        out.append(blk.model_copy(update={"items": its}))
    return out


_T73_ITEM = re.compile(r"Table 7\.3 items? (\d+)")
_T73_LIST = re.compile(r"Table 7\.3 items? ((?:\d+(?:, | and )?)+)")


def _t73_nums(code_ref: Optional[str]) -> List[int]:
    """Every Table 7.3 item cited: "item 2", "items 2 and 9", "items 2, 3 and 9"."""
    return [int(n) for m in _T73_LIST.finditer(code_ref or "")
            for n in re.findall(r"\d+", m.group(1))]
_T73_PREFIX = {"evc": "Per Section 2.4 + Table 7.1", "two_way": "Per Section 2.5 + Table 7.2"}


def _evc_one_package(items: List[Requirement]) -> Tuple[List[Requirement], bool]:
    """Fix round 28.10.2026 (CH04-07 L1, Cursor PR #19, sweep class 3): Table 7.3 (p.439)
    prints one requirement for all nine rows (i. EVC per Section 2.4, ii. two-way
    telephone per Section 2.5). When rows match, one EVC line and one two-way line are
    printed, each citing every row that requires it (as Ch 6 `_el_cite_every_row`). A
    'not listed' / not_required row, or the item 9 area NOT EVALUATED line, does not print
    beside a row that requires the package. Returns (items, EVC required)."""
    req = [it for it in items if it.status == "required" and "NOT EVALUATED" not in it.system
           and _T73_ITEM.search(it.code_ref or "")]
    if not req:
        return items, False
    out = []
    for kind in ("evc", "two_way"):
        lines = [it for it in req if ("Two-way" in it.system) == (kind == "two_way")]
        if not lines:
            continue
        nums = sorted({n for it in lines for n in _t73_nums(it.code_ref)})
        first = lines[0]
        if len(nums) < 2:
            out.append(first)
            continue
        txt = ", ".join(str(x) for x in nums[:-1]) + f" and {nums[-1]}"
        pre = _T73_PREFIX[kind]
        extras = []
        for it in lines:
            s = (it.spec or "").strip()
            x = s[len(pre):].lstrip(" -") if s.startswith(pre) else s
            if x and x not in extras:
                extras.append(x)
        rows = " ".join(dict.fromkeys(
            f"Table 7.3 item{'s' if len(_t73_nums(it.code_ref)) > 1 else ''} "
            f"{', '.join(map(str, _t73_nums(it.code_ref)))}: {it.detail}"
            for it in lines if it.detail))
        out.append(first.model_copy(update={
            "spec": pre + (" - " + "; ".join(extras) if extras else ""),
            "code_ref": f"Ch 7, #3.1 / Table 7.3 items {txt}",
            "page_ref": "p.439",
            "detail": ((rows + " ") if rows else "") + (
                f"Table 7.3 items {txt} each require this same system (p.439 prints one "
                f"requirement for all its rows); one line is printed for all of them (fix "
                f"round 28.10.2026, CH04-07 L1)."),
        }))
    return out, True


def _mixed_evc_not_evaluated() -> Requirement:
    return Requirement(
        system="Emergency Voice Evacuation (EVC) - NOT EVALUATED",
        status="required",
        spec="Not evaluated: list the occupancies of this mixed building (most restrictive, R13)",
        detail=("Table 7.3 (p.439) requires EVC and two-way telephone by height (items 1-2) "
                "and, at any height, by occupancy (items 3-9: malls, assembly, amusement and "
                "theme parks, educational, hotel, detention and correctional, storage and "
                "industrial with built-up area more than 5000 m2); it does not list 'mixed and "
                "multiple'. Below 23 m the requirement follows the occupancies in the building, "
                "so it is not evaluated until they are listed under 'most restrictive' (fix "
                "round 28.10.2026, CH04-07 M2; same rule as Ch 4 Class A, owner ruling "
                "12.10.2026, P3 Ch47 Q2; ruling R13)."),
        code_ref="Ch 7, #3.1 / Table 7.3; ruling R13", page_ref="p.439",
        source_rule="audit28_m2_mixed_evc")


def evaluate_evc(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 7 - Emergency Voice Evacuation + Two-way Telephone."""
    blocks = []
    # General requirements only fire when an EVC system IS actually required: a matched
    # Table 7.3 row prints a required EVC line (not a not_required row, nor a NOT
    # EVALUATED line).
    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    branch_items, evc_required = _evc_one_package(branch_items)
    # Fix round 28.10.2026 (CH04-07 M2): mixed_multiple with no occupancy listed (not an
    # R13 run) is NOT EVALUATED below the height rows, as Ch 4 Class A.
    if (not evc_required and b.occupancy == "mixed_multiple"
            and _R13_SOURCE.get() is None):
        branch_items = [_mixed_evc_not_evaluated()]
    if evc_required:
        gen = _dedupe(_collect_general(rules, b))
        if gen:
            blocks.append(SectionBlock(title="EVC - General Specifications (Ch 7, Tables 7.1 + 7.2)", items=gen))
    if branch_items:
        blocks.append(SectionBlock(title="EVC - Voice Evac + Two-way Telephone (Ch 7, Table 7.3)", items=_dedupe(branch_items)))

    return ChapterReport(
        chapter_code="EVC", chapter_title="Emergency Voice Evacuation (Ch 7)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=_rb_yard_tank_conditional(blocks, b, 7),
    )


def evaluate_el(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 6 - Emergency Lighting."""
    blocks = []
    gen = _dedupe(_collect_general(rules, b))
    if gen:
        blocks.append(SectionBlock(title="EL - General Specs + Coverage Locations (Ch 6, Tables 6.1 + 6.6)", items=gen))

    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    # Owner ruling 12.10.2026, P3 follow-up F-a2: a Business / Mercantile Group C
    # stand-alone building with the amusement box ticked takes Table 6.5 item 4; item 11
    # / 12 (stand-alone) is not applied (the YAML rows already exclude it).
    if (b.is_business_group_c or b.is_mercantile_group_c) and b.has_amusement_confounding:
        item = "11" if b.occupancy == "business" else "12"
        kind = "Business" if b.occupancy == "business" else "Mercantile"
        note = (f" {kind} Group C is also chosen: Table 6.5 item 4 AMUSEMENT "
                f"BUILDINGS governs and item {item} (stand-alone self-contained, Section 3.4) is "
                f"not applied (owner ruling 12.10.2026, P3 follow-up F-a2).")
        branch_items = [it.model_copy(update={"detail": (it.detail or "") + note})
                        if it.source_rule == "el_amusement_standalone"
                        and it.system.startswith("Central Battery") else it
                        for it in branch_items]
    # Owner ruling 13.10.2026, P4 Q1: below 23 m the Business group decides item 11
    # (Group C) or the height row (items 5-6). The main Business occupancy with no group
    # chosen is NOT EVALUATED by name. A listed other Business occupancy (R13) has no
    # group input: it keeps the height row, the more onerous of the two.
    if (b.occupancy == "business" and b.business_group is None and b.height_m < 23
            and not b.has_amusement_confounding):
        src = _R13_SOURCE.get()
        if src is not None and src.occupancy != "business":
            branch_items = [it.model_copy(update={"detail": (it.detail or "") + (
                " Business is a listed other occupancy with no group input: the height row "
                "(Table 6.5 items 5-6, monitored) is kept, the more onerous of items 5-6 and "
                "item 11 (Business Group C, stand-alone) under ruling R13 most restrictive "
                "(owner ruling 13.10.2026, P4 Q1).")}) for it in branch_items]
        else:
            branch_items = [_business_group_not_evaluated_el()]
    branch_items = _el_cite_every_row(branch_items)
    if branch_items:
        blocks.append(SectionBlock(title="EL - System Type Selection (Ch 6, Table 6.5)", items=_dedupe(branch_items)))

    return ChapterReport(
        chapter_code="EL", chapter_title="Emergency Lighting (Ch 6)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=_rb_yard_tank_conditional(blocks, b, 6),
    )


_T65_ITEMS = re.compile(r"Table 6\.5 items? (\d+)(?:-(\d+))?")


def _t65_items(code_ref: Optional[str]) -> List[int]:
    out = []
    for m in _T65_ITEMS.finditer(code_ref or ""):
        lo = int(m.group(1))
        out.extend(range(lo, int(m.group(2) or lo) + 1))
    return out


def _el_cite_every_row(items: List[Requirement]) -> List[Requirement]:
    """Owner ruling 25.10.2026 12:40Z (option A): when two Table 6.5 rows print the
    same system line (e.g. a 30 m amusement building: item 2 HIGHRISE and item 4
    AMUSEMENT BUILDINGS, both Central Battery OR Monitored), `_dedupe` keeps one line;
    that line cites every row that required it, not only the first row in the YAML."""
    groups: Dict[tuple, List[int]] = {}
    for i, it in enumerate(items):
        groups.setdefault((it.system, it.spec, it.status), []).append(i)
    out = list(items)
    for idx in groups.values():
        if len({items[i].source_rule for i in idx}) < 2:
            continue
        nums = sorted({n for i in idx for n in _t65_items(items[i].code_ref)})
        if len(nums) < 2:
            continue
        txt = ", ".join(str(n) for n in nums[:-1]) + f" and {nums[-1]}"
        first = items[idx[0]]
        out[idx[0]] = first.model_copy(update={
            "code_ref": f"Ch 6, #4.3 / Table 6.5 items {txt}",
            "detail": (first.detail or "") + (
                f" Table 6.5 items {txt} each require this same package; one line is "
                f"printed for all of them (owner ruling 25.10.2026)."),
        })
    return out


def _business_group_not_evaluated_el() -> Requirement:
    return Requirement(
        system="Emergency Lighting System Type (Business) - NOT EVALUATED",
        status="required",
        spec="Not evaluated: choose the Business group (A, B or C)",
        detail=("Below 23 m Table 6.5 (p.419) gives item 11 BUSINESS, GROUP C a stand alone "
                "self contained emergency lighting system (Section 3.4) and other buildings "
                "the low rise / midrise row, items 5-6, a monitored type self contained "
                "system (Section 3.3). The Business group (Table 1.1 row 2, p.48) was not "
                "chosen, so the system type is not evaluated (owner ruling 13.10.2026, "
                "P4 Q1)."),
        code_ref="Ch 6, #4.3 / Table 6.5 items 5-6, 11", page_ref="p.419",
        source_rule="p4_q1_business_group")


_FA_TEMPORARY_KINDS = ("temporary", "site_office_short", "site_office_long")


def _fa_sprinklered(b: Building, sprinklered: Optional[bool] = None) -> bool:
    """Sprinkler status for Table 8.13 item 22 (i)-(iii) (audit 28.10.2026, CH8-18): true
    when the caller says so (an attached parking in a sprinklered host building), when the
    building's own Ch 9 rows require sprinklers, or, under ruling R13 most restrictive,
    when any listed occupancy's Ch 9 rows require them."""
    if sprinklered or building_sprinklered(b):
        return True
    src = _R13_SOURCE.get()
    if src is not None and src.mixed_occupancy_mode == "most_restrictive" and src.secondary_occupancies:
        occs, base = _r13_base(src)
        return any(building_sprinklered(_r13_single(base, o)) for o in occs)
    return False


def _fa_parking_detection(it: Requirement, spr: bool) -> Requirement:
    """Audit 28.10.2026, CH8-18: Table 8.13 item 22 (i)-(iii), p.506, printed as the
    branch that applies to this building, with the other branch named."""
    analogy = "by analogy" in (it.system or "")
    tail = " - by analogy with item 22 (ruling R10)" if analogy else ""
    ref = "Ch 8, #5.1 / Table 8.13 item 22 " + ("(i)-(ii)" if spr else "(iii)") + (
        ", by analogy (ruling R10)" if analogy else "")
    if spr:
        return it.model_copy(update={
            "system": "Manual Fire Detection and Alarm System - parking sprinklered, no fire detectors" + tail,
            "spec": "Manual Fire Detection and Alarm System per Section 4.10; no fire detectors",
            "detail": ("Table 8.13 item 22, p.506: (i) no Fire Detectors are required if the "
                       "enclosed parking is provided fully with automatic sprinkler System; (ii) "
                       "where enclosed parking is provided with automatic sprinkler system, Manual "
                       "Fire Detection and Alarm System shall be provided as per Section 4.10. "
                       "This building's Ch 9 result requires automatic sprinklers, so (i)-(ii) "
                       "apply. Were the parking not sprinklered, (iii) a Heat Detection and Alarm "
                       "System per Section 4.7 would apply."
                       + (" Applied by analogy: Table 8.13 has no open-parking row (ruling R10, "
                          "12.10.2026)." if analogy else "")),
            "code_ref": ref, "page_ref": "p.506"})
    return it.model_copy(update={
        "system": "Heat Detection and Alarm System - parking not sprinklered" + tail,
        "spec": "Heat Detection and Alarm System per Section 4.7, throughout",
        "detail": ("Table 8.13 item 22 (iii), p.506: where enclosed parking is not provided with "
                   "automatic sprinkler system, Heat Detection and Alarm System shall be provided "
                   "as per Section 4.7. This building's Ch 9 result does not require automatic "
                   "sprinklers, so (iii) applies. A fully sprinklered parking would take (i)-(ii): "
                   "no fire detectors and a Manual Fire Detection and Alarm System per Section 4.10."
                   + (" Applied by analogy: Table 8.13 has no open-parking row (ruling R10, "
                      "12.10.2026)." if analogy else "")),
        "code_ref": ref, "page_ref": "p.506"})


def evaluate_fa(b: Building, rules: Dict[str, Any],
                sprinklered: Optional[bool] = None) -> ChapterReport:
    """Ch 8 - Fire Detection & Alarm. `sprinklered`: True when the building is known to be
    sprinklered by another building's system (attached parking in a sprinklered host)."""
    blocks = []
    # Table 8.13 item 28 PLANT NURSERY (p.508): no FA system is required, so neither the
    # Table 8.1 system lines nor the Table 8.14 / 8.15 lines apply (owner rulings
    # 12.10.2026, Ch8 Q4 and follow-up F1).
    nursery = b.occupancy == "storage_industrial" and b.is_plant_nursery
    # Audit 28.10.2026, CH8-03: infrastructure (yard-hydrant network) is not a building and
    # Table 8.13 prints no row for it: one line (fa_infrastructure), no Table 8.1 / 8.14 /
    # 8.15 lines. CH8-07: a temporary tent or a site office (Table 9.21.f rows A, D, E,
    # p.712) takes Table 8.14 items 32 / 33, not the addressable building system, so the
    # Table 8.1 system lines are not printed (its Table 8.14 / 8.15 lines stay).
    infra = b.occupancy == "infrastructure"
    temporary = b.tent_marquee_kind in _FA_TEMPORARY_KINDS
    no_rooms = nursery or infra
    gen = [] if (no_rooms or temporary) else _dedupe(_collect_general(rules, b))
    if gen:
        # Owner ruling R-B (28.10.2026): for Group T / U storage the Table 8.1 system lines
        # belong to the warehouse package, conditional like the Table 8.13 row
        # (fa_storage_yard_tank) and Ch 5-7; Table 8.15 tank lines stay required.
        blocks.extend(_rb_yard_tank_conditional(
            [SectionBlock(title="FA - General Requirements (Ch 8, #3 + #4 / Table 8.1.a)", items=gen)], b, 8))
    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    if any((it.system or "").startswith("Conditional FA System") for it in branch_items):
        spr = _fa_sprinklered(b, sprinklered)
        branch_items = [_fa_parking_detection(it, spr)
                        if (it.system or "").startswith("Conditional FA System") else it
                        for it in branch_items]
    if branch_items:
        blocks.append(SectionBlock(title="FA - Detection & Alarm by Occupancy / Height (Ch 8, Table 8.13)", items=_dedupe(branch_items)))

    aux = [] if no_rooms else _dedupe(_collect_flag(rules.get("auxiliary_rooms", []), b))
    if aux:
        blocks.append(SectionBlock(title="FA - Auxiliary Rooms (Ch 8, Table 8.14)", items=aux))

    eq = [] if no_rooms else _dedupe(_collect_flag(rules.get("equipment", []), b))
    if eq:
        blocks.append(SectionBlock(title="FA - Equipment (Ch 8, Table 8.15)", items=eq))

    return ChapterReport(
        chapter_code="FA", chapter_title="Fire Detection & Alarm (Ch 8)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


_SC_TALL = ("sc_highrise", "sc_super_highrise")
_SC_PARKING = ("parking_enclosed", "parking_open")

# Owner ruling R-B (28.10.2026): Groups T (aboveground tanks) and U (open yard) keep the
# Table 10.26 warehouse rows, as conditional (Cursor PRs #29, #30).
_SC_RULING_RB = ("Applies to any enclosed building on the site (warehouse, pump house, office). "
                 "Ch 10 prints no row for open yards / aboveground tank farms (owner ruling R-B, "
                 "28.10.2026). ")


def _sc_reconcile(items: List[Requirement], b: Building) -> List[Requirement]:
    """One line per system where two Ch 10 tables print the same one (audit C10-03, C10-08).

    Parking of 23 m or more: #3.2.1 (p.857) applies Table 10.20 to 'Highrise buildings' with no
    parking exclusion (Table 10.22, p.859, is the only Ch 10 table titled 'other than Parking
    usage'), and #3.5.1 (p.860) applies Table 10.23 to parking, which prints its own stair rows
    for parking more than 23 m. Both apply. The stair pressurization is printed once, on the
    parking line, carrying the more onerous Table 10.20 / 10.19 item 1 text. Open parking up to
    4000 m2: Table 10.23 item 2.2.i (no smoke purging or ventilation) and Table 10.20 item 4
    (corridor and open circulation area smoke management) differ; the text does not say which
    governs, so the more onerous Table 10.20 line is kept and item 2.2.i is named.
    Business of 23 m or more: Table 10.27 item 3.iii (p.865) is the same stair system."""
    tall_i = next((i for i, it in enumerate(items) if it.source_rule in _SC_TALL
                   and it.system.startswith("Stair Pressurization")), None)
    if tall_i is None:
        return items
    tall = items[tall_i]
    out = list(items)
    tname = "Table 10.19" if tall.source_rule == "sc_super_highrise" else "Table 10.20"
    tsec = "#3.1.1" if tall.source_rule == "sc_super_highrise" else "#3.2.1"
    if b.occupancy in _SC_PARKING:
        park_i = next((i for i, it in enumerate(out)
                       if it.source_rule == "sc_parking_stair_23_or_more"), None)
        if park_i is not None:
            pk = out[park_i]
            out[park_i] = pk.model_copy(update={
                "spec": tall.spec,
                "detail": (f"{pk.detail} One stair pressurization line (audit C10-03): {tname} "
                           f"({tsec}, highrise buildings, p.857) and Table 10.23 (#3.5.1, parking, "
                           f"p.860) both apply to this parking building; this line carries the more "
                           f"onerous {tname} item 1 text: {tall.detail}"),
                "code_ref": f"{pk.code_ref}; {tall.code_ref} item 1",
                "page_ref": f"{pk.page_ref}, {tall.page_ref}"})
            out[tall_i] = None
        cor_i = next((i for i, it in enumerate(out) if it is not None and it.source_rule in _SC_TALL
                      and it.system.startswith("Enclosed Corridor Smoke Management")), None)
        if cor_i is not None:
            c = out[cor_i]
            why = (f" Parking building of 23 m or more (audit C10-03): {tsec} (p.857) applies "
                   f"{tname} to highrise buildings with no parking exclusion, and #3.5.1 (p.860) "
                   f"applies Table 10.23 to parking; both apply. ")
            gfa = b.gross_floor_area_m2
            if b.occupancy == "parking_open" and 0 < gfa <= 4000:
                why += ("Table 10.23 item 2.2.i: open parking complying with Table 10.23.2.1 and "
                        "having a total floor area of up to 4000 m2 shall not be required to have any "
                        "smoke purging or ventilation system. The code does not state which table "
                        f"governs; this {tname} line is the more onerous and is kept; Table 10.23 item "
                        "2.2.i is checked, not governing.")
            elif b.occupancy == "parking_open" and gfa > 4000:
                why += ("The parking floors also take Table 10.23 item 2.3 (mechanical smoke purging "
                        "OR jet fan system OR hybrid, line below).")
            elif b.occupancy == "parking_enclosed":
                why += ("The parking floors also take Table 10.23 item 1 (mechanical smoke purging "
                        "via dedicated ducting, line below).")
            else:
                why += "Table 10.23 item 2.2 / 2.3 is NOT EVALUATED (gross floor area not entered)."
            out[cor_i] = c.model_copy(update={"detail": (c.detail or "") + why})
    elif b.occupancy == "business":
        out[tall_i] = tall.model_copy(update={
            "detail": (f"{tall.detail} Table 10.27 item 3.iii (p.865): However, stairs of open plan "
                       f"offices in highrise buildings shall be pressurized in accordance with Section "
                       f"2.6; the same stair system, printed once (audit C10-08)."),
            "code_ref": f"{tall.code_ref}; Table 10.27 item 3.iii",
            "page_ref": f"{tall.page_ref}, p.865"})
    return [it for it in out if it is not None]


def _sc_ruling_rb(items: List[Requirement], b: Building) -> List[Requirement]:
    if b.occupancy != "storage_industrial" or not (
            b.is_aboveground_tank_storage or b.is_open_yard_storage):
        return items
    return [it.model_copy(update={"status": "conditional",
                                  "detail": _SC_RULING_RB + (it.detail or "")})
            if (it.source_rule or "").startswith("sc_storage_industrial_")
            and "NOT EVALUATED" not in it.system and it.status == "required" else it
            for it in items]


def evaluate_sc(b: Building, rules: Dict[str, Any]) -> ChapterReport:
    """Ch 10 - Smoke Control & Smoke Management."""
    blocks = []
    branch_items, sel_id, sel_section, _ = _collect_branch(rules.get("branches", []), b)
    branch_items = _sc_ruling_rb(_sc_reconcile(branch_items, b), b)
    if branch_items:
        blocks.append(SectionBlock(title="SC - Smoke Control by Tier / Occupancy (Ch 10, Tables 10.19-10.27)", items=_dedupe(branch_items)))

    aux = _dedupe(_collect_flag(rules.get("auxiliary_rooms", []), b))
    if aux:
        blocks.append(SectionBlock(title="SC - Auxiliary Zones / Equipment (Ch 10, Table 10.27)", items=aux))

    # Section 2.5 / Table 10.3 general requirements, printed when a smoke control or
    # ventilation system line is required (audit C10-09). NOT EVALUATED lines and the Ch 3
    # CO cross-reference do not count as a system.
    if any(it.status == "required" and "NOT EVALUATED" not in it.system
           and not it.system.startswith("Carbon Monoxide")
           for blk in blocks for it in blk.items):
        gen = _dedupe(_collect_general(rules, b))
        if gen:
            blocks.append(SectionBlock(title="SC - General Requirements (Ch 10, Section 2.5 / Table 10.3)", items=gen))

    return ChapterReport(
        chapter_code="SC", chapter_title="Smoke Control (Ch 10)",
        selected_branch=sel_id, selected_branch_section=sel_section,
        blocks=blocks,
    )


# The whole building of an R13 most-restrictive run, while its single-occupancy sub-runs
# are evaluated, so the #3.2.2 flame-effect line sees every listed occupancy (owner ruling
# 13.10.2026, P3 follow-up F-a4-1).
_R13_SOURCE: ContextVar[Optional[Building]] = ContextVar("_R13_SOURCE", default=None)


def _flame_unsprinklered(b: Building) -> List[str]:
    """#3.2.2 'fully sprinkler protected', checked on every listed occupancy under ruling R13
    most restrictive (owner ruling 13.10.2026, P3 follow-up F-a4-1): the main occupancy and
    each other listed occupancy whose own Ch 9 result (at the R13 hazard class) gives no
    automatic sprinkler system, by name. A listed occupancy whose Ch 9 lines are NOT
    EVALUATED (storage hazard or animal housing group not chosen) is named too, never
    passed."""
    if b.mixed_occupancy_mode != "most_restrictive" or not b.secondary_occupancies:
        return [] if building_sprinklered(b) else [
            "it is not fully sprinkler protected per its Ch 9 result"]
    occs, base = _r13_base(b)
    out = [] if building_sprinklered(_r13_single(base, occs[0])) else [
        "it is not fully sprinkler protected per its Ch 9 result"]
    for o in occs[1:]:
        if o == "storage_industrial" and b.secondary_storage_hazard is None:
            out.append(f"its listed occupancy '{o}' has its Ch 9 lines NOT EVALUATED (storage "
                       f"hazard class not chosen), so full sprinkler protection is not shown")
        elif o == "animal_housing" and b.secondary_animal_housing_group is None:
            out.append(f"its listed occupancy '{o}' has its Ch 9 lines NOT EVALUATED (animal "
                       f"housing group not chosen), so full sprinkler protection is not shown")
        elif not building_sprinklered(_r13_single(base, o)):
            out.append(f"its listed occupancy '{o}' is not sprinkler protected per its own Ch 9 "
                       f"result (ruling R13 most restrictive; owner ruling 13.10.2026, P3 "
                       f"follow-up F-a4-1)")
    return out


def _flame_show_missing(b: Building) -> List[str]:
    """The #3.2.2 (p.923) conditions for an indoor flame effect show that this building
    does not meet, by name: fully sprinkler protected (Ch 9 result, every listed occupancy
    under R13; owner ruling 13.10.2026, P3 follow-up F-a4-1) and provided with an
    automatic fire detection and alarm system (Ch 8 result; owner ruling 12.10.2026, P3
    follow-up F-a1-3). Inside an R13 sub-run the whole building is checked, so every
    sub-report prints the same line."""
    b = _R13_SOURCE.get() or b
    out = _flame_unsprinklered(b)
    if not fa_automatic_detection_required(b):
        fa_rules = load_rules("ch8_fire_alarm.yaml") or {}
        row = _collect_branch(fa_rules.get("branches", []), b)[1]
        why = {
            "fa_nursery_plants": ("Table 8.13 item 28, p.508: 'Fire Detection and Alarm System "
                                  "shall not be required'"),
            "fa_parking_enclosed": ("Table 8.13 item 22 i-ii, p.506: no fire detectors in a "
                                    "parking fully provided with automatic sprinklers, a Manual "
                                    "Fire Detection and Alarm System only"),
            "fa_parking_open": ("Table 8.13 item 22 i-ii, p.506, applied by analogy under "
                                "ruling R10: no fire detectors in a parking fully provided with "
                                "automatic sprinklers, a Manual Fire Detection and Alarm "
                                "System only"),
        }.get(row)
        out.append("its Ch 8 result does not require an automatic fire detection and alarm "
                   "system" + (f" ({why})" if why else ""))
    return out


def lpg_input_stops(b: Building) -> List[str]:
    """Input combinations Ch 11 prohibits outright, or a required input left blank; the
    app stops on each (st.error + st.stop) and the LPG report line states the same.
    Owner rulings 12.10.2026, P3 Ch11 Q3 (#2.2.4-#2.2.5, p.884) and Q6 (#3.2.2, p.923);
    P3 follow-ups F-a1-1 (new or modified building is a required choice) and F-a1-3
    (#3.2.2 also needs automatic fire detection and alarm)."""
    out = []
    if b.has_gas_cylinders_villa and b.is_new_or_modified_building is None:
        out.append("Choose 'New or modified building' or 'Existing building' under Gas "
                   "cylinders: cylinder type LPG installations in all new and modified "
                   "buildings are not allowed (Ch 11 #2.2.4, p.884) and permission to install "
                   "LPG cylinders is strictly subject to Civil Defence approval (#2.2.5), so "
                   "the tool does not assume either (owner ruling 12.10.2026, P3 follow-up "
                   "F-a1-1).")
    elif (b.has_gas_cylinders_villa and b.is_new_or_modified_building
            and not b.has_cd_cylinder_approval):
        out.append("Cylinder type LPG installations in all new and modified buildings are not "
                   "allowed (Ch 11 #2.2.4, p.884); permission to install LPG cylinders is "
                   "strictly subject to Civil Defence approval based on site and building "
                   "inspection (#2.2.5). Choose a centralized LPG system, choose 'Existing "
                   "building' for an existing building that is not modified, or tick 'Civil "
                   "Defence approval obtained (#2.2.5)' (owner ruling 12.10.2026, P3 Ch11 Q3).")
    if b.has_lpg_flame_effect and b.lpg_flame_effect_show in ("indoor", "both"):
        missing = _flame_show_missing(b)
        if missing:
            out.append("No indoor flame effect show shall be allowed if the building is not "
                       "fully sprinkler protected and provided with automatic fire detection "
                       "and alarm system (Ch 11 #3.2.2, p.923). This building does not meet "
                       "it: " + "; and ".join(missing) + ". Choose an outdoor show, or a "
                       "building that meets both conditions (owner ruling 12.10.2026, P3 "
                       "Ch11 Q6 and follow-up F-a1-3).")
    return out


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
    if b.has_gas_cylinders_villa and branch_items:
        # Owner ruling 12.10.2026, P3 Ch11 Q3: #2.2.4-#2.2.5 (p.884) per the new / modified
        # building and Civil Defence approval inputs.
        if b.is_new_or_modified_building is None:
            pre = ("NOT EVALUATED: 'New or modified building' / 'Existing building' is not "
                   "chosen, so whether #2.2.4 (new and modified buildings) applies is not "
                   "evaluated; choose one (owner ruling 12.10.2026, P3 follow-up F-a1-1). ")
        elif b.is_new_or_modified_building and not b.has_cd_cylinder_approval:
            pre = ("This building is entered as new or modified with no Civil Defence approval "
                   "recorded: a cylinder type LPG installation is NOT allowed (#2.2.4); provide "
                   "a centralized LPG system, or record the Civil Defence approval (#2.2.5). ")
        elif b.is_new_or_modified_building:
            pre = ("Civil Defence approval recorded (#2.2.5): the cylinder installation follows "
                   "that approval and the items below. ")
        else:
            pre = ("Existing building, not modified: #2.2.4 (new and modified buildings) does not "
                   "apply; the installation is still strictly subject to Civil Defence approval "
                   "(#2.2.5). ")
        pre += "(Owner ruling 12.10.2026, P3 Ch11 Q3.) "
        branch_items = [it.model_copy(update={"detail": pre + (it.detail or "")})
                        if it.system.startswith("Cylinder Installations Not Allowed") else it
                        for it in branch_items]
    if branch_items:
        blocks.append(SectionBlock(title="LPG - Base Gas-System Requirements (Ch 11, Tables 11.1, 11.4, 11.5, 11.6)", items=_dedupe(branch_items)))

    addons = _dedupe(_collect_flag(rules.get("addons", []), b))
    if b.has_lpg_flame_effect and addons:
        # Ch 11 #3.2.2 / Table 11.12 #1.iii (p.923): no indoor flame effect show
        # unless the building is fully sprinkler protected (audit CH10-09). Owner
        # ruling 12.10.2026, P3 Ch11 Q6: indoor / outdoor show input; an indoor show
        # in an unsprinklered building stops the app (lpg_input_stops).
        show = b.lpg_flame_effect_show
        upd = None
        if show == "outdoor":
            upd = {"status": "not_required",
                   "detail": ("Outdoor show only: #3.2.2 applies to indoor flame effect shows "
                              "(owner ruling 12.10.2026, P3 Ch11 Q6).")}
        elif _flame_show_missing(b):
            # P3 follow-up F-a1-3: #3.2.2 needs BOTH full sprinkler protection (Ch 9) and
            # automatic fire detection and alarm (Ch 8); each missing one is named.
            why = "; and ".join(_flame_show_missing(b))
            if show in ("indoor", "both"):
                upd = {"detail": (f"An indoor show is entered and this building does not meet "
                                  f"#3.2.2: {why}. The indoor flame effect show is NOT allowed "
                                  f"(#3.2.2, p.923; owner ruling 12.10.2026, P3 Ch11 Q6 and "
                                  f"follow-up F-a1-3).")}
            else:
                upd = {"detail": (f"This building does not meet #3.2.2: {why}. An indoor flame "
                                  f"effect show is NOT allowed here (#3.2.2, p.923); outdoor "
                                  f"shows only. State whether the show is indoor or outdoor in "
                                  f"the gas systems inputs.")}
        if upd:
            addons = [it.model_copy(update=upd)
                      if it.system.startswith("Indoor Flame Effect Shows") else it for it in addons]
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
                            "various_locations", "kiosk_item_48"):
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


# Owner ruling 12.10.2026, P3 App Q2: the attached parking's own height and basement
# levels. With either one blank, the sub-evaluation is run at every height (and level
# count) the printed thresholds can tell apart; a line that is the same in every run does
# not depend on the blank input and is printed, every other line is NOT EVALUATED by name.
# Heights: Ch 1 / Ch 3-10 rows at 10, 15, 20, 23 and 90 m; the Table 9.6 item 13 / 9.19
# pump head at 45 and 90 m (height + depth). Levels: rows at more than 0, more than 2 and
# 3 or more basements (#1.7.45 high depth).
_PARK_HEIGHT_EDGES = (10.0, 15.0, 20.0, 23.0, 90.0)
_PARK_PUMP_HEAD_EDGES = (45.0, 90.0)
_PARK_PROBE_LEVELS = (0, 1, 2, 3)
_P3_Q2 = "owner ruling 12.10.2026, P3 App Q2"


def _park_probe_heights(depth: float) -> List[float]:
    hs = {0.0, 3.0, 120.0}
    for t in _PARK_HEIGHT_EDGES:
        hs.update((t - 0.5, t, t + 0.5))
    for t in _PARK_PUMP_HEAD_EDGES:
        hs.update((t - depth - 0.5, t - depth, t - depth + 0.5))
    return sorted(h for h in hs if h >= 0)


def _host_sprinkler_line(b: Building, fp_rules: Dict[str, Any]) -> Optional[Requirement]:
    """The host building's required automatic sprinkler line, if any (P3 App Q2: the
    attached parking takes the host table's sprinklers)."""
    items = list(_collect_general(fp_rules, b)) + list(_collect_branch(fp_rules.get("branches", []), b)[0])
    return next((it for it in items if it.status == "required"
                 and (it.system or "").startswith("Automatic Sprinkler System")), None)


def _with_host_sprinklers(ch: ChapterReport, host: Requirement) -> ChapterReport:
    """P3 App Q2: in a sprinklered host building the attached parking's Ch 9 sprinklers
    follow the host table (e.g. Table 9.19 'throughout the building including basements'):
    one sprinkler line citing the host table replaces the parking rows' own lines."""
    own = [it for blk in ch.blocks for it in blk.items
           if blk.title.startswith("FP - Branch") and (it.system or "").startswith("Automatic Sprinkler System")]
    said = "; ".join(f"{it.system} ({it.code_ref}): {it.status.replace('_', ' ')}" for it in own)
    line = Requirement(
        system="Automatic Sprinkler System (as the host building)",
        status="required", spec=host.spec,
        detail=(f"The attached parking is part of the host building, whose Ch 9 table requires "
                f"an automatic sprinkler system ({host.system}, {host.code_ref}): the parking "
                f"is sprinklered under that table ({_P3_Q2}). "
                + (f"The parking's own rows say: {said}." if said else "")),
        code_ref=host.code_ref, page_ref=host.page_ref, source_rule="owner_ruling_p3_app_q2")
    blocks, done = [], False
    for blk in ch.blocks:
        if blk.title.startswith("FP - Branch"):
            kept = [it for it in blk.items if it not in own]
            blocks.append(blk.model_copy(update={"items": [line] + kept}))
            done = True
        else:
            blocks.append(blk)
    if not done:
        blocks.insert(0, SectionBlock(title="FP - Branch Requirements (Ch 9)", items=[line]))
    return ch.model_copy(update={"blocks": blocks})


def _parking_depth(b: Building) -> float:
    """P3 follow-up F-a3: the attached parking's own depth below the fire access level;
    blank = the building's depth (the report says so by name)."""
    return b.depth_below_grade_m if b.parking_depth_m is None else b.parking_depth_m


def _parking_depth_note(b: Building) -> ChapterReport:
    """P3 follow-up F-a3: a blank parking depth is named, with the depth used."""
    return ChapterReport(
        chapter_code="PARK", chapter_title="Attached parking inputs",
        blocks=[SectionBlock(title="Attached parking - inputs used", items=[Requirement(
            system="Parking depth not entered: building depth used",
            status="conditional",
            spec=(f"Parking depth below the fire access level taken as the building's depth "
                  f"below grade, {b.depth_below_grade_m:g} m"),
            detail=("The attached parking's own depth below the fire access level was not "
                    "entered, so its basement lines use the building's depth (owner ruling "
                    "12.10.2026, P3 follow-up F-a3). High depth is more than 7 m below or more "
                    "than two basements below the level of exit discharge (Ch 1 #1.7.45, "
                    "p.45). Enter the parking depth when the parking does not reach the "
                    "building's lowest level."),
            code_ref="Ch 1, #1.7.45", page_ref="p.45",
            source_rule="owner_ruling_p3_f_a3")])])


def _attached_parking_run(b: Building, height: float, levels: int) -> List[ChapterReport]:
    """One sub-evaluation of the attached parking at the given own height and levels."""
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
    # P3 App Q2: the parking's own height (0 m = wholly below the fire access level) and
    # basement levels; P3 follow-up F-a3: its own depth (blank = the building's depth).
    geo = {"height_m": height} if height > 0 else {}
    synth = Building(
        **flags, **geo,
        project_name=b.project_name + " (parking sub-occupancy)" if b.project_name else "",
        occupancy=synth_occ,
        # Audit F9A-02 (28.10.2026): Table 9.24.D (p.721) is a covered / shaded parking
        # "having one level only"; the tick states the parking's own single level, so the
        # one-level test reads the parking, never the host's floors.
        floors_above_grade=(1 if (b.is_covered_shaded_parking and synth_occ == "parking_open")
                            else b.floors_above_grade),
        floors_below_grade=levels,
        depth_below_grade_m=_parking_depth(b) if levels > 0 else 0.0,
        gross_floor_area_m2=parking_area,
        ground_floor_bua_m2=parking_area,
        basement_bua_m2=parking_area if levels > 0 else 0.0,
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
    host_spr = building_sprinklered(b)
    if moe_rules: chapters.append(evaluate_moe(synth, moe_rules, sprinklered=host_spr))
    if fe_rules:  chapters.append(evaluate_fe(synth, fe_rules))
    if es_rules:  chapters.append(evaluate_es(synth, es_rules))
    if el_rules:  chapters.append(evaluate_el(synth, el_rules))
    if fa_rules:  chapters.append(evaluate_fa(synth, fa_rules, sprinklered=host_spr))   # CH8-18
    if fp_rules:
        # P3 App Q2: Ch 9 sprinklers still follow the host building's table.
        host_line = _host_sprinkler_line(b, fp_rules) if host_spr else None
        fp = evaluate_fp(synth, fp_rules, host_sprinklered=bool(host_line))
        chapters.append(_with_host_sprinklers(fp, host_line) if host_line else fp)
    if sc_rules:  chapters.append(evaluate_sc(synth, sc_rules))
    return chapters


def _merge_attached_parking_duties(chapters: List[ChapterReport],
                                   attached: List[ChapterReport]):
    """Owner ruling Q-3 (28.10.2026), audit F9A-05: one governing fire pump and one fire
    water tank line for the whole building, the most onerous of the host and the attached
    parking, citing both tables and #4.1.17 (p.695). The governing line stays in the host's
    Ch 9 chapter; the parking chapter's own line is removed. A line that cannot be ranked
    (no printed flow or minutes, or a NOT EVALUATED probe) is left as it is."""
    hi = next((i for i, c in enumerate(chapters) if c.chapter_code == "FP"), None)
    pi = next((i for i, c in enumerate(attached) if c.chapter_code == "FP"), None)
    if hi is None or pi is None:
        return chapters, attached
    host, park = chapters[hi], attached[pi]

    def find(ch, duty):
        return [(bi, ii) for bi, blk in enumerate(ch.blocks) for ii, it in enumerate(blk.items)
                if it.duty == duty and it.status == "required"]

    for duty in ("pump", "tank"):
        h, p = find(host, duty), find(park, duty)
        if not h and len(p) == 1 and host.blocks:
            # The host prints no fire pump / tank of its own: the parking's duty is the
            # building's one governing line, carried into the host Ch 9 chapter (Q-3).
            pit = park.blocks[p[0][0]].items[p[0][1]]
            what = "fire pump set" if duty == "pump" else "fire water tank"
            moved = pit.model_copy(update={"detail": (pit.detail or "") + (
                f" One {what} for the whole building, host and attached parking (owner ruling "
                f"Q-3, 28.10.2026; #4.1.17, p.695): the host building's own table prints no "
                f"{what}, so the attached parking's governs.")})
            ti = next((bi for bi, blk in enumerate(host.blocks)
                       if blk.title.startswith("FP - Branch")), 0)
            host = host.model_copy(update={"blocks": [
                blk.model_copy(update={"items": list(blk.items) + [moved]}) if bi == ti else blk
                for bi, blk in enumerate(host.blocks)]})
            park = park.model_copy(update={"blocks": [
                blk.model_copy(update={"items": [it for ii, it in enumerate(blk.items)
                                                 if (bi, ii) != p[0]]})
                if bi == p[0][0] else blk for bi, blk in enumerate(park.blocks)]})
            continue
        if len(h) != 1 or len(p) != 1:
            continue
        hit = host.blocks[h[0][0]].items[h[0][1]]
        pit = park.blocks[p[0][0]].items[p[0][1]]
        hk, pk = _duty_key(hit), _duty_key(pit)
        if hk[0] == 0 or pk[0] == 0:
            continue
        w, o, where = (hit, pit, "attached parking") if hk >= pk else (pit, hit, "host building")
        what = "fire pump set" if duty == "pump" else "fire water tank"
        same = "the same duty" if hk == pk else "not governing"
        note = (f" One {what} for the whole building, host and attached parking (owner ruling "
                f"Q-3, 28.10.2026; #4.1.17, p.695: a common fire pump set and fire water tank "
                f"are permitted where the arrangement satisfies the required hydraulic "
                f"calculations); "
                + ("both tables give the same duty. " if hk == pk else
                   "this line is the most onerous of the two. ")
                + f"Also checked ({where}, {same}): {o.spec} ({o.code_ref}).")
        if duty == "pump" and _max_num(o.spec, "bar") > _max_num(w.spec, "bar"):
            note += f" The pump must also meet {_max_num(o.spec, 'bar'):g} bar where that table requires it."
        merged = w.model_copy(update={
            "detail": (w.detail or "") + note,
            "code_ref": " + ".join(dict.fromkeys(r for r in (w.code_ref, o.code_ref) if r)),
            "page_ref": ", ".join(dict.fromkeys(r for r in (w.page_ref, o.page_ref) if r)) or None})
        host = host.model_copy(update={"blocks": [
            blk.model_copy(update={"items": [merged if (bi, ii) == h[0] else it
                                             for ii, it in enumerate(blk.items)]})
            if bi == h[0][0] else blk for bi, blk in enumerate(host.blocks)]})
        park = park.model_copy(update={"blocks": [
            blk.model_copy(update={"items": [it for ii, it in enumerate(blk.items)
                                             if (bi, ii) != p[0]]})
            if bi == p[0][0] else blk for bi, blk in enumerate(park.blocks)]})
    park = park.model_copy(update={"blocks": [blk for blk in park.blocks if blk.items]})
    chapters = list(chapters)
    attached = list(attached)
    chapters[hi], attached[pi] = host, park
    return chapters, attached


def _line_key(title: str, it: Requirement) -> tuple:
    return (title, it.system, it.status, it.spec, it.code_ref)


def _probe_not_evaluated(runs: List[List[ChapterReport]], missing: List[str]) -> List[ChapterReport]:
    """P3 App Q2: lines the same in every probe run are printed; every other line is named
    NOT EVALUATED (one line per system), with the values it takes across the runs."""
    what = " and ".join(missing)
    out = []
    for ci, ch in enumerate(runs[0]):
        per_run = [[(blk.title, it) for blk in r[ci].blocks for it in blk.items] for r in runs]
        keysets = [{_line_key(t, it) for t, it in pr} for pr in per_run]
        stable = set.intersection(*keysets)
        blocks = []
        for blk in ch.blocks:
            items = [it for it in blk.items if _line_key(blk.title, it) in stable]
            if items:
                blocks.append(blk.model_copy(update={"items": items}))
        variants: Dict[str, List[str]] = {}
        for pr in per_run:
            for t, it in pr:
                if _line_key(t, it) in stable:
                    continue
                v = f"{it.status.replace('_', ' ')}" + (f", {it.spec}" if it.spec else "") + \
                    (f" ({it.code_ref})" if it.code_ref else "")
                vs = variants.setdefault(it.system, [])
                if v not in vs:
                    vs.append(v)
        if variants:
            lines = []
            for name, vs in variants.items():
                absent = any(not any(it.system == name for _, it in pr) for pr in per_run)
                lines.append(Requirement(
                    system=f"{name} - NOT EVALUATED",
                    status="required",
                    spec=f"Not evaluated: enter the attached parking {what}",
                    detail=(f"This line depends on the attached parking's own {what}, which "
                            f"{'were' if len(missing) > 1 else 'was'} not entered; the tower's "
                            f"values are not used ({_P3_Q2}). Across the values the code tells "
                            f"apart it reads: " + " | ".join(vs)
                            + ("; at some values it is not printed at all." if absent else ".")),
                    source_rule="owner_ruling_p3_app_q2"))
            blocks.append(SectionBlock(
                title=f"{ch.chapter_code} - Lines keyed on the parking {what} - NOT EVALUATED",
                items=lines))
        same = {r[ci].selected_branch for r in runs}
        upd = {"blocks": blocks}
        if len(same) > 1:
            upd.update(selected_branch=None, selected_branch_section=(
                f"Depends on the attached parking {what} (not entered; {_P3_Q2})"))
        out.append(ch.model_copy(update=upd))
    return out


def evaluate_attached_parking(b: Building) -> List[ChapterReport]:
    """Build a synthetic parking Building and run every chapter against it, returning a
    per-chapter list. Used to surface parking sub-occupancy requirements when the main
    occupancy is non-parking but has an in-building parking area.

    The PARKING AREA (parking_area_m2) drives Ch 10 SC area-based thresholds (e.g. 3600 m^2
    make-up-air exception for enclosed parking; 4000 m^2 small-vs-large open parking split).
    Audit ENG-11: a blank parking area is NOT EVALUATED (no fallback), and every yes/no
    flag the user set carries over, so an unticked room is never brought back by a schema
    default. Owner ruling 12.10.2026, P3 App Q2: the parking's own height above the fire
    access level and its basement levels are used (never the tower's); a blank one leaves
    the lines keyed on it NOT EVALUATED by name; Ch 9 sprinklers follow the host table.
    P3 follow-up F-a3: the parking's own depth below the fire access level; blank = the
    building's depth, named in a PARK note line.
    """
    if b.parking_area_m2 <= 0:
        return [_parking_area_not_evaluated()]
    missing = []
    if b.parking_height_m is None:
        missing.append("height above the fire access level")
    if b.parking_basement_levels is None:
        missing.append("basement levels")
    levels = ([b.parking_basement_levels] if b.parking_basement_levels is not None
              else list(_PARK_PROBE_LEVELS))
    runs = []
    for lv in levels:
        depth = _parking_depth(b) if lv > 0 and not b.pump_room_at_grade else 0.0
        hs = [b.parking_height_m] if b.parking_height_m is not None else _park_probe_heights(depth)
        runs += [_attached_parking_run(b, h, lv) for h in hs]
    out = runs[0] if len(runs) == 1 else _probe_not_evaluated(runs, missing)
    # P3 follow-up F-a3: the depth is used only where the parking has (or may have)
    # basement levels, in a building that has basements.
    if (b.parking_depth_m is None and b.parking_basement_levels != 0
            and b.floors_below_grade > 0):
        out = [_parking_depth_note(b)] + list(out)
    return out


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


_EL_KIND_RANK = {"monitored": 3, "central_or_monitored": 2, "stand_alone": 1}


def _el_kind(it: Requirement) -> Optional[str]:
    s = it.system or ""
    if s.startswith("Monitored Self-Contained EL"):
        return "monitored"
    if s.startswith("Central Battery"):
        return "central_or_monitored"
    if s.startswith("Stand-alone Self-Contained EL"):
        return "stand_alone"
    return None


def _r13_one_el_package(items: List[Requirement]) -> List[Requirement]:
    """Owner ruling R-F (28.10.2026): in most restrictive mixed mode the building gets ONE
    Table 6.5 system type, the one that meets every row that applies. #4.2 (p.419): where
    central battery or monitored emergency lighting is required, one centralized system
    covers the entire facility, so a stand-alone line cannot sit beside it, and a
    Monitored Self-Contained system meets both "Monitored" and "Central Battery OR
    Monitored" rows. The rows not printed are named in the kept line."""
    kinds = {_el_kind(it) for it in items if it.status == "required"} - {None}
    if len(kinds) < 2:
        # A villa row's "not mandatory" line cannot stand beside a required system that
        # serves the facility (not the villa's own basement-only line).
        facility = any(_el_kind(it) and it.status == "required"
                       and "basement only" not in (it.system or "") for it in items)
        if not facility:
            return items
        return [it for it in items if not (
            _el_kind(it) is None and it.status == "not_required"
            and (it.system or "").startswith("Emergency Lighting ("))]
    gov = max(kinds, key=lambda k: _EL_KIND_RANK[k])
    typed = [it for it in items if _el_kind(it) and it.status == "required"]
    nums = sorted({n for it in typed for n in _t65_items(it.code_ref)})
    dropped = [it for it in typed if _el_kind(it) != gov]
    out, kept = [], False
    for it in items:
        k = _el_kind(it)
        if k and it.status == "required":
            if k != gov or kept:
                continue
            kept = True
            txt = (", ".join(str(n) for n in nums[:-1]) + f" and {nums[-1]}") if len(nums) > 1 \
                else (str(nums[0]) if nums else "")
            names = "; ".join(f"{d.system} ({d.code_ref})" for d in dropped)
            out.append(it.model_copy(update={
                "code_ref": f"Ch 6, #4.2 / #4.3 / Table 6.5 items {txt}" if txt else it.code_ref,
                "detail": (it.detail + " " if it.detail else "") + (
                    f"Mixed occupancy, most restrictive: one system type for the building "
                    f"(owner ruling R-F, 28.10.2026). #4.2 (p.419) requires one centralized "
                    f"emergency lighting system for the entire facility; this package meets every "
                    f"Table 6.5 row that applies (items {txt}). Not printed separately: {names}."),
            }))
            continue
        # A villa row's "not mandatory" line cannot stand beside a required facility system.
        if k is None and it.status == "not_required" and (it.system or "").startswith("Emergency Lighting ("):
            continue
        out.append(it)
    return out


_FA_HEIGHT_ROWS = {"fa_super_highrise", "fa_highrise", "fa_midrise_lowrise"}
_FA_PROTOCOL = re.compile(r"Phased Evacuation Alarm|^Positive Alarm Sequence|^General Fire Alarm")


def _r13_one_fa_protocol(contrib: List[tuple]) -> List[tuple]:
    """Owner ruling R-F (28.10.2026), extending R7: a mixed building has ONE alarm
    protocol. An occupancy's own Table 8.13 row protocol governs over the height row
    (items 1-4) protocol, as R7 rules for a single occupancy; between occupancy rows the
    main occupancy's governs, else the first listed. The protocols not applied are named.
    `contrib` is the list of (occupancy, items) of the Table 8.13 block."""
    def is_proto(it):
        return it.status == "required" and bool(_FA_PROTOCOL.search(it.system or ""))
    own = [(occ, its) for occ, its in contrib
           if any(is_proto(it) and it.source_rule not in _FA_HEIGHT_ROWS for it in its)]
    if not own:
        return contrib
    gov_occ = own[0][0]
    dropped = [(occ, it) for occ, its in contrib for it in its if is_proto(it)
               and not (occ == gov_occ and it.source_rule not in _FA_HEIGHT_ROWS)]
    if not dropped:
        return contrib
    names = "; ".join(f"{it.system} ({occ}, {it.source_rule})" for occ, it in dropped)
    note = (f" Mixed occupancy, one alarm protocol (owner ruling R-F, 28.10.2026, extending "
            f"R7): the {gov_occ} Table 8.13 row protocol governs. Not applied: {names}. "
            f"Confirm the protocol with Civil Defence where portions have different rows.")
    out = []
    for occ, its in contrib:
        new = []
        for it in its:
            if is_proto(it) and (occ, it) in [(o, d) for o, d in dropped]:
                continue
            if is_proto(it) and occ == gov_occ:
                it = it.model_copy(update={"detail": (it.detail or "") + note})
            new.append(it)
        out.append((occ, new))
    return out


def _r13_one_evc_package(contrib: List[tuple]) -> List[tuple]:
    """Owner ruling R-F (28.10.2026) with CH04-07 L1: in most restrictive mixed mode the
    Table 7.3 rows of every occupancy give ONE EVC line and ONE two-way line, citing every
    row that requires the package. Each occupancy's run is already collapsed by
    `_evc_one_package`; here the lines with the most rows are kept, their citation widened
    to every row, and the 'not listed' / NOT EVALUATED lines of other occupancies dropped."""
    def is_req(it):
        return (it.status == "required" and "NOT EVALUATED" not in it.system
                and _T73_ITEM.search(it.code_ref or ""))
    req_occ = [occ for occ, its in contrib if any(is_req(it) for it in its)]
    if not req_occ:
        return contrib
    out = []
    for two_way in (False, True):
        lines = [it for _, its in contrib for it in its
                 if is_req(it) and ("Two-way" in it.system) == two_way]
        if not lines:
            continue
        nums = sorted({n for it in lines for n in _t73_nums(it.code_ref)})
        base = max(lines, key=lambda it: len(_t73_nums(it.code_ref)))
        if len(nums) > len(_t73_nums(base.code_ref)):
            txt = ", ".join(str(x) for x in nums[:-1]) + f" and {nums[-1]}"
            extra = " ".join(dict.fromkeys(
                f"Table 7.3 item {_t73_nums(it.code_ref)[0]}: {it.detail}" for it in lines
                if it.detail and len(_t73_nums(it.code_ref)) == 1
                and _t73_nums(it.code_ref)[0] not in _t73_nums(base.code_ref)))
            base = base.model_copy(update={
                "code_ref": f"Ch 7, #3.1 / Table 7.3 items {txt}", "page_ref": "p.439",
                "detail": (base.detail or "") + (" " + extra if extra else "") + (
                    f" Table 7.3 items {txt} each require this same system; one line is "
                    f"printed for all of them.")})
        out.append(base.model_copy(update={"detail": (base.detail or "") + (
            f" [Mixed occupancy, most restrictive (ruling R13, R-F): required by "
            f"{', '.join(req_occ)}.]")}))
    return [(contrib[0][0], out)]


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
            if ch.chapter_code == "FA" and t.startswith("FA - Detection"):
                contrib = _r13_one_fa_protocol(contrib)
            if ch.chapter_code == "EVC" and t.startswith("EVC - Voice Evac"):
                contrib = _r13_one_evc_package(contrib)
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
            if ch.chapter_code == "EL" and t.startswith("EL - System Type"):
                items = _r13_one_el_package(items)
            blocks.append(SectionBlock(title=t, items=_merge_duties(items)))
        sec = ch.selected_branch_section
        extra = "; ".join(f"{occ}: {c.selected_branch}" for occ, c in others if c.selected_branch)
        if extra:
            sec = f"{sec or ''} + most restrictive with {extra} (ruling R13)".strip()
        out.append(ch.model_copy(update={"blocks": blocks, "selected_branch_section": sec}))
    return out


def _r13_base(b: Building) -> Tuple[List[str], Building]:
    """Ruling R13 most restrictive: the listed occupancies (main first) and the building at
    the highest hazard class of those listed, on which each occupancy is evaluated."""
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
    return occs, b.model_copy(update={"hazard_class": hz, "is_extra_hazard_2": eh2 and hz == "HH"})


def _r13_single(base: Building, o: str) -> Building:
    return base.model_copy(update={"occupancy": o, "secondary_occupancies": [],
                                   "mixed_occupancy_mode": "none"})


def _evaluate_core(b: Building) -> ComplianceReport:
    """Ruling R13 (12.10.2026): in most_restrictive mixed mode every listed occupancy is
    evaluated on the same building, at the highest hazard class of those listed, and the
    chapters are merged keeping the most onerous line per system."""
    if b.mixed_occupancy_mode == "most_restrictive" and b.secondary_occupancies:
        occs, base = _r13_base(b)
        hz = base.hazard_class
        tok = _R13_SOURCE.set(b)
        try:
            reps = [_evaluate_single(_r13_single(base, o)) for o in occs]
        finally:
            _R13_SOURCE.reset(tok)
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
        # Owner ruling 12.10.2026, P3 Storey Q4: the same for a secondary animal housing.
        if "animal_housing" in occs[1:] and b.secondary_animal_housing_group is None:
            i = occs.index("animal_housing")
            reps[i] = reps[i].model_copy(update={"chapters": [
                _animal_group_not_evaluated(c) if c.chapter_code == "FP" else c
                for c in reps[i].chapters]})
            note = (note or "") + (
                f" Animal housing group not chosen: its Ch 9 lines are NOT EVALUATED, and its "
                f"other chapters use {hz}, the highest class of the other occupancies (owner "
                f"ruling 12.10.2026, P3 Storey Q4).")
        elif "animal_housing" in occs[1:]:
            g = b.secondary_animal_housing_group
            note = (note or "") + (
                f" Animal housing (other occupancy): Group {g}, {ANIMAL_HOUSING_GROUPS[g][0]} "
                f"({ANIMAL_HOUSING_GROUPS[g][1]}, {ANIMAL_HOUSING_GROUPS[g][2]}; owner ruling "
                f"12.10.2026, P3 Storey Q4).")
        r0 = reps[0]
        return r0.model_copy(update={
            "building": base,
            "chapters": _merge_most_restrictive([(o, r.chapters) for o, r in zip(occs, reps)]),
            "requires_wet_riser": any(r.requires_wet_riser for r in reps),
            "mixed_occupancy_note": note,
        })
    r = _evaluate_single(b)
    if b.occupancy == "mixed_multiple":
        r = _mixed_class_a_not_evaluated(r)
    return r


def _mark_not_evaluated(ch: ChapterReport) -> ChapterReport:
    blocks = [blk.model_copy(update={"items": [
        it.model_copy(update={"status": "not_evaluated"})
        if "NOT EVALUATED" in (it.system or "") and it.status == "required" else it
        for it in blk.items]}) for blk in ch.blocks]
    return ch.model_copy(update={"blocks": blocks})


def evaluate(b: Building) -> ComplianceReport:
    """Evaluate the building (see `_evaluate_core`). Audit UX-03 (28.10.2026): a line that
    names a missing input ("... - NOT EVALUATED") is reported with its own status
    `not_evaluated`, never counted as a required system; the engine builds it as a
    required line internally so that no chapter logic treats the gap as a pass."""
    r = _evaluate_core(b)
    return r.model_copy(update={
        "chapters": [_mark_not_evaluated(c) for c in r.chapters],
        "attached_parking_chapters": [_mark_not_evaluated(c) for c in r.attached_parking_chapters],
    })


def _mixed_class_a_not_evaluated(r: ComplianceReport) -> ComplianceReport:
    """Owner ruling 12.10.2026, P3 Ch47 Q2: mixed_multiple has no Class A line of its own;
    its listed occupancies decide (R13). With none listed, the Class A line is named as
    NOT EVALUATED, never left out silently."""
    item = Requirement(
        system="Class A Fire Extinguisher - NOT EVALUATED",
        status="required",
        spec="Not evaluated: list the occupancies of this mixed building (most restrictive, R13)",
        detail=("Table 4.3 row 1 (p.373-374) lists Class A extinguishers by occupancy and does "
                "not list 'mixed and multiple'. The Class A type follows the occupancies in the "
                "building (owner ruling 12.10.2026, P3 Ch47 Q2; ruling R13), so it is not "
                "evaluated until they are listed under 'most restrictive'."),
        code_ref="Ch 4, Table 4.3 row 1; ruling R13", page_ref="p.373-374",
        source_rule="p3_ch47_q2_mixed_class_a")
    chapters = [c.model_copy(update={"blocks": list(c.blocks) + [SectionBlock(
                    title="Class A - mixed occupancy", items=[item])]})
                if c.chapter_code == "FE" else c for c in r.chapters]
    return r.model_copy(update={"chapters": chapters})


def _secondary_hazard(o: str, b: Building) -> Optional[str]:
    """Hazard class a secondary occupancy brings to the R13 most-restrictive run.
    Storage / industrial: the class chosen for it, None when not chosen (owner ruling
    12.10.2026, Ch9 Q9). Animal housing: its group's class, None when not chosen (P3
    Storey Q4). Robotic / mechanical parking: HH (Ch9 Q7)."""
    if o == "storage_industrial":
        h = b.secondary_storage_hazard
        return None if h is None else ("HH" if h == "EH2" else h)
    if o == "animal_housing":
        # Owner ruling 12.10.2026, P3 Storey Q4: the group's #1.1.13 class, None (no
        # hazard brought) when no group is chosen, never the OH2 default.
        g = b.secondary_animal_housing_group
        return None if g is None else ANIMAL_HOUSING_GROUPS[g][0]
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
    # Owner ruling Q-3 (28.10.2026): one governing fire pump and tank for host + parking.
    chapters, attached = _merge_attached_parking_duties(chapters, attached)

    # Never leave a report section silently blank — append an explanatory
    # "not required" note to any chapter that produced zero requirements.
    for ch in chapters:
        _ensure_chapter_not_blank(ch, b)
    for ch in attached:
        _ensure_chapter_not_blank(ch, b)

    ol = compute_occupant_load(b)
    fa_summary = compute_fire_access(b, requires_wet_riser=wet, sprinklered=spr)

    r = ComplianceReport(
        building=b,
        chapters=chapters,
        requires_wet_riser=wet,
        high_ceiling=_eval_high_ceiling(fp_rules, b),
        attached_parking_chapters=attached,
        occupant_load=ol,
        fire_access=fa_summary,
        mixed_occupancy_note=_mixed_occupancy_note(b),
    )
    if b.occupancy == "mercantile_c" and not b.is_kiosk:
        r = _mercantile_c_scope(r)
    return r


# Owner ruling 13.10.2026, P4 Q5: a food truck or mercantile truck (Mercantile Group C)
# takes only its own items: Ch 4 extinguishers as mercantile, Ch 8 Table 8.14 item 34 /
# 35 heat detector, Ch 6 Table 6.5 item 12 and, with LPG, Ch 11 Table 11.3. Every other
# chapter is named not applicable. With no type chosen every chapter is NOT EVALUATED.
_TRUCK_KEEP = {
    "FE": None,    # whole chapter
    "LPG": None,   # whole chapter
    "FA": ("fa_aux_food_truck", "fa_aux_mercantile_truck_required"),
    "EL": ("el_mercantile_group_c", "el_amusement_standalone"),
}


def _mercantile_c_scope(r: ComplianceReport) -> ComplianceReport:
    b = r.building
    if b.mercantile_c_type is None:
        line = Requirement(
            system="Mercantile Group C Type - NOT EVALUATED",
            status="required",
            spec="Not evaluated: choose kiosk (permanent or temporary), food truck or "
                 "mercantile truck",
            detail=("Table 1.1 row 11 (p.50) Mercantile Group C covers kiosks, food trucks "
                    "and mercantile trucks. A kiosk follows Table 9.20.b row C (p.701) or "
                    "Table 9.21.b with Ch 1 Table 1.9 item 48 (p.98); a truck takes only its "
                    "own items. The type was not chosen, so this chapter is not evaluated "
                    "(owner ruling 13.10.2026, P4 Q5)."),
            code_ref="Ch 1, Table 1.1 row 11", page_ref="p.50",
            source_rule="p4_q5_mercantile_c_type")
        chapters = [c.model_copy(update={
            "blocks": [SectionBlock(title=f"{c.chapter_code} - NOT EVALUATED", items=[line])],
            "selected_branch": None, "selected_branch_section": None}) for c in r.chapters]
    else:
        kind = MERCANTILE_C_TYPES[b.mercantile_c_type].lower()
        chapters = []
        for c in r.chapters:
            keep = _TRUCK_KEEP.get(c.chapter_code, ())
            if keep is None:
                chapters.append(c)
                continue
            items = [it for blk in c.blocks for it in blk.items if it.source_rule in keep]
            if items:
                chapters.append(c.model_copy(update={
                    "blocks": [SectionBlock(title=f"{c.chapter_code} - {kind.capitalize()} "
                                                  f"(Mercantile Group C)", items=items)]}))
                continue
            chapters.append(c.model_copy(update={
                "selected_branch": None, "selected_branch_section": None,
                "blocks": [SectionBlock(title=f"{c.chapter_code} - Not applicable", items=[
                    Requirement(
                        system=f"{c.chapter_title} - Not Applicable to a {kind.capitalize()}",
                        status="not_required",
                        detail=(f"Table 1.1 row 11 (p.50) lists the {kind} under Mercantile "
                                f"Group C. A truck takes only its own items: Ch 4 fire "
                                f"extinguishers, Ch 8 Table 8.14 item 34 / 35 heat detector "
                                f"(p.511), Ch 6 Table 6.5 item 12 (p.419) and, with LPG "
                                f"cylinders, Ch 11 Table 11.3 (p.899). This chapter's "
                                f"building rows are not applied to a truck (owner ruling "
                                f"13.10.2026, P4 Q5)."),
                        source_rule="p4_q5_truck_not_applicable")])]}))
    return r.model_copy(update={
        "chapters": chapters, "attached_parking_chapters": [], "occupant_load": None,
        "fire_access": None, "high_ceiling": None, "requires_wet_riser": False})


# ---------------------------- Markdown renderer ------------------------------

def report_to_markdown(r: ComplianceReport) -> str:
    b = r.building
    L = []
    L.append("# UAE FLSC 2018 - Fire & Life Safety Requirements")
    if b.project_name:
        L.append(f"**Project:** {b.project_name}")
    L.append("")
    L.append("## Building profile")
    # Owner answer 12.10.2026, Ch9 Q6; owner rulings 13.10.2026, P4 Q1 / Q5
    _grp = f" ({b.occupancy_qualifier})" if b.occupancy_qualifier else ""
    L.append(f"- Occupancy: `{b.occupancy}`{_grp}")
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
