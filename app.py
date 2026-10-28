"""UAE FLSC 2018 - Multi-chapter Fire & Life Safety. Streamlit UI.

Chapter prefixes:
  FE  Fire Extinguishers (Ch 4)
  ES  Exit Signs (Ch 5)
  EL  Emergency Lighting (Ch 6)
  EVC Voice Evacuation (Ch 7)
  FA  Fire Detection & Alarm (Ch 8)
  FP  Fire Protection (Ch 9)
  SC  Smoke Control (Ch 10)
  LPG Liquefied Petroleum Gas (Ch 11)

Special-rooms / various-locations / equipment flags drive multiple chapters and live
in a SHARED 'Special Rooms & Equipment' master block. Per-chapter expanders carry
only items truly unique to that chapter.
"""
from __future__ import annotations

import datetime as _dt
import inspect
import json as _json
import re as _re
from pathlib import Path

import streamlit as st
import yaml as _yaml

from flsc_schema import (Building, OCCUPANCY_DEFS, default_hazard, DISCLAIMER,
                         HAZARD_NOT_CLASSIFIED, ANIMAL_HOUSING_GROUPS, BUSINESS_GROUPS,
                         MERCANTILE_C_TYPES)
from engine import evaluate, report_to_markdown, build_rule_lookup, lpg_input_stops
from export import (report_to_docx_bytes, report_to_pdf_bytes, report_to_xlsx_bytes,
                    field_label, inputs_rows, tool_revision,
                    export_file_name, branch_label)
from figures import figure_caption, figures_for
from submission_checklist import build_submission_checklist
from occupant_load import TABLE_3_13_ROWS
import ui

# Bilingual chapter titles (EN / AR) for report headings
CHAPTER_AR = {
    "FSA": "الوصول لمركبات الدفاع المدني",
    "MOE": "وسائل الهروب",
    "FE": "طفايات الحريق",
    "ES": "لافتات المخارج",
    "EL": "الإضاءة الطارئة",
    "EVC": "نظام الإخلاء الصوتي",
    "FA": "كشف وإنذار الحريق",
    "FP": "أنظمة الحماية من الحريق",
    "SC": "التحكم في الدخان",
    "LPG": "غاز البترول المسال",
    "ACC": "إمكانية الوصول",
    "EAP": "خطط الطوارئ والإخلاء",
}

def chapter_heading(code: str, title: str, bilingual: bool = True) -> str:
    ar = CHAPTER_AR.get(code, "")
    if bilingual and ar:
        return f"{code} — {title}  ·  {ar}"
    return f"{code} — {title}"



def _call_export(fn, report, kind: str | None, meta: dict | None = None):
    """Cloud can hot-reload app.py before export.py. Accept 1- and 2-arg fallbacks."""
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        params = {}
    if "meta" in params:
        return fn(report, kind, meta=meta) if kind is not None else fn(report, meta=meta)
    if kind is not None and len(params) >= 2:
        return fn(report, kind)
    return fn(report)


# Index of source_rule -> {file, kind, match} for the "Why triggered?" expander.
# Cached so it builds once per server start (rules YAMLs don't change at runtime).
@st.cache_data(show_spinner=False)
def _cached_rule_lookup():
    return build_rule_lookup()


# ---------------- Input help texts (audit UX-16, 28.10.2026) -----------------
# Every input says what it drives and cites the clause. For a yes/no input the cited
# lines are read off the rule YAMLs themselves (the code_ref / page_ref of every line
# the input switches on), so a rule fix also fixes the help text.
_HELP_BANNED = (chr(0x7E), chr(0x2248), chr(0xA7))   # tilde, approximately sign, section sign


