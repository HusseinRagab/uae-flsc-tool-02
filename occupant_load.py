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

Owner answer 12.10.2026, F6 (phase 3): an optional per-storey table (storey, Table
3.13 row, area). When it has lines it governs: each storey's OL is the sum of its
uses, each rounded up (#4.1.2); Table 3.14 runs on each storey (#4.3.1, #4.1.3) and
the storey with the highest OL is named as governing. A line with no row takes the
densest Table 3.13 row of the occupancy (Ch3 Q2). A line or storey the table cannot
value (no storey name, unknown row, no row for an occupancy with no Table 3.13 row,
a storey with no area) is refused by name and no exit count is stated.

Owner ruling 12.10.2026, P3 Storey Q1: each storey carries an "identical storeys"
count. A storey counts that many times in the building total OL; the governing storey
is still the one with the highest OL. The counts must add up to the floors above grade
plus the basements: otherwise no exit count is stated (NOT EVALUATED, the gap named).
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from flsc_schema import Building, OccupantLoadSummary, StoreyLoad

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
    # Storage / Industrial Group A = Extra Hazard Group 2 (#1.1.13.5.a, p.530); Group B =
    # Extra Hazard Group 1 (#1.1.13.4.a, p.529) - audit CH123-03.
    "15.i": ("Storage A (Extra Hazard Group 2): high hazard storage", 27.9),
    "16.i": ("Storage B,C (Group B incl. Extra Hazard Group 1): low and ordinary hazard storage", 27.9),
    "17.i": ("Industrial A (Extra Hazard Group 2): high hazard content", 9.3),
    "18.i": ("Industrial B,C (Group B incl. Extra Hazard Group 1): general, low hazard", 9.3),
    # Table 3.13 prints parking rows 19 "Group A,B" and 20 "Group C"; Table 1.1 row 15
    # (p.53) uses A = enclosed, B = mechanical / robotic, C = open / covered (audit
    # CH123-24). The tool routes by use, not by these letters.
    "19.i": ("Parking (Table 3.13 row 19, printed Group A,B; Table 1.1 Group A): enclosed parkings", 27.9),
    "19.ii": ("Parking (Table 3.13 row 19, printed Group A,B; Table 1.1 Group C): open parkings", 27.9),
    "20.i": ("Parking (Table 3.13 row 20, printed Group C; Table 1.1 Group B): mechanical / robotic parkings", 46.5),
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
       for o in ("mercantile_a", "mercantile_b", "mercantile_c")},
    "parking_enclosed": ["19.i"], "parking_open": ["19.ii"],
    "animal_housing": ["21"],
}
# Storage / industrial: Groups A (rows 15, 17) are high hazard = Extra Hazard Group 2
# (#1.1.13.5.a, p.530); Groups B,C (rows 16, 18) include Extra Hazard Group 1 = Group B
# (#1.1.13.4.a, p.529). Audit CH123-03: HH without the EH2 tick takes rows 16 / 18.
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
_F6 = "owner answer 12.10.2026, F6"
_SQ1 = "owner ruling 12.10.2026, P3 Storey Q1"


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
    if occ == "storage_industrial":
        rows = _STORAGE_ROWS[b.hazard_class == "HH" and b.is_extra_hazard_2]
    elif occ in ("parking_enclosed", "parking_open") and b.has_robotic_parking:
        # Audit CH123-23: robotic / mechanical parking ticked -> Table 3.13 row 20.i.
        rows = ["20.i"]
    else:
        rows = _ROWS_BY_OCCUPANCY.get(occ, [])
    if not rows:
        return 0.0, "Not in Table 3.13"
    row = min(rows, key=lambda r: TABLE_3_13_ROWS[r][1])
    f, ref = _row_factor(b, row)
    if len(rows) > 1:
        ref += (f" (densest Table 3.13 row of this occupancy, {_Q2}: per-use areas give the "
                "exact load)")
    if occ == "storage_industrial" and b.hazard_class == "HH" and not b.is_extra_hazard_2:
        ref += (" (HH without Extra Hazard Group 2 = Extra Hazard Group 1 = Storage / "
                "Industrial Group B, #1.1.13.4.a p.529: Group B,C rows; audit CH123-03)")
    if rows == ["20.i"]:
        ref += (" (robotic / mechanical parking ticked; driver-parked levels take row 19: "
                "enter per-use areas; audit CH123-23)")
    return f, ref


