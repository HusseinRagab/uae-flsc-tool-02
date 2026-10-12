"""UAE FLSC 2018 Table 3.13 occupant-load factors and Table 3.14 exit counts.

Ch 3 #4.1.2 (p.283): the occupant load is "not less than" floor area / factor of
"the floor area assigned to that use", so each use's quotient is rounded UP and
the uses are added. #4.3.1 (p.288) and #4.1.3 (p.283): Table 3.14 is applied per
storey.

Owner rulings 12.10.2026 (Ch 3 Q1-Q3):
  - Q1: Table 3.14 runs on the occupant load of the largest storey, from the new
    "Largest storey area" input. Blank: the whole GFA (the master behaviour), and
    the line says so.
  - Q2: per-use areas (Table 3.13 row, area). OL = sum of the rounded-up loads.
    Blank: the DENSEST Table 3.13 row of the occupancy. Occupancies with no Table
    3.13 row (fuel station, infrastructure, mixed, underground) are not evaluated
    until per-use areas are entered: no exit count is stated.
  - Q3: mall factor from the gross leasable area (Table 3.13 row 14, p.287):
    less than 14,000 m2 -> 2.8 m2; from 14,000 m2, 3.3 m2 plus 0.1 m2 for each FULL
    1,290 m2 above 14,000 m2, maximum 5.1 m2. Blank GLA: the GFA, labelled.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from flsc_schema import Building, OccupantLoadSummary

# Table 3.13 rows that carry an area factor (m2 per person), read off p.285-287.
# Rows with no area factor are left out: 1.iii bench seating (455 mm linear), 1.iv
# and 1.xxii fixed / theater seating (number of seats), 8 and 9 villas ("None"),
# 18.ii special purpose industrial ("NA"). Row 4.vi "Both sides of Smoke
# Compartment 2.8 m2, net" is the refuge-area capacity across a smoke barrier,
# not a use of floor area, so it is not offered as a use (owner question).
# Where the page prints "i." twice in one group, the second is listed as "ii".
MALL_ROW = "14"
TABLE_3_13_ROWS: Dict[str, Tuple[str, float]] = {
    "1.i": ("Assembly: concentrated (ballroom, dance floor) - net", 0.65),
    "1.i prayer": ("Assembly: prayer rooms - net", 0.9),
    "1.ii": ("Assembly: less concentrated, outdoors (meeting rooms, restaurant) - net", 1.4),
    "1.v": ("Assembly: waiting spaces in theaters, similar spaces", 0.28),
    "1.vi": ("Assembly: kitchens", 9.3),
    "1.vii": ("Assembly: library stacks area", 9.3),
    "1.viii": ("Assembly: library reading rooms - net", 4.6),
    "1.ix": ("Assembly: swimming pool (water surface)", 4.6),
    "1.x": ("Assembly: swimming pool decks", 2.8),
    "1.xi": ("Assembly: exercise room with equipment", 4.6),
    "1.xii": ("Assembly: exercise room without equipment", 1.4),
    "1.xiii": ("Assembly: stages - net", 1.4),
    "1.xiv": ("Assembly: lighting and access catwalks - net", 9.3),
    "1.xv": ("Assembly: casinos and gaming areas", 1.0),
    "1.xvi": ("Assembly: skating rinks", 4.6),
    "1.xvii": ("Assembly: food court seating areas", 1.4),
    "1.xviii": ("Assembly: airport concourse", 9.3),
    "1.xix": ("Assembly: airport waiting areas", 1.4),
    "1.xx": ("Assembly: airport baggage claim", 1.9),
    "1.xxi": ("Assembly: airport baggage handling", 27.9),
    "1.xxiii": ("Assembly: museum", 5.0),
    "2.i": ("Business: regular office areas", 9.3),
    "2.ii": ("Business: concentrated office areas", 4.6),
    "2.iii": ("Business: air traffic control observation levels", 3.7),
    "3.i": ("Educational: classroom - net", 1.9),
    "3.ii": ("Educational: shops, laboratories, vocational - net", 4.6),
    "4.i": ("Healthcare A,B: inpatient treatment departments", 22.3),
    "4.ii": ("Healthcare A,B: sleeping departments", 11.1),
    "4.iii": ("Healthcare A,B: consultation departments", 9.3),
    "4.iv": ("Healthcare A,B: clinics", 9.3),
    "4.v": ("Healthcare A,B: limited care", 9.3),
    "5.i": ("Healthcare C: ambulatory health care", 13.0),
    "6.i": ("Residential A: apartments", 18.6),
    "7.i": ("Residential B,C: staff accommodation, hostels", 18.6),
    "7.ii": ("Residential B,C: labor accommodation", 18.6),
    "10": ("Detention A,B,C", 11.1),
    "11.i": ("Hotel: hotel apartments", 18.6),
    "11.ii": ("Hotel: hotel guest rooms", 18.6),
    "12": ("Day care A,B - net", 3.3),
    "13.i": ("Mercantile: sales area on floor below street floor", 2.8),
    "13.ii": ("Mercantile: sales area on street floor", 2.8),
    "13.iii": ("Mercantile: sales area on floors above street floor", 5.6),
    "13.iv": ("Mercantile: sales area on two or more street floors", 3.7),
    "13.v": ("Mercantile: floors used only for offices", 9.3),
    "13.vi": ("Mercantile: floors used for goods and not public", 27.9),
    MALL_ROW: ("Mall A,B: factor from the mall gross leasable area", 0.0),
    "15.i": ("Storage A: high hazard storage", 27.9),
    "16.i": ("Storage B,C: low and ordinary hazard storage", 27.9),
    "17.i": ("Industrial A: high hazard content", 9.3),
    "18.i": ("Industrial B,C: general, low hazard", 9.3),
    "19.i": ("Parking A,B: enclosed parkings", 27.9),
    "19.ii": ("Parking A,B: open parkings", 27.9),
    "20.i": ("Parking C: mechanical / robotic parkings", 46.5),
    "21": ("Animal housing A,B,C", 11.1),
}

# Table 3.13 rows of each occupancy (p.285-287). With no per-use areas the
# DENSEST of them is used (owner ruling 12.10.2026, Ch3 Q2).
_ASSEMBLY = [k for k in TABLE_3_13_ROWS if k.startswith("1.")]
_ROWS_BY_OCCUPANCY: Dict[str, List[str]] = {
    **{o: _ASSEMBLY for o in ("assembly_a", "assembly_b", "assembly_c")},
    "business": ["2.i", "2.ii", "2.iii"],
    **{o: ["3.i", "3.ii"] for o in ("education_a", "education_b", "education_c")},
    **{o: ["4.i", "4.ii", "4.iii", "4.iv", "4.v"] for o in ("healthcare_a", "healthcare_b")},
    "healthcare_c": ["5.i"],
    "residential": ["6.i"],
    "staff_accommodation": ["7.i"], "hostel": ["7.i"], "labour_accommodation": ["7.ii"],
    **{o: ["10"] for o in ("detention_a", "detention_b", "detention_c")},
    **{o: ["11.i", "11.ii"] for o in ("hotel_a", "hotel_b", "hotel_c")},
    **{o: ["12"] for o in ("daycare_a", "daycare_b", "daycare_c")},
    **{o: ["13.i", "13.ii", "13.iii", "13.iv", "13.v", "13.vi"]
       for o in ("mercantile_a", "mercantile_b")},
    "parking_enclosed": ["19.i"], "parking_open": ["19.ii"],
    "animal_housing": ["21"],
}
# Storage / industrial: Groups A (rows 15, 17) are high hazard; B,C (rows 16, 18) are not.
_STORAGE_ROWS = {True: ["15.i", "17.i"], False: ["16.i", "18.i"]}

# Table 3.13 has rows 1 to 21 only (p.285-287): none for these (CH3-03).
_NOT_IN_TABLE_3_13 = {
    "motor_fuel_dispensing": "motor fuel dispensing",
    "infrastructure": "infrastructure",
    "mixed_multiple": "mixed / multiple occupancy",
    "high_depth_underground": "high-depth underground",
    "low_depth_underground": "low-depth underground",
}

_MALLS = ("mall_covered", "mall_open", "mall_mixed")
_Q1 = "owner ruling 12.10.2026, Ch3 Q1"
_Q2 = "owner ruling 12.10.2026, Ch3 Q2"
_Q3 = "owner ruling 12.10.2026, Ch3 Q3"


def min_exits_for_ol(occupant_load: int, outdoor: bool = False) -> Tuple[int, str]:
    """Table 3.14 (p.288) required number of means of egress."""
    if outdoor:
        if occupant_load > 9000:
            return 4, "Table 3.14 row vii outdoor OL more than 9,000 -> not less than 4 exits"
        if occupant_load > 6000:
            return 3, "Table 3.14 row vi outdoor OL more than 6,000 -> not less than 3 exits"
    if occupant_load > 1000:
        return 4, "Table 3.14 row iv OL more than 1,000 -> not less than 4 exits"
    if occupant_load >= 500:
        return 3, "Table 3.14 row iii OL 500 - 1,000 -> not less than 3 exits"
    return 2, "Table 3.14 rows i-ii OL less than 500 -> minimum 2 means of egress"


def mall_factor(gla_m2: float) -> Tuple[float, str]:
    """Table 3.13 row 14 (p.287), owner ruling 12.10.2026, Ch3 Q3: 0.1 m2 is added
    for each FULL 1,290 m2 above 14,000 m2."""
    if gla_m2 < 14000:
        return 2.8, "Table 3.13 row 14.i mall GLA less than 14,000 m2 -> 2.8 m2"
    steps = int((gla_m2 - 14000) // 1290)
    f = round(min(3.3 + 0.1 * steps, 5.1), 1)
    cap = " (maximum 5.1 m2)" if f >= 5.1 else ""
    return f, (f"Table 3.13 row 14.ii/iii mall GLA {gla_m2:,.0f} m2: 3.3 m2 + 0.1 m2 x "
               f"{steps} full 1,290 m2 increments above 14,000 m2 = {f:.1f} m2{cap}")


def _ol(area: float, factor: float) -> int:
    """#4.1.2 (p.283): not less than area / factor -> round up."""
    return int(math.ceil(round(area / factor, 9))) if area > 0 and factor > 0 else 0