@st.cache_data(show_spinner=False)
def _rule_refs_by_field() -> dict:
    """Building field -> [(code_ref, page_ref, system name)] for every rule line the
    field switches on directly: the rule's `flag`, or a `match` / `when` condition
    `field: true` / `field_is: true` on the rule or on the line."""
    out: dict = {}

    def pos_keys(cond) -> set:
        keys = set()
        if isinstance(cond, dict):
            for k, v in cond.items():
                if v is True and isinstance(k, str):
                    keys.add(k[:-3] if k.endswith("_is") else k)
        return keys

    for yf in sorted((Path(__file__).parent / "rules").glob("ch*.yaml")):
        try:
            data = _yaml.safe_load(yf.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        for rules in data.values():
            if not isinstance(rules, list):
                continue
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                trig = pos_keys(rule.get("match")) | pos_keys(rule.get("when"))
                if isinstance(rule.get("flag"), str):
                    trig.add(rule["flag"])
                for line in rule.get("systems") or []:
                    if not isinstance(line, dict):
                        continue
                    cref = line.get("code_ref") or rule.get("section")
                    pref = line.get("page_ref") or rule.get("page") or ""
                    if not cref:
                        continue
                    for f in trig | pos_keys(line.get("when")):
                        lst = out.setdefault(f, [])
                        if all((cref, pref) != (a, b) for a, b, _ in lst):
                            lst.append((str(cref), str(pref), str(line.get("name") or "")))
    return out


def _h(lead: str, *fields: str, limit: int = 5) -> str:
    """Help text: a hand-written lead (what the input is, with its definition clause)
    plus the rule lines the named Building fields switch on."""
    refs = []
    for f in fields:
        for cref, pref, name in _rule_refs_by_field().get(f, []):
            item = f"{name} ({cref}{', ' + pref if pref else ''})" if name else \
                f"{cref}{', ' + pref if pref else ''}"
            if item not in refs:
                refs.append(item)
    text = lead.strip()
    if refs:
        shown = refs[:limit]
        more = len(refs) - len(shown)
        text += " Ticking it adds: " + "; ".join(shown) + (
            f"; and {more} more line(s)" if more > 0 else "") + "."
    for bad in _HELP_BANNED:
        text = text.replace(bad, "")
    return text


# Glossary used by the sidebar "📖 Glossary" expander (Tier 2 UI #6).
# Acronyms / terms that appear in chapter outputs, ordered alphabetically.
GLOSSARY = [
    ("AFFL", "Above Finished Floor Level"),
    ("Aspiration", "Aspirating Smoke Detection — drawn-air analyser; very early warning (e.g. VESDA). Used in cold storage, server rooms, very high ceilings."),
    ("BUA", "Built-Up Area — the floor area enclosed by a building's exterior walls."),
    ("CD", "Civil Defence — the UAE federal authority enforcing the Fire & Life Safety Code."),
    ("CDGH-OP-25", "Operational reference of the UAE FLSC 2018 edition (Civil Defence Guideline Handbook, Operational Procedure 25)."),
    ("EH1 / EH2", "Extra Hazard Group 1 / 2 — sprinkler hazard classification (NFPA 13). EH1 = significant Class A/B combustibles; EH2 = quantities of flammable/combustible liquids."),
    ("ESFR", "Early Suppression Fast Response (sprinkler) — high-flow head designed to control + suppress a developing fire, common in rack storage."),
    ("ESV", "Emergency Shut-off Valve — required on LPG, gas, and some chemical lines, accessible from outside the protected area."),
    ("EVC", "Emergency Voice Communication / Voice-Evacuation system — programmable PA + tone system (Ch 7)."),
    ("FACP", "Fire Alarm Control Panel — the master detection/notification controller."),
    ("FCC", "Fire Command Centre — purpose-built control room with FACP, EVC, sprinkler annunciation, generator status, etc."),
    ("FFE", "Final Floor Elevation."),
    ("FHC", "Fire Hose Cabinet — wall-mounted cabinet containing a hose reel and (often) extinguishers."),
    ("GFA", "Gross Floor Area — total floor area summed across all storeys."),
    ("HC", "High Challenge (wall / fire wall) — enhanced fire-resistance assembly per code Ch 1."),
    ("HE", "Horizontal Exit — passage through a fire-rated wall into another fire compartment on the same level."),
    ("HH", "High Hazard — sprinkler hazard classification with rapidly developing fires (e.g. flammable liquid warehouse)."),
    ("HoE", "House of Expertise — UAE Civil Defence designation for an approved fire consultancy."),
    ("Hose Reel", "Manually operated water hose, typically 30 m × 19 mm, fed from a 250 gpm pump per UAE Ch 9."),
    ("IDF / MDF", "Intermediate / Main Distribution Frame — telecoms cross-connect rooms."),
    ("IS", "Intrinsically Safe — electrical equipment certified for hazardous (explosive) atmospheres."),
    ("K-factor", "Sprinkler discharge coefficient (US units): flow Q = K·√P. K11.2 / K25.2 etc."),
    ("KG", "Kindergarten (educational Group A in UAE FLSC)."),
    ("LEL", "Lower Explosive Limit — minimum gas concentration in air that will ignite. UAE LPG code sets gas-leak alarm at 15% LEL (low) / 30% LEL (high)."),
    ("LH", "Light Hazard — sprinkler hazard classification with limited combustibles (offices, residential, schools)."),
    ("LPG", "Liquefied Petroleum Gas (Ch 11)."),
    ("LV / MV", "Low Voltage / Medium Voltage electrical rooms. The code names LV and HV rooms only; this tool treats an MV room as HV (ruling R12)."),
    ("MCP", "Manual Call Point — wall-mounted manual fire-alarm push station, 1.2 m AFFL, every 61 m."),
    ("MOE", "Means of Egress (Ch 3)."),
    ("MRI", "Magnetic Resonance Imaging room (healthcare auxiliary, Table 9.30.S)."),
    ("MRL", "Machine Room-Less elevator — has no separate machine room (uncheck `has_lift_machine_room` if applicable)."),
    ("NFPA", "National Fire Protection Association (US) — UAE FLSC defers to NFPA 10/13/14/72/96 etc. in many sections."),
    ("NS / S", "Non-Sprinklered / Sprinklered — Table 3.16 column heads (Means of Egress)."),
    ("OH1 / OH2", "Ordinary Hazard Group 1 / 2 — sprinkler hazard classifications (NFPA 13)."),
    ("OL", "Occupant Load — number of occupants used to size egress (Tables 3.13/3.14)."),
    ("OT", "Operating Theatre (healthcare auxiliary)."),
    ("Pa", "Pascals — pressure unit used for stair / lobby pressurisation (UAE Ch 10 Table 10.3.a: 12.5–45 Pa)."),
    ("PAS", "Positive Alarm Sequence — timed alarm delay (typically 15 s / 180 s / 240 s) to let staff investigate before mass notification."),
    ("PRDP", "Pressure Reducing Distribution Panel — Stage-2 regulator + ESV serving a single kitchen / apartment in central LPG distribution."),
    ("PRV", "Pressure Relief Valve — required on every LPG container; replace every 10 years per Table 11.14."),
    ("RMU", "Ring Main Unit — medium-voltage switchgear in a small dedicated room."),
    ("STI", "Speech Transmission Index — voice-evacuation intelligibility metric."),
    ("UL / FM", "Underwriters Laboratories / Factory Mutual — US product-listing bodies (Ch 9 #6.1.1 / #6.1.3, p.770: equipment must be listed, approved and registered by the Civil Defence Material Approval Department; UL, FM, LPS and EN listings are among the accepted standards)."),
    ("UPS", "Uninterruptible Power Supply room (electrical auxiliary, Table 9.30.U)."),
    ("VESDA", "Very Early Smoke Detection Apparatus — brand-leading aspiration smoke detector."),
    ("Wet Riser", "Vertical water-filled pipe with fire-brigade landing valves on each floor; sized 750 gpm (2 standpipes) or 1000 gpm (3+ standpipes) @ 6.9 bar."),
    ("Yard Hydrant", "External fire-brigade hydrant on a dedicated water network (not shared with irrigation). UAE typically 1000 gpm @ 6.9 bar / 90-min tank for infrastructure."),
]


# ----- Cached evaluate to remove the 0.4 s (about) lag on every input change -----
@st.cache_data(show_spinner=False)
def _cached_evaluate(building_json: str):
    """Cache compliance reports keyed on the JSON-serialised Building.
    Streamlit hashes the JSON string and serves the cached ComplianceReport when
    the same input recurs (very common during sidebar tweaking)."""
    return evaluate(Building.model_validate_json(building_json))


OCCUPANCY_OPTIONS = {
    "Villa": ["villa_private", "villa_commercial"],
    "Residential / Lodging": ["residential", "hotel_a", "hotel_b", "hotel_c",
                               "hostel", "labour_accommodation", "staff_accommodation"],
    "Business / Office": ["business"],
    "Assembly": ["assembly_a", "assembly_b", "assembly_c"],
    "Mall": ["mall_covered", "mall_open", "mall_mixed"],
    "Mercantile": ["mercantile_a", "mercantile_b", "mercantile_c"],   # P4 (13.10.2026)
    "Education": ["education_a", "education_b", "education_c"],
    "Healthcare": ["healthcare_a", "healthcare_b", "healthcare_c"],
    "Daycare": ["daycare_a", "daycare_b", "daycare_c"],
    "Detention": ["detention_a", "detention_b", "detention_c"],
    "Parking": ["parking_enclosed", "parking_open"],
    "Storage / Industrial": ["storage_industrial", "motor_fuel_dispensing"],
    "Mixed / Underground": ["mixed_multiple", "high_depth_underground",
                            "low_depth_underground", "animal_housing"],
    # Audit ENG-22: Ch 9 #4.10 / Table 9.26 (p.723), yard-hydrant network only.
    "Infrastructure": ["infrastructure"],
}
OCC_FLAT = [(g, occ) for g, items in OCCUPANCY_OPTIONS.items() for occ in items]


def _occ_label(code: str) -> str:
    """Short, human-friendly label for an occupancy code — the part of its
    definition before ' - ', e.g. 'hotel_a' -> 'Hotel Group A'. Falls back to
    the raw code if no definition is found."""
    defn = OCCUPANCY_DEFS.get(code, code)
    return defn.split(" - ", 1)[0].strip() if " - " in defn else code


# ---------------- Scenario load guard ----------------------------------------
# A loaded value outside the widget's range would be clamped silently by
# st.number_input (e.g. a height of -5 m shown as 0). Refuse the file instead
# and name every bad value.
_SCENARIO_LIMITS = {
    # key: (label, minimum, whole number?)
    "height_m_input": ("Building height", 0.0, False),
    "floors_above_input": ("Floors above grade", 1, True),
    "floors_below_input": ("Basements", 0, True),
    "ground_bua_input": ("Ground-floor BUA", 0.0, False),
    "basement_bua_input": ("Basement BUA", 0.0, False),
    "gfa_input": ("Total GFA", 0.0, False),
    "plot_area_input": ("Plot area", 0.0, False),
    "depth_below_grade_input": ("Depth below grade", 0.0, False),
    "parking_area_m2_input": ("Parking area", 0.0, False),
    # Owner ruling 12.10.2026, P3 App Q2 (blank allowed: not entered)
    "parking_height_m_input": ("Parking height above the fire access level", 0.0, False),
    "parking_basement_levels_input": ("Parking basement levels", 0, True),
    # Owner ruling 12.10.2026, P3 follow-up F-a3 (blank allowed: building depth used)
    "parking_depth_m_input": ("Parking depth below the fire access level", 0.0, False),
    "ceiling_height_m_input": ("Ceiling height", 0.0, False),
    "corridor_length_m": ("Corridor length", 0.0, False),
    "assembly_area_m2_input": ("Assembly-hall area", 0.0, False),
    "tunnel_length_m_input": ("Tunnel length", 0.0, False),
    # Table 9.27 storage inputs (#4.1.13 / #4.1.14, Group T)
    "max_unit_area_m2_input": ("Largest unit compartment area", 0.0, False),
    "sum_gf_bua_m2_input": ("Sum of GF BUAs on the plot", 0.0, False),
    "ast_storage_area_m2_input": ("Aboveground tank storage area", 0.0, False),
    "ast_tank_capacity_m3_input": ("Aboveground tank capacity", 0.0, False),
    "exit_stairs_input": ("Exit stairs", 1, True),
    # Table 9.21.e outlet area (audit CH9B-14)
    "commercial_outlet_gf_bua_m2_input": ("Commercial outlet GF BUA", 0.0, False),
    # Ch 3 / Ch 2 inputs, owner rulings 12.10.2026 (Ch3 Q1-Q5)
    "largest_storey_area_m2_input": ("Largest storey area", 0.0, False),
    "mall_gla_m2_input": ("Mall gross leasable area", 0.0, False),
    "building_volume_m3_input": ("Building volume", 0.0, False),
    "use_area_count_input": ("Number of per-use areas", 0, True),
    # Ch3 Q2 per-use areas: up to 10 rows of (Table 3.13 row, area m2).
    **{f"use_area_m2_{i}": (f"Per-use area {i + 1}", 0.0, False) for i in range(10)},
}
USE_AREA_MAX = sum(1 for k in _SCENARIO_LIMITS if k.startswith("use_area_m2_"))
USE_AREA_KEYS = [k for i in range(USE_AREA_MAX)
                 for k in (f"use_area_row_{i}", f"use_area_m2_{i}")]


# Owner answer 12.10.2026, F6: per-storey table <-> data editor frame. "count" =
# identical storeys (owner ruling 12.10.2026, P3 Storey Q1); a line without it is 1.
_STOREY_COLS = ("storey", "row", "area_m2", "count")


def _storey_table_frame(lines):
    import pandas as pd
    lines = [ln for ln in (lines or []) if isinstance(ln, dict)]
    return pd.DataFrame({
        "storey": pd.Series([ln.get("storey") for ln in lines], dtype="object"),
        "row": pd.Series([ln.get("row") for ln in lines], dtype="object"),
        "area_m2": pd.Series([ln.get("area_m2") for ln in lines], dtype="float64"),
        "count": pd.Series([ln.get("count", 1) for ln in lines], dtype="Int64"),
    })


def _storey_table_records(df) -> list:
    """Editor frame -> saved lines. Fully blank lines (a row just added) are dropped;
    any other line is kept as entered, and the report names what it lacks."""
    out = []
    for rec in df.to_dict("records"):
        nm, rw, ar, ct = (rec.get(k) for k in _STOREY_COLS)
        nm = nm.strip() if isinstance(nm, str) else ""
        rw = rw if isinstance(rw, str) and rw else None
        ar = float(ar) if isinstance(ar, (int, float)) and ar == ar else None
        # Identical storeys (P3 Storey Q1): blank = 1; a whole number is stored as int;
        # anything else is kept as entered and the app stops on it by name.
        try:
            blank = ct is None or bool(ct != ct)
        except (TypeError, ValueError):     # pandas NA
            blank = True
        if blank:
            ct = 1
        elif isinstance(ct, (int, float)) and not isinstance(ct, bool) and float(ct).is_integer():
            ct = int(ct)
        if nm or rw or ar is not None:
            out.append({"storey": nm, "row": rw, "area_m2": ar, "count": ct})
    return out


def _storey_count(ct):
    """Identical-storeys count of a saved line (owner ruling 12.10.2026, P3 Storey Q1):
    None (a line saved before the column) = 1; a whole number (2 or 2.0) = int; anything
    else is returned as is, and the app stops on it by name."""
    if ct is None:
        return 1
    if (isinstance(ct, (int, float)) and not isinstance(ct, bool)
            and ct == ct and abs(ct) != float("inf") and float(ct).is_integer()):
        return int(ct)
    return ct


def _invalid_scenario_values(data: dict) -> list:
    # Yes/no keys that do not start with has_ / is_ (audit ENG-23 load type check).
    _BOOL_KEYS = {"pump_room_at_grade", "gf_beyond_100m_from_hydrant", "villa_converted_use",
                  "fuel_dispensing_multistorey", "tower_setback_over_30m", "mercantile_multi_tenant"}
    # Choice widgets: the stored value must be one of the options (audit ENG-23).
    _CHOICE_KEYS = {
        "attached_parking_kind_radio": ("Parking type", ("Enclosed parking", "Open parking")),
        "gas_system_radio": ("Gas system type", (
            "No gas system", "LPG tanks (aboveground / roof / podium)",
            "Gas infrastructure connection (central piped supply)",
            "Gas cylinders (villa / domestic / small commercial)")),
        "wet_riser_radio": ("Number of standpipes", (
            "2 standpipes (Fire pump 750 gpm @ 6.9 bar)",
            "3 or more standpipes (Fire pump 1000 gpm @ 6.9 bar)")),
        "motor_fuel_group_radio": ("Motor fuel group", (
            "Group A - mini-marts/restaurants/retail/service as INDIVIDUAL buildings (sprinklers + 300 gpm @ 4.5 bar)",
            "Group B - restaurants/bakeries within a single mini mart, service/repair stations, fleet, marine (hose reel only + 50 gpm @ 6.9 bar)",
            "Group C - mini-mart ONLY without service/repair, OR EV charging (extinguishers only - no water-based system)")),
        "tunnel_kind_radio": ("Tunnel kind", ("Road / Rail tunnel", "Cable tunnel")),
        "height_datum_input": ("Height datum", ("grade", "occupiable_ceiling")),
        "construction_type_input": ("Construction type", (
            "unspecified", "type_i", "type_ii", "type_iii", "type_iv", "type_v")),
        "hazard_override_input": ("Hazard class override", ("auto", "LH", "OH1", "OH2", "HH")),
        "tent_marquee_kind_input": ("Tent / marquee / site office (Table 9.21.f)", (
            "none", "temporary", "permanent", "commercial_desert", "site_office_short",
            "site_office_long", "small_detached")),
    }
    bad = []
    for key, (label, lo, whole) in _SCENARIO_LIMITS.items():
        if key not in data or data[key] is None:
            continue
        v = data[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            bad.append(f"{label} = {v!r} (not a number)")
        elif whole and float(v) != int(v):
            bad.append(f"{label} = {v} (must be a whole number)")
        elif v < lo:
            bad.append(f"{label} = {v} (minimum {lo})")
    # Audit ENG-23: a stored yes/no is a real bool ("false" never ticks a box), and a
    # stored choice is one of the widget's options (never re-pointed to another one).
    for key, v in data.items():
        if (key.startswith(("has_", "is_")) or key in _BOOL_KEYS) and not isinstance(v, bool):
            bad.append(f"{key} = {v!r} (not true / false)")
    for key, (label, allowed) in _CHOICE_KEYS.items():
        if key in data and data[key] not in allowed:
            bad.append(f"{label} = {data[key]!r} (not a listed option)")
    occ = data.get("occupancy_chosen")
    if occ is not None and (not isinstance(occ, (list, tuple)) or tuple(occ) not in OCC_FLAT):
        bad.append(f"Occupancy = {occ!r} (not a listed occupancy)")
    for key in ("project_name_input", "project_notes_input"):
        if key in data and not isinstance(data[key], str):
            bad.append(f"{key} = {data[key]!r} (not text)")
    _enums = {
        "storage_hazard_input": ("Storage hazard class", (None, "LH", "OH1", "OH2", "HH")),
        "storage_commodity_input": ("Storage commodity", (
            "none", "class_i_iv", "plastics_rubber", "tires", "rolled_paper")),
        "hangar_group_input": ("Aircraft hangar group", ("I", "II_III", "IV")),
        # Owner ruling 12.10.2026, Ch9 Q9
        "secondary_storage_hazard_input": ("Secondary storage hazard class", (
            None, "LH", "OH1", "OH2", "HH", "EH2")),
        # Owner ruling 12.10.2026, P3 Storey Q4
        "secondary_animal_housing_group_input": ("Secondary animal housing group", (
            None, "A", "B", "C")),
        # Phase 3 CH10-16: Table 10.27 item 8 / item 14
        "theater_cinema_kind_input": ("Theatre / cinema kind", (None, "cinema", "theatre", "both")),
        # Owner ruling 12.10.2026, P3 Ch11 Q6: #3.2.2
        "lpg_flame_effect_show_input": ("Flame effect show", (None, "indoor", "outdoor", "both")),
        # Owner ruling 12.10.2026, P3 follow-up F-a1-1: #2.2.4, required, no pre-fill
        "new_or_modified_building_input": ("New or modified building", (None, "new", "existing")),
        # Owner rulings 13.10.2026, P4 Q1 / Q5, required, no pre-fill
        "business_group_input": ("Business group", (None, "A", "B", "C")),
        "mercantile_c_type_input": ("Mercantile Group C type", (
            None, "kiosk_permanent", "kiosk_temporary", "food_truck", "mercantile_truck")),
        "kiosk_location_input": ("Kiosk location (Table 1.9 item 48 iii)", (
            None, "sprinklered_or_mall", "other")),
    }
    # Ch3 Q2 per-use areas (owner ruling 12.10.2026): known Table 3.13 rows, at most
    # as many rows as the sidebar offers.
    from occupant_load import TABLE_3_13_ROWS as _rows
    n_max = sum(1 for k in _SCENARIO_LIMITS if k.startswith("use_area_m2_"))
    _enums.update({f"use_area_row_{i}": (f"Per-use area {i + 1} Table 3.13 row", tuple(_rows))
                   for i in range(n_max)})
    for key, (label, allowed) in _enums.items():
        if key in data and data[key] not in allowed:
            bad.append(f"{label} = {data[key]!r} (not a listed option)")
    n_use = data.get("use_area_count_input")
    if isinstance(n_use, int) and not isinstance(n_use, bool) and n_use > n_max:
        bad.append(f"Number of per-use areas = {n_use} (maximum {n_max})")
    # Owner answer 12.10.2026, Ch9 Q6: animal housing group A / B / C (#1.1.13).
    if data.get("animal_housing_group_input") not in (None, "A", "B", "C"):
        bad.append(f"Animal housing group = {data['animal_housing_group_input']!r} "
                   "(not a listed option)")
    # Owner answer 12.10.2026, F6: per-storey table, a list of {storey, row, area_m2,
    # count}.
    # A blank storey name or row is kept (the report names it); a wrong type, an
    # unknown row or a negative / non-numeric area is refused here.
    tbl = data.get("storey_table_input")
    if tbl is not None:
        if not isinstance(tbl, list):
            bad.append(f"Per-storey table = {tbl!r} (not a list)")
        elif len(tbl) > 200:
            bad.append(f"Per-storey table has {len(tbl)} lines (maximum 200)")
        else:
            for i, ln in enumerate(tbl, 1):
                if not isinstance(ln, dict) or set(ln) - {"storey", "row", "area_m2", "count"}:
                    bad.append(f"Per-storey table line {i} = {ln!r} (not a storey / row / "
                               "area / count line)")
                    continue
                # Owner ruling 12.10.2026, P3 Storey Q1: identical storeys, a whole number
                # of at least 1 (a file saved before the column has none: it loads as 1).
                ct = ln.get("count")
                if ct is not None and (isinstance(ct, bool) or not isinstance(ct, (int, float))
                                       or not (1 <= ct < float("inf"))
                                       or not float(ct).is_integer()):
                    bad.append(f"Per-storey table line {i} identical storeys = {ct!r} (a whole "
                               "number of at least 1)")
                nm, rw, ar = ln.get("storey"), ln.get("row"), ln.get("area_m2")
                if nm is not None and not isinstance(nm, str):
                    bad.append(f"Per-storey table line {i} storey = {nm!r} (not text)")
                if rw is not None and rw not in _rows:
                    bad.append(f"Per-storey table line {i} Table 3.13 row = {rw!r} "
                               "(not a listed option)")
                if ar is not None and (isinstance(ar, bool) or not isinstance(ar, (int, float))):
                    bad.append(f"Per-storey table line {i} area = {ar!r} (not a number)")
                elif ar is not None and (ar != ar or ar < 0):
                    bad.append(f"Per-storey table line {i} area = {ar} (minimum 0)")
    mode = data.get("mixed_occupancy_mode_input")
    if mode is not None and mode not in ("none", "most_restrictive", "separated"):
        bad.append(f"Mixed occupancy mode = {mode!r} (not a listed mode)")
    secs = data.get("secondary_occupancies_input")
    if secs is not None:
        known = {occ for _, occ in OCC_FLAT}
        if not isinstance(secs, list):
            bad.append(f"Secondary occupancies = {secs!r} (not a list)")
        else:
            bad += [f"Secondary occupancy {o!r} (not a known occupancy)" for o in secs if o not in known]
    return bad


# ---------------- Master 'Check all' helper ----------------------------------
def _touch(*keys) -> None:
    """Audit UX-08: remember that the user set these inputs themselves, so the
    'Assumptions used' box no longer lists them as defaults."""
    t = dict(st.session_state.get("_touched") or {})
    for k in keys:
        t[k] = True
    st.session_state["_touched"] = t


def _register_master(master_key: str, child_keys: list[str]):
    if master_key not in st.session_state:
        st.session_state[master_key] = False
    for k in child_keys:
        st.session_state.setdefault(k, False)

    def _cb():
        v = st.session_state[master_key]
        for k in child_keys:
            st.session_state[k] = v
        _touch(*child_keys)
    return _cb


# ----------------- SHARED Special Rooms & Equipment groups -----------------
SPECIAL_ROOMS_KEYS = [
    "has_anesthetizing_room", "has_battery_charger_room", "has_bms_room",
    "has_battery_room", "has_computer_room", "has_control_room",
    "has_diesel_generator_room", "has_main_electrical_room", "has_ahu_room",
    "has_lv_mv_room", "has_mv_room", "has_transformer_room_utility",
    "has_transformer_room_private", "has_lift_machine_room",
    "has_main_telephone_room", "has_main_server_room", "has_rmu_idf_mdf_room",
    "has_gsm_room", "has_operation_theater", "has_mri_scanning_room",
    "has_records_room", "has_ups_room", "has_cold_freezer_room",
    "has_fire_pump_room",
]
VARIOUS_LOCATIONS_KEYS = [
    "has_atrium", "has_rain_screen_glazing", "has_stairs", "has_elevator",
    "has_bathrooms_with_heaters", "has_laundry_storage_rooms", "has_pantries",
    "has_permanent_stages", "has_roof_lpg_or_restaurant", "has_garbage_chute",
    "has_high_ceiling", "has_tunnel", "has_exterior_balconies",
    "has_roof_restaurant_assembly", "has_food_trucks",
]
EQUIPMENT_KEYS = [
    "has_commercial_kitchen", "has_flammable_liquid_tanks",
    "has_cable_spread_areas", "has_boilers", "has_cooling_towers",
    "has_oil_filled_transformers", "has_bulk_oil_storage",
    "has_bulk_flammable_liquid_storage", "has_bulk_flammable_gas_storage",
    "has_bulk_flammable_solid_storage", "has_high_hazard_logistics",
    "has_chemical_warehouse", "has_explosives", "has_processing_plant",
]

# Per-chapter unique groups
FE_KEYS = [
    "has_class_b_storage_zones", "has_combustible_metals", "has_group_a_plastic_storage",
    "has_hv_or_heavy_electrical", "has_parking_area",
]
ES_FEATURE_KEYS = ["has_evacuation_elevator", "has_horizontal_exits", "has_dead_end_paths"]
ES_ZONE_KEYS = [
    "has_amusement_confounding", "has_nightclub_disco", "has_theater_cinema",
    "has_nursery_within", "has_auditorium_within", "has_hh_storage_zones",
    "has_mall_play_food_cinema", "has_robotic_parking",
    "villa_converted_use", "fuel_dispensing_multistorey",
]

# First-load defaults (also what a Load starts from: audit ENG-12, Load replaces).
FIRST_LOAD_DEFAULTS = {
    "has_stairs": True, "has_elevator": True,
    "has_diesel_generator_room": False, "has_main_electrical_room": True,
    "has_main_telephone_room": True, "has_lift_machine_room": True,
    "has_fire_pump_room": True,
    # Audit ENG-11: parking is evaluated only when the user ticks it.
    "has_parking_area": False,
    "has_dead_end_paths": True,
    # Geometry inputs are session_state-driven so presets can write to them
    "height_m_input": 45.0,
    "floors_above_input": 12,
    "floors_below_input": 1,
    "ground_bua_input": 800.0,
    "basement_bua_input": 800.0,
    "gfa_input": 8000.0,
    "plot_area_input": 4000.0,
    # Verifier re-check 28.10.2026: the sample states its one basement's depth, so the
    # first screen is a complete report (3.5 m per basement, as the presets).
    "depth_below_grade_input": 3.5,
    # Owner ruling 12.10.2026, P3 follow-up F-a1-1: "New or modified building" is a
    # required choice with no pre-fill (new_or_modified_building_input starts blank).
}
for key, default in FIRST_LOAD_DEFAULTS.items():
    st.session_state.setdefault(key, default)


def _apply_loaded_scenario(state, data: dict, save_keys: list) -> tuple:
    """Audit ENG-12 / ENG-23: Load REPLACES the session, never merges. Every saved key
    is first cleared (its widget starts from its default, the same as a new session),
    then the file is laid over it through the save-key allow-list. The occupancy pickers
    are set from the saved occupancy. Returns (keys in the file that are not inputs,
    inputs the file lacks: they took their defaults)."""
    derived = ["occupancy_category_select", "occupancy_sub_select", "_last_occupancy"]
    for k in list(save_keys) + derived:
        if k in state:
            del state[k]
    for k, v in FIRST_LOAD_DEFAULTS.items():
        state[k] = v
    # Owner ruling Q-4 (28.10.2026): an old file's "is_single_tenant_storage: true" is
    # single tenant; false or absent stays blank (a required choice, never multi by default).
    if "is_single_tenant_storage" in data and "storage_tenancy_input" not in data:
        data = dict(data)
        if data.pop("is_single_tenant_storage") is True:
            data["storage_tenancy_input"] = "single"
    ignored = sorted(k for k in data if k not in save_keys)
    for k in save_keys:
        if k not in data:
            continue
        v = data[k]
        # occupancy_chosen was serialised as a list (from a tuple); restore the tuple
        if k == "occupancy_chosen" and isinstance(v, list) and len(v) == 2:
            v = tuple(v)
        state[k] = v
    occ = state.get("occupancy_chosen")
    if isinstance(occ, tuple) and len(occ) == 2:
        state["occupancy_category_select"], state["occupancy_sub_select"] = occ
        state["_last_occupancy"] = occ[1]
    # Audit UX-05: flags cleared for the previous project are not restored into this one.
    state["_cleared_flags"] = {}
    state["_flag_change_note"] = None
    defaulted = [k for k in save_keys if k not in data]
    return ignored, defaulted

# =============================================================================
# Occupancy-aware flag auto-clear (silent UX, no nagging)
# =============================================================================
# When the user picks an occupancy that doesn't typically have certain rooms
# / equipment, those flags are auto-unchecked in session_state. The user can
# still tick anything manually if their specific project needs it — no
# warnings, no flags, just sensible defaults.
#
# Defined as a dict so we can mirror the same logic for villa, petrol station,
# animal housing, family daycare, etc.

# Villa-specific incompatible flag list (single-family dwellings).
VILLA_INCOMPATIBLE_FLAGS = [
    # Special Rooms — none of these are present in a typical villa
    "has_anesthetizing_room", "has_battery_charger_room", "has_bms_room",
    "has_battery_room", "has_computer_room", "has_control_room",
    "has_diesel_generator_room", "has_main_electrical_room", "has_ahu_room",
    "has_lv_mv_room", "has_mv_room", "has_transformer_room_utility",
    "has_transformer_room_private", "has_lift_machine_room",
    "has_main_telephone_room", "has_main_server_room", "has_rmu_idf_mdf_room",
    "has_gsm_room", "has_operation_theater", "has_mri_scanning_room",
    "has_records_room", "has_ups_room", "has_cold_freezer_room",
    "has_fire_pump_room",
    # Various locations — stair shaft sprinklers + elevator pit sprinklers
    # don't apply to villas (Ch 9 villa branches don't require sprinklers).
    "has_stairs", "has_elevator",
    "has_atrium", "has_rain_screen_glazing", "has_bathrooms_with_heaters",
    "has_laundry_storage_rooms", "has_pantries", "has_permanent_stages",
    "has_roof_lpg_or_restaurant", "has_roof_restaurant_assembly", "has_garbage_chute", "has_tunnel",
    # Equipment / commercial / industrial
    "has_commercial_kitchen", "has_flammable_liquid_tanks",
    "has_cable_spread_areas", "has_boilers", "has_cooling_towers",
    "has_oil_filled_transformers", "has_bulk_oil_storage",
    "has_bulk_flammable_liquid_storage", "has_bulk_flammable_gas_storage",
    "has_bulk_flammable_solid_storage", "has_high_hazard_logistics",
    "has_chemical_warehouse", "has_explosives", "has_processing_plant",
    # FE hazard add-ons
    "has_class_b_storage_zones", "has_combustible_metals", "has_group_a_plastic_storage",
    "has_hv_or_heavy_electrical",
    # ES special zones
    "has_amusement_confounding", "has_nightclub_disco", "has_theater_cinema",
    "has_nursery_within", "has_auditorium_within", "has_hh_storage_zones",
    "has_mall_play_food_cinema", "has_robotic_parking",
    "fuel_dispensing_multistorey",
    # Audit ENG-11: no parking sub-evaluation unless the user ticks it.
    "has_parking_area",
]


# "Infrastructure" is a yard-hydrant network only — NOT a building. Clear
# every building-level flag.
INFRASTRUCTURE_INCOMPATIBLE_FLAGS = VILLA_INCOMPATIBLE_FLAGS


# Animal housing — typically a single-storey stable / kennel / barn.
ANIMAL_HOUSING_INCOMPATIBLE_FLAGS = [
    "has_elevator", "has_lift_machine_room",
    "has_diesel_generator_room", "has_main_telephone_room",
    "has_fire_pump_room", "has_parking_area",
    "has_commercial_kitchen", "has_atrium", "has_garbage_chute",
    "has_anesthetizing_room", "has_operation_theater", "has_mri_scanning_room",
    "has_records_room", "has_ups_room", "has_main_server_room",
    "has_rmu_idf_mdf_room", "has_gsm_room", "has_bms_room",
    "has_battery_charger_room", "has_battery_room", "has_computer_room",
    "has_control_room", "has_cold_freezer_room",
]


# Daycare Group B (adult day care, Table 1.1 row 10, p.50) — often in a villa-sized building.
DAYCARE_B_INCOMPATIBLE_FLAGS = [
    "has_elevator", "has_lift_machine_room", "has_diesel_generator_room",
    "has_main_telephone_room", "has_fire_pump_room",
    "has_commercial_kitchen", "has_atrium",
    "has_anesthetizing_room", "has_operation_theater",
    "has_mri_scanning_room", "has_main_server_room",
    "has_rmu_idf_mdf_room", "has_gsm_room",
]


# Daycare Group C (group not printed in Table 1.1 row 10) — villa-like in scale.
DAYCARE_C_INCOMPATIBLE_FLAGS = VILLA_INCOMPATIBLE_FLAGS


# Motor fuel dispensing (petrol station) — single-storey canopy + small
# kiosk. Group A may have a fire pump room; Group B/C typically don't.
PETROL_STATION_INCOMPATIBLE_FLAGS = [
    "has_stairs", "has_elevator", "has_lift_machine_room",
    "has_main_telephone_room", "has_diesel_generator_room",
    "has_atrium", "has_garbage_chute", "has_pantries",
    "has_anesthetizing_room", "has_battery_charger_room", "has_bms_room",
    "has_battery_room", "has_computer_room",
    "has_lv_mv_room", "has_mv_room", "has_transformer_room_utility",
    "has_transformer_room_private",
    "has_main_server_room", "has_rmu_idf_mdf_room", "has_gsm_room",
    "has_operation_theater", "has_mri_scanning_room",
    "has_records_room", "has_ups_room", "has_cold_freezer_room",
    "has_parking_area",
    "has_commercial_kitchen", "has_flammable_liquid_tanks",
    "has_bulk_oil_storage", "has_bulk_flammable_gas_storage",
    "has_bulk_flammable_solid_storage", "has_high_hazard_logistics",
    "has_chemical_warehouse", "has_explosives", "has_processing_plant",
    "has_permanent_stages", "has_amusement_confounding",
    "has_nightclub_disco", "has_theater_cinema",
    "has_nursery_within", "has_auditorium_within",
    "has_hh_storage_zones", "has_mall_play_food_cinema",
    "has_robotic_parking", "villa_converted_use",
]


# Mercantile Group A (Table 1.1: hardware, paint, furniture stores, showrooms, small
# restaurants) - typically no lift / diesel gen.
MERCANTILE_A_INCOMPATIBLE_FLAGS = [
    "has_elevator", "has_lift_machine_room",
    "has_diesel_generator_room",
    "has_anesthetizing_room", "has_operation_theater",
    "has_mri_scanning_room",
]


# Map every occupancy to its incompatible-flag list. Occupancies absent from
# the dict use the universal first-load defaults (typical multi-family/
# commercial building) — no auto-clear happens for them.
INCOMPATIBLE_FLAGS_BY_OCC = {
    "villa_private":          VILLA_INCOMPATIBLE_FLAGS,
    "villa_commercial":       VILLA_INCOMPATIBLE_FLAGS,
    "infrastructure":         INFRASTRUCTURE_INCOMPATIBLE_FLAGS,
    "animal_housing":         ANIMAL_HOUSING_INCOMPATIBLE_FLAGS,
    "daycare_b":              DAYCARE_B_INCOMPATIBLE_FLAGS,
    "daycare_c":              DAYCARE_C_INCOMPATIBLE_FLAGS,
    "motor_fuel_dispensing":  PETROL_STATION_INCOMPATIBLE_FLAGS,
    "mercantile_a":           MERCANTILE_A_INCOMPATIBLE_FLAGS,
    "hostel":                 ["has_parking_area"],
    "parking_enclosed":       ["has_main_telephone_room"],
    "parking_open":           ["has_diesel_generator_room",
                                "has_main_telephone_room"],
    "storage_industrial":     ["has_elevator", "has_lift_machine_room"],
}


# Flags that apply to listed occupancies only; every other occupancy clears them on an
# occupancy change. is_mercantile_group_c is the old 'Mercantile Group C (stand-alone)'
# tick, kept only so an older file stops until it is resolved (owner ruling 13.10.2026,
# P4 Q6). Post office: owner ruling 13.10.2026, P4 Q2.
OCC_ONLY_FLAGS = {
    "is_mercantile_group_c": ("mercantile_a", "mercantile_b"),
    "is_post_office": ("business",),
}


def _p4_building_kwargs(occupancy: str) -> dict:
    """Owner rulings 13.10.2026, P4 Q1-Q5: the Business group, post office, Mercantile
    Group C type and kiosk location, each passed only where it applies."""
    ss = st.session_state
    grp = ss.get("business_group_input") if occupancy == "business" else None
    mtype = ss.get("mercantile_c_type_input") if occupancy == "mercantile_c" else None
    loc = (ss.get("kiosk_location_input")
           if mtype in ("kiosk_permanent", "kiosk_temporary") else None)
    return {"business_group": grp,
            "is_post_office": bool(ss.get("is_post_office")) and grp == "B",
            "mercantile_c_type": mtype,
            "kiosk_in_sprinklered_area_or_mall": None if loc is None else loc == "sprinklered_or_mall"}


def _incompatible_flags(occupancy: str) -> list:
    flags = list(INCOMPATIBLE_FLAGS_BY_OCC.get(occupancy, []))
    flags += [f for f, occs in OCC_ONLY_FLAGS.items() if occupancy not in occs]
    return flags


def _apply_incompatible_flag_reset(occupancy: str, remember: bool = True,
                                   state=None) -> tuple:
    """Set the flags that do not apply to the occupancy to False. Does NOT touch flags
    that are compatible: the user keeps their state.

    Audit UX-05 (28.10.2026): a flag cleared this way is remembered, and it is ticked
    again as soon as the user returns to an occupancy it applies to (residential ->
    villa -> residential keeps the stairs, lift, pump room, ...). Both lists are kept
    in '_flag_change_note' so the sidebar names them. A preset or a Load starts afresh
    (remember=False: nothing is remembered or restored). Returns (cleared, restored)."""
    ss = st.session_state if state is None else state
    stash = dict(ss.get("_cleared_flags") or {}) if remember else {}
    off = set(_incompatible_flags(occupancy))
    restored = [f for f in stash if f not in off and not ss.get(f)]
    for f in restored:
        ss[f] = True
    for f in [f for f in stash if f not in off]:
        stash.pop(f, None)
    cleared = []
    for f in _incompatible_flags(occupancy):
        if ss.get(f) is True:
            cleared.append(f)
            if remember and f not in OCC_ONLY_FLAGS:
                stash[f] = True
        ss[f] = False
    ss["_cleared_flags"] = stash
    ss["_flag_change_note"] = (occupancy, cleared, restored) if remember else None
    return cleared, restored


# ---------------- Storage / industrial inputs (Table 9.27) -------------------
# Audit UX-01 (28.10.2026): drawn under the storage hazard class, before every stop.
def _sum_gf_bua_input() -> None:
    """The plot GF BUA sum (#4.1.13), required for storage (owner ruling 12.10.2026,
    Ch9 Q1). One widget key, drawn for a primary or a listed (secondary) storage."""
    st.session_state.setdefault("sum_gf_bua_m2_input", 0.0)
    st.number_input(
        "Sum of GF BUAs of all buildings on the plot (m2) (required)", min_value=0.0,
        step=100.0, key="sum_gf_bua_m2_input",
        help="#4.1.13 (p.695): the sum of the built-up ground floor areas of all buildings "
             "and structures on the plot, excluding separated service blocks, security "
             "guard house and separated washrooms. Selects the Table 9.27 area row (row 4 "
             "above 3600 m2) and the #4.1.6 yard hydrant (p.694). Enter this building's GF "
             "BUA when it is the only building on the plot. Required: 0 stops the "
             "evaluation (owner ruling 12.10.2026, Ch9 Q1).")


def _storage_tenancy_input() -> None:
    """Owner ruling Q-4 (28.10.2026): tenancy is a required choice with no default, for a
    storage main occupancy and for storage listed as another occupancy (verifier
    28.10.2026: the second case had no input)."""
    st.radio(
        "Storage tenancy (required)", ["multi", "single"], index=None, horizontal=True,
        key="storage_tenancy_input",
        format_func=lambda x: {"multi": "Multi-tenant (Groups A-E)",
                               "single": "Single tenant (Groups F-J)"}[x],
        help="Table 9.27 (p.724-733): multi-tenant Groups A (LH) / B (OH1) / C (OH2) / D "
             "(EH1) / E (EH2), p.724-728, or single tenant Groups F / G / H / I / J, "
             "p.729-733. Tanks and pumps differ, e.g. row 1 tank 30 min multi-tenant, "
             "45 min single tenant. No default: the tool stops until it is chosen "
             "(owner ruling Q-4, 28.10.2026).")


def _storage_specialty_inputs() -> None:
    """Table 9.27 specialty groups (K-V), commodity groups (L-O), unit compartment
    and tank inputs, in one expander under the storage hazard class."""
    with st.expander("Storage / industrial specialty (Table 9.27)",
                     expanded=not st.session_state.get("storage_tenancy_input")):
        st.caption("Choose the tenancy, then tick only the specialty groups that apply.")
        _storage_tenancy_input()
        st.checkbox(
            "Idle wood / plastic pallet warehouse (Group K - high-challenge fire load)",
            key="is_idle_pallet_storage",
            help="Table 9.27 Group K (p.734): warehouse storing idle wood or plastic pallets.")
        st.checkbox(
            "Cold storage facility (below 4 deg C - Group P)", key="is_cold_storage",
            help=_h("Table 9.27 Group P (p.739-740): storage facilities with below 4 deg C "
                    "(dry type sprinklers).", "is_cold_storage"))
        st.checkbox(
            "Aircraft hangar (Group Q)", key="is_aircraft_hanger",
            help="Table 9.27 Group Q (p.741-742): aircraft hangars, by hangar group I / II "
                 "and III / IV below.")
        if st.session_state.get("is_aircraft_hanger"):
            st.radio("Aircraft hangar group (Table 9.27 Q.1-Q.3)", ["I", "II_III", "IV"],
                     format_func=lambda x: {"I": "Group I", "II_III": "Group II or III",
                                            "IV": "Group IV"}[x],
                     key="hangar_group_input", on_change=_touch, args=("hangar_group_input",),
                     help="Table 9.27 Q.1-Q.3 (p.741-742): the hangar group per the code's "
                          "hangar classification. Group I carries the highest pump duty "
                          "(Q.1).")
        st.checkbox(
            "Flammable / combustible liquid WAREHOUSE (Group R - foam, 120-min tank)",
            key="is_flammable_liquid_warehouse",
            help="Table 9.27 Group R (p.743): warehouse storing flammable or combustible "
                 "liquids. Also Ch 4 Table 4.3 row 3 item 2.i (p.376): 50 L wheeled foam + "
                 "4 kg dry powder (owner ruling Q-2, 28.10.2026).")
        st.checkbox(
            "Flammable / combustible liquid INDUSTRIAL process (Group S - foam per Table 9.11.C)",
            key="is_flammable_liquid_industrial",
            help="Table 9.27 Group S (p.744): industrial occupancy processing flammable or "
                 "combustible liquids.")
        st.checkbox(
            "Open yard storage / no building envelope (Group U)", key="is_open_yard_storage",
            help=_h("Table 9.27 Group U (p.746): open yard storage of materials. The "
                    "warehouse packages of the other chapters stay conditional for any "
                    "enclosed building on the site (owner ruling R-B, 28.10.2026).",
                    "is_open_yard_storage"))
        st.checkbox(
            "Plant nursery (Group V - extinguishers only)", key="is_plant_nursery",
            help="Table 9.27 Group V (p.746): nurseries (plants and vegetation), fire "
                 "extinguishers as per Chapter 4.")
        st.checkbox(
            "Aboveground flammable / combustible liquid storage tanks (Group T)",
            key="is_aboveground_tank_storage",
            help="Table 9.27 Group T (p.745): storage of flammable and combustible liquids "
                 "in aboveground tanks; the row follows the tank storage area and capacity "
                 "below. Also Ch 4 Table 4.3 row 3 item 2.i wheeled foam (p.376) and Ch 8 "
                 "Table 8.15 item 3 tank detection (p.512). Ch 5-8 / 10 warehouse packages are "
                 "conditional on an enclosed building on the site (owner ruling R-B).")
        if st.session_state.get("is_aboveground_tank_storage"):
            st.session_state.setdefault("ast_storage_area_m2_input", 0.0)
            st.session_state.setdefault("ast_tank_capacity_m3_input", 0.0)
            st.number_input("Tank storage area (m2)", min_value=0.0, step=10.0,
                            key="ast_storage_area_m2_input",
                            help="Table 9.27 Group T row 1 (p.745) needs a storage area less "
                                 "than 230 m2 AND a tank capacity less than 190 m3. 0 = not "
                                 "stated: row 2 applies.")
            st.number_input("Tank capacity (m3)", min_value=0.0, step=10.0,
                            key="ast_tank_capacity_m3_input",
                            help="Table 9.27 Group T row 1 (p.745): capacity less than 190 m3. "
                                 "0 = not stated: Group T row 2 applies.")
        st.selectbox(
            "Stored commodity (Table 9.27 Groups L-O)",
            ["none", "class_i_iv", "plastics_rubber", "tires", "rolled_paper"],
            format_func=lambda x: {
                "none": "General storage (Groups A-J by hazard class)",
                "class_i_iv": "Class I-IV commodities (Group L)",
                "plastics_rubber": "Plastics / rubber (Group M)",
                "tires": "Tires (Group N)",
                "rolled_paper": "Rolled paper (Group O)"}[x],
            key="storage_commodity_input", on_change=_touch, args=("storage_commodity_input",),
            help="Table 9.27 commodity groups L (p.735), M (p.736), N (p.737) and O (p.738). "
                 "General storage keeps the hazard-class groups A-J.")
        st.session_state.setdefault("max_unit_area_m2_input", 0.0)
        st.number_input(
            "Largest unit compartment area (m2)", min_value=0.0, step=10.0,
            key="max_unit_area_m2_input",
            help="#4.1.14 (p.695): built-up GF area of the largest unit separated from the "
                 "adjacent units by fire resistance rated construction. 0 = the whole ground "
                 "floor is one unit.")


# ---------------- Room / location / equipment checkboxes (audit UX-16 / UX-17) -----
# (key, label, lead of the help text). The help text adds the rule lines each box
# switches on, read off the rule YAMLs (_h). Letters are the Ch 9 Table 9.30 / 9.31 rows.
_SPECIAL_ROOM_WIDGETS = [
    ("has_anesthetizing_room", "Anesthetizing room (A)", "Ch 9 Table 9.30.A (p.752)."),
    ("has_battery_charger_room", "Battery charger room (B)", "Ch 9 Table 9.30.B (p.752)."),
    ("has_bms_room", "BMS room (C)", "Ch 9 Table 9.30.C (p.752)."),
    ("has_battery_room", "Battery room (D)", "Ch 9 Table 9.30.D (p.752)."),
    ("has_computer_room", "Computer room (E)", "Ch 9 Table 9.30.E (p.752)."),
    ("has_control_room", "Control room / fire command centre (F)", "Ch 9 Table 9.30.F (p.752)."),
    ("has_diesel_generator_room", "Diesel generator room, foam (G)",
     "Ch 9 Table 9.30.G (p.752) and Table 9.31.E (p.756): foam sprinkler system."),
    ("has_main_electrical_room", "Main electrical room (H)", "Ch 9 Table 9.30.H (p.753)."),
    ("has_ahu_room", "AHU room (I)", "Ch 9 Table 9.30.I (p.753)."),
    ("has_lv_mv_room", "LV room (J)", "Ch 9 Table 9.30.J LV rooms and MV rooms (p.753)."),
    ("has_mv_room", "MV room (J, treated as HV, ruling R12)",
     "Table 4.3 lists LV and HV rooms only: an MV room takes the HV extinguisher (wheeled CO2 "
     "12 kg), an engineering decision (ruling R12). Table 9.30.J covers LV and MV rooms as "
     "printed (p.753)."),
    ("has_transformer_room_utility", "Transformer room, utility (K)",
     "Ch 9 Table 9.30.K transformer rooms (p.753): none, unless the power utility company "
     "specifies."),
    ("has_transformer_room_private", "Transformer room, private (L)",
     "Ch 9 Table 9.30.L transformer rooms not owned by the utility (p.753)."),
    ("has_lift_machine_room", "Lift machine room (M)", "Ch 9 Table 9.30.M (p.754)."),
    ("has_main_telephone_room", "Main telephone room (N)", "Ch 9 Table 9.30.N (p.754)."),
    ("has_main_server_room", "Main server room (O)", "Ch 9 Table 9.30.O (p.754)."),
    ("has_rmu_idf_mdf_room", "RMU / IDF / MDF / CDF / MMR room (P)", "Ch 9 Table 9.30.P (p.754)."),
    ("has_gsm_room", "GSM room (Q)", "Ch 9 Table 9.30.Q (p.754)."),
    ("has_operation_theater", "Operation theatre (R)", "Ch 9 Table 9.30.R (p.755)."),
    ("has_mri_scanning_room", "MRI / scanning room (S)", "Ch 9 Table 9.30.S (p.755)."),
    ("has_records_room", "Records room (T)", "Ch 9 Table 9.30.T (p.755)."),
    ("has_ups_room", "UPS room (U)", "Ch 9 Table 9.30.U (p.755)."),
    ("has_cold_freezer_room", "Cold / freezer room (V)", "Ch 9 Table 9.30.V (p.755)."),
    # Audit CH8-10: Ch 8 Table 8.14 item 24 PUMP ROOM (p.511) prints no pump type.
    ("has_fire_pump_room", "Pump room (fire pump or other)",
     "Any pump room: Ch 8 Table 8.14 item 24 PUMP ROOM (p.511) prints no pump type; Ch 10 "
     "Table 10.27 item 5 (p.866) covers the fire pump room ventilation."),
]

_VARIOUS_LOCATION_WIDGETS = [
    ("has_atrium", "Atrium", "Ch 9 Table 9.29 row A (p.749), Ch 8 Table 8.14 item 1 (p.509), "
     "Ch 10 Table 10.27 item 15 (p.866)."),
    ("has_rain_screen_glazing", "Rain-screen / glazed envelope", "Ch 9 Table 9.29 row C (p.749)."),
    ("has_stairs", "Stairs (shaft sprinklers + smoke detector at top)",
     "Ch 9 Table 9.29 row D (p.749) and Ch 8 Table 8.14 item 14 (p.510)."),
    ("has_elevator", "Elevator (pit sprinklers + smoke detector at top of shaft)",
     "Ch 9 Table 9.29 row E (p.749) and Ch 8 Table 8.14 item 15 (p.510)."),
    ("has_bathrooms_with_heaters", "Bathrooms with heaters above false ceiling",
     "Ch 9 Table 9.29 rows F.ii and G.i (p.749)."),
    # Audit CH8-10: Table 8.14 items 21 LAUNDRY / 22 STORAGE ROOM (p.510) print no
    # occupancy; Table 9.29 row H names residential / hotel-apartment rooms.
    ("has_laundry_storage_rooms", "Laundry / storage rooms",
     "Any laundry or storage room: Ch 8 Table 8.14 items 21-22 (p.510) print no occupancy. "
     "Ch 9 Table 9.29 row H (p.749) covers residential and hotel-apartment laundry and "
     "storage rooms in a sprinklered building."),
    # Audit CH8-10: Table 8.14 item 23 PANTRY (p.510) prints no occupancy.
    ("has_pantries", "Pantries",
     "Any pantry: Ch 8 Table 8.14 item 23 (p.510) prints no occupancy. Ch 9 Table 9.29 row "
     "I (p.749) covers pantries in offices and commercial buildings that are sprinklered."),
    ("has_permanent_stages", "Permanent stages (assembly)", "Ch 9 Table 9.29 row J (p.749)."),
    ("has_roof_lpg_or_restaurant", "Roof with LPG tanks, restaurant, assembly or sheesha (wet riser to roof)",
     "Ch 9 Table 9.29 row K (p.750): the building wet riser is extended to a roof with LPG "
     "tanks, restaurant seating, assembly or sheesha bars."),
    ("has_roof_restaurant_assembly", "Roof used for restaurant, assembly or sheesha (manual alarm)",
     "Ch 8 Table 8.14 item 36 BUILDING ROOFS (p.511): roofs used for restaurant seating, "
     "assembly and as sheesha bars take a manual fire detection and alarm system. Tick this "
     "and the box above for such a roof."),
    ("has_food_trucks", "Food trucks, any fuel (FA Table 8.14 item 34)",
     "Heat detector per Section 4.7 in each food truck, Ch 8 Table 8.14 item 34 (p.511)."),
    # Audit CH8-10: Table 8.14 item 25 GARBAGE ROOM (p.511) prints no chute condition.
    ("has_garbage_chute", "Garbage room / chute",
     "Any garbage room: Ch 8 Table 8.14 item 25 GARBAGE ROOM (p.511) prints no chute "
     "condition. Ch 9 Table 9.29 row L (p.750) covers the garbage chute sprinklers."),
    ("has_exterior_balconies", "Exterior balconies (Table 9.29 row B)",
     "Sprinklered buildings: sidewall or pendent heads on exterior balconies, not more than "
     "12 m2 per head, 79 deg C rating (Ch 9 Table 9.29 row B, p.749)."),
    ("has_high_ceiling", "High ceiling (more than 10 m)",
     "A space more than 10 m high: Ch 9 Table 9.29 row M and Table 9.29.A high-ceiling sprinkler design (p.750-751) "
     "and Ch 8 Table 8.14 items 18-19 (p.510). Enter the ceiling height below."),
    ("has_tunnel", "Tunnel inside building (Table 6.6 #9 / Ch 10 #3.7)",
     "Ch 6 Table 6.6 item 9 (p.420), Ch 9 Table 9.28 (tunnel kind and length under FP - "
     "Settings) and Ch 10 #3.7."),
]

_EQUIPMENT_WIDGETS = [
    # Audit CH8-06: Table 8.15 item 1 KITCHEN HOOD (p.512) prints no burner count.
    ("has_commercial_kitchen", "Commercial kitchen with cooking hood (A)",
     "Any kitchen hood: Ch 8 Table 8.15 item 1 fusible link heat detection (p.512) prints no "
     "burner count. Ch 9 Table 9.31.A wet chemical system (p.756) is for commercial kitchens "
     "having 3 or more burners."),
    ("has_flammable_liquid_tanks", "Flammable liquid tanks (C)", "Ch 9 Table 9.31.C (p.756)."),
    ("has_cable_spread_areas", "Cable spread areas (D)", "Ch 9 Table 9.31.D (p.756)."),
    ("has_boilers", "Boilers / boiler rooms (F)", "Ch 9 Table 9.31.F (p.756)."),
    # Audit CH8-05: Table 8.15 item 7 COOLING TOWERS (p.512) prints no combustibility.
    ("has_cooling_towers", "Cooling towers (G)",
     "Every cooling tower: Ch 8 Table 8.15 item 7 linear heat detection on the cable trays "
     "(p.512). Ch 9 Table 9.31.G deluge spray (p.756) applies where the cooling tower "
     "material is not tested and certified for non-combustibility."),
    ("has_oil_filled_transformers", "Oil-filled transformers (H)", "Ch 9 Table 9.31.H (p.756)."),
    ("has_bulk_oil_storage", "Bulk oil storage (I)", "Ch 9 Table 9.31.I (p.756)."),
    ("has_bulk_flammable_liquid_storage", "Bulk flammable liquid storage (J)",
     "Ch 9 Table 9.31.J (p.756)."),
    ("has_bulk_flammable_gas_storage", "Bulk flammable gas storage (K)",
     "Ch 9 Table 9.31.K (p.757)."),
    ("has_bulk_flammable_solid_storage", "Bulk flammable solid storage (L)",
     "Ch 9 Table 9.31.L (p.757)."),
    ("has_high_hazard_logistics", "High-hazard logistics (M)", "Ch 9 Table 9.31.M (p.757)."),
    ("has_chemical_warehouse", "Chemical warehouse (N)", "Ch 9 Table 9.31.N (p.757)."),
    ("has_explosives", "Arms / ammunition / explosives (O)", "Ch 9 Table 9.31.O (p.757)."),
    ("has_processing_plant", "Processing / generating plant (P)", "Ch 9 Table 9.31.P (p.757)."),
]


def _basement_parking(basement_bua: float, levels: int) -> dict:
    """Preset values for an enclosed parking wholly in the basements."""
    return {"parking_area_m2_input": float(basement_bua) * levels,
            "parking_height_m_input": 0.0, "parking_basement_levels_input": int(levels),
            "parking_depth_m_input": None}


# ---------------- Archetype presets ----------------
# A preset writes geometry + occupancy + a few common flags. Selecting "Custom" leaves
# everything as-is so the user can build from scratch.
ARCHETYPE_PRESETS = {
    "Custom (manual entry)": None,
    "Private villa G+1 (250 m² GF, 600 m² plot)": {
        "occ": "villa_private",
        "height_m_input": 6.0, "floors_above_input": 2, "floors_below_input": 0,
        "ground_bua_input": 250.0, "basement_bua_input": 0.0,
        "gfa_input": 500.0, "plot_area_input": 600.0,
        "has_parking_area": False,
        # Villas don't have these — _apply_preset() also enforces this
        # via VILLA_INCOMPATIBLE_FLAGS but listing the most-important ones
        # here makes the preset self-documenting.
        "has_diesel_generator_room": False,
        "has_main_electrical_room": False,
        "has_main_telephone_room": False,
        "has_lift_machine_room": False,
        "has_fire_pump_room": False,
        "has_stairs": False,    # Ch 9 villa branches don't require stair sprinklers
        "has_elevator": False,  # Ch 9 villa branches don't require elevator pit sprinklers
    },
    "Lowrise residential (G+3, 800 m² GF)": {
        "occ": "residential",
        "height_m_input": 14.0, "floors_above_input": 4, "floors_below_input": 1,
        "ground_bua_input": 800.0, "basement_bua_input": 800.0,
        "gfa_input": 3200.0, "plot_area_input": 2000.0, "depth_below_grade_input": 3.5,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
        **_basement_parking(800.0, 1),
    },
    "Midrise residential (G+6, 18 m)": {
        "occ": "residential",
        "height_m_input": 21.0, "floors_above_input": 7, "floors_below_input": 1,
        "ground_bua_input": 1000.0, "basement_bua_input": 1000.0,
        "gfa_input": 7000.0, "plot_area_input": 3000.0, "depth_below_grade_input": 3.5,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
        **_basement_parking(1000.0, 1),
    },
    "Highrise residential (55 m, G+18, 2 basements)": {
        "occ": "residential",
        "height_m_input": 55.0, "floors_above_input": 18, "floors_below_input": 2,
        "ground_bua_input": 1200.0, "basement_bua_input": 1200.0,
        "gfa_input": 22000.0, "plot_area_input": 5000.0, "depth_below_grade_input": 7.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
        **_basement_parking(1200.0, 2),
    },
    "Super-highrise residential (120 m, 35 storeys)": {
        "occ": "residential",
        "height_m_input": 120.0, "floors_above_input": 35, "floors_below_input": 3,
        "ground_bua_input": 1800.0, "basement_bua_input": 1800.0,
        "gfa_input": 60000.0, "plot_area_input": 25000.0, "depth_below_grade_input": 10.5,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
        **_basement_parking(1800.0, 3),
    },
    "Hotel (highrise, 18 storeys, 60 m)": {
        "occ": "hotel_a",
        "height_m_input": 60.0, "floors_above_input": 18, "floors_below_input": 2,
        "ground_bua_input": 1500.0, "basement_bua_input": 1500.0,
        "gfa_input": 25000.0, "plot_area_input": 5000.0, "depth_below_grade_input": 7.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
        **_basement_parking(1500.0, 2),
        "has_commercial_kitchen": True,
    },
    "Hospital (lowrise, 3000 m² GF)": {
        "occ": "healthcare_a",
        "height_m_input": 12.0, "floors_above_input": 3, "floors_below_input": 1,
        "ground_bua_input": 3000.0, "basement_bua_input": 2000.0,
        "gfa_input": 9000.0, "plot_area_input": 8000.0, "depth_below_grade_input": 3.5,
        "has_parking_area": True, "attached_parking_kind_radio": "Open parking",
        "parking_area_m2_input": 3000.0, "parking_height_m_input": 0.0,
        "parking_basement_levels_input": 0, "parking_depth_m_input": None,
        "has_anesthetizing_room": True, "has_operation_theater": True,
        "has_mri_scanning_room": True,
    },
    "Covered mall (3 floors, 25000 m² GF)": {
        "occ": "mall_covered",
        "height_m_input": 18.0, "floors_above_input": 3, "floors_below_input": 2,
        "ground_bua_input": 25000.0, "basement_bua_input": 25000.0,
        "gfa_input": 75000.0, "plot_area_input": 50000.0, "depth_below_grade_input": 7.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
        **_basement_parking(25000.0, 2),
        "has_atrium": True, "has_commercial_kitchen": True, "has_theater_cinema": True,
        "theater_cinema_kind_input": "cinema",
    },
    "Office, Business Group B (highrise, 30 m, 8 storeys)": {
        "occ": "business", "business_group_input": "B",
        "height_m_input": 30.0, "floors_above_input": 8, "floors_below_input": 2,
        "ground_bua_input": 800.0, "basement_bua_input": 800.0,
        "gfa_input": 6400.0, "plot_area_input": 2500.0, "depth_below_grade_input": 7.0,
        "has_parking_area": True, "attached_parking_kind_radio": "Enclosed parking",
        **_basement_parking(800.0, 2),
    },
    "Warehouse (multi-tenant OH2, 4000 m², only building on the plot)": {
        "occ": "storage_industrial",
        "height_m_input": 10.0, "floors_above_input": 1, "floors_below_input": 0,
        "ground_bua_input": 4000.0, "basement_bua_input": 0.0,
        "gfa_input": 4000.0, "plot_area_input": 8000.0,
        "has_parking_area": False,
        "storage_hazard_input": "OH2", "is_extra_hazard_2": False,
        "storage_tenancy_input": "multi", "sum_gf_bua_m2_input": 4000.0,
    },
    "Petrol station (Group A)": {
        "occ": "motor_fuel_dispensing",
        "height_m_input": 4.0, "floors_above_input": 1, "floors_below_input": 0,
        "ground_bua_input": 300.0, "basement_bua_input": 0.0,
        "gfa_input": 300.0, "plot_area_input": 2000.0,
        "has_parking_area": False,
        "motor_fuel_group_radio": "Group A - mini-marts/restaurants/retail/service as INDIVIDUAL buildings (sprinklers + 300 gpm @ 4.5 bar)",
    },
}


def _apply_preset():
    """Callback for the Apply-preset button. Writes preset values into session_state
    BEFORE widgets render (so widgets pick them up via their `key`).

    Auto-clears any flags marked as incompatible for the target occupancy
    BEFORE applying the preset overrides — so stale first-load defaults
    (e.g. has_diesel_generator_room=True) don't leak into a villa / petrol
    station / animal-housing / family-daycare scenario."""
    name = st.session_state.get("archetype_preset_select", "Custom (manual entry)")
    cfg = ARCHETYPE_PRESETS.get(name)
    if not cfg:
        return
    # Work on a copy so we can pop("occ") without mutating ARCHETYPE_PRESETS.
    cfg = dict(cfg)
    occ_target = cfg.pop("occ", None)
    if occ_target:
        st.session_state["occupancy_chosen"] = next(
            (kv for kv in OCC_FLAT if kv[1] == occ_target), None
        )
        # Also set the two-stage picker's session-state keys so the dropdowns
        # show the new occupancy on next render.
        for cat_label, occ_list in OCCUPANCY_OPTIONS.items():
            if occ_target in occ_list:
                st.session_state["occupancy_category_select"] = cat_label
                st.session_state["occupancy_sub_select"] = occ_target
                break
        # Baseline reset for villa / petrol station / animal housing / daycare_b/c /
        # infrastructure / hostel / parking / small mercantile. A preset starts afresh:
        # nothing is remembered for a later restore (audit UX-05).
        _apply_incompatible_flag_reset(occ_target, remember=False)
        # The occupancy-change reset (audit ENG-13) must not undo the preset values.
        st.session_state["_last_occupancy"] = occ_target
        st.session_state["hazard_override_input"] = "auto"
    for k, v in cfg.items():
        st.session_state[k] = v
    # Audit UX-08: the report names the preset whose values it uses.
    st.session_state["_profile_source"] = f"preset '{name}'"
    _touch(*cfg.keys())


def _clear_all_flags():
    """Uncheck every Special Room / Various Location / Equipment / FE / ES
    flag (and the master 'Check all' toggles) so the user can start from a
    clean flag set without unticking each box individually. Geometry,
    occupancy and gas-system selections are left untouched."""
    for k in (SPECIAL_ROOMS_KEYS + VARIOUS_LOCATIONS_KEYS + EQUIPMENT_KEYS
              + FE_KEYS + ES_FEATURE_KEYS + ES_ZONE_KEYS):
        st.session_state[k] = False
    for master in ("rooms_all", "var_all", "eq_all", "fe_all",
                   "es_feat_all", "es_zone_all"):
        st.session_state[master] = False
    st.session_state["_cleared_flags"] = {}
    _touch(*(SPECIAL_ROOMS_KEYS + VARIOUS_LOCATIONS_KEYS + EQUIPMENT_KEYS
             + FE_KEYS + ES_FEATURE_KEYS + ES_ZONE_KEYS))


rooms_cb = _register_master("rooms_all", SPECIAL_ROOMS_KEYS)
var_cb   = _register_master("var_all",   VARIOUS_LOCATIONS_KEYS)
eq_cb    = _register_master("eq_all",    EQUIPMENT_KEYS)
fe_cb    = _register_master("fe_all",    FE_KEYS)
es_feat_cb = _register_master("es_feat_all", ES_FEATURE_KEYS)
es_zone_cb = _register_master("es_zone_all",
                              [k for k in ES_ZONE_KEYS if k != "has_robotic_parking"])


# -----------------------------------------------------------------------------
# Print layout (Tier 3 UI #15; audit UX-02, 28.10.2026): a toggle in THIS session
# hides the sidebar and the contents / export column so the report of the building
# on screen prints cleanly to A4. The old "?print=1" link opened a new session, which
# printed the first-load sample instead of the user's building; it is gone.
PRINT_MODE = bool(st.session_state.get("print_layout", False))

st.set_page_config(
    page_title="UAE FLSC 2018 - Fire & Life Safety",
    page_icon="🧯",
    layout="wide",
    # Audit UX-18: "auto" keeps the sidebar closed on a phone, open on a desktop.
    initial_sidebar_state="auto",
)
ui.inject_css(PRINT_MODE)
ui.render_hero(PRINT_MODE)
_top_c1, _top_c2, _top_c3 = st.columns([3, 2, 2])
with _top_c1:
    bilingual_headings = st.checkbox(
        "Bilingual chapter headings (EN + AR)", value=True, key="bilingual_headings",
        help="Show the Arabic chapter title under each English chapter heading in the report.",
    )
with _top_c2:
    st.toggle("Print layout", key="print_layout",
              help="Hides the sidebar and the contents / export column so this building's "
                   "report prints from the browser (Ctrl+P / Print to PDF). Turn it off to "
                   "edit again. For a formal record use the Detailed PDF.")
with _top_c3:
    # Audit UX-18: on a phone the contents and exports column stacks below the report.
    if not PRINT_MODE:
        st.markdown("[⬇ Contents and exports](#exports)", unsafe_allow_html=True)

# ----- First-run orientation: how to use + 'this is a sample' note -----
with st.expander("ℹ️ New here? How to use this tool (3 steps)", expanded=False):
    st.markdown(
        "1. **Set the building profile** in the sidebar — pick the occupancy and "
        "enter the geometry (height, floors, areas). Or open **⚡ Quick start** to "
        "load a typical UAE archetype.\n"
        "2. **Tick the special rooms, equipment and gas systems** your building has "
        "— these drive the fire-alarm, fire-protection, smoke-control and LPG "
        "requirements.\n"
        "3. **Read the colour-coded report** below "
        "(🔴 required · 🔵 recommended · 🟡 conditional · ⚪ not required), filter or "
        "search it, switch the view to **Cards** to open **🔍 Why triggered** on any "
        "line, then **download Word or PDF**. Check the **Assumptions used in this "
        "report** box: it lists every input you did not set yourself.\n\n"
        "_The report updates live as you edit. The building shown on first load is "
        "just a sample — change the profile or load an archetype to begin. Inputs live "
        "only in this browser tab: save the project to keep them._"
    )


with st.sidebar:
    ui.render_sidebar_brand()
    # ----- Quick start: archetype presets -----
    with st.expander("⚡ Quick start - load an archetype", expanded=False):
        st.selectbox(
            "Archetype preset",
            options=list(ARCHETYPE_PRESETS.keys()),
            key="archetype_preset_select",
            help="Pick a typical UAE building archetype, then click Apply to fill geometry + occupancy + common flags. "
                 "Then customize as needed.",
        )
        st.button("Apply preset", on_click=_apply_preset, width="stretch",
                  help="Writes the archetype's occupancy, geometry, parking and flags into the "
                       "sidebar inputs. The report names the preset under 'Assumptions used "
                       "in this report'; check every value against your drawings.")
        st.caption("'Custom' leaves your current inputs untouched.")
        st.markdown("---")
        st.button("🔄 Clear all rooms / equipment flags",
                  on_click=_clear_all_flags, width="stretch",
                  help="Unticks every Special Room / Various Location / Equipment / "
                       "FE / ES flag so you can start a clean set. Geometry, "
                       "occupancy and gas selections are left as-is.")

    with st.expander("💾 Save / Load scenario", expanded=False):
        # ----- Save -----
        _save_keys = [
            # Geometry
            "height_m_input", "floors_above_input", "floors_below_input",
            "ground_bua_input", "basement_bua_input", "gfa_input",
            "plot_area_input", "depth_below_grade_input",
            # Project (audit ENG-23: project name, datum, construction type, hazard override)
            "project_name_input", "project_notes_input",
            "height_datum_input", "construction_type_input", "hazard_override_input",
            # Hazard / occupancy
            "occupancy_chosen", "mercantile_multi_tenant",
            # Owner rulings 13.10.2026, P4 Q1-Q6 (is_mercantile_group_c = old tick, Q6)
            "business_group_input", "is_post_office", "mercantile_c_type_input",
            "kiosk_location_input", "is_mercantile_group_c",
            # Parking
            "has_parking_area", "attached_parking_kind_radio", "parking_area_m2_input",
            "parking_height_m_input", "parking_basement_levels_input",   # P3 App Q2
            "parking_depth_m_input",                                     # P3 F-a3
            # Special rooms / various / equipment / FE / ES / Gas / FP / SC
            *SPECIAL_ROOMS_KEYS, *VARIOUS_LOCATIONS_KEYS, *EQUIPMENT_KEYS,
            *FE_KEYS, *ES_FEATURE_KEYS, *ES_ZONE_KEYS,
            "ceiling_height_m_input", "corridor_length_m",
            "assembly_area_m2_input", "theater_cinema_kind_input",
            "gas_system_radio",
            "has_lpg_tank_roof_mounted", "has_lpg_tank_underground_mounded",
            "has_lpg_cylinders_indoor", "has_lpg_cylinders_food_truck", "has_lpg_flame_effect",
            # Owner rulings 12.10.2026, P3 Ch11 Q3, Q4, Q6
            # P3 follow-up F-a1-1: the choice replaced the "is_new_or_modified_building" box
            "has_lpg_tank_at_grade", "new_or_modified_building_input", "has_cd_cylinder_approval",
            "lpg_flame_effect_show_input",
            "wet_riser_radio", "motor_fuel_group_radio",
            "storage_tenancy_input", "is_idle_pallet_storage",
            "is_cold_storage", "is_aircraft_hanger",
            "is_flammable_liquid_warehouse", "is_flammable_liquid_industrial",
            "is_open_yard_storage", "is_plant_nursery",
            "storage_hazard_input", "is_extra_hazard_2", "storage_commodity_input",
            "max_unit_area_m2_input", "sum_gf_bua_m2_input", "hangar_group_input",
            "is_aboveground_tank_storage", "ast_storage_area_m2_input",
            "ast_tank_capacity_m3_input",
            "tunnel_kind_radio", "tunnel_length_m_input",
            # Ch 9 routing inputs (phase 1)
            "exit_stairs_input", "is_covered_shaded_parking", "pump_room_at_grade",
            "gf_beyond_100m_from_hydrant", "has_single_exit_stair",
            # Mixed occupancy (ruling R13)
            "mixed_occupancy_mode_input", "secondary_occupancies_input",
            # Owner ruling 12.10.2026, Ch9 Q9; P3 Storey Q4
            "secondary_storage_hazard_input", "secondary_animal_housing_group_input",
            # Ch 3 / Ch 2 inputs (owner rulings 12.10.2026, Ch3 Q1-Q6)
            "largest_storey_area_m2_input", "mall_gla_m2_input", "use_area_count_input",
            *USE_AREA_KEYS, "building_volume_m3_input",
            "is_waterfront", "is_theme_park", "tower_setback_over_30m",
            # Owner answers 12.10.2026: F6 per-storey table, Ch9 Q6 animal housing group
            "storey_table_input", "animal_housing_group_input",
            # Phase 3 app package: #4.1.2 (CH9A-20), Tables 9.21.e / 9.21.f (CH9B-14)
            "has_water_reactive_materials", "has_attached_commercial_outlet",
            "commercial_outlet_gf_bua_m2_input", "tent_marquee_kind_input",
        ]
        def _serializable(v):
            # Convert tuple to list for JSON; passthrough rest
            if isinstance(v, tuple):
                return list(v)
            return v
        _scenario = {k: _serializable(st.session_state.get(k)) for k in _save_keys
                     if k in st.session_state}
        _scenario_json = _json.dumps(_scenario, indent=2, default=str)
        # Mimic a Save-As dialogue. Audit UX-10 (28.10.2026): the name follows the project
        # name (<project>_<YYYY-MM-DD>) until the user types their own; it no longer
        # freezes at the first run's "default project".
        _default_stem = ((st.session_state.get("project_name_input") or "").strip()
                         or "project") + f"_{_dt.date.today().isoformat()}"
        if st.session_state.get("save_as_filename") in (None, "", st.session_state.get("_save_as_default")):
            st.session_state["save_as_filename"] = _default_stem
        st.session_state["_save_as_default"] = _default_stem
        _save_name = st.text_input(
            "Save as",
            key="save_as_filename",
            help="File name of the saved project; it follows the project name and today's "
                 "date until you type your own. The file saves with the .flsc extension.",
        )
        _safe_stem = _re.sub(r"[^A-Za-z0-9._-]+", "_", (_save_name or "").strip()).strip("_") \
            or _re.sub(r"[^A-Za-z0-9._-]+", "_", _default_stem)
        st.download_button(
            "💾 Save project (.flsc)",
            data=_scenario_json,
            file_name=f"{_safe_stem}.flsc",
            mime="application/octet-stream",
            width="stretch", on_click="ignore", key="save_project_sidebar",
            help="Downloads every input of this session as a .flsc file. Inputs live only in "
                 "this browser tab: save before closing or refreshing it.",
        )
        # ----- Load -----
        # Accepts the new .flsc extension AND .json for backward compatibility
        # with older saved scenarios from before the extension change.
        _uploaded = st.file_uploader(
            "Load project (.flsc)",
            type=["flsc", "json"],
            key="scenario_uploader",
            help="Replaces every input with the saved project (nothing is merged). A file "
                 "with an impossible value is refused and the value is named.",
        )
        if _uploaded is not None and not st.session_state.get("_scenario_loaded_marker"):
            try:
                _data = _json.loads(_uploaded.read().decode("utf-8"))
                if not isinstance(_data, dict):
                    raise ValueError("refused: the file does not hold a saved project.")
                _bad = _invalid_scenario_values(_data)
                if _bad:
                    raise ValueError("refused, impossible value(s): " + "; ".join(_bad)
                                     + ". Nothing was loaded.")
                # Audit ENG-12: Load replaces the session (never merges) and restores
                # the occupancy pickers.
                _ignored, _defaulted = _apply_loaded_scenario(st.session_state, _data, _save_keys)
                # F6 / Ch9 Q6 (owner answers 12.10.2026): a file without these keys
                # (saved before phase 3) clears them, so no table or group from the
                # previous project is carried over; the editor restarts from the file.
                st.session_state["storey_table_input"] = list(_data.get("storey_table_input") or [])
                st.session_state["storey_table_base"] = st.session_state["storey_table_input"]
                st.session_state.pop("storey_table_editor", None)
                st.session_state["animal_housing_group_input"] = _data.get("animal_housing_group_input")
                # Owner ruling 13.10.2026, P4 Q1: an older file's 'Business Group C
                # (stand-alone)' tick is not carried into the group; it is only named in
                # the stop that asks for the group.
                st.session_state["_legacy_business_group_c"] = _data.get("is_business_group_c") is True
                st.session_state["_profile_source"] = f"file '{_uploaded.name}'"
                st.session_state["_touched"] = {k: True for k in _data if k in _save_keys}
                st.session_state["_scenario_loaded_marker"] = True
                st.session_state["_scenario_load_note"] = (
                    (f"Not inputs, ignored: {', '.join(_ignored)}. " if _ignored else "")
                    + (f"Not in the file, defaults used: {', '.join(_defaulted)}."
                       if _defaulted else ""))
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load: {e}")
        elif _uploaded is None:
            # Reset marker so a future upload re-applies
            st.session_state["_scenario_loaded_marker"] = False
        if "_scenario_load_note" in st.session_state:
            st.success("Scenario loaded: it replaced the previous inputs.")
            _note = st.session_state.pop("_scenario_load_note")
            if _note:
                st.caption(_note)

    with st.expander("📖 Glossary (acronyms & terms)", expanded=False):
        _gloss_q = st.text_input(
            "Filter glossary",
            value="",
            placeholder="e.g. PAS, ESFR, K-factor, Pa, hazard…",
            help="Case-insensitive match on term or definition.",
            key="glossary_filter",
        )
        _q = (_gloss_q or "").strip().lower()
        for term, defn in GLOSSARY:
            if _q and _q not in term.lower() and _q not in defn.lower():
                continue
            st.markdown(f"**{term}** — {defn}")
        if not _q:
            st.caption(
                f"{len(GLOSSARY)} terms. Type to filter. "
                "Items here are the acronyms most likely to appear in the report."
            )

    with st.expander("📍 Jump to OUTPUT section", expanded=False):
        st.markdown(
            "Click to scroll the main report:\n\n"
            "- [FSA - Fire Service Access](#ch-fsa)\n"
            "- [MOE - Means of Egress](#ch-moe)\n"
            "- [FE - Fire Extinguishers](#ch-fe)\n"
            "- [ES - Exit Signs](#ch-es)\n"
            "- [EL - Emergency Lighting](#ch-el)\n"
            "- [EVC - Voice Evacuation](#ch-evc)\n"
            "- [FA - Fire Detection & Alarm](#ch-fa)\n"
            "- [FP - Fire Protection](#ch-fp)\n"
            "- [SC - Smoke Control](#ch-sc)\n"
            "- [LPG - LPG Code](#ch-lpg)\n"
            "- [⮕ Attached parking](#attached-parking)\n"
            "- [FP High Ceiling Design](#high-ceiling)",
            unsafe_allow_html=True,
        )

    st.header("🏢 Building profile")
    project_name = st.text_input(
        "Project name", key="project_name_input",
        help="Printed as the title of every export and used in the export and save file "
             "names. It drives no code requirement.")
    project_notes = st.text_area(
        "Project notes (included in exports)",
        height=70,
        placeholder="Client / consultant / reviewer / design version.",
        key="project_notes_input",
        help="Printed under 'Project notes' in the Word, PDF and Excel exports and the "
             "Markdown copy. It drives no code requirement.",
    )

    # Set initial selectbox value if not already in session_state
    # ----- Two-stage occupancy picker (Tier 3 UI #11) -----
    # Stage 1: pick the broad category (Villa / Residential / Hotel / ...)
    # Stage 2: pick the specific occupancy within that category.
    # The legacy `occupancy_chosen` (category, occupancy) tuple is kept as the
    # source of truth so all downstream code, scenario save/load, and presets
    # continue to work unchanged.
    if "occupancy_chosen" not in st.session_state:
        st.session_state["occupancy_chosen"] = next(kv for kv in OCC_FLAT if kv[1] == "residential")
    _cur_cat, _cur_occ = st.session_state["occupancy_chosen"]
    _categories = list(OCCUPANCY_OPTIONS.keys())
    # Audit UX-20: the pickers take their value from session state only (no index= as
    # well), so Streamlit no longer warns that a default and a state value compete.
    if st.session_state.get("occupancy_category_select") not in _categories:
        st.session_state["occupancy_category_select"] = (
            _cur_cat if _cur_cat in _categories else _categories[0])
    if st.session_state.get("occupancy_sub_select") not in OCCUPANCY_OPTIONS[
            st.session_state["occupancy_category_select"]]:
        _opts0 = OCCUPANCY_OPTIONS[st.session_state["occupancy_category_select"]]
        st.session_state["occupancy_sub_select"] = _cur_occ if _cur_occ in _opts0 else _opts0[0]

    def _on_occupancy_category_change():
        # Audit ENG-13: a category change picks the sub-occupancy here, so the
        # occupancy-change reset below sees the new occupancy on this run.
        cat = st.session_state.get("occupancy_category_select")
        opts = OCCUPANCY_OPTIONS.get(cat, [])
        if opts and st.session_state.get("occupancy_sub_select") not in opts:
            st.session_state["occupancy_sub_select"] = opts[0]

    _chosen_cat = st.selectbox(
        "1. Category",
        _categories,
        key="occupancy_category_select",
        on_change=_on_occupancy_category_change,
        help="Pick the broad occupancy family (Ch 1 Table 1.1, p.48-50). The specific "
             "occupancy list below updates.",
    )
    _options_in_cat = OCCUPANCY_OPTIONS[_chosen_cat]
    _chosen_sub = st.selectbox(
        "2. Specific occupancy (UAE FLSC classification)",
        _options_in_cat,
        format_func=_occ_label,
        key="occupancy_sub_select",
        help="The occupancy of Ch 1 Table 1.1 (p.48-50). It selects the occupancy row of "
             "every chapter table (Ch 3 Table 3.13 / 3.16, Ch 5 Table 5.3, Ch 6 Table 6.5, "
             "Ch 7 Table 7.3, Ch 8 Table 8.13, Ch 9 Tables 9.18-9.28, Ch 10 Tables "
             "10.19-10.27) and the hazard class (Ch 9 #1.1.13). Its definition is shown "
             "below.",
    )
    # Persist back to the canonical tuple consumed by the rest of the app.
    st.session_state["occupancy_chosen"] = (_chosen_cat, _chosen_sub)
    occupancy = _chosen_sub
    # Audit ENG-13: whenever the resolved occupancy differs from the last one seen (a
    # sub-occupancy pick or a category change alike), the flags that do not apply to the
    # new occupancy are cleared and the hazard override goes back to the derived class.
    # Presets and Load set the last-seen occupancy themselves, so their values stay.
    if st.session_state.get("_last_occupancy") not in (None, occupancy):
        _apply_incompatible_flag_reset(occupancy)
        st.session_state["hazard_override_input"] = "auto"
    st.session_state["_last_occupancy"] = occupancy
    st.info(OCCUPANCY_DEFS.get(occupancy, ""))
    # Audit UX-06: every input that appears or disappears with the occupancy lives in
    # this one container, so the expanders below keep their place (and stay open).
    with st.container():   # audit UX-06: fixed slot for occupancy-specific inputs
        if occupancy == "animal_housing":
            # Owner answer 12.10.2026, Ch9 Q6: the three groups take their printed hazard
            # class (#1.1.13.1.q / r, p.528; #1.1.13.3.a, p.529). No default group.
            st.selectbox(
                "Animal housing group (required)", list(ANIMAL_HOUSING_GROUPS), index=None,
                format_func=lambda g: (f"Group {g} - {ANIMAL_HOUSING_GROUPS[g][3]} "
                                       f"({ANIMAL_HOUSING_GROUPS[g][0]}, {ANIMAL_HOUSING_GROUPS[g][1]})"),
                placeholder="Select the group (#1.1.13)",
                key="animal_housing_group_input",
                help="Ch 9 #1.1.13: Group A (animal market, pet shops, bird market, veterinary "
                     "clinic) and Group C (zoo) are Light Hazard (#1.1.13.1.q, r, p.528); Group B "
                     "(stable, animal sheds, livestock shelter, slaughter houses) is Ordinary "
                     "Hazard Group 2 (#1.1.13.3.a, p.529).")
        if occupancy in ("mercantile_a", "mercantile_b"):
            # Audit ENG-02: Ch 1 Table 1.1 row 11 (p.50).
            st.checkbox("Group of mercantile occupancies under a single roof or not separated",
                        key="mercantile_multi_tenant",
                        help="Ch 1 Table 1.1 row 11 (p.50): a group of mercantile occupancies under "
                             "a single roof or not separated and having a ground floor built up "
                             "area of more than 3600 m2, irrespective of the number of storeys, "
                             "shall be considered as Malls.")
            # Owner ruling 13.10.2026, P4 Q6: an older file's Group C tick stays visible (and
            # the report stops) until it is cleared here or the occupancy is set to
            # Mercantile Group C.
            if st.session_state.get("is_mercantile_group_c"):
                st.checkbox("Mercantile Group C tick from an older file (untick to confirm this "
                            "building is not Mercantile Group C)", key="is_mercantile_group_c",
                            help="Mercantile Group C (kiosks, food trucks, mercantile trucks, "
                                 "Table 1.1 row 11, p.50) is now its own occupancy. Untick this, "
                                 "or choose 'mercantile_c' as the occupancy (owner ruling "
                                 "13.10.2026, P4 Q6).")
        if occupancy == "mercantile_c":
            # Owner ruling 13.10.2026, P4 Q5: the type is required, no default.
            st.selectbox(
                "Mercantile Group C type (required)", list(MERCANTILE_C_TYPES), index=None,
                format_func=lambda t: MERCANTILE_C_TYPES[t], placeholder="Select the type",
                key="mercantile_c_type_input",
                help="Table 1.1 row 11 (p.50): kiosks, food trucks, mercantile trucks. A kiosk "
                     "takes Table 9.20.b row C (midrise, p.701) or Table 9.21.b (lowrise, by "
                     "inference) and Ch 1 Table 1.9 item 48 (p.98); a temporary kiosk also takes "
                     "Ch 8 Table 8.14 item 31. A truck takes only its own items: Ch 4 "
                     "extinguishers, Ch 8 Table 8.14 item 34 / 35, Ch 6 Table 6.5 item 12 and, "
                     "with LPG cylinders, Ch 11 Table 11.3 (owner rulings 13.10.2026, P4 Q4-Q5).")
            if st.session_state.get("mercantile_c_type_input") in ("kiosk_permanent",
                                                                    "kiosk_temporary"):
                st.selectbox(
                    "Kiosk location (Table 1.9 item 48 iii) (required)",
                    ["sprinklered_or_mall", "other"], index=None,
                    format_func=lambda x: {
                        "sprinklered_or_mall": "In a sprinkler protected area or a mall building",
                        "other": "Elsewhere"}[x],
                    placeholder="Select where the kiosk is", key="kiosk_location_input",
                    help="Ch 1 Table 1.9 item 48 iii (p.98): kiosks located at sprinkler "
                         "protected areas and mall buildings shall be provided with automatic "
                         "sprinkler system. Blank: that line is NOT EVALUATED. The kiosk area is "
                         "the ground floor built-up area (item 48 v: 18 m2 at most).")
        if occupancy == "business":
            # Owner rulings 13.10.2026, P4 Q1-Q2: the group is required, no default.
            st.selectbox(
                "Business group (required)", list(BUSINESS_GROUPS), index=None,
                format_func=lambda g: f"Group {g} - {BUSINESS_GROUPS[g]}",
                placeholder="Select the group (Table 1.1 row 2)", key="business_group_input",
                help="Ch 1 Table 1.1 row 2 (p.48). The Ch 3, 8 and 9 tables print Business "
                     "Groups A, B, C together; Group C takes Ch 6 Table 6.5 item 11 (p.419, "
                     "stand-alone self-contained emergency lighting) below 23 m. #1.1.13 does "
                     "not list Business: Light Hazard, except a post office (owner rulings "
                     "13.10.2026, P4 Q1-Q2).")
            if st.session_state.get("business_group_input") == "B":
                st.checkbox("Post office", key="is_post_office",
                            help="#1.1.13.3.c (p.529) lists post offices under Ordinary Hazard "
                                 "Group 2: the hazard class becomes OH2 (owner ruling 13.10.2026, "
                                 "P4 Q2).")
        # Audit UX-05: name what the occupancy change cleared or restored (it stays until the
        # next occupancy change, so it is not lost when the user scrolls).
        _note = st.session_state.get("_flag_change_note")
        if _note and _note[0] == occupancy and (_note[1] or _note[2]):
            _msg = []
            if _note[1]:
                _msg.append(f"Cleared {len(_note[1])} input(s) that do not apply to "
                            f"{_occ_label(occupancy)}: "
                            + ", ".join(field_label(f) for f in _note[1])
                            + ". They are ticked again if you return to an occupancy they "
                              "apply to.")
            if _note[2]:
                _msg.append(f"Restored {len(_note[2])} input(s) cleared by an earlier "
                            "occupancy change: " + ", ".join(field_label(f) for f in _note[2])
                            + ".")
            st.caption("💡 " + " ".join(_msg))
        elif occupancy in INCOMPATIBLE_FLAGS_BY_OCC:
            st.caption(
                "💡 Special Rooms / Equipment that typically don't apply to this "
                "occupancy are cleared when it is chosen. Tick anything below if your "
                "specific project needs it."
            )

    st.subheader("📐 Geometry")
    st.caption("Above-grade left, below-grade + plot right.")
    height_datum = st.radio(
        "Height datum (FAQ Annexure 1)",
        options=["grade", "occupiable_ceiling"],
        format_func=lambda x: "Lowest grade / Fire Service access" if x == "grade" else "Ceiling of highest occupiable space",
        horizontal=True, key="height_datum_input",
        help="Where the building height below is measured from. Ch 1 #1.7.39-#1.7.42 "
             "(p.44-45): total height, excluding roof parapets, from the lowest grade or "
             "lowest level of Fire Service access; FAQ Annexure 1 Q2-Q5 (p.1273): to the "
             "ceiling of the occupiable space. Use the datum the Civil Defence reviewer "
             "will use at the 15 m / 23 m / 90 m boundaries.",
    )
    # Audit ENG-21: the class is taken from the height as entered; say which printed
    # definition that height follows and that the other one can give another class.
    if height_datum == "occupiable_ceiling":
        st.warning("Height datum: ceiling of the highest occupiable space (FAQ Annexure 1 "
                   "Q2-Q5, p.1273). Ch 1 #1.7.39-#1.7.42 (p.44-45) measure the total height "
                   "of the building, excluding roof parapets, from the lowest grade or lowest "
                   "level of Fire Service access. The height class is taken from the height "
                   "as entered: near 15 m, 23 m and 90 m check the class with the other "
                   "datum.")
    else:
        st.caption("Height datum: total height of the building, excluding roof parapets, from "
                   "the lowest grade or lowest level of Fire Service access (Ch 1 #1.7.39-"
                   "#1.7.42, p.44-45). FAQ Q2-Q5 (p.1273) measure to the ceiling of the "
                   "occupiable or usable space.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Above-grade**")
        height_m = st.number_input(
            "Building height (m)", min_value=0.0, step=1.0, key="height_m_input",
            help="Total height of the building, excluding roof parapets, from the datum "
                 "above (Ch 1 #1.7.39-#1.7.42, p.44-45). It sets the height class: lowrise "
                 "up to 15 m, midrise more than 15 m and less than 23 m, highrise 23 m up "
                 "to 90 m (ruling R1), super highrise more than 90 m; the class selects "
                 "the height row of every chapter table. Required: 0 m stops the "
                 "evaluation.")
        floors_above = st.number_input(
            "Floors above grade (including GF)", min_value=1, step=1, key="floors_above_input",
            help="Storeys above grade, counting the ground floor. Drives the storey-count "
                 "rows, e.g. Ch 9 #4.1.7 (p.694: storage and industrial occupancies having "
                 "more than 3 floors above the fire access level are fully sprinklered) and "
                 "the storey count of the per-storey table (Ch 3 Table 3.14).")
        ground_bua = st.number_input(
            "Ground-floor BUA (m²)", min_value=0.0, step=50.0, key="ground_bua_input",
            help="Built-up ground floor area: the total ground floor area of this building, "
                 "including carpet areas, wall and column thickness, stair, elevator and "
                 "service shafts (Ch 9 #4.1.12, p.695). Drives the Ch 2 fire access extent "
                 "(the building footprint, #2.8.6.a, p.213), the area rows of Ch 9 Tables "
                 "9.18-9.27 and the storage thresholds (#4.1.6, p.694). Required: 0 stops "
                 "the evaluation (a blank never counts as a pass).")
        gfa = st.number_input(
            "Total GFA (m²)", min_value=0.0, step=100.0, key="gfa_input",
            help="Gross floor area of all storeys: the area within the inside perimeter of "
                 "the outside walls, with no deductions for hallways, stairs, closets, "
                 "interior walls, columns and shafts, excluding atrium floor openings (Ch 3 "
                 "#1.4.6, p.242). Drives the occupant load (Ch 3 Table 3.13) when no "
                 "per-storey or per-use areas are entered, and the GFA-keyed rows (e.g. Ch 7 "
                 "Table 7.3 item 9 takes the larger of GFA and GF BUA, p.439). "
                 "Required: 0 stops the evaluation.")
    with c2:
        st.markdown("**Below-grade + plot**")
        plot_area = st.number_input(
            "Plot area (m²)", min_value=0.0, step=100.0, key="plot_area_input",
            help="The total area under the plot number, including the ground floor area of "
                 "the buildings, set back, landscaping, parking areas and open spaces (Ch 9 "
                 "#4.1.10, p.695). Drives the plot-area rows: #4.1.4 (p.694, yard fire "
                 "hydrants above 20,000 m2 plot area) and the plot rows of Tables 9.19 / "
                 "9.20. Required: 0 stops the evaluation.")
        floors_below = st.number_input(
            "Basements (below grade)", min_value=0, step=1, key="floors_below_input",
            help="Storeys below the level of exit discharge. More than two basements, or "
                 "more than 7 m below, is a high depth underground building (Ch 1 #1.7.45, "
                 "p.45); up to two is low depth (#1.7.44). Sets the basement rows of Ch 6, "
                 "Ch 9 and Ch 10.")
        if int(floors_below) > 0:
            basement_bua = st.number_input(
                "Basement BUA (m²)", min_value=0.0, step=50.0, key="basement_bua_input",
                help="Built-up area of all the basement floors (Ch 9 #4.1.11, p.695). Drives "
                     "the villa basement rows (Ch 9 Table 9.23.A.3, p.716, more than 1500 m2; "
                     "Ch 6 Table 6.5 item 14, p.419) and, for an underground building, the "
                     "Ch 2 fire access footprint.")
            depth_below_grade = st.number_input(
                "Depth below grade (m)", min_value=0.0, step=0.5,
                help="Distance from the level of exit discharge to the lowest basement "
                     "floor. More than 7 m is a high depth underground building (Ch 1 "
                     "#1.7.45, p.45): it triggers Ch 10 Table 10.22 (deep-underground smoke "
                     "control) even with 2 basements or fewer.",
                key="depth_below_grade_input",
            )
        else:
            # Reset and disable when no basements
            st.session_state["basement_bua_input"] = 0.0
            st.session_state["depth_below_grade_input"] = 0.0
            basement_bua = 0.0
            depth_below_grade = 0.0
            st.caption("_Basement BUA + Depth N/A (no basements)._")

    # ---- Soft validation warnings (UX #6) ----
    _warnings = []
    if int(floors_below) > 0 and float(basement_bua) <= 0:
        _warnings.append("⚠ Basement floor count > 0 but Basement BUA = 0 - check basement area")
    if int(floors_below) == 0 and float(basement_bua) > 0:
        _warnings.append("⚠ Basement BUA entered but basement count = 0")
    if float(height_m) > 0 and int(floors_above) > 0 and float(height_m) / int(floors_above) < 2.5:
        _warnings.append(f"⚠ Implied storey height {height_m/floors_above:.1f} m looks low - verify height vs floor count")
    if float(depth_below_grade) > 7 and int(floors_below) <= 2:
        _warnings.append("ℹ Depth > 7 m with <=2 basements still triggers Ch 10 Table 10.22 (deep-underground SC) - intended.")
    with st.container():   # audit UX-06: a fixed slot, so the expanders below stay open
        for w in _warnings:
            st.caption(w)

    derived_hazard = default_hazard(
        occupancy, st.session_state.get("animal_housing_group_input"),
        is_post_office=(occupancy == "business" and st.session_state.get("business_group_input") == "B"
                        and bool(st.session_state.get("is_post_office"))))   # P4 Q2
    # Owner ruling 12.10.2026, Ch9 Q7: robotic / mechanical parking is Extra Hazard
    # Group 2 (#1.1.13.5.b, p.530); the hazard is forced to HH + EH2 when ticked.
    _robotic_eh2 = (bool(st.session_state.get("has_robotic_parking"))
                    and occupancy in ("parking_enclosed", "parking_open"))
    with st.container():   # audit UX-06: fixed slot for the hazard notes
        if _robotic_eh2:
            derived_hazard = "HH"
            st.caption("Hazard class: **HH, Extra Hazard Group 2** (robotic / mechanical parking "
                       "is ticked: #1.1.13.5.b, p.530 lists 'Parking, Group B (Robotic, Mechanical "
                       "parking)' under Extra Hazard, Group 2; owner ruling 12.10.2026, Ch9 Q7).")
        elif occupancy == "animal_housing":
            _ahg = st.session_state.get("animal_housing_group_input")
            if _ahg in ANIMAL_HOUSING_GROUPS:
                _hz, _cl, _pg, _ = ANIMAL_HOUSING_GROUPS[_ahg]
                st.caption(f"Hazard class (Animal Housing Group {_ahg}, {_cl}, {_pg}): **{_hz}** "
                           "(owner answer 12.10.2026, Ch9 Q6)")
        elif occupancy != "storage_industrial":
            st.caption(f"Hazard class (auto-derived from occupancy, #1.1.13): **{derived_hazard}**")
        if occupancy in ("assembly_b", "assembly_c"):
            # Owner ruling 12.10.2026, Ch9 Q5: Assembly B/C stay LH (#1.1.13.1 a-b).
            st.caption("Assembly Groups B and C are Light Hazard (#1.1.13.1 a-b, p.526-527). "
                       "Where the space has a kitchen, a stage or similar, choose **OH1** under "
                       "'Override hazard class': #1.1.13.2 a (p.528) lists Assembly Group A "
                       "(banquet halls, restaurants with more than 50 people, theaters, concert "
                       "halls, cinemas) as Ordinary Hazard Group 1 (owner ruling 12.10.2026, Ch9 Q5).")
        if occupancy in HAZARD_NOT_CLASSIFIED:
            st.caption("#1.1.13 does not name this occupancy: the hazard class above is the "
                       "tool's working value. Select the class for the actual contents under "
                       "'Override hazard class'.")
    with st.expander("Mixed occupancy + construction type (Ch 1)", expanded=False):
        st.selectbox(
            "Mixed occupancy mode (Ch 1 #2.4–2.5)",
            options=["none", "most_restrictive", "separated"],
            format_func=lambda x: {
                "none": "Single occupancy (default)",
                "most_restrictive": "Most restrictive package (intermingled)",
                "separated": "Separated by fire barriers (Table 1.2)",
            }[x],
            key="mixed_occupancy_mode_input",
            help="Ch 1 #2.4-#2.5: an intermingled (mixed) occupancy takes the most "
                 "restrictive package of every listed occupancy (#2.4.4; one line per "
                 "system, ruling R13); a separated one keeps each occupancy behind fire "
                 "barriers per Table 1.2. 'Single occupancy' evaluates the occupancy above "
                 "only.",
        )
        # Ruling R13 (12.10.2026): in most-restrictive mode every listed occupancy
        # is evaluated and the most onerous line per system is kept (Ch 1 #2.4.4).
        # The primary occupancy is dropped from the list so the widget never holds a
        # value missing from its options after the primary changes.
        if st.session_state.get("secondary_occupancies_input"):
            st.session_state["secondary_occupancies_input"] = [
                o for o in st.session_state["secondary_occupancies_input"] if o != occupancy]
        st.multiselect(
            "Other occupancies in the building",
            # Owner rulings 13.10.2026, P4 Q4-Q5: a kiosk or truck is its own building.
            options=[occ for _, occ in OCC_FLAT if occ not in (occupancy, "mercantile_c")],
            format_func=_occ_label,
            key="secondary_occupancies_input",
            help="Most restrictive: each one is evaluated and the most onerous line per "
                 "system is kept; lines a secondary occupancy brings say so. Separated: "
                 "listed in the report note only.",
        )
        if (st.session_state.get("mixed_occupancy_mode_input") == "most_restrictive"
                and "storage_industrial" in (st.session_state.get("secondary_occupancies_input") or [])):
            # Owner ruling 12.10.2026, Ch9 Q9: the hazard of a secondary storage occupancy
            # is chosen, never assumed (Table 9.27 groups follow #1.1.13, Tables 9.1 / 9.2).
            st.selectbox(
                "Storage / industrial (other occupancy) hazard class (required)",
                ["LH", "OH1", "OH2", "HH", "EH2"], index=None,
                format_func=lambda x: {"LH": "LH", "OH1": "OH1", "OH2": "OH2",
                                       "HH": "HH (Extra Hazard Group 1)",
                                       "EH2": "HH + Extra Hazard Group 2 (#1.1.13.5)"}[x],
                placeholder="Select from the stored materials and activities",
                key="secondary_storage_hazard_input",
                help="Table 9.27 groups A-J are chosen by hazard class per #1.1.13, Table 9.1 "
                     "(materials) and Table 9.2 (activities). Owner ruling 12.10.2026, Ch9 Q9.")
            # Owner ruling 12.10.2026, Ch9 Q1: the plot GF BUA sum is required for storage.
            _sum_gf_bua_input()
            _storage_tenancy_input()
        if (st.session_state.get("mixed_occupancy_mode_input") == "most_restrictive"
                and "animal_housing" in (st.session_state.get("secondary_occupancies_input") or [])):
            # Owner ruling 12.10.2026, P3 Storey Q4 (as Ch9 Q9 for storage): the group of
            # a secondary animal housing is chosen, never assumed (#1.1.13, p.528-529).
            st.selectbox(
                "Animal housing (other occupancy) group (required)", list(ANIMAL_HOUSING_GROUPS),
                index=None,
                format_func=lambda g: (f"Group {g} - {ANIMAL_HOUSING_GROUPS[g][3]} "
                                       f"({ANIMAL_HOUSING_GROUPS[g][0]}, {ANIMAL_HOUSING_GROUPS[g][1]})"),
                placeholder="Select the group (#1.1.13)",
                key="secondary_animal_housing_group_input",
                help="Ch 9 #1.1.13: Group A (animal market, pet shops, bird market, veterinary "
                     "clinic) and Group C (zoo) are Light Hazard (#1.1.13.1.q, r, p.528); Group "
                     "B (stable, animal sheds, livestock shelter, slaughter houses) is Ordinary "
                     "Hazard Group 2 (#1.1.13.3.a, p.529). Owner ruling 12.10.2026, P3 Storey Q4.")
        st.selectbox(
            "Construction type (Ch 1 #2.6 — reporting aid)",
            options=["unspecified", "type_i", "type_ii", "type_iii", "type_iv", "type_v"],
            format_func=lambda x: x.replace("_", " ").title() if x != "unspecified" else "Not specified",
            key="construction_type_input",
            help="Ch 1 #2.6 construction type. A reporting aid only: it is printed in the "
                 "detailed export profile and drives no requirement line.",
        )
    with st.container():   # audit UX-06: fixed slot for the hazard inputs
        if occupancy == "storage_industrial":
            # Table 9.27 groups depend on the stored materials and activities (#1.1.13,
            # #1.1.23 / Table 9.1, #1.1.24 / Table 9.2): no silent default (CH9C-28).
            hazard = st.selectbox(
                "Storage hazard class (required)", ["LH", "OH1", "OH2", "HH"], index=None,
                placeholder="Select from the stored materials and activities",
                key="storage_hazard_input",
                help="Table 9.27 groups A-J are chosen by hazard class per #1.1.13, Table 9.1 "
                     "(materials) and Table 9.2 (activities). HH = Extra Hazard.")
            with st.container():   # audit UX-06: fixed slot
                if hazard == "HH":
                    st.checkbox("Extra Hazard Group 2 (#1.1.13.5)", key="is_extra_hazard_2",
                                help="Unticked = Extra Hazard Group 1 (#1.1.13.4): Table 9.27 "
                                     "Group D / I and the Group B egress rows (Ch 3 Table 3.16 "
                                     "rows 17 / 19, Table 3.13 rows 16 / 18). Ticked = Group E / "
                                     "J and the Group A high hazard egress rows.")
                else:
                    st.session_state["is_extra_hazard_2"] = False
                if st.session_state.get("has_robotic_parking"):
                    st.caption("Robotic / mechanical parking is ticked: the attached parking is "
                               "evaluated at HH, Extra Hazard Group 2 (#1.1.13.5.b, p.530; owner "
                               "ruling 12.10.2026, Ch9 Q7). The warehouse keeps the class chosen here.")
            # Audit UX-01 (28.10.2026): every Table 9.27 input is drawn here, under the
            # hazard class and BEFORE any stop, so the stop that asks for one of them
            # never names a field that is not on screen (a stand-alone warehouse was a
            # dead end: the field lived in 'FP - Settings', drawn after the stop).
            _sum_gf_bua_input()
            _storage_specialty_inputs()
        else:
            st.session_state["is_extra_hazard_2"] = False
            with st.expander("Override hazard class (advanced)"):
                # Audit ENG-23: keyed and saved; "auto" = the derived class, so an override
                # is never carried silently to another occupancy (reset on change, ENG-13).
                if st.session_state.get("hazard_override_input") not in ("auto", "LH", "OH1", "OH2", "HH"):
                    st.session_state["hazard_override_input"] = "auto"
                if _robotic_eh2:
                    # Unkeyed so the saved override is not changed while robotic is ticked.
                    st.selectbox("Hazard class", ["HH"], disabled=True,
                                 help="Fixed at HH (Extra Hazard Group 2) while robotic / "
                                      "mechanical parking is ticked (#1.1.13.5.b; owner "
                                      "ruling 12.10.2026, Ch9 Q7).")
                    _hz_pick = "HH"
                else:
                    _hz_pick = st.selectbox(
                        "Hazard class", ["auto", "LH", "OH1", "OH2", "HH"],
                        format_func=lambda x: f"Derived ({derived_hazard})" if x == "auto" else x,
                        key="hazard_override_input",
                        help="Ch 9 #1.1.13 (p.526-530) hazard classification of the actual "
                             "contents (see Table 9.1 materials and Table 9.2 activities). "
                             "It selects the hazard-keyed Ch 9 rows and the high-ceiling "
                             "design (Table 9.29.A). 'Derived' is the class #1.1.13 gives "
                             "the occupancy; it returns to Derived on an occupancy change.")
                hazard = derived_hazard if _hz_pick == "auto" else _hz_pick
            if _robotic_eh2:
                hazard = "HH"

    # =========================================================================
    # SHARED: Special Rooms & Equipment (drives FE / FA / FP / SC / LPG / EL)
    # =========================================================================
    st.markdown("---")
    st.markdown("### 🅿️ Spaces, equipment & gas")
    st.caption("Flags shared across FE / FA / FP / SC / LPG / EL chapters.")

    with st.expander("🅿️ Parking & special rooms", expanded=False):
        # ----- Attached parking sub-occupancy (drives MOE/FE/FP/FA/SC parking sub-evaluation) -----
        st.markdown("**Attached parking area**")
        st.checkbox("Building has parking",
                    key="has_parking_area",
                    help="Runs a parallel evaluation of the parking as its own occupancy "
                         "(enclosed: Table 1.1 parking definitions; Ch 9 Table 9.24, Ch 10 "
                         "Table 10.23) and prints it under 'Attached Parking Area'. One "
                         "governing fire pump and fire water tank covers the whole building "
                         "(#4.1.17, p.695). Needs the parking area, height and levels below.")
        with st.container():   # audit UX-06: fixed slot for the parking inputs
            if st.session_state.get("has_parking_area"):
                parking_kind = st.radio(
                    "Parking type",
                    options=["Enclosed parking", "Open parking"],
                    key="attached_parking_kind_radio", on_change=_touch, args=("attached_parking_kind_radio",),
                    help="Enclosed or open parking as defined in Ch 1 Table 1.1 (the "
                         "definition is shown below). It selects the enclosed or open rows "
                         "of Ch 9 Table 9.24 and Ch 10 Table 10.23.",
                )
                attached_parking_kind_val = "open" if parking_kind == "Open parking" else "enclosed"
                # Show the verbatim UAE code definition for the selected parking type
                _key = "parking_open" if attached_parking_kind_val == "open" else "parking_enclosed"
                st.info(OCCUPANCY_DEFS.get(_key, ""))
                st.session_state.setdefault("parking_area_m2_input", 0.0)
                parking_area_m2_val = st.number_input(
                    "Parking footprint area (m²) (required)",
                    min_value=0.0, step=100.0,
                    key="parking_area_m2_input",
                    help="Total parking footprint - drives Ch 10 SC area thresholds: enclosed parking 3,600 m² make-up-air exception (single-basement); open parking 4,000 m² small-vs-large split (>4,000 m² requires mechanical smoke purging or jet-fan system). Required: 0 = not entered, the attached parking is NOT EVALUATED (no fallback to the basement or ground-floor BUA).",
                )
                if float(parking_area_m2_val) <= 0:
                    st.caption("Enter the parking footprint area: until then the attached parking "
                               "is not evaluated (the report says so).")
                # Owner ruling 12.10.2026, P3 App Q2: the parking's own height and levels.
                # Audit UX-27: "(required)" sits in the label, not in a cut-off placeholder.
                parking_height_m_val = st.number_input(
                    "Parking height above the fire access level (m) (required)",
                    min_value=0.0, value=None, step=0.5, key="parking_height_m_input",
                    placeholder="Not entered",
                    help="Height of the parking structure itself above the fire access level "
                         "(0 = wholly below it), not the tower height. It sets the height-keyed "
                         "parking rows, e.g. Ch 10 Table 10.23 item 1.iv (p.860, stairs of parking "
                         "more than 23 m) and the Table 9.24 rows. Ch 9 sprinklers still follow the "
                         "host building's table. Blank: those lines are NOT EVALUATED (owner ruling "
                         "12.10.2026, P3 App Q2).")
                parking_basement_levels_val = st.number_input(
                    "Parking basement levels (required)",
                    min_value=0, value=None, step=1, key="parking_basement_levels_input",
                    placeholder="Not entered",
                    help="Number of basement levels the parking occupies (0 = none), at most the "
                         "building's basements; the building's depth below grade is used for them. "
                         "Blank: the lines keyed on the basement levels are NOT EVALUATED (owner "
                         "ruling 12.10.2026, P3 App Q2).")
                if parking_height_m_val is None or parking_basement_levels_val is None:
                    st.caption("Enter the parking height and basement levels: until then the "
                               "parking lines that depend on them are NOT EVALUATED (the tower "
                               "height is not used).")
                # Owner ruling 12.10.2026, P3 follow-up F-a3: the parking's own depth.
                parking_depth_m_val = st.number_input(
                    "Parking depth below the fire access level (m)",
                    min_value=0.0, value=None, step=0.5, key="parking_depth_m_input",
                    placeholder="Blank: building depth",
                    help="Depth of the parking's lowest level below the fire access level, at "
                         "most the building's depth below grade. More than 7 m is high depth "
                         "(Ch 1 #1.7.45, p.45). Used where the parking has basement levels; "
                         "more than 0 m with 0 levels is refused (F-a4-2). "
                         "Blank: the building's depth is used and the report says so (owner "
                         "ruling 12.10.2026, P3 follow-up F-a3).")
            else:
                attached_parking_kind_val = "enclosed"
                parking_area_m2_val = 0.0
                parking_height_m_val = None
                parking_basement_levels_val = None
                parking_depth_m_val = None
        # Audit UX-15: robotic parking sits with the parking (it was under ES zones) and
        # says which chapters it changes.
        st.checkbox("Robotic / mechanical parking", key="has_robotic_parking",
                    help=_h("Parking, Group B (robotic, mechanical parking) is Extra Hazard "
                            "Group 2 (Ch 9 #1.1.13.5.b, p.530): a parking occupancy or the "
                            "attached parking is evaluated at HH + EH2 (owner ruling "
                            "12.10.2026, Ch9 Q7). Ch 8 Table 8.13 item 23 (p.506) governs its detection (owner ruling R-I).",
                            "has_robotic_parking"))
        with st.container():   # audit UX-06: fixed slot
            if st.session_state.get("has_robotic_parking"):
                st.caption("Robotic / mechanical parking is Extra Hazard Group 2 (#1.1.13.5.b, "
                           "p.530): the parking is evaluated at HH + EH2 (owner ruling "
                           "12.10.2026, Ch9 Q7).")
        st.markdown("---")
        st.markdown("**Special rooms checklist**")
        # Audit UX-16: name the table the letters belong to.
        st.caption("Letters (A)-(V) are the rows of Ch 9 Table 9.30 Auxiliary Rooms Fire "
                   "Protection Systems (p.752-755); each room also brings its Ch 8 Table 8.14 "
                   "and Ch 4 Table 4.3 lines.")
        st.checkbox("Check all", key="rooms_all", on_change=rooms_cb,
                    help="Ticks (or unticks) every special room below.")
        # Audit UX-17: one column, so no room name is cut off in the narrow sidebar.
        for _key, _label, _lead in _SPECIAL_ROOM_WIDGETS:
            st.checkbox(_label, key=_key, help=_h(_lead, _key), on_change=_touch, args=(_key,))

    with st.expander("🛗 Various locations & spaces", expanded=False):
        st.caption("Rows of Ch 9 Table 9.29 Various Locations (p.749-750) and Ch 8 Table 8.14 "
                   "(p.509-511).")
        st.checkbox("Check all", key="var_all", on_change=var_cb,
                    help="Ticks (or unticks) every location below.")
        for _key, _label, _lead in _VARIOUS_LOCATION_WIDGETS:
            st.checkbox(_label, key=_key, help=_h(_lead, _key), on_change=_touch, args=(_key,))
            if _key == "has_high_ceiling":
                with st.container():   # audit UX-06: fixed slot
                    if st.session_state.get("has_high_ceiling"):
                        st.session_state.setdefault("ceiling_height_m_input", 12.0)
                        ceiling_height_m = st.number_input(
                            "Ceiling height (m)", min_value=10.0, max_value=30.0, step=0.5,
                            help="Height of the high-ceiling space. Selects the Ch 9 Table "
                                 "9.29.A height band (p.750-751) for the sprinkler design and the "
                                 "Ch 8 Table 8.14 items 18 / 19 detection (p.510: more than 10 m "
                                 "to less than 20 m beam detection; more than 20 m aspiration).",
                            key="ceiling_height_m_input",
                        )
                    else:
                        ceiling_height_m = 0.0

    with st.expander("🔥 Gas systems (Ch 11 LPG)", expanded=False):
        st.markdown("**Gas system type - one type only**")
        gas_choice = st.radio(
            "Select the building's gas-system type",
            options=[
                "No gas system",
                "LPG tanks (aboveground / roof / podium)",
                "Gas infrastructure connection (central piped supply)",
                "Gas cylinders (villa / domestic / small commercial)",
            ],
            key="gas_system_radio",
            help="Single mutually-exclusive choice. Triggers Ch 11 LPG requirements per type, or 'No Gas System' note.",
        )
        # Set the three underlying flags to match the radio choice
        st.session_state["has_lpg_tanks"] = gas_choice.startswith("LPG tanks")
        st.session_state["has_gas_infra_connection"] = gas_choice.startswith("Gas infrastructure")
        st.session_state["has_gas_cylinders_villa"] = gas_choice.startswith("Gas cylinders")

        # ----- Add-on variants (layer additional Ch 11 requirements) -----
        if gas_choice.startswith("LPG tanks"):
            st.markdown("*LPG tank variants (tick all that apply):*")
            st.checkbox("Roof-mounted tank (Tables 11.7/11.8 - max 2,000 Gal)",
                        key="has_lpg_tank_roof_mounted",
                        help="Roof / podium tanks: Table 11.7 location and construction rules, Table 11.8 separations, 2,000 Gal aggregate cap (or 1,000 Gal if construction does not comply with Table 11.7 #2.i). Not allowed above 90 m (#2.5.1.3).")
            st.checkbox("Underground / mounded tank (Tables 11.9/11.10)",
                        key="has_lpg_tank_underground_mounded",
                        help="Different rule set: ASME container, cathodic protection, separation measured from PRV / fill connections (not tank surface). ASME-listed containers may qualify for separation reduction per Table 11.10.b.")
            st.checkbox("Aboveground at-grade LPG tanks (Table 11.5)",
                        key="has_lpg_tank_at_grade",
                        help="Tick when the project also has tanks above ground at grade beside roof or underground tanks: the Table 11.5 items (72,000 Gal per location, Table 11.6.a separations, fixed water spray) then print as required. With neither roof nor underground ticked, the tanks are taken at grade (owner ruling 12.10.2026, P3 Ch11 Q4).")
        else:
            st.session_state["has_lpg_tank_roof_mounted"] = False
            st.session_state["has_lpg_tank_underground_mounded"] = False
            st.session_state["has_lpg_tank_at_grade"] = False

        if gas_choice.startswith("Gas cylinders"):
            st.markdown("*Cylinder variants (tick all that apply):*")
            st.checkbox("Indoor cylinder room (Table 11.2)",
                        key="has_lpg_cylinders_indoor",
                        help="Table 11.2: indoor cylinders only for residential / apartments / villas where Civil Defence permits (#2.4.2.1). Ventilated masonry compartment on an external wall, 1 x 24 kg, no ignition source within 1.5 m, detector at most 30 cm above floor.")
            st.selectbox(
                "New or modified building",
                options=[None, "new", "existing"],
                format_func=lambda v: {None: "Not chosen (required)",
                                       "new": "New or modified building",
                                       "existing": "Existing building (not modified)"}[v],
                key="new_or_modified_building_input",
                help="Required, no default. Cylinder type LPG installations in all new and "
                     "modified buildings are not allowed (Ch 11 #2.2.4, p.884). A new or "
                     "modified building stops here unless the Civil Defence approval below is "
                     "ticked; with no choice the tool stops until one is made (owner rulings "
                     "12.10.2026, P3 Ch11 Q3 and follow-up F-a1-1).")
            st.checkbox("Civil Defence approval obtained (#2.2.5)",
                        key="has_cd_cylinder_approval",
                        help="Permission to install LPG cylinders is strictly subject to approval of Civil Defence based on site and building inspection (Ch 11 #2.2.5, p.884). Tick only when that approval is held.")
        else:
            st.session_state["has_lpg_cylinders_indoor"] = False
            st.session_state["has_cd_cylinder_approval"] = False

        # Food truck is independent from the radio (mobile food truck is a separate scenario)
        st.markdown("*Food truck (independent option):*")
        st.checkbox("Food truck LPG cylinders (Table 11.3)",
                    key="has_lpg_cylinders_food_truck",
                    help="Mobile food truck LPG installation - dedicated ventilated cylinder compartment, secure mounting, suppression over cooking surface.")
        st.markdown("*Flame effect (assembly / entertainment):*")
        st.checkbox("Flame-effect LPG installation (Table 11.12)",
                    key="has_lpg_flame_effect",
                    help="LPG used for indoor / outdoor flame-effect shows (Ch 11 #3, Table 11.12): cylinders 6 m from the audience and stage, no piping within 3 m of the audience, 24 kg maximum indoors, indoor shows only in fully sprinklered buildings with fire alarm (#3.2.2).")
        if st.session_state.get("has_lpg_flame_effect"):
            st.selectbox(
                "Indoor / outdoor show",
                options=[None, "indoor", "outdoor", "both"],
                format_func=lambda v: {None: "Not stated", "indoor": "Indoor show",
                                       "outdoor": "Outdoor show",
                                       "both": "Indoor and outdoor shows"}[v],
                key="lpg_flame_effect_show_input",
                help="No indoor flame effect show shall be allowed if the building is not fully "
                     "sprinkler protected and provided with automatic fire detection and alarm "
                     "(Ch 11 #3.2.2, p.923). An indoor show in a building that is not sprinkler "
                     "protected stops here (owner ruling 12.10.2026, P3 Ch11 Q6).",
            )

    with st.expander("⚙️ Equipment (FP Table 9.31 + FA Table 8.15)", expanded=False):
        st.caption("Letters (A)-(P) are the rows of Ch 9 Table 9.31 Equipment Fire Protection "
                   "Systems (p.756-757); each also brings its Ch 8 Table 8.15 item (p.512-513).")
        st.checkbox("Check all", key="eq_all", on_change=eq_cb,
                    help="Ticks (or unticks) every equipment item below.")
        for _key, _label, _lead in _EQUIPMENT_WIDGETS:
            st.checkbox(_label, key=_key, help=_h(_lead, _key), on_change=_touch, args=(_key,))

    # =========================================================================
    # PER-CHAPTER expanders (only chapter-unique inputs)
    # =========================================================================
    st.markdown("---")
    st.markdown("### ⚙️ Chapter-specific inputs")

    # ----- FSA (Ch 2) -----  owner rulings 12.10.2026, Ch3 Q5 / Q6
    with st.expander("🚒 FSA - Settings (Ch 2 Fire Service Access)", expanded=False):
        st.session_state.setdefault("building_volume_m3_input", 0.0)
        st.number_input(
            "Building volume (m3)", min_value=0.0, step=1000.0,
            key="building_volume_m3_input",
            help="Gross cubical extent for storage / industrial fire access (#2.8.8.a, "
                 "#2.8.9.a, Tables 2.6 / 2.7). 0 = not entered: footprint x height is used "
                 "and labelled as the fallback.")
        st.checkbox("Waterfront property (Table 2.8)", key="is_waterfront",
                    help="#2.8.10: the Table 2.8 line is printed as required when ticked.")
        st.checkbox("Theme / amusement park (Table 2.5, #2.9.3, #2.9.4)", key="is_theme_park",
                    help="Table 2.5 extent (3/4 perimeter, not less than Table 2.3 / 2.4), "
                         "Emergency Command Centre, and a Fire Lift when multi storey. Also Ch 5 "
                         "Table 5.3 item 6.vi photoluminescent strips (p.397) and Ch 7 Table 7.3 "
                         "item 5 EVC + two-way telephone (p.439).")
        st.checkbox("Tower set back more than 30 m from the fire access road "
                    "(#2.8.6.b / #2.8.7.b)", key="tower_setback_over_30m",
                    help="Highrise / super highrise tower facade more than 30 m from the fire "
                         "access road: access to 1/4 of the tower perimeter above the podium.")

    # ----- MOE (Ch 3) -----  owner rulings 12.10.2026, Ch3 Q1-Q3
    with st.expander("🚶 MOE - Settings (Ch 3 Means of Egress)", expanded=False):
        st.session_state.setdefault("largest_storey_area_m2_input", 0.0)
        st.number_input(
            "Largest storey area (m2)", min_value=0.0, step=100.0,
            key="largest_storey_area_m2_input",
            help="Table 3.14 runs on the occupant load of the largest storey (#4.3.1, "
                 "#4.1.3). 0 = not entered: the whole GFA is used and the report says so. "
                 "Not used when the per-storey table below has lines.")
        if occupancy in ("mall_covered", "mall_open", "mall_mixed"):
            st.session_state.setdefault("mall_gla_m2_input", 0.0)
            st.number_input(
                "Mall gross leasable area, GLA (m2)", min_value=0.0, step=1000.0,
                key="mall_gla_m2_input",
                help="Ch 3 Table 3.13 row 14 (p.283-287): GLA less than 14,000 m2 -> 2.8 m2; "
                     "from 14,000 m2, 3.3 m2 + 0.1 m2 per full 1,290 m2, maximum 5.1 m2. "
                     "Sets the mall occupant load factor. 0 = GFA, labelled.")
        st.markdown("*Per-use areas (#1.4.5): Table 3.13 row and floor area*")
        st.session_state.setdefault("use_area_count_input", 0)
        _n_use = st.number_input(
            "Number of per-use areas", min_value=0, max_value=USE_AREA_MAX, step=1,
            key="use_area_count_input",
            help="Ch 3 #1.4.5 (p.242): the occupant load is figured on the actual use of each "
                 "floor area (Table 3.13, p.283-287). 0 = none: the densest Table 3.13 row "
                 "of the occupancy is used; fuel station, infrastructure, mixed and "
                 "underground are not evaluated until per-use areas are entered.")
        _row_ids = list(TABLE_3_13_ROWS)
        for _i in range(int(_n_use or 0)):
            _c1, _c2 = st.columns([3, 2])
            with _c1:
                st.selectbox(f"Use {_i + 1}: Table 3.13 row", options=_row_ids,
                             format_func=lambda r: f"{r} - {TABLE_3_13_ROWS[r][0]}",
                             key=f"use_area_row_{_i}",
                             help="The Ch 3 Table 3.13 row (p.283-287) whose occupant load "
                                  "factor applies to this use (#1.4.5, p.242).")
            with _c2:
                st.session_state.setdefault(f"use_area_m2_{_i}", 0.0)
                st.number_input(f"Use {_i + 1}: area (m2)", min_value=0.0,
                                step=50.0, key=f"use_area_m2_{_i}",
                                help="Floor area of this use. Area divided by the Table 3.13 "
                                     "factor gives its occupant load (#1.4.5, p.242).")
        # Owner answer 12.10.2026, F6: per-storey per-use table. When it has lines it
        # governs the OL and the Table 3.14 count (per storey, #4.3.1 / #4.1.3).
        st.markdown("*Per-storey table (optional): storey, Table 3.13 row, area, identical "
                    "storeys*")
        st.caption("One line per use on each storey; lines with the same storey name form "
                   "one storey. Row blank = the densest Table 3.13 row of the occupancy. "
                   "Identical storeys: how many storeys this one stands for (same count on "
                   "every line of the storey); the counts must add up to the floors above "
                   "grade plus the basements, or no exit count is stated. When the table has "
                   "lines it replaces the largest storey area and the per-use areas above for "
                   "the occupant load and Table 3.14.")
        if "storey_table_base" not in st.session_state:
            st.session_state["storey_table_base"] = list(
                st.session_state.get("storey_table_input") or [])
        _edited = st.data_editor(
            _storey_table_frame(st.session_state["storey_table_base"]),
            key="storey_table_editor", num_rows="dynamic", hide_index=True,
            column_config={
                "storey": st.column_config.TextColumn(
                    "Storey", help="Storey name or level, e.g. GF, L1, B1."),
                "row": st.column_config.SelectboxColumn(
                    "Table 3.13 row", options=list(TABLE_3_13_ROWS),
                    format_func=lambda r: f"{r} - {TABLE_3_13_ROWS[r][0]}",
                    help="Blank = the densest Table 3.13 row of the occupancy (Ch3 Q2)."),
                "area_m2": st.column_config.NumberColumn(
                    "Area (m2)", min_value=0.0, step=10.0,
                    help="Floor area of this use on this storey (#1.4.5)."),
                # Owner ruling 12.10.2026, P3 Storey Q1
                "count": st.column_config.NumberColumn(
                    "Identical storeys", min_value=1, step=1, format="%d",
                    help="Number of identical storeys this storey stands for (a typical "
                         "floor), at least 1; give every line of the storey the same count. "
                         "The storey counts that many times in the total occupant load; the "
                         "governing storey is still the one with the highest OL. Blank = 1."),
            })
        st.session_state["storey_table_input"] = _storey_table_records(_edited)

    # ----- FE (Ch 4) -----
    with st.expander("🧯 FE - Settings (Ch 4)", expanded=False):
        st.caption("Hazard add-ons of Ch 4 Table 4.3 Application of Fire Extinguishers "
                   "(p.373-377).")
        st.checkbox("Check all", key="fe_all", on_change=fe_cb,
                    help="Ticks (or unticks) every extinguisher add-on below.")
        st.checkbox(
            "Class B storage zones (chemical / linen / waste / flammable / solvent / lab stores)",
            key="has_class_b_storage_zones",
            help=_h("Ch 4 Table 4.3 row 2 Class B (p.375).", "has_class_b_storage_zones"))
        st.checkbox(
            "Combustible metals storage / activity (Class D)",
            key="has_combustible_metals",
            help=_h("Ch 4 Table 4.3 row 8 Class D fires (p.377).", "has_combustible_metals"))
        st.checkbox(
            "Group A plastic storage / activity (wheeled foam, Table 4.3 row 3)",
            key="has_group_a_plastic_storage",
            help=_h("Ch 4 Table 4.3 row 3 wheeled foam (p.376).", "has_group_a_plastic_storage"))
        st.checkbox(
            "HV room or heavy electrical machinery",
            key="has_hv_or_heavy_electrical",
            help=_h("Ch 4 Table 4.3 row 5 Class C, HV room (p.376). An MV room ticked under "
                    "Special rooms is already treated as HV (ruling R12).",
                    "has_hv_or_heavy_electrical"))
        # has_parking_area moved to "Special rooms and usage" - removed from here

    # ----- ES (Ch 5) - merged single expander -----
    with st.expander("🚪 ES - Settings (Ch 5 Exit Signs)", expanded=False):
        st.markdown("**Egress features**")
        st.checkbox("Check all - features", key="es_feat_all", on_change=es_feat_cb,
                    help="Ticks (or unticks) every egress feature below.")
        st.checkbox("Evacuation elevator (designated egress lift)", key="has_evacuation_elevator",
                    help=_h("A lift designated for evacuation.", "has_evacuation_elevator"))
        st.checkbox("Horizontal exits", key="has_horizontal_exits",
                    help=_h("Exits through a fire-rated wall into another compartment on the "
                            "same level.", "has_horizontal_exits"))
        st.checkbox("Dead-end / mistakable paths present", key="has_dead_end_paths", on_change=_touch, args=("has_dead_end_paths",),
                    help=_h("Doors, stairs or passages that could be mistaken for an exit.",
                            "has_dead_end_paths"))
        st.markdown("---")
        st.markdown("**Special zones / add-ons (Table 5.3)**")
        st.checkbox("Check all - zones", key="es_zone_all", on_change=es_zone_cb,
                    help="Ticks (or unticks) every special zone below (not the robotic "
                         "parking, which sits with the parking).")
        st.checkbox("Amusement / mazes / mirrors / play areas (assembly)", key="has_amusement_confounding",
                    help=_h("Ch 5 Table 5.3 item 6 (p.397).", "has_amusement_confounding"))
        st.checkbox("Night club / disco", key="has_nightclub_disco",
                    help=_h("Ch 5 Table 5.3 item 6.vii (p.397).", "has_nightclub_disco"))
        st.checkbox("Theatre / cinema", key="has_theater_cinema",
                    help=_h("Ch 5 Table 5.3 item 6.viii (p.397) and Ch 10 Table 10.27 items 8 / "
                            "14 (p.866); choose cinema or theatre below.", "has_theater_cinema"))
        # Audit UX-15: the kind sits next to the box that asks for it (it was in SC).
        with st.container():   # audit UX-06: fixed slot
            if st.session_state.get("has_theater_cinema"):
                st.selectbox(
                    "Theatre / cinema kind (Ch 10 Table 10.27 items 8 / 14)",
                    options=[None, "cinema", "theatre", "both"],
                    format_func=lambda v: {None: "Not stated", "cinema": "Cinema",
                                           "theatre": "Theatre", "both": "Cinema and theatre"}[v],
                    key="theater_cinema_kind_input",
                    help="Ch 10 Table 10.27 (p.866): cinema, item 8, dedicated smoke purge per "
                         "Section 2.13 (6 ACH permitted); theatre, item 14, smoke management "
                         "per Section 2.9. Not stated: the report prints the row as NOT "
                         "EVALUATED.",
                )
        st.checkbox("Nursery (inside education)", key="has_nursery_within",
                    help=_h("Ch 5 Table 5.3 item 8.ii (p.398).", "has_nursery_within"))
        st.checkbox("Auditorium (inside education)", key="has_auditorium_within",
                    help=_h("Ch 5 Table 5.3 item 8.iii (p.398).", "has_auditorium_within"))
        st.checkbox("HH storage / robotic / cold / cable spread / industrial basement", key="has_hh_storage_zones",
                    help=_h("Ch 5 Table 5.3 item 15.ii (p.399).", "has_hh_storage_zones"))
        st.checkbox("Mall play / food court / cinema zones", key="has_mall_play_food_cinema",
                    help=_h("Ch 5 Table 5.3 item 16.iii (p.399).", "has_mall_play_food_cinema"))
        st.checkbox("Villa converted to other use", key="villa_converted_use",
                    help=_h("A villa used for another occupancy: Ch 9 Table 9.21.d (number of "
                            "exit stairs under FP - Settings) and the converted-villa rows of "
                            "Ch 5 and Ch 8.", "villa_converted_use"))
        st.checkbox("Fuel dispensing multi-storey", key="fuel_dispensing_multistorey",
                    help=_h("A fuel dispensing building with more than the ground floor: the Ch 5 "
                            "exit sign rows apply.", "fuel_dispensing_multistorey"))

    # ----- EL (Ch 6) -----
    with st.expander("💡 EL - Settings (Ch 6 Emergency Lighting)", expanded=False):
        st.info("EL follows the height class, the occupancy and the special-room boxes above "
                "(Ch 6 Table 6.5, p.419; Table 6.6, p.420). No EL-specific inputs: the only "
                "EL-tied box is 'Tunnel inside building' under Various locations.")

    # ----- EVC (Ch 7) -----
    with st.expander("📢 EVC - Settings (Ch 7 Voice Evacuation)", expanded=False):
        st.info("EVC + Two-way Telephone auto-derive from height tier and occupancy class. "
                "No EVC-specific inputs needed - required for super-highrise / highrise / mall / assembly / "
                "amusement / education / hotel / detention / storage > 5,000 m². Lowrise residential / "
                "business / villa / parking / fuel dispensing are not required.")

    # ----- FA (Ch 8) -----
    with st.expander("🚨 FA - Settings (Ch 8 Fire Detection & Alarm)", expanded=False):
        st.info("FA auto-derives from height tier, occupancy and the Special Rooms / Various Locations / "
                "Equipment flags above (Tables 8.13 / 8.14 / 8.15). No FA-specific inputs needed.")


def gs_early(k):
    return bool(st.session_state.get(k, False))


# Audit UX-09 / UX-01 (28.10.2026): the input stops are collected first and shown
# together after the WHOLE sidebar is drawn (FP, SC and LPG settings included), so a
# stop never hides the inputs it asks for and no expander disappears while it shows.
_STOPS: list = []


def _stop(msg: str) -> None:
    _STOPS.append(msg)


# ---------- Height must be stated ------------------------------------------
# Every table routes on height (Ch 1 #1.7.39-#1.7.42); 0 m would silently be
# taken as lowrise. Only infrastructure (no building height) may stay at 0.
if float(height_m) <= 0 and occupancy != "infrastructure":
    _stop("Building height must be more than 0 m. Enter the height in the sidebar "
             "(Geometry) to evaluate the building.")

# ---------- Blank geometry (standing rule: a blank never counts as a pass) ------
# Fix round 28.10.2026: for any building with a height (not the infrastructure yard
# network), a ground-floor BUA, GFA or plot area of 0 stops by name. An underground
# building with a basement BUA may have no ground floor; a food or mercantile truck
# has no plot.
_is_truck = (occupancy == "mercantile_c" and st.session_state.get("mercantile_c_type_input")
             in ("food_truck", "mercantile_truck"))
_underground_occ = occupancy in ("high_depth_underground", "low_depth_underground")
if float(height_m) > 0 and occupancy != "infrastructure":
    for _blank_label, _blank_val, _blank_ref, _blank_skip in (
            ("Ground-floor BUA (m²)", ground_bua, "Ch 9 #4.1.12, p.695",
             _underground_occ and float(basement_bua) > 0),
            ("Total GFA (m²)", gfa, "Ch 3 #1.4.6, p.242", False),
            ("Plot area (m²)", plot_area, "Ch 9 #4.1.10, p.695", _is_truck)):
        if float(_blank_val or 0.0) <= 0 and not _blank_skip:
            _stop(f"'{_blank_label}' is 0 (sidebar: Building profile > Geometry). A blank "
                  f"input never counts as a pass: enter it ({_blank_ref}) to evaluate the "
                  f"building.")

# ---------- Mercantile group that is a Mall (audit ENG-02) -------------------
if (occupancy in ("mercantile_a", "mercantile_b") and gs_early("mercantile_multi_tenant")
        and float(ground_bua) > 3600):
    _stop("A group of mercantile occupancies under a single roof or not separated and "
             "having a ground floor built up area of more than 3600 m2, irrespective of the "
             "number of storeys, shall be considered as Malls (Ch 1 Table 1.1 row 11, p.50). "
             "Choose a Mall occupancy (covered, open or mixed) in the sidebar.")

# ---------- Storage hazard class must be chosen (CH9C-28) -------------------
if occupancy == "storage_industrial" and hazard is None:
    _stop("Select the storage hazard class in the sidebar. Table 9.27 "
             "groups depend on the stored materials and activities (#1.1.13, Tables 9.1 "
             "and 9.2), so the tool does not assume one.")


# ---------- Owner rulings 12.10.2026, Ch9 Q1 and Q9 -------------------------
_storage_secondary = (st.session_state.get("mixed_occupancy_mode_input") == "most_restrictive"
                      and "storage_industrial" in (st.session_state.get("secondary_occupancies_input") or [])
                      and occupancy != "storage_industrial")
if ((occupancy == "storage_industrial" or _storage_secondary)
        and not st.session_state.get("storage_tenancy_input")):
    _stop("Select the storage tenancy (sidebar: under 'Storage hazard class' for a storage "
          "building, or under Mixed occupancy when storage is another occupancy): "
          "multi-tenant Groups A-E or single tenant Groups F-J of Table 9.27 (p.724-733). "
          "Tanks and pumps differ, so the tool does not assume one (owner ruling Q-4, "
          "28.10.2026).")
# Verifier re-check 28.10.2026: an outlet ticked with its area blank decides Table 9.21.e
# row 1 / 2 (and the sprinkler system); a blank is never a pass.
# Same scope as the control and the Building flag (lowrise villas, business, Assembly C),
# so a tick left behind by a height or occupancy change never blocks the evaluation.
if (st.session_state.get("has_attached_commercial_outlet")
        and float(height_m) <= 15
        and occupancy in ("villa_private", "villa_commercial", "business", "assembly_c")
        and float(st.session_state.get("commercial_outlet_gf_bua_m2_input") or 0.0) <= 0):
    _stop("Enter the commercial outlet built-up ground floor area (sidebar: Ch 9 routing, under "
          "'Commercial / mercantile outlet attached'), or clear the tick. Table 9.21.e rows "
          "(p.711) split at 900 m2 of the outlet's GF BUA: row 2 adds sprinklers.")
if _storage_secondary and not st.session_state.get("secondary_storage_hazard_input"):
    _stop("Select the hazard class of the storage / industrial occupancy listed under "
             "'Other occupancies' (sidebar, Mixed occupancy). Table 9.27 groups depend on the "
             "stored materials and activities (#1.1.13, Tables 9.1 and 9.2), so the tool does "
             "not assume one (owner ruling 12.10.2026, Ch9 Q9).")
if (occupancy == "storage_industrial" or _storage_secondary) \
        and float(st.session_state.get("sum_gf_bua_m2_input") or 0.0) <= 0:
    _stop("Enter the sum of GF BUAs of all buildings on the plot (sidebar: under 'Storage "
          "hazard class', or under Mixed occupancy when storage is another occupancy). Table "
          "9.27 row 4 applies above 3600 m2 (#4.1.13); enter this building's GF BUA when it "
          "is the only building on the plot (owner ruling 12.10.2026, Ch9 Q1).")

# ---------- Owner ruling 12.10.2026, P3 App Q2 -----------------------------------
if (st.session_state.get("has_parking_area") and parking_basement_levels_val is not None
        and int(parking_basement_levels_val) > int(floors_below)):
    _stop(f"Attached parking basement levels ({int(parking_basement_levels_val)}) cannot "
             f"exceed the building's basements ({int(floors_below)}): the parking is in the "
             "building (owner ruling 12.10.2026, P3 App Q2). Correct either input.")
# Owner ruling 12.10.2026, P3 follow-up F-a3: nor its depth the building's depth.
if (st.session_state.get("has_parking_area") and parking_depth_m_val is not None
        and float(parking_depth_m_val) > float(depth_below_grade)):
    _stop(f"Attached parking depth below the fire access level ({float(parking_depth_m_val):g} m) "
             f"cannot exceed the building's depth below grade ({float(depth_below_grade):g} m): "
             "the parking is in the building (owner ruling 12.10.2026, P3 follow-up F-a3). "
             "Correct either input.")
# Owner ruling 13.10.2026, P3 follow-up F-a4-2: no depth without basement levels.
if (st.session_state.get("has_parking_area") and parking_basement_levels_val is not None
        and int(parking_basement_levels_val) == 0 and parking_depth_m_val is not None
        and float(parking_depth_m_val) > 0):
    _stop(f"Attached parking depth below the fire access level ({float(parking_depth_m_val):g} m) "
             "is entered with 0 parking basement levels: a parking with no basement levels has "
             "no depth below the fire access level (owner ruling 13.10.2026, P3 follow-up "
             "F-a4-2). Enter the parking basement levels, or clear the depth.")

# ---------- Owner ruling 12.10.2026, P3 Storey Q4 (as Ch9 Q9) ------------------
_animal_secondary = (st.session_state.get("mixed_occupancy_mode_input") == "most_restrictive"
                     and "animal_housing" in (st.session_state.get("secondary_occupancies_input") or [])
                     and occupancy != "animal_housing")
if _animal_secondary \
        and st.session_state.get("secondary_animal_housing_group_input") not in ANIMAL_HOUSING_GROUPS:
    _stop("Select the group of the animal housing occupancy listed under 'Other "
             "occupancies' (sidebar, Mixed occupancy): Group A (animal market, pet shops, bird "
             "market, veterinary clinic) and Group C (zoo) are Light Hazard (#1.1.13.1.q, r, "
             "p.528); Group B (stable, animal sheds, livestock shelter, slaughter houses) is "
             "Ordinary Hazard Group 2 (#1.1.13.3.a, p.529). The tool does not assume one (owner "
             "ruling 12.10.2026, P3 Storey Q4).")

# ---------- Owner ruling 12.10.2026, P3 Storey Q1 ------------------------------
_bad_counts = [f"line {i} ({ln.get('storey') or 'no storey name'}): {ln.get('count')!r}"
               for i, ln in enumerate(st.session_state.get("storey_table_input") or [], 1)
               if not (isinstance(_storey_count(ln.get("count")), int)
                       and not isinstance(ln.get("count"), bool)
                       and _storey_count(ln.get("count")) >= 1)]
if _bad_counts:
    _stop("Per-storey table: the identical storeys count must be a whole number of at "
             "least 1 (owner ruling 12.10.2026, P3 Storey Q1). Correct " +
             "; ".join(_bad_counts) + ".")

if occupancy == "animal_housing" \
        and st.session_state.get("animal_housing_group_input") not in ANIMAL_HOUSING_GROUPS:
    _stop("Select the animal housing group (sidebar, under the occupancy): Group A (animal "
             "market, pet shops, bird market, veterinary clinic) and Group C (zoo) are Light "
             "Hazard (#1.1.13.1.q, r, p.528); Group B (stable, animal sheds, livestock shelter, "
             "slaughter houses) is Ordinary Hazard Group 2 (#1.1.13.3.a, p.529). A project "
             "saved before the split has no group, and the tool does not assume one (owner "
             "answer 12.10.2026, Ch9 Q6).")

# ---------- Owner rulings 13.10.2026, P4 Q1, Q5, Q6 ---------------------------
if occupancy in ("mercantile_a", "mercantile_b") and gs_early("is_mercantile_group_c"):
    _stop("This project was saved with 'Mercantile Group C (stand-alone)' ticked. Mercantile "
             "Group C (kiosks, food trucks, mercantile trucks, Ch 1 Table 1.1 row 11, p.50) is "
             "now its own occupancy: choose 'mercantile_c' as the occupancy, or untick 'Mercantile "
             "Group C tick from an older file' in the sidebar to confirm this building is "
             "Mercantile Group A or B (owner ruling 13.10.2026, P4 Q6).")
if occupancy == "business" and st.session_state.get("business_group_input") not in BUSINESS_GROUPS:
    _stop("Select the Business group (sidebar, under the occupancy): Group A electronic data "
             "processing, telephone exchanges, radio and television stations, laboratories; Group "
             "B offices, banks, government offices, post offices; Group C barber shops, beauty "
             "shops, massage centers, typing and translation centers, print shops, photo studios "
             "(Ch 1 Table 1.1 row 2, p.48). Group C takes Ch 6 Table 6.5 item 11 below 23 m, so "
             "the tool does not assume a group (owner ruling 13.10.2026, P4 Q1)."
             + (" The file had the old 'Business Group C (stand-alone)' box ticked."
                if st.session_state.get("_legacy_business_group_c") else ""))
if occupancy == "mercantile_c":
    if st.session_state.get("mercantile_c_type_input") not in MERCANTILE_C_TYPES:
        _stop("Select the Mercantile Group C type (sidebar, under the occupancy): kiosk "
                 "(permanent or temporary), food truck or mercantile truck (Ch 1 Table 1.1 row "
                 "11, p.50). A kiosk and a truck take different items, so the tool does not "
                 "assume one (owner ruling 13.10.2026, P4 Q5).")
    if st.session_state.get("secondary_occupancies_input"):
        _stop("A Mercantile Group C kiosk or truck is evaluated as its own building: clear "
                 "'Other occupancies' (sidebar, Mixed occupancy), or evaluate the host building "
                 "separately (owner rulings 13.10.2026, P4 Q4-Q5).")
    if (st.session_state.get("mercantile_c_type_input") in ("kiosk_permanent", "kiosk_temporary")
            and float(ground_bua) > 18):
        _stop(f"Kiosks or group of kiosks shall not have an area more than 18 m2 (Ch 1 Table "
                 f"1.9 item 48 v, p.98). The ground floor built-up area (the kiosk area) is "
                 f"{float(ground_bua):g} m2: enter 18 m2 or less, or choose Mercantile Group A "
                 f"or B.")

# ---------- Pre-evaluate to detect wet riser requirement ---------------------
prelim = None if _STOPS else _cached_evaluate(Building(
    project_name=project_name, occupancy=occupancy, height_m=height_m,
    floors_above_grade=int(floors_above), floors_below_grade=int(floors_below),
    depth_below_grade_m=float(depth_below_grade),
    gross_floor_area_m2=gfa, ground_floor_bua_m2=ground_bua,
    basement_bua_m2=basement_bua, plot_area_m2=plot_area, hazard_class=hazard,
).model_dump_json())

with st.sidebar:
    # ----- FP (Ch 9) - wet riser sizing + motor-fuel sub-group -----
    with st.expander("💧 FP - Settings (Ch 9)", expanded=False):
        # Motor fuel dispensing sub-group selector (Table 9.25 A/B/C) - only when relevant
        if occupancy == "motor_fuel_dispensing":
            mfg_choice = st.radio(
                "Motor fuel dispensing sub-group (Table 9.25)",
                options=[
                    "Group A - mini-marts/restaurants/retail/service as INDIVIDUAL buildings (sprinklers + 300 gpm @ 4.5 bar)",
                    "Group B - restaurants/bakeries within a single mini mart, service/repair stations, fleet, marine (hose reel only + 50 gpm @ 6.9 bar)",
                    "Group C - mini-mart ONLY without service/repair, OR EV charging (extinguishers only - no water-based system)",
                ],
                key="motor_fuel_group_radio", on_change=_touch, args=("motor_fuel_group_radio",),
                help="Three groups in Table 9.25 with very different system requirements. Pick the one matching the facility.",
            )
            motor_fuel_group_val = mfg_choice[6]  # 'A', 'B', or 'C'
        else:
            motor_fuel_group_val = "A"

        # Storage / Industrial specialty inputs (Table 9.27): drawn under the storage
        # hazard class since audit UX-01 (28.10.2026), before any stop.
        if occupancy == "storage_industrial":
            st.caption("Storage / industrial (Table 9.27) inputs are under 'Storage hazard "
                       "class' in the Building profile.")

        # Tunnel Fire Protection (Table 9.28) - shown when has_tunnel ticked
        if st.session_state.get("has_tunnel"):
            st.markdown("**Tunnel Fire Protection (Table 9.28):**")
            tunnel_kind_choice = st.radio(
                "Tunnel kind",
                options=["Road / Rail tunnel", "Cable tunnel"],
                key="tunnel_kind_radio", on_change=_touch, args=("tunnel_kind_radio",),
                help="Cable: deluge water spray OR water mist. Road/rail: depends on length tier.",
            )
            tunnel_kind_val = "cable" if tunnel_kind_choice.startswith("Cable") else "road_rail"
            st.session_state.setdefault("tunnel_length_m_input", 0.0)
            tunnel_length_m_val = st.number_input(
                "Tunnel length (m)", min_value=0.0, step=10.0,
                help="Cable: < 60 m vs >= 60 m. Road/rail: < 90 m (no FP), 90-1000 m, > 1000 m.",
                key="tunnel_length_m_input",
            )
        else:
            tunnel_kind_val = "road_rail"
            tunnel_length_m_val = 0.0

        # Routing inputs that change which Table 9.18-9.24 row applies.
        if occupancy == "parking_open" or gs_early("villa_converted_use"):
            st.session_state.setdefault("exit_stairs_input", 2)
            st.number_input(
                "Number of exit stairs", min_value=1, step=1, key="exit_stairs_input", on_change=_touch, args=("exit_stairs_input",),
                help="Table 9.24.C.2 (open parking 15 m to less than 23 m): 750 gpm for 2 stairs, "
                     "1000 gpm for 3 or more. Table 9.21.d: converted villa with one stair.",
            )
        if occupancy == "parking_open":
            st.checkbox("Covered / shaded parking, one level only (Table 9.24.D)",
                        key="is_covered_shaded_parking",
                        help="Table 9.24.D rows are keyed on the covered/shaded parking area "
                             "(taken as the ground-floor BUA).")
        if float(height_m) < 23:
            st.checkbox("Single exit stair (Tables 9.20.c, 9.21.c, 9.21.d)",
                        key="has_single_exit_stair",
                        help="Midrise/lowrise residential, business and similar buildings with "
                             "only one exit stair have their own rows (Ch 9 Tables 9.20.c / "
                             "9.21.c, p.703 / p.709) and the single-exit conditions of Ch 3 "
                             "Table 3.24 item 2 (p.317) / Table 3.19 item 2 (p.304).")
        if int(floors_below) > 0:
            st.checkbox("Fire pump room at grade (not in the lowest basement)",
                        key="pump_room_at_grade",
                        help="Table 9.19 rows and Table 9.6 item 13 zoning are measured from the "
                             "lowest fire pump set level. Unticked, the tool takes the pump room "
                             "at the lowest basement (height + depth below grade).")
        if occupancy == "storage_industrial":
            st.checkbox("Ground floor more than 100 m from an existing functional hydrant (#4.1.6)",
                        key="gf_beyond_100m_from_hydrant",
                        help=_h("#4.1.6 (p.694): storage and industrial occupancies whose "
                                "built-up ground floor areas are more than 100 m away from "
                                "existing, functional and available hydrants take a yard fire "
                                "hydrant system per Section 3.11.",
                                "gf_beyond_100m_from_hydrant"))
        # Audit CH9A-20: #4.1.2 (p.694)
        st.checkbox("Water reactive materials stored or handled (#4.1.2)",
                    key="has_water_reactive_materials",
                    help="#4.1.2: water based fire protection systems shall not be installed or "
                         "used where water reactive materials are stored and handled.")
        # Audit CH9B-14: Tables 9.21.e and 9.21.f (p.711-712), lowrise only.
        if float(height_m) <= 15 and occupancy in ("villa_private", "villa_commercial",
                                                   "business", "assembly_c"):
            st.checkbox("Commercial / mercantile outlet attached or in the same plot "
                        "(Table 9.21.e)", key="has_attached_commercial_outlet",
                        help="#4.5.5 (p.711): lowrise villas (G+1), business (Groups A, B, C) and "
                             "mosques (Assembly Group C) having commercial and mercantile outlets "
                             "attached to it or in the same plot.")
            if st.session_state.get("has_attached_commercial_outlet"):
                st.session_state.setdefault("commercial_outlet_gf_bua_m2_input", 0.0)
                st.number_input("Commercial outlet built-up ground floor area (m2) (required)",
                                min_value=0.0, step=50.0,
                                key="commercial_outlet_gf_bua_m2_input",
                                help="Table 9.21.e rows: up to 900 m2 / more than 900 m2 of the "
                                     "OUTLET's built-up ground floor area. 0 = not entered: the "
                                     "row is not evaluated.")
        if float(height_m) <= 15:
            st.selectbox(
                "Tent / marquee / site office (Table 9.21.f)",
                ["none", "temporary", "permanent", "commercial_desert", "site_office_short",
                 "site_office_long", "small_detached"],
                format_func=lambda x: {
                    "none": "Not a tent / marquee / site office",
                    "temporary": "A. Temporary tents and marquees",
                    "permanent": "B. Permanent tents and marquees",
                    "commercial_desert": "C. Permanent commercial tents and desert camps",
                    "site_office_short": "D. Site offices (required for less than 6 months)",
                    "site_office_long": "E. Site offices (required for more than 6 months)",
                    "small_detached": "F. Detached G+1 building, GF BUA up to 150 m2, any occupancy",
                }[x],
                key="tent_marquee_kind_input",
                help="#4.5.6 (p.712): tents, marquees, site offices and site dwellings take "
                     "Table 9.21.f instead of the generic lowrise rows.")

        if prelim is not None and prelim.requires_wet_riser:
            st.markdown("**Wet riser sizing** — required because the matched FP branch emits a wet-riser system.")
            standpipe_choice = st.radio(
                "Number of standpipes in the wet-riser system",
                options=["2 standpipes (Fire pump 750 gpm @ 6.9 bar)",
                         "3 or more standpipes (Fire pump 1000 gpm @ 6.9 bar)"],
                help="Ch 9 Tables 9.18-9.20 pump notes (p.696-701): the fire pump is 750 gpm "
                     "at 6.9 bar for 2 standpipes and 1000 gpm for 3 or more. The choice sizes "
                     "the Fire Pump line under FP Branch Requirements. Left on 2, it is listed "
                     "under 'Assumptions used in this report'.",
                key="wet_riser_radio", on_change=_touch, args=("wet_riser_radio",),
            )
            wet_riser_standpipes = 2 if standpipe_choice.startswith("2 ") else 3
        elif prelim is None:
            wet_riser_standpipes = 2
            st.caption("Wet-riser sizing: shown once the input stop in the main page is "
                       "resolved.")
        else:
            wet_riser_standpipes = 2
            st.info("Wet-riser sizing N/A - the matched FP branch does not require a wet-riser system.")
        st.caption("All other FP outputs auto-derived from occupancy + geometry + Special Rooms / Various Locations / Equipment flags above.")

    # ----- SC (Ch 10) -----
    with st.expander("💨 SC - Settings (Ch 10)", expanded=False):
        st.session_state.setdefault("corridor_length_m", 0.0)
        corridor_length_m = st.number_input(
            "Longest enclosed corridor length (m)",
            min_value=0.0, step=5.0,
            key="corridor_length_m",   # audit ENG-23: saved and restored
            help="More than 60 m in a lowrise / midrise building: Ch 10 Table 10.27 item 4 "
                 "requires natural ventilation per Section 2.15 where the exterior façade / "
                 "roof is accessible. The code's list (mercantile, staff / labour "
                 "accommodation, residential, office) reads 'such as', so it applies to any "
                 "occupancy; hospitals, schools and malls follow their own rows.",
        )
        # Hall-area trigger: Table 10.27 items 9-13 (assembly) and item 2.3 (school sports
        # hall / auditorium), both "having area more than 2000 m2". Phase 3 CH10-16: no
        # GFA fallback; 0 = not entered.
        if occupancy.startswith(("assembly_", "education_")):
            st.session_state.setdefault("assembly_area_m2_input", 0.0)
            assembly_area_m2 = st.number_input(
                "Largest assembly-hall / sports-hall / auditorium area (m²)",
                min_value=0.0, step=100.0,
                key="assembly_area_m2_input",
                help="Ch 10 Table 10.27 items 9-13 (exhibition / assembly / sports hall / "
                     "auditorium / indoor stadium) and item 2.3 (school sports hall / "
                     "auditorium): smoke purge per Section 2.13 when more than 2,000 m2. "
                     "Left at 0 in an assembly building of more than 2,000 m2 GFA, the "
                     "report prints these rows as NOT EVALUATED.",
            )
        else:
            assembly_area_m2 = 0.0
        # Table 10.27 item 8 / item 14 (Phase 3 CH10-16): the theatre / cinema kind is
        # asked next to the 'Theatre / cinema' box under ES - Settings (audit UX-15).
        st.caption("Other SC outputs (Tables 10.19-10.27) auto-derive from height tier, occupancy, "
                   "depth below grade and Special Rooms / Various Locations / Equipment flags.")

    # ----- LPG (Ch 11) -----
    with st.expander("⛽ LPG - Settings (Ch 11)", expanded=False):
        st.info("LPG output auto-derived from the gas-system choice under 'Gas systems (Ch 11 LPG)' above:\n\n"
                "- **LPG tanks** (aboveground / roof / podium)\n"
                "- **Gas infrastructure connection** (municipal / central piped supply)\n"
                "- **Gas cylinders** (villa / domestic / small commercial)\n\n"
                "If none are ticked, the LPG section reports 'No Gas System Present'.")


if _STOPS:
    for _msg in _STOPS:
        st.error(_msg)
    st.stop()


def gs(k):
    return bool(st.session_state.get(k, False))

building = Building(
    project_name=project_name, occupancy=occupancy, height_m=height_m,
    height_datum=st.session_state.get("height_datum_input", "grade"),
    mixed_occupancy_mode=st.session_state.get("mixed_occupancy_mode_input", "none"),
    secondary_occupancies=[o for o in st.session_state.get("secondary_occupancies_input", [])
                           if o != occupancy],
    construction_type=st.session_state.get("construction_type_input", "unspecified"),
    floors_above_grade=int(floors_above), floors_below_grade=int(floors_below),
    depth_below_grade_m=float(depth_below_grade),
    gross_floor_area_m2=gfa, ground_floor_bua_m2=ground_bua,
    basement_bua_m2=basement_bua, plot_area_m2=plot_area, hazard_class=hazard,
    corridor_length_m=float(corridor_length_m),
    assembly_area_m2=float(assembly_area_m2),
    has_high_ceiling=gs("has_high_ceiling"), ceiling_height_m=ceiling_height_m,
    wet_riser_standpipes=int(wet_riser_standpipes),
    motor_fuel_group=motor_fuel_group_val,
    # Storage / Industrial specialty (Table 9.27 specialty groups)
    is_aircraft_hanger=gs("is_aircraft_hanger"),
    is_cold_storage=gs("is_cold_storage"),
    is_flammable_liquid_warehouse=gs("is_flammable_liquid_warehouse"),
    is_flammable_liquid_industrial=gs("is_flammable_liquid_industrial"),
    is_open_yard_storage=gs("is_open_yard_storage"),
    is_plant_nursery=gs("is_plant_nursery"),
    storage_tenancy=(st.session_state.get("storage_tenancy_input")
                     if occupancy == "storage_industrial" or _storage_secondary
                     else None),   # ruling Q-4 (main or listed storage)
    is_idle_pallet_storage=gs("is_idle_pallet_storage"),
    is_extra_hazard_2=(gs("is_extra_hazard_2") and occupancy == "storage_industrial")
    or _robotic_eh2,   # owner ruling 12.10.2026, Ch9 Q7
    storage_commodity=(st.session_state.get("storage_commodity_input") or "none")
    if occupancy == "storage_industrial" else "none",
    max_unit_area_m2=float(st.session_state.get("max_unit_area_m2_input") or 0.0)
    if occupancy == "storage_industrial" else 0.0,
    sum_gf_bua_m2=float(st.session_state.get("sum_gf_bua_m2_input") or 0.0)
    if (occupancy == "storage_industrial" or _storage_secondary) else 0.0,
    # Owner ruling 12.10.2026, Ch9 Q9
    secondary_storage_hazard=st.session_state.get("secondary_storage_hazard_input")
    if _storage_secondary else None,
    # Owner ruling 12.10.2026, P3 Storey Q4
    secondary_animal_housing_group=st.session_state.get("secondary_animal_housing_group_input")
    if _animal_secondary else None,
    hangar_group=st.session_state.get("hangar_group_input") or "I",
    is_aboveground_tank_storage=gs("is_aboveground_tank_storage") and occupancy == "storage_industrial",
    ast_storage_area_m2=float(st.session_state.get("ast_storage_area_m2_input") or 0.0),
    ast_tank_capacity_m3=float(st.session_state.get("ast_tank_capacity_m3_input") or 0.0),
    has_exterior_balconies=gs("has_exterior_balconies"),
    tunnel_kind=tunnel_kind_val,
    tunnel_length_m=float(tunnel_length_m_val),
    # Special rooms
    has_anesthetizing_room=gs("has_anesthetizing_room"),
    has_battery_charger_room=gs("has_battery_charger_room"),
    has_bms_room=gs("has_bms_room"), has_battery_room=gs("has_battery_room"),
    has_computer_room=gs("has_computer_room"), has_control_room=gs("has_control_room"),
    has_diesel_generator_room=gs("has_diesel_generator_room"),
    has_main_electrical_room=gs("has_main_electrical_room"),
    has_ahu_room=gs("has_ahu_room"), has_lv_mv_room=gs("has_lv_mv_room"),
    has_mv_room=gs("has_mv_room"),
    has_transformer_room_utility=gs("has_transformer_room_utility"),
    has_transformer_room_private=gs("has_transformer_room_private"),
    has_lift_machine_room=gs("has_lift_machine_room"),
    has_main_telephone_room=gs("has_main_telephone_room"),
    has_main_server_room=gs("has_main_server_room"),
    has_rmu_idf_mdf_room=gs("has_rmu_idf_mdf_room"),
    has_gsm_room=gs("has_gsm_room"), has_operation_theater=gs("has_operation_theater"),
    has_mri_scanning_room=gs("has_mri_scanning_room"),
    has_records_room=gs("has_records_room"), has_ups_room=gs("has_ups_room"),
    has_cold_freezer_room=gs("has_cold_freezer_room"),
    has_fire_pump_room=gs("has_fire_pump_room"),
    # Various locations
    has_atrium=gs("has_atrium"), has_rain_screen_glazing=gs("has_rain_screen_glazing"),
    has_stairs=gs("has_stairs"), has_elevator=gs("has_elevator"),
    has_bathrooms_with_heaters=gs("has_bathrooms_with_heaters"),
    has_laundry_storage_rooms=gs("has_laundry_storage_rooms"),
    has_pantries=gs("has_pantries"),
    has_permanent_stages=gs("has_permanent_stages"),
    has_roof_lpg_or_restaurant=gs("has_roof_lpg_or_restaurant"),
    has_roof_restaurant_assembly=gs("has_roof_restaurant_assembly"),
    has_food_trucks=gs("has_food_trucks"),
    has_garbage_chute=gs("has_garbage_chute"),
    has_tunnel=gs("has_tunnel"),
    # Equipment + Gas
    has_commercial_kitchen=gs("has_commercial_kitchen"),
    has_lpg_tanks=gs("has_lpg_tanks"),
    has_gas_infra_connection=gs("has_gas_infra_connection"),
    has_gas_cylinders_villa=gs("has_gas_cylinders_villa"),
    has_lpg_tank_roof_mounted=gs("has_lpg_tank_roof_mounted"),
    has_lpg_tank_underground_mounded=gs("has_lpg_tank_underground_mounded"),
    has_lpg_cylinders_indoor=gs("has_lpg_cylinders_indoor"),
    has_lpg_cylinders_food_truck=gs("has_lpg_cylinders_food_truck"),
    has_lpg_flame_effect=gs("has_lpg_flame_effect"),
    # Owner rulings 12.10.2026, P3 Ch11 Q3, Q4, Q6
    has_lpg_tank_at_grade=gs("has_lpg_tank_at_grade") and gs("has_lpg_tanks"),
    # P3 follow-up F-a1-1: None = not chosen (the app stops below for cylinders)
    is_new_or_modified_building=({"new": True, "existing": False}.get(
        st.session_state.get("new_or_modified_building_input"))
        if gs("has_gas_cylinders_villa") else None),
    has_cd_cylinder_approval=gs("has_cd_cylinder_approval") and gs("has_gas_cylinders_villa"),
    lpg_flame_effect_show=(st.session_state.get("lpg_flame_effect_show_input")
                           if gs("has_lpg_flame_effect") else None),
    has_flammable_liquid_tanks=gs("has_flammable_liquid_tanks"),
    has_cable_spread_areas=gs("has_cable_spread_areas"),
    has_boilers=gs("has_boilers"),
    has_cooling_towers=gs("has_cooling_towers"),
    has_oil_filled_transformers=gs("has_oil_filled_transformers"),
    has_bulk_oil_storage=gs("has_bulk_oil_storage"),
    has_bulk_flammable_liquid_storage=gs("has_bulk_flammable_liquid_storage"),
    has_bulk_flammable_gas_storage=gs("has_bulk_flammable_gas_storage"),
    has_bulk_flammable_solid_storage=gs("has_bulk_flammable_solid_storage"),
    has_high_hazard_logistics=gs("has_high_hazard_logistics"),
    has_chemical_warehouse=gs("has_chemical_warehouse"),
    has_explosives=gs("has_explosives"),
    has_processing_plant=gs("has_processing_plant"),
    # FE chapter-specific
    has_class_b_storage_zones=gs("has_class_b_storage_zones"),
    has_combustible_metals=gs("has_combustible_metals"),
    has_group_a_plastic_storage=gs("has_group_a_plastic_storage"),
    has_hv_or_heavy_electrical=gs("has_hv_or_heavy_electrical"),
    has_parking_area=gs("has_parking_area"),
    attached_parking_kind=attached_parking_kind_val,
    parking_area_m2=float(parking_area_m2_val),
    # Owner ruling 12.10.2026, P3 App Q2 (None = not entered)
    parking_height_m=None if parking_height_m_val is None else float(parking_height_m_val),
    parking_basement_levels=(None if parking_basement_levels_val is None
                             else int(parking_basement_levels_val)),
    # Owner ruling 12.10.2026, P3 follow-up F-a3 (None = building depth used, named)
    parking_depth_m=None if parking_depth_m_val is None else float(parking_depth_m_val),
    # ES chapter-specific
    has_evacuation_elevator=gs("has_evacuation_elevator"),
    has_horizontal_exits=gs("has_horizontal_exits"),
    has_dead_end_paths=gs("has_dead_end_paths"),
    has_amusement_confounding=gs("has_amusement_confounding"),
    has_nightclub_disco=gs("has_nightclub_disco"),
    has_theater_cinema=gs("has_theater_cinema"),
    theater_cinema_kind=(st.session_state.get("theater_cinema_kind_input")
                         if gs("has_theater_cinema") else None),
    has_nursery_within=gs("has_nursery_within"),
    has_auditorium_within=gs("has_auditorium_within"),
    has_hh_storage_zones=gs("has_hh_storage_zones"),
    has_mall_play_food_cinema=gs("has_mall_play_food_cinema"),
    has_robotic_parking=gs("has_robotic_parking"),
    villa_converted_use=gs("villa_converted_use"),
    fuel_dispensing_multistorey=gs("fuel_dispensing_multistorey"),
    # Ch 9 routing inputs (shown only where they apply; hidden ones stay off)
    exit_stairs=(int(st.session_state.get("exit_stairs_input", 2) or 2)
                 if occupancy == "parking_open" or gs("villa_converted_use") else 2),
    is_covered_shaded_parking=gs("is_covered_shaded_parking") and occupancy == "parking_open",
    has_single_exit_stair=gs("has_single_exit_stair") and float(height_m) < 23,
    pump_room_at_grade=gs("pump_room_at_grade") and int(floors_below) > 0,
    gf_beyond_100m_from_hydrant=gs("gf_beyond_100m_from_hydrant") and occupancy == "storage_industrial",
    # Ch 3 / Ch 2 inputs (owner rulings 12.10.2026, Ch3 Q1-Q6)
    largest_storey_area_m2=float(st.session_state.get("largest_storey_area_m2_input") or 0.0),
    mall_gla_m2=(float(st.session_state.get("mall_gla_m2_input") or 0.0)
                 if occupancy in ("mall_covered", "mall_open", "mall_mixed") else 0.0),
    use_areas=[{"row": st.session_state.get(f"use_area_row_{i}"),
                "area_m2": float(st.session_state.get(f"use_area_m2_{i}") or 0.0)}
               for i in range(int(st.session_state.get("use_area_count_input") or 0))
               if st.session_state.get(f"use_area_row_{i}") in TABLE_3_13_ROWS],
    building_volume_m3=float(st.session_state.get("building_volume_m3_input") or 0.0),
    is_waterfront=gs("is_waterfront"),
    is_theme_park=gs("is_theme_park"),
    tower_setback_over_30m=gs("tower_setback_over_30m"),
    # Owner answer 12.10.2026, F6: per-storey table (blank = the inputs above)
    storey_uses=[{"storey": ln.get("storey") or "", "row": ln.get("row"),
                  "area_m2": float(ln.get("area_m2") or 0.0),
                  # P3 Storey Q1: a line saved before the column counts once
                  "count": _storey_count(ln.get("count"))}
                 for ln in (st.session_state.get("storey_table_input") or [])],
    # Owner answer 12.10.2026, Ch9 Q6
    animal_housing_group=(st.session_state.get("animal_housing_group_input")
                          if occupancy == "animal_housing" else None),
    # Phase 3 app package (audit ENG-02, CH9A-20, CH9B-14)
    mercantile_multi_tenant=gs("mercantile_multi_tenant") and occupancy in ("mercantile_a", "mercantile_b"),
    # Owner rulings 13.10.2026, P4 Q1-Q5
    **_p4_building_kwargs(occupancy),
    has_water_reactive_materials=gs("has_water_reactive_materials"),
    has_attached_commercial_outlet=(gs("has_attached_commercial_outlet") and float(height_m) <= 15
                                    and occupancy in ("villa_private", "villa_commercial",
                                                      "business", "assembly_c")),
    commercial_outlet_gf_bua_m2=float(st.session_state.get("commercial_outlet_gf_bua_m2_input") or 0.0),
    tent_marquee_kind=(st.session_state.get("tent_marquee_kind_input") or "none")
    if float(height_m) <= 15 else "none",
)
# Read back by tests (round trip of every input, audit ENG-23); not saved.
st.session_state["_building_json"] = building.model_dump_json()

# ---------- Ch 11 prohibitions (owner rulings 12.10.2026, P3 Ch11 Q3 and Q6) ----
_lpg_stops = lpg_input_stops(building)
if _lpg_stops:
    for _msg in _lpg_stops:
        st.error(_msg)
    st.stop()
report = _cached_evaluate(building.model_dump_json())


# ---------- Top summary ------------------------------------------------------
# Audit UX-14 (28.10.2026): readable labels; rule IDs only behind "Show rule IDs".
_SHOW_RULE_IDS = bool(st.session_state.get("show_rule_ids", False))


def _humanize_codes(text: str) -> str:
    """Occupancy codes with an underscore (mercantile_a, hotel_a, parking_enclosed ...)
    read as their Table 1.1 names in notes written by the engine (audit UX-14)."""
    if not text:
        return text

    def _rep(m):
        code = m.group(0)
        return _occ_label(code) if code in OCCUPANCY_DEFS else code
    return _re.sub(r"\b[a-z]+(?:_[a-z0-9]+)+\b", _rep, text)


def _branch_chip(ch):
    if ch is None or not ch.selected_branch:
        return None
    lab = branch_label(ch)
    return f"{lab} [rule {ch.selected_branch}]" if _SHOW_RULE_IDS else lab


# Audit UX-08: the first load is a sample, and it says so where the user looks first.
_GEOMETRY_KEYS = ("height_m_input", "floors_above_input", "floors_below_input",
                  "ground_bua_input", "gfa_input", "plot_area_input")
_IS_SAMPLE = (not st.session_state.get("_profile_source") and occupancy == "residential"
              and not (project_name or "").strip()
              and all(st.session_state.get(k) == FIRST_LOAD_DEFAULTS[k] for k in _GEOMETRY_KEYS))
if _IS_SAMPLE:
    st.info("**Sample building.** This report is for the first-load sample (45 m residential, "
            "12 floors, 1 basement). Enter your building in the sidebar (Building profile) or "
            "apply a preset under Quick start.")

st.markdown("### Building classification")
st.markdown(
    ui.classification_html(
        building.height_class,
        building.building_category,
        [(c, _branch_chip(report.chapter(c)), None)
         for c in ("MOE", "FE", "ES", "EL", "EVC", "FA", "FP", "SC", "LPG")
         if report.chapter(c) is not None],
    ),
    unsafe_allow_html=True,
)
# Owner answer 12.10.2026, Ch9 Q6; owner rulings 13.10.2026, P4 Q1 / Q5
_ahg_txt = f" **({building.occupancy_qualifier})**" if building.occupancy_qualifier else ""
st.caption(f"**Occupancy:** {OCCUPANCY_DEFS.get(occupancy) or _occ_label(occupancy)}{_ahg_txt}"
           f"  |  **Hazard class:** {building.hazard_class}"
           + (f"  |  rule code `{occupancy}`" if _SHOW_RULE_IDS else ""))

_ol = report.occupant_load
_fa = report.fire_access
_tot = report.count_status()


# Audit UX-23: what changed since the previous input (not since the previous rerun:
# a search or filter change keeps the comparison).
def _line_set(rep) -> frozenset:
    out = set()
    for prefix, chapters in (("", rep.chapters), ("P-", rep.attached_parking_chapters or [])):
        for ch in chapters:
            for blk in ch.blocks:
                for it in blk.items:
                    out.add((f"{prefix}{ch.chapter_code}", it.system, it.status))
    return frozenset(out)


_lines_now = _line_set(report)
_bjson = building.model_dump_json()
if st.session_state.get("_lines_now_json") != _bjson:
    st.session_state["_lines_before"] = st.session_state.get("_lines_now")
    st.session_state["_lines_now"] = _lines_now
    st.session_state["_lines_now_json"] = _bjson
_lines_before = st.session_state.get("_lines_before")
_req_before = (None if _lines_before is None
               else sum(1 for (c, _s, stt) in _lines_before
                        if stt == "required" and not c.startswith("P-")))


def _short_extent(ext: str) -> str:
    """Audit UX-25: a metric-sized fire access value; the full text is in the caption."""
    if not ext:
        return "-"
    m = _re.search(r"\b(\d+/\d+)\b", ext)
    if m:
        return m.group(1)
    if ext.lower().startswith("whole"):
        return "Whole"
    return " ".join(ext.split()[:2])


d1, d2, d3, d4 = st.columns(4)
with d1:
    st.metric("Height class", building.height_class.replace("_", " "))
    st.caption(f"Datum: {getattr(building, 'height_datum', 'grade').replace('_', ' ')}")
with d2:
    # Not evaluated (villa; no Table 3.13 row and no per-use areas): no exit count is
    # shown (owner ruling 12.10.2026, Ch3 Q2). See the OL note.
    _ol_ok = bool(_ol and _ol.evaluated and _ol.occupant_load)
    st.metric("Occupant load", f"{_ol.occupant_load:,}" if _ol_ok else "not evaluated")
    _basis = (f"governing storey '{_ol.governing_storey}'" if _ol and _ol.governing_storey
              else "whole-building" if _ol and _ol.storey_area_m2 == _ol.area_m2
              else "largest storey")
    st.caption((f"≥ {_ol.min_exits} exits (Table 3.14 on the {_basis}"
                f" OL {_ol.storey_occupant_load:,})") if _ol_ok else
               (_ol.exit_ref if _ol else ""))
with d3:
    _n_req = _tot.get("required", 0)
    st.metric("Required systems", _n_req,
              delta=(None if _req_before is None or _req_before == _n_req
                     else _n_req - _req_before),
              delta_color="off",
              help="Required lines of the main report; the change is against the previous "
                   "input.")
    st.caption(f"Conditional {_tot.get('conditional', 0)}")
with d4:
    st.metric("Fire access (perimeter)", _short_extent(_fa.extent if _fa else ""))
    st.caption(((_fa.extent + " · ") if _fa and _fa.extent else "") + (_fa.extent_ref if _fa else ""))
st.markdown(ui.status_summary_html(_tot), unsafe_allow_html=True)
# Audit UX-03: a missing input is its own status and the report says it is incomplete.
_ne_lines = list(dict.fromkeys(
    f"{ch.chapter_code}: {it.system}"
    for ch in list(report.chapters) + list(report.attached_parking_chapters or [])
    for blk in ch.blocks for it in blk.items if it.status == "not_evaluated"))
if _ne_lines:
    st.warning(f"**Report incomplete: {len(_ne_lines)} line(s) NOT EVALUATED.** An input is "
               "missing; a missing input is never taken as a pass. Enter it and the line is "
               "evaluated. The exports carry the same notice.\n\n"
               + "\n".join(f"- {x}" for x in _ne_lines))
if _ol and _ol.note:
    st.caption(f"OL: {_ol.note}")
for _w in (_ol.warnings if _ol else []):   # owner answer 12.10.2026, F6
    st.warning(f"Per-storey table: {_w}")
if report.mixed_occupancy_note:
    st.info(_humanize_codes(report.mixed_occupancy_note))

if _lines_before is not None and _lines_before != _lines_now:
    _added = sorted(_lines_now - _lines_before)
    _removed = sorted(_lines_before - _lines_now)
    with st.expander(f"What changed since the previous input: {len(_added)} line(s) added, "
                     f"{len(_removed)} removed", expanded=False):
        for _c, _sys, _stt in _added[:60]:
            st.markdown(f"➕ **{_c}** {_sys} ({_stt.replace('_', ' ')})")
        for _c, _sys, _stt in _removed[:60]:
            st.markdown(f"➖ **{_c}** {_sys} ({_stt.replace('_', ' ')})")
        if len(_added) > 60 or len(_removed) > 60:
            st.caption("First 60 of each shown.")


# ---------- Assumptions used in this report (audit UX-08, 28.10.2026) -----------
def _assumptions(b: Building, rep) -> list:
    """Every input the report rests on that the user did not set: the sample or preset
    profile, boxes pre-ticked on first load and never touched, choices left on their
    default, and the fallbacks the engine uses for a blank optional input. Each names
    where to change it."""
    ss = st.session_state
    touched = ss.get("_touched") or {}
    src = ss.get("_profile_source")
    out = []
    if _IS_SAMPLE:
        out.append("Sample building: the geometry is the first-load sample (sidebar: "
                   "Building profile > Geometry).")
    elif src and str(src).startswith("preset"):
        out.append(f"Values from the {src}: occupancy, geometry, parking and flags are "
                   "archetype values; check them against the drawings (sidebar: Quick "
                   "start).")
    if not src:
        pre = [k for k, v in FIRST_LOAD_DEFAULTS.items()
               if v is True and getattr(b, k, False) and not touched.get(k)]
        if pre:
            out.append("Ticked on first load and never changed: "
                       + ", ".join(field_label(k) for k in pre)
                       + " (sidebar: Spaces, equipment & gas; ES - Settings).")
    if rep.requires_wet_riser and not touched.get("wet_riser_radio"):
        out.append(f"Wet riser: {b.wet_riser_standpipes} standpipes (the first option; sidebar: "
                   "FP - Settings, Number of standpipes).")
    if b.occupancy == "motor_fuel_dispensing" and not touched.get("motor_fuel_group_radio"):
        out.append(f"Motor fuel dispensing Group {b.motor_fuel_group} (the first option; "
                   "sidebar: FP - Settings, Table 9.25).")
    if b.has_parking_area and not touched.get("attached_parking_kind_radio"):
        out.append(f"Parking type {b.attached_parking_kind} (the first option; sidebar: "
                   "Parking & special rooms).")
    if b.has_parking_area and b.parking_depth_m is None and (b.parking_basement_levels or 0) > 0:
        out.append("Parking depth not entered: the building's depth below grade is used "
                   "(sidebar: Parking & special rooms).")
    if b.is_aircraft_hanger and not touched.get("hangar_group_input"):
        out.append(f"Aircraft hangar Group {b.hangar_group} (the first option; sidebar: "
                   "Storage / industrial specialty).")
    if b.has_tunnel and not touched.get("tunnel_kind_radio"):
        out.append("Tunnel kind: road / rail (the first option; sidebar: FP - Settings).")
    if (b.occupancy == "parking_open" or b.villa_converted_use) and not touched.get("exit_stairs_input"):
        out.append(f"Number of exit stairs: {b.exit_stairs} (the default; sidebar: FP - Settings).")
    if b.occupancy == "storage_industrial":
        if b.storage_commodity == "none" and not touched.get("storage_commodity_input"):
            out.append("Stored commodity: general storage, Table 9.27 Groups A-J by hazard "
                       "class (sidebar: Storage / industrial specialty).")
        if not b.max_unit_area_m2:
            out.append("Largest unit compartment area not entered: the whole ground floor is "
                       "one unit (#4.1.14; sidebar: Storage / industrial specialty).")
        if not b.building_volume_m3:
            out.append("Building volume not entered: footprint x height is used for the Ch 2 "
                       "storage / industrial access rows (sidebar: FSA - Settings).")
    if b.is_aboveground_tank_storage and not (b.ast_storage_area_m2 and b.ast_tank_capacity_m3):
        out.append("Tank storage area or capacity not stated: Table 9.27 Group T row 2 applies "
                   "(sidebar: Storage / industrial specialty).")
    if (not b.storey_uses and not b.use_areas and not b.largest_storey_area_m2
            and b.floors_above_grade + b.floors_below_grade > 1):
        out.append("Largest storey area not entered: Table 3.14 runs on the whole GFA "
                   "(sidebar: MOE - Settings).")
    if (b.occupancy in HAZARD_NOT_CLASSIFIED
            and st.session_state.get("hazard_override_input", "auto") == "auto"):
        out.append(f"Hazard class {b.hazard_class} is the tool's working value: #1.1.13 does "
                   "not name this occupancy (sidebar: Override hazard class).")
    return out


_ASSUMPTIONS = _assumptions(building, report)
if _ASSUMPTIONS:
    with st.container(border=True):
        st.markdown(f"**Assumptions used in this report ({len(_ASSUMPTIONS)})** - inputs you "
                    "did not set yourself. Each is printed in the exports.")
        st.markdown("\n".join(f"- {a}" for a in _ASSUMPTIONS))

# ---------- Scenario A vs B compare ------------------------------------------
with st.expander("Compare scenario A vs B (height / occupancy)", expanded=False):
    st.caption("Quick what-if: keep current profile as A, edit B, compare required counts.")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("**Scenario A (current)**")
        st.write(f"Occupancy: {_occ_label(building.occupancy)}")
        st.write(f"Height: {building.height_m:g} m → **{building.height_class}**")
        st.write(f"Required systems: **{_tot.get('required', 0)}**")
        if _ol:
            st.write(f"OL: {_ol.occupant_load:,} → ≥ {_ol.min_exits} exits per storey"
                     if _ol.evaluated else "OL: not evaluated (no exit count)")
    with sc2:
        st.markdown("**Scenario B**")
        b_occ = st.selectbox("B occupancy", options=list(OCCUPANCY_DEFS.keys()),
                             index=list(OCCUPANCY_DEFS.keys()).index(building.occupancy)
                             if building.occupancy in OCCUPANCY_DEFS else 0,
                             key="scenario_b_occ", format_func=_occ_label,
                             help="Occupancy of scenario B (Ch 1 Table 1.1); every other input "
                                  "is copied from the current building (A).")
        b_h = st.number_input("B height (m)", min_value=0.0, value=float(building.height_m),
                              step=1.0, key="scenario_b_height",
                              help="Height of scenario B, measured as for A (Ch 1 #1.7.39-"
                                   "#1.7.42, p.44-45); it sets B's height class.")
        # Scenario B follows the main input's rule: a storage hazard class is chosen, never
        # assumed (CH9C-28; owner ruling 12.10.2026, Ch9 Q1 / Q9), and the plot GF BUA sum
        # is required.
        b_hz, b_sum = None, float(building.sum_gf_bua_m2)
        if b_occ == "storage_industrial":
            b_hz = st.selectbox(
                "B storage hazard class (required)", ["LH", "OH1", "OH2", "HH", "EH2"],
                index=None, key="scenario_b_storage_hazard",
                format_func=lambda x: "HH + Extra Hazard Group 2 (#1.1.13.5)" if x == "EH2" else x,
                placeholder="Select from the stored materials and activities",
                help="Table 9.27 groups follow the hazard class (#1.1.13, Tables 9.1 / 9.2); "
                     "never assumed (CH9C-28).")
            b_sum = st.number_input(
                "B sum of GF BUAs of all buildings on the plot (m2) (required)",
                min_value=0.0, value=b_sum, step=100.0, key="scenario_b_sum_gf_bua",
                help="#4.1.13 (p.695) sum of the GF BUAs on the plot, required for storage "
                     "(owner ruling 12.10.2026, Ch9 Q1).")
        elif b_occ in HAZARD_NOT_CLASSIFIED:
            st.caption(f"#1.1.13 does not name this occupancy: B uses the tool's working "
                       f"hazard class {default_hazard(b_occ)}, as the main input does without "
                       f"an override.")
        if b_occ in ("mercantile_a", "mercantile_b") and building.ground_floor_bua_m2 > 3600:
            st.caption("Ch 1 Table 1.1 row 11 (p.50): a group of mercantile occupancies under a "
                       "single roof or not separated, with a ground floor built up area of more "
                       "than 3600 m2, is a Mall: choose a Mall occupancy for B in that case.")
        # Owner rulings 13.10.2026, P4 Q1 / Q5: a group or type is chosen, never assumed;
        # B keeps A's choice when the occupancy is the same.
        b_grp, b_post = building.business_group, building.is_post_office
        b_mtype = building.mercantile_c_type
        b_kiosk = building.kiosk_in_sprinklered_area_or_mall
        if b_occ == "business" and building.occupancy != "business":
            b_grp = st.selectbox("B business group (required)", list(BUSINESS_GROUPS),
                                 index=None, key="scenario_b_business_group",
                                 format_func=lambda g: f"Group {g}",
                                 placeholder="Select the group (Table 1.1 row 2)",
                                 help="Ch 1 Table 1.1 row 2 (p.48); required, no default "
                                      "(owner ruling 13.10.2026, P4 Q1).")
            b_post = False
            st.caption("B post office is not asked: Group B is evaluated as an office (LH).")
        if b_occ == "mercantile_c" and building.occupancy != "mercantile_c":
            b_mtype = st.selectbox("B Mercantile Group C type (required)",
                                   list(MERCANTILE_C_TYPES), index=None,
                                   key="scenario_b_mercantile_c_type",
                                   format_func=lambda t: MERCANTILE_C_TYPES[t],
                                   placeholder="Select the type",
                                   help="Ch 1 Table 1.1 row 11 (p.50); required, no default "
                                        "(owner ruling 13.10.2026, P4 Q5).")
            b_kiosk = None
        _b_run = st.button("Run comparison", key="run_scenario_compare",
                           help="Evaluates B and compares its required count with A.")
        if _b_run and float(b_h) <= 0 and b_occ != "infrastructure":
            st.error("Scenario B height must be more than 0 m.")
        elif _b_run and b_occ == "business" and b_grp is None:
            st.error("Scenario B is NOT EVALUATED: select the B business group (owner ruling "
                     "13.10.2026, P4 Q1).")
        elif _b_run and b_occ == "mercantile_c" and b_mtype is None:
            st.error("Scenario B is NOT EVALUATED: select the B Mercantile Group C type (owner "
                     "ruling 13.10.2026, P4 Q5).")
        elif _b_run and b_occ == "storage_industrial" and b_hz is None:
            st.error("Scenario B is NOT EVALUATED: select the B storage hazard class. Table "
                     "9.27 groups depend on the stored materials and activities (#1.1.13, "
                     "Tables 9.1 and 9.2), so the tool does not assume one.")
        elif _b_run and b_occ == "storage_industrial" and float(b_sum) <= 0:
            st.error("Scenario B is NOT EVALUATED: enter the B sum of GF BUAs of all buildings "
                     "on the plot (#4.1.13; owner ruling 12.10.2026, Ch9 Q1).")
        elif _b_run:
            if b_occ == "storage_industrial":
                _b_upd = {"hazard_class": "HH" if b_hz == "EH2" else b_hz,
                          "is_extra_hazard_2": b_hz == "EH2", "sum_gf_bua_m2": float(b_sum)}
            else:
                _b_upd = {"hazard_class": default_hazard(
                    b_occ, building.animal_housing_group,
                    is_post_office=(b_occ == "business" and b_grp == "B" and b_post)),
                    "is_extra_hazard_2": False}
            # Owner rulings 13.10.2026, P4 Q1-Q5: group / type only where they apply; a
            # kiosk or truck is its own building (no other occupancies).
            _b_upd.update({
                "business_group": b_grp if b_occ == "business" else None,
                "is_post_office": bool(b_post) and b_occ == "business" and b_grp == "B",
                "mercantile_c_type": b_mtype if b_occ == "mercantile_c" else None,
                "kiosk_in_sprinklered_area_or_mall": b_kiosk if b_occ == "mercantile_c" else None,
            })
            if b_occ == "mercantile_c":
                _b_upd.update({"secondary_occupancies": [], "mixed_occupancy_mode": "none"})
            b_building = building.model_copy(update={
                "occupancy": b_occ,
                "height_m": float(b_h),
                **_b_upd,
            })
            b_report = evaluate(b_building)
            b_tot = b_report.count_status()
            st.success(
                f"B → **{b_building.height_class}** · Required **{b_tot.get('required', 0)}** "
                f"(Δ {b_tot.get('required', 0) - _tot.get('required', 0):+d} vs A)"
            )
            _bol = b_report.occupant_load
            if _bol:
                st.caption(
                    f"B OL: {_bol.occupant_load:,} → ≥ {_bol.min_exits} exits per storey"
                    if _bol.evaluated else "B OL: not evaluated (no exit count)"
                )



# ---------- Special-rooms / flags summary chip strip (Tier 3 UI #12) ---------
# Shows at a glance which yes/no inputs are ticked, with the same labels as the
# exports' inputs table (audit UX-14).
def _ticked_chips(building_obj: Building) -> str:
    ticked = [field_label(name) for name, f in type(building_obj).model_fields.items()
              if f.annotation is bool and getattr(building_obj, name, False) is True]
    if not ticked:
        return ""
    return " ".join(f"`{t}`" for t in ticked)


_chip_str = _ticked_chips(building)
if _chip_str:
    _n = _chip_str.count("`") // 2
    with st.expander(f"🔧 Inputs summary — {_n} flag(s) ticked",
                     expanded=False):
        st.markdown(_chip_str)

# ---------- Expanded soft-validation warnings (Tier 2 UI #9) -----------------

def _sanity_check_inputs(b: Building) -> tuple[list[str], list[str], list[str]]:
    """Look at the full Building model + session_state flags and return three lists:
    (prohibitions, warnings, info). None of them stops the report (the input stops do
    that); a prohibition is a printed code ban the inputs run into; warnings flag
    unusual combinations a designer should confirm; info is FYI traceability."""
    errs: list[str] = []
    warns: list[str] = []
    info: list[str] = []

    def gs(k):  # session-state shorthand
        return bool(st.session_state.get(k, False))

    # --- Printed prohibitions (advisory: the report is still printed) ---
    if gs("has_lpg_tank_roof_mounted") and b.height_m > 90:
        errs.append(
            "🚫 **LPG roof tank on super-highrise (>90 m) is PROHIBITED.** "
            "UAE Ch 11 #2.5.1.3 (p.900) bans roof LPG installations on buildings "
            "taller than 90 m. Either lower the building, change to a podium / "
            "ground tank, or uncheck the roof-mounted flag."
        )

    # --- Unusual / suspicious combinations ---
    if b.occupancy == "storage_industrial" and b.hazard_class == "LH":
        warns.append(
            "⚠ Storage / industrial occupancy is rarely LH (Light Hazard). "
            "Most warehouses are OH1/OH2/EH per the commodity (Table 9.27). "
            "Confirm hazard class is intentional."
        )

    if b.occupancy == "mall_covered" and not b.has_atrium:
        warns.append(
            "⚠ Covered mall selected without 'Atrium' ticked. Most covered malls "
            "have at least one atrium, which triggers additional Ch 9/10 atrium "
            "requirements. Confirm intentional."
        )

    if b.occupancy == "healthcare_a" and not (b.has_operation_theater
                                              or b.has_mri_scanning_room
                                              or b.has_anesthetizing_room):
        warns.append(
            "⚠ Inpatient hospital (Healthcare Group A) without Operation theatre / MRI / "
            "Anesthetizing room ticked. Confirm the project scope — most "
            "inpatient hospitals have at least one of these."
        )

    if b.height_m >= 23 and not b.has_evacuation_elevator:
        warns.append(
            "⚠ Highrise (23 m or more, ruling R1) without 'Evacuation elevator' ticked "
            "(ES - Settings). Civil Defence often expects at least one designated "
            "firefighter / evacuation lift on highrise. Confirm with the AHJ if absent."
        )

    if (b.occupancy.startswith("hotel_")
            and not b.has_commercial_kitchen
            and b.height_m > 15):
        info.append(
            "ℹ Hotel without 'Commercial kitchen with cooking hood' ticked. Most hotels have "
            "a kitchen (triggers Ch 9 wet chemical + Ch 8 fusible-link). "
            "Confirm intentional."
        )

    if (b.occupancy in ("assembly_a", "assembly_b", "assembly_c")
            and b.gross_floor_area_m2 > 2000
            and b.assembly_area_m2 == 0):
        info.append(
            "ℹ Assembly occupancy with GFA > 2,000 m² but no largest assembly-hall area "
            "entered. Ch 10 Table 10.27 items 9-13 "
            "triggers on the assembly-hall area; set the value in SC settings "
            "to ensure the right smoke-purge rule fires."
        )

    if (b.occupancy.startswith("residential")
            and b.floors_above_grade >= 4
            and not b.has_garbage_chute):
        info.append(
            "ℹ G+4 residential without 'Garbage room / chute' ticked. Most UAE "
            "residential buildings of this size have a chute (Ch 9 Table 9.29). "
            "Confirm intentional."
        )

    if b.has_lpg_tanks and b.height_m >= 23:
        info.append(
            "ℹ LPG tanks declared on a highrise. Per Ch 11 #2.5.1.2 (p.900) "
            "central tanks are preferred underground or above ground rather "
            "than on the roof; a roof tank is permitted on buildings up to "
            "90 m only (#2.5.1.3). Verify location."
        )

    if b.has_diesel_generator_room and not b.has_main_electrical_room:
        warns.append(
            "⚠ Diesel generator room ticked but 'Main electrical room' is not. "
            "Diesel gen rooms almost always accompany a main electrical room — "
            "verify the building has neither."
        )

    if b.has_high_ceiling and b.ceiling_height_m < 10:
        warns.append(
            "⚠ 'High ceiling' is ticked but the ceiling height is < 10 m. "
            "Ch 9 Table 9.29.A high-ceiling design starts at 10 m. Untick the "
            "flag or raise the height."
        )

    if b.depth_below_grade_m > 7 and b.floors_below_grade <= 2:
        info.append(
            "ℹ Depth > 7 m with ≤ 2 basements — Ch 10 Table 10.22 deep-"
            "underground SC still triggers via the depth threshold (intended)."
        )

    # NOTE: villa / petrol-station / animal-housing / daycare_c / etc. used
    # to get a "flags ticked that don't apply" warning here. That's been
    # replaced by the auto-clear at occupancy-change time (see
    # `_apply_incompatible_flag_reset`), which names the cleared flags and
    # restores them on return (audit UX-05).

    return errs, warns, info


# ---------- Sanity-check banner (Tier 2 UI #9) -------------------------------
# Audit UX-26: an input STOP is a red error; everything here is advisory and uses
# the warning / info style, collapsed so a repeated advisory does not push the report
# down.
_errs, _warns, _info = _sanity_check_inputs(building)
for e in _errs:
    st.warning(e + " (Advisory: the report below is still printed.)", icon="🚫")
if _warns:
    with st.expander(f"⚠ Sanity checks — {len(_warns)} warning(s)", expanded=False):
        for w in _warns:
            st.warning(w)
if _info:
    with st.expander(f"ℹ Sanity checks — {len(_info)} info note(s)", expanded=False):
        for i in _info:
            st.info(i)


_STATUS_BADGE = {
    "required":     ("🔴", "REQUIRED"),
    "recommended":  ("🔵", "RECOMMENDED"),
    "conditional":  ("🟡", "CONDITIONAL"),
    "not_required": ("⚪", "NOT REQUIRED"),
    "not_evaluated": ("🟣", "NOT EVALUATED"),   # audit UX-03
}

_STATUS_ORDER = ["required", "not_evaluated", "recommended", "conditional", "not_required"]


def _badge(s: str) -> tuple:
    """Badge of a status; a status added later (for example 'not_evaluated') shows with
    its own name instead of failing."""
    return _STATUS_BADGE.get(s, ("⚫", str(s).replace("_", " ").upper()))


def _filter_items(items, allowed_statuses: set, text_q: str):
    """Apply the global status + text filter to a list of Requirements."""
    text_q = (text_q or "").strip().lower()
    out = []
    for r in items:
        if allowed_statuses and r.status not in allowed_statuses:
            continue
        if text_q:
            hay = " ".join(filter(None, [r.system, r.spec, r.detail,
                                          r.code_ref])).lower()
            if text_q not in hay:
                continue
        out.append(r)
    return out


def _chapter_counts(ch):
    """Return {status -> count} totals across all blocks in a chapter, plus 'total'."""
    counts = {s: 0 for s in _STATUS_ORDER}
    for blk in ch.blocks:
        for it in blk.items:
            counts[it.status] = counts.get(it.status, 0) + 1
    counts["total"] = sum(v for k, v in counts.items() if k != "total")
    return counts


_RULE_LOOKUP = _cached_rule_lookup()


def render_block(title, items, allowed_statuses: set, text_q: str,
                 chapter_code: str = "", view: str = "Table"):
    items = _filter_items(items, allowed_statuses, text_q)
    if not items:
        return
    st.subheader(title)
    if view == "Table":
        # Audit UX-13: one wrapping table per block (fast, compact, prints well).
        st.markdown(ui.requirements_table_html(items, _SHOW_RULE_IDS), unsafe_allow_html=True)
        return
    for req in items:
        with st.container(border=True):
            st.markdown(ui.requirement_head(req.status, req.system),
                        unsafe_allow_html=True)
            if req.spec:
                st.markdown(f"**Spec:** {req.spec}")
            if req.detail:
                st.markdown(req.detail)
            cite = [p for p in (req.code_ref, req.page_ref) if p]
            if cite:
                st.caption("📖 " + " · ".join(cite))
            # "Why triggered?": the rule's conditions in words; the rule ID and its raw
            # YAML only with "Show rule IDs" (audit UX-14). The code-excerpt expander was
            # removed: no excerpt files are bundled, so it never appeared (audit UX-21).
            if req.source_rule:
                info = _RULE_LOOKUP.get(req.source_rule)
                with st.expander(
                    "🔍 Why triggered" + (f" — rule `{req.source_rule}`" if _SHOW_RULE_IDS else ""),
                    expanded=False,
                ):
                    if info and info["match"]:
                        _hm = _human_match(info["match"])
                        st.caption(f"Conditions: {_hm}" if _hm else "Conditions in the rule file.")
                        if _SHOW_RULE_IDS:
                            st.caption(f"Source: `rules/{info['file']}` · kind: `{info['kind']}`")
                            st.code(_format_match_yaml(info["match"]), language="yaml")
                    elif info:
                        st.caption("Applies to every building (no condition).")
                    else:
                        st.caption("(Match conditions not located in the rule files.)")


def _format_match_yaml(match: dict) -> str:
    """Pretty-print a match/when dict as a small YAML snippet."""
    return _yaml.safe_dump(match, sort_keys=False, default_flow_style=False).strip()


_OP_SUFFIX_LABEL = {
    "_gte": "≥", "_lte": "≤", "_gt": ">", "_lt": "<",
    "_is": "=", "_not": "≠ (not in)", "_in": "∈",
}


def _human_value(v) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        return f"{v:,}"
    if isinstance(v, (list, tuple)):
        return ", ".join(_human_value(x) for x in v)
    if isinstance(v, str) and v in OCCUPANCY_DEFS:
        return _occ_label(v)
    if isinstance(v, dict):
        return _human_match(v)
    return str(v).replace("_", " ")


def _human_match(match: dict) -> str:
    """Translate a YAML match/when dict into a plain-English fragment for the
    branch-rationale caption (audit UX-14: occupancy names and input labels, not
    codes). Example:
      {occupancy: hotel_a, height_m_gte: 23, height_m_lte: 90, plot_area_m2_lte: 3000}
      -> "Hotel Group A, 23 ≤ height ≤ 90 m, Plot area (m2) ≤ 3,000"
    """
    if not match:
        return ""
    parts: list[str] = []

    # Occupancy slot
    if "occupancy" in match:
        parts.append(_human_value(match["occupancy"]))
    elif "occupancy_in" in match:
        parts.append("any of: " + _human_value(match["occupancy_in"]))
    if "occupancy_not" in match:
        parts.append("not: " + _human_value(match["occupancy_not"]))
    if "occupancy_group_is" in match:
        parts.append(f"occupancy group = {match['occupancy_group_is']}")

    # Height tier
    h_gt = match.get("height_m_gt")
    h_gte = match.get("height_m_gte")
    h_lt = match.get("height_m_lt")
    h_lte = match.get("height_m_lte")
    h_lo = h_gt if h_gt is not None else h_gte
    h_hi = h_lt if h_lt is not None else h_lte
    if h_lo is not None and h_hi is not None:
        op_lo = "<" if h_gt is not None else "≤"
        op_hi = "<" if h_lt is not None else "≤"
        parts.append(f"{h_lo} {op_lo} height {op_hi} {h_hi} m")
    elif h_lo is not None:
        op = ">" if h_gt is not None else "≥"
        parts.append(f"height {op} {h_lo} m")
    elif h_hi is not None:
        op = "<" if h_lt is not None else "≤"
        parts.append(f"height {op} {h_hi} m")

    # Hazard class
    if "hazard_class" in match:
        parts.append(f"hazard class = {match['hazard_class']}")
    if "hazard_class_is" in match:
        parts.append(f"hazard class = {match['hazard_class_is']}")
    if "hazard_class_in" in match:
        parts.append("hazard class ∈ " + ", ".join(match["hazard_class_in"]))

    # Building category
    if "building_category_is" in match:
        parts.append(f"category = {match['building_category_is']}")

    # Anything else (areas, floors, flags) — labels from the inputs table
    skip_keys = {
        "occupancy", "occupancy_in", "occupancy_not", "occupancy_group_is",
        "height_m_gt", "height_m_gte", "height_m_lt", "height_m_lte",
        "hazard_class", "hazard_class_is", "hazard_class_in",
        "building_category_is",
    }
    for k, v in match.items():
        if k in skip_keys:
            continue
        if k in ("any_of", "all_of", "any", "all") and isinstance(v, list):
            subs = [_human_match(x) if isinstance(x, dict) else _human_value(x) for x in v]
            joiner = " or " if k.startswith("any") else " and "
            parts.append("(" + joiner.join(x for x in subs if x) + ")")
            continue
        if k == "flag":
            parts.append(f"{field_label(str(v))} ticked")
            continue
        for suf, label in _OP_SUFFIX_LABEL.items():
            if k.endswith(suf):
                field = k[: -len(suf)]
                parts.append(f"{field_label(field)} {label} {_human_value(v)}")
                break
        else:
            parts.append(f"{field_label(k)} = {_human_value(v)}")

    return ", ".join(parts)


# ---------- Status legend (Tier-1 UI #1) -------------------------------------
st.markdown(ui.legend_html(), unsafe_allow_html=True)

# ---------- Filter bar (Tier-1 UI #2; audit UX-13 / UX-14) --------------------
_present = {it.status for _p, chs in (("", report.chapters), ("P", report.attached_parking_chapters or []))
            for ch in chs for blk in ch.blocks for it in blk.items}
_status_opts = _STATUS_ORDER + sorted(_present - set(_STATUS_ORDER))
_filt_c1, _filt_c2 = st.columns([2, 3])
with _filt_c1:
    _allowed = st.multiselect(
        "Filter by status",
        options=_status_opts,
        # Audit UX-13: the design lines first; 'not required' (traceability) on request.
        default=[s for s in _status_opts if s != "not_required"],
        format_func=lambda s: f"{_badge(s)[0]} {_badge(s)[1]}",
        help="Narrow the report by status. Default = every status except 'not required' "
             "(exemptions kept for traceability: add them here).",
        key="filter_status",
    )
with _filt_c2:
    _text_q = st.text_input(
        "Search requirements",
        value="",
        placeholder="e.g. 'Sprinkler', 'Pa', 'Civil Defence', 'Section 4.6' …",
        help="Case-insensitive substring match against system name, spec, detail, and code-ref.",
        key="filter_text",
    )
_view_c1, _view_c2, _view_c3 = st.columns([2, 2, 2])
with _view_c1:
    _view = st.radio("Report view", ["Table", "Cards"], horizontal=True, key="report_view",
                     help="Table: one compact row per requirement (fast, prints well). Cards: "
                          "one card per requirement with 'Why triggered'.")
with _view_c2:
    _req_only = st.toggle("Required only", key="filter_required_only",
                          help="Shows only the required lines, whatever the status filter says.")
with _view_c3:
    st.toggle("Show rule IDs", key="show_rule_ids",
              help="Adds the tool's internal rule IDs (and the raw rule conditions in the "
                   "cards) for checking the rule files. Off: readable table / row labels only.")
_allowed_set = {"required"} if _req_only else set(_allowed)

if PRINT_MODE:
    # Single full-width column for print; create a dummy right column we just
    # don't render into.
    col_left = st.container()
    col_right = st.container()
else:
    col_left, col_right = st.columns([2, 1])


def _chapter_caption(ch, parking: bool = False) -> None:
    if not ch.selected_branch:
        return
    _human = _human_match((_RULE_LOOKUP.get(ch.selected_branch) or {}).get("match", {}))
    st.caption(
        ("Governing parking table / row: " if parking else "Governing table / row: ")
        + branch_label(ch)
        + (f" · rule `{ch.selected_branch}`" if _SHOW_RULE_IDS else "")
        + (f"\n\n**Why this row:** {_human}" if _human else "")
    )


with col_left:
    _shown_any = False
    for ch in report.chapters:
        # Skip the entire chapter heading if no items pass the filter — keeps
        # the report tight when the user is searching for a specific term.
        if not any(_filter_items(blk.items, _allowed_set, _text_q)
                   for blk in ch.blocks):
            continue
        _shown_any = True
        st.markdown(
            ui.chapter_header(
                ch.chapter_code, ch.chapter_title,
                arabic=CHAPTER_AR.get(ch.chapter_code) if bilingual_headings else None,
                anchor=f"ch-{ch.chapter_code.lower()}",
            ),
            unsafe_allow_html=True,
        )
        _chapter_caption(ch)
        _figs = [fig for fig in figures_for(ch.chapter_code) if fig["path"].exists()]
        if _figs:
            with st.expander(
                f"UAE FLSC figure — {_figs[0]['figure']}"
                + (f" + {len(_figs)-1} more" if len(_figs) > 1 else ""),
                expanded=False,
            ):
                for fig in _figs:
                    st.image(str(fig["path"]), caption=figure_caption(fig), width="stretch")
        for block in ch.blocks:
            render_block(block.title, block.items, _allowed_set, _text_q,
                         chapter_code=ch.chapter_code, view=_view)

    # ---------- Attached parking sub-occupancy section ----------
    if report.attached_parking_chapters:
        _park_shown = [ch for ch in report.attached_parking_chapters
                       if any(_filter_items(blk.items, _allowed_set, _text_q) for blk in ch.blocks)]
        if _park_shown:
            _shown_any = True
            st.markdown("---")
            kind = report.building.attached_parking_kind
            synth_occ = "parking_open" if kind == "open" else "parking_enclosed"
            st.markdown(
                ui.chapter_header(
                    "🅿", "Attached Parking Area",
                    arabic="منطقة مواقف السيارات الملحقة" if bilingual_headings else None,
                    anchor="attached-parking", parking=True,
                ),
                unsafe_allow_html=True,
            )
            st.caption(f"Sub-occupancy evaluation as {_occ_label(synth_occ)} (driven by "
                       "**Building has parking** under Parking & special rooms). All "
                       "parking-specific requirements from MOE / FE / ES / EL / FA / FP / SC "
                       "are surfaced here.")
            for ch in _park_shown:
                st.markdown(
                    ui.chapter_header(
                        f"P-{ch.chapter_code}", ch.chapter_title,
                        arabic=CHAPTER_AR.get(ch.chapter_code) if bilingual_headings else None,
                        parking=True,
                    ),
                    unsafe_allow_html=True,
                )
                _chapter_caption(ch, parking=True)
                for block in ch.blocks:
                    render_block(block.title, block.items, _allowed_set, _text_q,
                                 chapter_code=ch.chapter_code, view=_view)
            st.markdown("---")

    # Audit UX-22: a search or filter with no match says so.
    if not _shown_any:
        st.info(f"No requirements match"
                + (f" '{_text_q.strip()}'" if (_text_q or "").strip() else "")
                + " with the status filter "
                + (", ".join(_badge(s)[1].lower() for s in sorted(_allowed_set)) or "(none)")
                + ". Clear the search box or add statuses to the filter.")

    if report.high_ceiling and report.high_ceiling.applies:
        hc = report.high_ceiling
        st.markdown("<a name='high-ceiling'></a>", unsafe_allow_html=True)
        st.subheader("FP - High Ceiling Sprinkler Design (Table 9.29.A)")
        with st.container(border=True):
            if hc.height_range:
                st.table({
                    "Ceiling height": f"{hc.ceiling_height_m} m",
                    "Hazard class": hc.hazard_class,
                    "Height band": hc.height_range,
                    "K-factor": hc.k_factor or "-",
                    "Min pressure": hc.min_pressure or "-",
                    "Min sprinklers": str(hc.min_sprinklers or "-"),
                    "Density": hc.density or "-",
                    "Design area": hc.design_area or "-",
                    "Pump (no hydrant)": f"{hc.pump_without_hydrant_gpm} gpm" if hc.pump_without_hydrant_gpm else "-",
                    "Pump (with hydrant)": f"{hc.pump_with_hydrant_gpm} gpm" if hc.pump_with_hydrant_gpm else "-",
                })
            if hc.note:
                st.caption(hc.note)


# ---------- Exports (audit UX-07 / UX-11 / UX-12, 28.10.2026) -----------------
@st.cache_resource(show_spinner=False)
def _export_store() -> dict:
    """Built export files, kept across reruns and sessions (bytes keyed on the inputs,
    the kind and the notes), so a second click does not rebuild them."""
    return {}


_EXPORT_META = {
    "notes": (st.session_state.get("project_notes_input") or "").strip(),
    "revision": tool_revision(),
    "inputs": inputs_rows(building, report.requires_wet_riser),
    "assumptions": list(_ASSUMPTIONS),
}
_EXPORT_META_KEY = _json.dumps(_EXPORT_META, sort_keys=True, default=str)


def _export_data(fmt: str, kind: str | None):
    """A callable for st.download_button: the file is built only when the button is
    clicked (no export cost on every rerun), then kept in the store."""
    store = _export_store()
    key = (_bjson, fmt, kind, _EXPORT_META_KEY)
    rep, meta = report, dict(_EXPORT_META)

    def _build() -> bytes:
        if key not in store:
            meta["generated"] = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
            if fmt == "pdf":
                data = _call_export(report_to_pdf_bytes, rep, kind, meta)
            elif fmt == "docx":
                data = _call_export(report_to_docx_bytes, rep, kind, meta)
            else:
                data = _call_export(report_to_xlsx_bytes, rep, None, meta)
            while len(store) >= 8:
                store.pop(next(iter(store)))
            store[key] = data
        return store[key]
    return _build


with col_right:
  if not PRINT_MODE:
    # Audit UX-18: the target of the "Contents and exports" link at the top.
    st.markdown("<a name='exports' id='exports'></a>", unsafe_allow_html=True)
    # ----- Table of contents with per-chapter status counts (Tier-1 UI #3) -----
    _toc_rows = []
    for ch in report.chapters:
        _short = ch.chapter_title.split("(")[0].strip()
        _toc_rows.append((f"ch-{ch.chapter_code.lower()}", ch.chapter_code,
                          _short, _chapter_counts(ch)))
    if report.attached_parking_chapters:
        ap_counts = {}
        for c in report.attached_parking_chapters:
            for s, n in _chapter_counts(c).items():
                if s != "total":
                    ap_counts[s] = ap_counts.get(s, 0) + n
        _toc_rows.append(("attached-parking", "🅿", "Attached parking", ap_counts))
    if report.high_ceiling and report.high_ceiling.applies:
        _toc_rows.append(("high-ceiling", "FP", "High-ceiling design", None))
    st.markdown(ui.toc_html(_toc_rows), unsafe_allow_html=True)
    st.caption("Click a chapter to jump. Counts ignore the filter bar. To print this "
               "report, turn on 'Print layout' at the top.")

    st.markdown("---")
    with st.expander("📋 Copy report (Markdown)", expanded=False):
        md_base = report_to_markdown(report)
        # Prepend project notes if any
        _notes = (st.session_state.get("project_notes_input") or "").strip()
        md = (f"## Project notes\n\n{_notes}\n\n---\n\n" + md_base) if _notes else md_base
        st.code(md, language="markdown")
    _proj = project_name or "building"

    st.caption("Files are built when you click (a few seconds for the Detailed PDF).")
    w1, w2 = st.columns(2)
    with w1:
        st.download_button(
            "Compact Word",
            data=_export_data("docx", "compact"),
            file_name=export_file_name(_proj, "compact", "docx"),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch", on_click="ignore", key="dl_compact_docx",
            help="Required system headers, the inputs used and the assumptions",
        )
    with w2:
        st.download_button(
            "Detailed Word",
            data=_export_data("docx", "detailed"),
            file_name=export_file_name(_proj, "detailed", "docx"),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            width="stretch", on_click="ignore", key="dl_detailed_docx",
            help="Full evaluation with status column, inputs used and code figures",
        )
    pdf_c1, pdf_c2 = st.columns(2)
    with pdf_c1:
        st.download_button(
            "Compact PDF",
            data=_export_data("pdf", "compact"),
            file_name=export_file_name(_proj, "compact", "pdf"),
            mime="application/pdf",
            width="stretch", on_click="ignore", key="dl_compact_pdf",
            help="Required system headers, the inputs used and the assumptions",
        )
    with pdf_c2:
        st.download_button(
            "Detailed PDF",
            data=_export_data("pdf", "detailed"),
            file_name=export_file_name(_proj, "detailed", "pdf"),
            mime="application/pdf",
            width="stretch", on_click="ignore", key="dl_detailed_pdf",
            help="Full evaluation with status column, inputs used and code figures",
        )
    st.download_button(
        "Executive summary PDF",
        data=_export_data("pdf", "executive"),
        file_name=export_file_name(_proj, "executive", "pdf"),
        mime="application/pdf",
        width="stretch", on_click="ignore", key="dl_executive_pdf",
        help="Profile, OL and one governing requirement per chapter",
    )
    st.download_button(
        "Excel system schedule (.xlsx)",
        data=_export_data("xlsx", None),
        file_name=export_file_name(_proj, "systems", "xlsx"),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch", on_click="ignore", key="dl_xlsx",
        help="Profile, inputs used, every requirement and the CD checklist",
    )
    st.caption("Downloads go to your browser’s download folder. Every export carries the "
               f"date and the tool revision ({tool_revision()}).")
    # Audit UX-19: the inputs live only in this browser tab.
    st.caption("Your inputs live only in this browser tab: a refresh or a new tab starts "
               "again from the sample. Save the project to keep them.")
    st.download_button(
        "💾 Save project (.flsc)",
        data=_scenario_json,
        file_name=f"{_safe_stem}.flsc",
        mime="application/octet-stream",
        width="stretch", on_click="ignore", key="save_project_main",
        help="The same file as Save / Load in the sidebar: every input of this session.",
    )
    with st.expander("CD drawing submission checklist (Annexure 2)", expanded=False):
        for pkg, note, req in build_submission_checklist(report):
            st.markdown(f"{'☑' if req else '☐'} **{pkg}** — {note}")

# ---------- Disclaimer footer (Tier-1 UI #4) ---------------------------------
st.markdown(ui.footer_html(DISCLAIMER), unsafe_allow_html=True)
