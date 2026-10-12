"""UAE FLSC 2018 Table 3.13 occupant-load factors and Table 3.14 exit counts.

Ch 3 #4.1.2 (p.283): the occupant load is "not less than" floor area / factor, so
the quotient is rounded UP. #4.3.1 (p.288) and #4.1.3 (p.283): Table 3.14 is
applied per storey. The tool has the total GFA and the storey counts but no
per-storey area, so the storey OL is bounded, never split by a guess:
  - one storey and no basement: storey OL = total OL (exact);
  - otherwise the largest storey is at least GFA / (all storeys) and at most
    the GFA, and the exit count stated is the one the lower bound proves
    ("at least k"), with the upper value named beside it.
Occupancies Table 3.13 has no row for (fuel station, infrastructure,
underground, mixed use) and malls whose GLA is not known get no OL: the
factor depends on the actual use / the GLA, which the tool does not have.
"""
from __future__ import annotations

import math
from typing import Optional, Tuple

from flsc_schema import Building, OccupantLoadSummary

# Primary Table 3.13 factor (m2 per person) by schema occupancy (p.285-287).
# Where the occupancy spans rows with different factors, the primary is the
# least dense row and the denser row is reported beside it (_ALT_FACTOR_M2).
_OL_FACTOR_M2: dict[str, Tuple[float, str]] = {
    "assembly_a": (0.65, "Table 3.13 row 1.i concentrated (ballroom / dance floor)"),
    "assembly_b": (0.65, "Table 3.13 row 1.i concentrated"),
    "assembly_c": (1.4, "Table 3.13 row 1.ii less concentrated (meeting room / restaurant)"),
    "business": (9.3, "Table 3.13 row 2.i regular office"),
    "education_a": (1.9, "Table 3.13 row 3.i classroom (net)"),
    "education_b": (1.9, "Table 3.13 row 3.i classroom (net)"),
    "education_c": (1.9, "Table 3.13 row 3.i classroom (net)"),
    "mercantile_a": (2.8, "Table 3.13 row 13.ii sales on street floor"),
    "mercantile_b": (2.8, "Table 3.13 row 13.ii sales on street floor"),
    "healthcare_a": (22.3, "Table 3.13 row 4.i inpatient treatment departments"),
    "healthcare_b": (9.3, "Table 3.13 row 4.iv clinics"),
    "healthcare_c": (13.0, "Table 3.13 row 5.i ambulatory healthcare"),
    "hotel_a": (18.6, "Table 3.13 row 11 hotel guest rooms / apartments"),
    "hotel_b": (18.6, "Table 3.13 row 11 hotel guest rooms"),
    "hotel_c": (18.6, "Table 3.13 row 11 hotel guest rooms"),
    "daycare_a": (3.3, "Table 3.13 row 12 day care (net)"),
    "daycare_b": (3.3, "Table 3.13 row 12 day care (net)"),
    "daycare_c": (3.3, "Table 3.13 row 12 day care (net)"),
    "residential": (18.6, "Table 3.13 row 6.i apartments"),
    "labour_accommodation": (18.6, "Table 3.13 row 7 labour accommodation"),
    "staff_accommodation": (18.6, "Table 3.13 row 7.i staff accommodation"),
    "hostel": (18.6, "Table 3.13 row 7.i hostels"),
    "animal_housing": (11.1, "Table 3.13 row 21 animal housing"),
    "detention_a": (11.1, "Table 3.13 row 10 detention"),
    "detention_b": (11.1, "Table 3.13 row 10 detention"),
    "detention_c": (11.1, "Table 3.13 row 10 detention"),
    "villa_private": (0.0, "Table 3.13 row 8 private villa: factor 'None'"),
    "villa_commercial": (0.0, "Table 3.13 row 9 commercial villa: factor 'None'"),
    "mall_covered": (2.8, "Table 3.13 row 14.i mall GLA less than 14,000 m2"),
    "mall_open": (2.8, "Table 3.13 row 14.i mall GLA less than 14,000 m2"),
    "mall_mixed": (2.8, "Table 3.13 row 14.i mall GLA less than 14,000 m2"),
    "parking_enclosed": (27.9, "Table 3.13 row 19.i enclosed parking"),
    "parking_open": (27.9, "Table 3.13 row 19.ii open parking"),
    "storage_industrial": (27.9, "Table 3.13 rows 15.i / 16.i storage"),
}

# Denser Table 3.13 row the same occupancy can contain (CH3-02). The tool has
# no per-use area (#1.4.5, p.242), so both results are shown.
_ALT_FACTOR_M2: dict[str, Tuple[float, str]] = {
    "storage_industrial": (9.3, "industrial use (Table 3.13 rows 17.i / 18.i, 9.3 m2)"),
    "healthcare_a": (11.1, "sleeping departments (Table 3.13 row 4.ii, 11.1 m2)"),
    "assembly_c": (0.65, "dance floor / concentrated use (Table 3.13 row 1.i, 0.65 m2 net)"),
}

# Table 3.13 has rows 1 to 21 only (p.285-287): none for these (CH3-03).
_NOT_IN_TABLE_3_13 = {
    "motor_fuel_dispensing": "motor fuel dispensing",
    "infrastructure": "infrastructure",
    "mixed_multiple": "mixed / multiple occupancy",
    "high_depth_underground": "high-depth underground",
    "low_depth_underground": "low-depth underground",
}

_MALLS = ("mall_covered", "mall_open", "mall_mixed")


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