def _gla(b: Building) -> Tuple[float, str]:
    if b.mall_gla_m2 > 0:
        return float(b.mall_gla_m2), "GLA entered"
    return float(b.gross_floor_area_m2 or 0), "GLA not entered: GFA used as the GLA"


def _row_factor(b: Building, row: str) -> Tuple[float, str]:
    label, f = TABLE_3_13_ROWS[row]
    if row == MALL_ROW:
        gla, basis = _gla(b)
        f, ref = mall_factor(gla)
        return f, f"{ref} ({basis}; {_Q3})"
    return f, f"Table 3.13 row {row} {label.split(': ', 1)[-1]} {f:g} m2"


def _not_evaluated(area: float, factor_ref: str, why: str, exit_ref: str) -> OccupantLoadSummary:
    """No exit count is stated: min_exits 0 (never a 2-exit minimum as if it were
    the answer, owner ruling 12.10.2026, Ch3 Q2)."""
    return OccupantLoadSummary(
        area_m2=area, factor_m2_per_person=0.0, factor_ref=factor_ref,
        occupant_load=0, min_exits=0, evaluated=False, exit_ref=exit_ref, note=why)


def _whole_area(b: Building) -> Tuple[float, str]:
    if b.gross_floor_area_m2 and b.gross_floor_area_m2 > 0:
        return float(b.gross_floor_area_m2), "GFA"
    if b.ground_floor_bua_m2 and b.ground_floor_bua_m2 > 0:
        return float(b.ground_floor_bua_m2), "ground-floor BUA (no GFA entered)"
    return 0.0, ""