def _storey_table_warnings(b: Building, total_area: float,
                           largest_area: float) -> List[str]:
    """Input checks on the per-storey table (F6). They do not stop the evaluation. (The
    storey count is a refusal, not a warning: owner ruling 12.10.2026, P3 Storey Q1.)"""
    w = []
    gfa = float(b.gross_floor_area_m2 or 0)
    if gfa > 0 and total_area > gfa:
        w.append(f"The per-storey areas add up to {total_area:,.0f} m2, more than the GFA "
                 f"of {gfa:,.0f} m2: check the inputs.")
    if b.use_areas:
        w.append("The whole-building per-use areas are not used: the per-storey table "
                 f"governs ({_F6}).")
    ls = float(b.largest_storey_area_m2 or 0)
    if ls > 0:
        txt = (f"The largest storey area input ({ls:,.0f} m2) is not used for Table 3.14: the "
               f"per-storey table governs ({_F6})")
        if largest_area > ls:
            txt += (f"; the table has a storey of {largest_area:,.0f} m2, larger than it: "
                    "check the inputs")
        w.append(txt + ".")
    return w


def _from_storeys(b: Building) -> OccupantLoadSummary:
    """Owner answer 12.10.2026, F6: per-storey per-use table."""
    occ_f, occ_ref = _occupancy_factor(b)
    problems: List[str] = []
    order: List[str] = []
    areas: Dict[str, Dict[Optional[str], float]] = {}
    counts: Dict[str, List[int]] = {}
    refused: set = set()
    for i, u in enumerate(b.storey_uses, 1):
        name = (u.storey or "").strip()
        row = u.row or None
        if not name:
            problems.append(f"line {i}: no storey name")
            continue
        if name not in areas:
            order.append(name)
            areas[name] = {}
            counts[name] = []
        if u.count not in counts[name]:
            counts[name].append(u.count)
        if row is not None and row not in TABLE_3_13_ROWS:
            problems.append(f"line {i} ({name}): {row!r} is not a Table 3.13 row the tool lists")
            refused.add(name)
            continue
        if row is None and u.area_m2 > 0 and occ_f <= 0:
            problems.append(f"line {i} ({name}): no Table 3.13 row chosen, and this occupancy "
                            "has none (Table 3.13, p.285-287): choose the row of the actual use "
                            "(#1.4.5)")
            refused.add(name)
            continue
        areas[name][row] = areas[name].get(row, 0.0) + float(u.area_m2)
    problems += [f"storey {n!r}: no area entered" for n in order
                 if n not in refused and sum(areas[n].values()) <= 0]
    # P3 Storey Q1: every line of a storey carries the same identical-storeys count.
    problems += [f"storey {n!r}: its lines give different identical-storey counts "
                 f"({', '.join(map(str, counts[n]))}); give every line of the storey the same "
                 "count" for n in order if len(counts[n]) > 1]
    count = {n: counts[n][0] for n in order}
    total_area = sum(sum(a.values()) * count[n] for n, a in areas.items())
    if problems:
        return _not_evaluated(
            total_area, "Per-storey table", (
                f"Not evaluated: per-storey table ({_F6}): " + "; ".join(problems) +
                ". Correct the table; no exit count is stated until every line can be valued."),
            "Table 3.14 not evaluated: per-storey table line(s) to correct (no exit count stated)")

    results: List[StoreyLoad] = []
    densest, densest_ref = None, ""
    for name in order:
        ol_s, parts = 0, []
        for row, a in areas[name].items():
            if a <= 0:
                continue
            if row is None:
                f, ref = occ_f, occ_ref
                label = "no row chosen (densest row)"
            else:
                f, ref = _row_factor(b, row)
                label = f"row {row}"
            n = _ol(a, f)
            ol_s += n
            parts.append(f"{label}: {a:,.0f} m2 / {f:g} m2 = {n:,}")
            if densest is None or f < densest:
                densest, densest_ref = f, ref
        exits, _ = min_exits_for_ol(ol_s)
        results.append(StoreyLoad(storey=name, area_m2=sum(areas[name].values()),
                                  occupant_load=ol_s, min_exits=exits, parts=parts,
                                  count=count[name]))
    per = " | ".join(f"{s.storey}" + (f" (x{s.count} identical storeys)" if s.count > 1 else "")
                     + ": " + "; ".join(s.parts) +
                     f" -> OL {s.occupant_load:,} -> {s.min_exits} exits" for s in results)
    # P3 Storey Q1: the counts must cover every storey of the building, else no exit
    # count is stated and the gap is named.
    n_listed = sum(s.count for s in results)
    n_bld = b.floors_above_grade + b.floors_below_grade
    if n_listed != n_bld:
        gap = (f"{n_bld - n_listed} storey(s) not covered" if n_listed < n_bld
               else f"{n_listed - n_bld} storey(s) more than the building has")
        return OccupantLoadSummary(
            area_m2=total_area, factor_m2_per_person=0.0,
            factor_ref="Per-storey table", occupant_load=0, min_exits=0, evaluated=False,
            exit_ref=("Table 3.14 not evaluated: the per-storey table counts do not cover the "
                      f"building's storeys ({gap}; no exit count stated)"),
            note=(f"Not evaluated: per-storey table ({_F6}; {_SQ1}): the identical-storey counts "
                  f"add up to {n_listed} storey(s), the building has {n_bld} (floors above grade "
                  f"{b.floors_above_grade} + basements {b.floors_below_grade}): {gap}. List every "
                  "storey, or give a typical storey its identical-storeys count, so the counts "
                  f"add up to {n_bld}; no exit count is stated until they do. Listed: {per}."),
            storeys=results)
    gov = max(results, key=lambda s: s.occupant_load)
    exits, ref = min_exits_for_ol(gov.occupant_load)
    total = sum(s.occupant_load * s.count for s in results)
    warnings = _storey_table_warnings(b, total_area, max(s.area_m2 for s in results))
    note = (f"OL per storey from the per-storey table (#1.4.5, #4.1.2, #4.1.3, #4.3.1; {_F6}): "
            f"{per}. Governing storey: {gov.storey} (OL {gov.occupant_load:,}). Building total "
            f"OL {total:,} = the sum of the storeys, each counted as many times as its "
            f"identical-storeys count ({_SQ1}; each use rounded up).")
    if any(None in areas[n] for n in order):
        note += f" Lines with no row chosen use {occ_ref}."
    if warnings:
        note += " Check: " + " ".join(warnings)
    return OccupantLoadSummary(
        area_m2=total_area, factor_m2_per_person=densest or 0.0,
        factor_ref=f"Per-storey table (densest factor used: {densest_ref})",
        occupant_load=total, min_exits=exits,
        exit_ref=(f"{ref} (governing storey '{gov.storey}': OL {gov.occupant_load:,}; per "
                  f"storey, #4.3.1, #4.1.3; {_F6})"),
        note=note, storey_area_m2=gov.area_m2, storey_occupant_load=gov.occupant_load,
        governing_storey=gov.storey, storeys=results, warnings=warnings)


def compute_occupant_load(b: Building) -> OccupantLoadSummary:
    occ = b.occupancy

    if occ.startswith("villa_"):
        return _not_evaluated(
            float(b.gross_floor_area_m2 or 0), "Table 3.13 rows 8 / 9: 'None'", (
                "Not evaluated: Table 3.13 rows 8 and 9 print 'None' for villas; villa egress "
                "is set by Tables 3.27 / 3.28 (see the Means of Egress items). Table 3.14 "
                "does not apply to villas."),
            "Table 3.14 not applied to villas (Tables 3.27 / 3.28)")

    if b.storey_uses:
        return _from_storeys(b)

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