def _ol(area: float, factor: float) -> int:
    """#4.1.2 (p.283): not less than area / factor -> round up."""
    return int(math.ceil(round(area / factor, 9))) if area > 0 else 0


def _storey_bounds(b: Building) -> Tuple[float, Optional[float], Optional[float], str]:
    """(total area, largest-storey low bound, largest-storey high bound, basis).
    Bounds are None when they cannot be derived from the inputs."""
    gfa = float(b.gross_floor_area_m2 or 0)
    gf = float(b.ground_floor_bua_m2 or 0)
    storeys = b.floors_above_grade + b.floors_below_grade
    single = b.floors_above_grade == 1 and b.floors_below_grade == 0
    if gfa > 0:
        if single:
            return gfa, gfa, gfa, "single storey: storey area = GFA"
        return gfa, gfa / storeys, gfa, (
            f"no per-storey area: largest storey taken between GFA / {storeys} storeys "
            f"= {gfa / storeys:,.0f} m2 and the whole GFA {gfa:,.0f} m2")
    if gf > 0:
        if single:
            return gf, gf, gf, "single storey: storey area = ground-floor BUA (no GFA entered)"
        return gf, gf, None, ("no GFA entered: the ground-floor BUA is one storey, so the "
                              "largest storey is at least that area")
    return 0.0, None, None, ""


def _not_evaluated(area: float, factor_ref: str, why: str) -> OccupantLoadSummary:
    return OccupantLoadSummary(
        area_m2=area, factor_m2_per_person=0.0, factor_ref=factor_ref,
        occupant_load=0, min_exits=2,
        exit_ref=("Table 3.14 row i: minimum 2 means of egress per storey; 3 or 4 where a "
                  "storey OL reaches 500 / exceeds 1,000 - not evaluated (OL not computed)"),
        note=why,
    )


def compute_occupant_load(b: Building) -> OccupantLoadSummary:
    occ = b.occupancy
    area, low, high, basis = _storey_bounds(b)

    if occ in _NOT_IN_TABLE_3_13:
        return _not_evaluated(area, "Not in Table 3.13", (
            f"Not evaluated: Table 3.13 (p.285-287) has no row for {_NOT_IN_TABLE_3_13[occ]}. "
            "#1.4.5 (p.242): divide the floor area assigned to each actual use by that use's "
            "Table 3.13 factor and add the results; then apply Table 3.14 per storey."))

    factor, factor_ref = _OL_FACTOR_M2.get(occ, (0.0, "Not in Table 3.13"))
    if factor <= 0:
        return _not_evaluated(area, factor_ref, (
            "Not evaluated: Table 3.13 rows 8 and 9 print 'None' for villas; villa egress is "
            "set by Tables 3.27 / 3.28 (see the Means of Egress items)."
            if occ.startswith("villa_") else
            "Not evaluated: no occupant-load factor for this occupancy."))
    if area <= 0:
        return _not_evaluated(0.0, factor_ref, "Not evaluated: no GFA or ground-floor BUA entered.")

    if occ in _MALLS and area >= 14000:
        return _not_evaluated(area, "Table 3.13 row 14 (needs the mall GLA)", (
            "Not evaluated: Table 3.13 row 14 (p.287) keys the mall factor on the gross "
            "leasable area: less than 14,000 m2 -> 2.8 m2; 14,000 m2 -> 3.3 m2; 0.1 m2 added "
            "for every 1,290 m2 increment, maximum 5.1 m2. With GFA of 14,000 m2 or more the "
            "GLA is not known, so the factor is not known. Enter the GLA (owner question)."))

    total = _ol(area, factor)
    lo_ol = _ol(low, factor)
    exits, ref = min_exits_for_ol(lo_ol)
    notes = [f"Total OL = {area:,.0f} m2 / {factor:g} m2 per person = {total:,} "
             "(rounded up: #4.1.2 'not less than')."]
    if low == high:
        exit_ref = f"{ref} (storey OL {lo_ol:,}; per storey, #4.3.1)"
    else:
        hi_ol = _ol(high, factor) if high is not None else None
        hi_exits = min_exits_for_ol(hi_ol)[0] if hi_ol is not None else 4
        if hi_exits == exits:
            exit_ref = (f"{ref} for every storey (largest storey OL at least {lo_ol:,}; "
                        "#4.3.1)")
        else:
            exit_ref = (f"Table 3.14 per storey (#4.3.1): at least {exits} exits (largest storey "
                        f"OL at least {lo_ol:,}); up to {hi_exits} if one storey carries "
                        f"{'the whole GFA' if hi_ol is not None else 'more area'} - enter the "
                        "largest storey area")
        notes.append(f"Table 3.14 is per storey; {basis}. The total OL is not used for "
                     "Table 3.14.")
    alt = _ALT_FACTOR_M2.get(occ)
    if alt:
        a_factor, a_label = alt
        a_total = _ol(area, a_factor)
        a_exits = min_exits_for_ol(_ol(low, a_factor))[0]
        notes.append(f"Factor {factor:g} m2 is {factor_ref}. For {a_label}: total OL "
                     f"{a_total:,}, at least {a_exits} exits per storey. #1.4.5 (p.242) takes "
                     "each use's own area; the tool has no per-use area (owner question).")
    notes.append("Gross area used; Table 3.13 'net' factors apply to the net area of that use.")
    return OccupantLoadSummary(
        area_m2=area,
        factor_m2_per_person=factor,
        factor_ref=factor_ref,
        occupant_load=total,
        min_exits=exits,
        exit_ref=exit_ref,
        note=" ".join(notes),
    )