def _storey_note(b: Building, whole: float, whole_basis: str,
                 on_what: str) -> Tuple[Optional[float], str]:
    """(largest storey area or None, text). None = not entered."""
    ls = float(b.largest_storey_area_m2 or 0)
    if ls <= 0:
        single = b.floors_above_grade == 1 and b.floors_below_grade == 0
        if single:
            return None, f"single storey: Table 3.14 runs on {on_what}"
        return None, (f"largest storey area not entered: Table 3.14 runs on {on_what} "
                      f"({_Q1}); enter the largest storey area for the per-storey count "
                      "(#4.3.1)")
    text = f"largest storey area {ls:,.0f} m2 entered ({_Q1})"
    if whole > 0 and ls > whole:
        text += f"; it exceeds the {whole_basis} of {whole:,.0f} m2: check the inputs"
    return ls, text


def _from_use_areas(b: Building) -> OccupantLoadSummary:
    unknown = [u.row for u in b.use_areas if u.row not in TABLE_3_13_ROWS]
    if unknown:
        return _not_evaluated(
            b.use_area_total_m2, "Per-use areas", (
                f"Not evaluated: per-use area row(s) {', '.join(map(repr, unknown))} are not "
                "Table 3.13 rows the tool lists. Correct the per-use areas."),
            "Table 3.14 not evaluated: a per-use area names an unknown Table 3.13 row")
    parts, total, densest, densest_ref = [], 0, None, ""
    for u in b.use_areas:
        if u.area_m2 <= 0:
            continue
        f, ref = _row_factor(b, u.row)
        n = _ol(u.area_m2, f)
        total += n
        parts.append(f"row {u.row}: {u.area_m2:,.0f} m2 / {f:g} m2 = {n:,}")
        if densest is None or f < densest:
            densest, densest_ref = f, ref
    whole = b.use_area_total_m2
    ls, storey_text = _storey_note(b, whole, "sum of the per-use areas",
                                   "the whole-building OL (sum of the per-use loads)")
    if ls is None:
        storey_ol, storey_area = total, whole
        basis = storey_text
    else:
        # The largest storey's OL cannot exceed that storey at the densest entered
        # factor, nor the building total: the smaller of the two is an upper bound.
        storey_area = ls
        storey_ol = min(total, _ol(ls, densest))
        basis = (f"{storey_text}; storey OL taken as {ls:,.0f} m2 at the densest entered "
                 f"factor {densest:g} m2, not more than the total ({storey_ol:,})")
    exits, ref = min_exits_for_ol(storey_ol)
    note = (f"OL by actual use (#1.4.5, #4.1.2, {_Q2}): " + "; ".join(parts) +
            f" -> total {total:,} (each use rounded up). Table 3.14: {basis}.")
    return OccupantLoadSummary(
        area_m2=whole, factor_m2_per_person=densest or 0.0,
        factor_ref=f"Per-use areas (densest entered: {densest_ref})",
        occupant_load=total, min_exits=exits,
        exit_ref=f"{ref} (storey OL {storey_ol:,}; per storey, #4.3.1)",
        note=note, storey_area_m2=storey_area, storey_occupant_load=storey_ol)


def _occupancy_factor(b: Building) -> Tuple[float, str]:
    occ = b.occupancy
    if occ in _MALLS:
        gla, basis = _gla(b)
        f, ref = mall_factor(gla)
        return f, f"{ref} ({basis}; {_Q3})"
    rows = (_STORAGE_ROWS[b.hazard_class == "HH"] if occ == "storage_industrial"
            else _ROWS_BY_OCCUPANCY.get(occ, []))
    if not rows:
        return 0.0, "Not in Table 3.13"
    row = min(rows, key=lambda r: TABLE_3_13_ROWS[r][1])
    f, ref = _row_factor(b, row)
    if len(rows) > 1:
        ref += (f" (densest Table 3.13 row of this occupancy, {_Q2}: per-use areas give the "
                "exact load)")
    return f, ref


def compute_occupant_load(b: Building) -> OccupantLoadSummary:
    occ = b.occupancy

    if occ.startswith("villa_"):
        return _not_evaluated(
            float(b.gross_floor_area_m2 or 0), "Table 3.13 rows 8 / 9: 'None'", (
                "Not evaluated: Table 3.13 rows 8 and 9 print 'None' for villas; villa egress "
                "is set by Tables 3.27 / 3.28 (see the Means of Egress items). Table 3.14 "
                "does not apply to villas."),
            "Table 3.14 not applied to villas (Tables 3.27 / 3.28)")

    if b.use_area_total_m2 > 0:
        return _from_use_areas(b)

    if occ in _NOT_IN_TABLE_3_13:
        return _not_evaluated(_whole_area(b)[0], "Not in Table 3.13", (
            f"Not evaluated: Table 3.13 (p.285-287) has no row for "
            f"{_NOT_IN_TABLE_3_13[occ]}. Means of egress (occupant load, Table 3.14 exits, "
            "Table 3.16 limits) is not evaluated until the floor area of each actual use is "
            f"entered ({_Q2}). #1.4.5 (p.242): divide the floor area assigned to each actual "
            "use by that use's Table 3.13 factor and add the results; then apply Table 3.14 "
            "per storey."),
            "MOE not evaluated: enter the per-use areas (no exit count stated)")

    factor, factor_ref = _occupancy_factor(b)
    if factor <= 0:
        return _not_evaluated(0.0, factor_ref, "Not evaluated: no occupant-load factor for "
                              "this occupancy.", "Table 3.14 not evaluated")
    whole, whole_basis = _whole_area(b)
    if whole <= 0:
        return _not_evaluated(0.0, factor_ref, "Not evaluated: no GFA or ground-floor BUA "
                              "entered.", "Table 3.14 not evaluated (no area)")

    total = _ol(whole, factor)
    ls, storey_text = _storey_note(b, whole, whole_basis, f"the whole {whole_basis}")
    storey_area = ls if ls is not None else whole
    storey_ol = _ol(storey_area, factor)
    exits, ref = min_exits_for_ol(storey_ol)
    if ls is None:
        why = storey_text.split(":", 1)[0]
        exit_ref = f"{ref} (OL {storey_ol:,} on the whole {whole_basis}: {why}; {_Q1})"
    else:
        exit_ref = (f"{ref} (largest storey OL {storey_ol:,} = {ls:,.0f} m2 / {factor:g} m2; "
                    f"per storey, #4.3.1, {_Q1})")
    notes = [f"Total OL = {whole:,.0f} m2 ({whole_basis}) / {factor:g} m2 per person = "
             f"{total:,} (rounded up: #4.1.2 'not less than'). Factor: {factor_ref}.",
             f"Table 3.14: {storey_text}."]
    if ls is not None:
        notes.append("The total OL is not used for Table 3.14 (#4.1.3).")
    notes.append("Gross area used; Table 3.13 'net' factors apply to the net area of that use.")
    return OccupantLoadSummary(
        area_m2=whole,
        factor_m2_per_person=factor,
        factor_ref=factor_ref,
        occupant_load=total,
        min_exits=exits,
        exit_ref=exit_ref,
        note=" ".join(notes),
        storey_area_m2=storey_area,
        storey_occupant_load=storey_ol,
    )
