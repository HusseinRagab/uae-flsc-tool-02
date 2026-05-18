"""Per-occupancy sanity audit. Identifies which True-by-default flags
typically don't apply for each occupancy. Mirrors the villa fix pattern.

This is a one-time analysis script — NOT a production rule. Output goes
to stdout; no app or schema files are modified.
"""
import sys, typing
sys.path.insert(0, ".")
from flsc_schema import Building, Occupancy, OCCUPANCY_DEFS  # noqa: E402

# Current first-load defaults from app.py (the flags set to True up-front)
DEFAULT_TRUE_FLAGS = (
    "has_stairs", "has_elevator", "has_diesel_generator_room",
    "has_main_electrical_room", "has_main_telephone_room",
    "has_lift_machine_room", "has_fire_pump_room", "has_parking_area",
)

# Per-occupancy applicability assessment for each default-True flag.
# 'yes' = typical / 'no' = typically not present / 'maybe' = depends on size
# 'n/a' = the occupancy itself doesn't have buildings of this type
APPLICABILITY = {
    "villa_private":          dict(stairs="no",elevator="no",diesel="no",electrical="no",telephone="no",lift="no",pump="no",parking="maybe"),
    "villa_commercial":       dict(stairs="no",elevator="no",diesel="no",electrical="no",telephone="no",lift="no",pump="no",parking="maybe"),
    "residential":            dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "labour_accommodation":   dict(stairs="yes",elevator="maybe",diesel="yes",electrical="yes",telephone="yes",lift="maybe",pump="yes",parking="maybe"),
    "staff_accommodation":    dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "hostel":                 dict(stairs="yes",elevator="maybe",diesel="yes",electrical="yes",telephone="yes",lift="maybe",pump="yes",parking="no"),
    "hotel_a":                dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "hotel_b":                dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "hotel_c":                dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "business":               dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "assembly_a":             dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "assembly_b":             dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "assembly_c":             dict(stairs="yes",elevator="maybe",diesel="maybe",electrical="yes",telephone="maybe",lift="maybe",pump="maybe",parking="yes"),
    "education_a":            dict(stairs="yes",elevator="maybe",diesel="maybe",electrical="yes",telephone="maybe",lift="maybe",pump="maybe",parking="maybe"),
    "education_b":            dict(stairs="yes",elevator="maybe",diesel="yes",electrical="yes",telephone="yes",lift="maybe",pump="yes",parking="yes"),
    "education_c":            dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "mercantile_a":           dict(stairs="yes",elevator="no",diesel="no",electrical="yes",telephone="maybe",lift="no",pump="maybe",parking="yes"),
    "mercantile_b":           dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "healthcare_a":           dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "healthcare_b":           dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="maybe",pump="maybe",parking="yes"),
    "healthcare_c":           dict(stairs="yes",elevator="maybe",diesel="maybe",electrical="yes",telephone="maybe",lift="maybe",pump="maybe",parking="yes"),
    "daycare_a":              dict(stairs="yes",elevator="maybe",diesel="maybe",electrical="yes",telephone="maybe",lift="maybe",pump="maybe",parking="maybe"),
    "daycare_b":              dict(stairs="yes",elevator="no",diesel="no",electrical="yes",telephone="no",lift="no",pump="no",parking="maybe"),
    "daycare_c":              dict(stairs="no",elevator="no",diesel="no",electrical="maybe",telephone="no",lift="no",pump="no",parking="no"),
    "detention_a":            dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "detention_b":            dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "detention_c":            dict(stairs="yes",elevator="maybe",diesel="yes",electrical="yes",telephone="yes",lift="maybe",pump="maybe",parking="yes"),
    "mall_covered":           dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "mall_open":              dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "mall_mixed":             dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "parking_enclosed":       dict(stairs="yes",elevator="yes",diesel="maybe",electrical="yes",telephone="no",lift="yes",pump="yes",parking="n/a"),
    "parking_open":           dict(stairs="yes",elevator="maybe",diesel="no",electrical="yes",telephone="no",lift="maybe",pump="maybe",parking="n/a"),
    "storage_industrial":     dict(stairs="maybe",elevator="no",diesel="yes",electrical="yes",telephone="maybe",lift="no",pump="yes",parking="yes"),
    "motor_fuel_dispensing":  dict(stairs="no",elevator="no",diesel="no",electrical="yes",telephone="no",lift="no",pump="maybe",parking="no"),
    "infrastructure":         dict(stairs="n/a",elevator="n/a",diesel="n/a",electrical="n/a",telephone="n/a",lift="n/a",pump="n/a",parking="n/a"),
    "animal_housing":         dict(stairs="no",elevator="no",diesel="no",electrical="yes",telephone="no",lift="no",pump="no",parking="no"),
    "mixed_multiple":         dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "high_depth_underground": dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
    "low_depth_underground":  dict(stairs="yes",elevator="yes",diesel="yes",electrical="yes",telephone="yes",lift="yes",pump="yes",parking="yes"),
}

LABEL = dict(stairs="stairs",elevator="elevator",diesel="diesel gen",
             electrical="main electrical",telephone="telephone",
             lift="lift machine",pump="fire pump",parking="parking area")

ALL_OCC = list(typing.get_args(Occupancy))

print(f"{'Occupancy':<25} | {'NO-apply flags ticked by default':<55} | severity")
print("-" * 110)

rows = []
for occ in ALL_OCC:
    appl = APPLICABILITY.get(occ, {})
    not_apply = [LABEL[k] for k, v in appl.items() if v == "no"]
    na = [LABEL[k] for k, v in appl.items() if v == "n/a"]
    if not_apply or na:
        if na and not any(v != "n/a" for v in appl.values()):
            severity = "ALL N/A (not a building)"
        elif len(not_apply) >= 5:
            severity = "HIGH (villa-like)"
        elif len(not_apply) >= 3:
            severity = "MODERATE"
        elif len(not_apply) >= 1:
            severity = "MINOR"
        else:
            severity = "OK"
        rows.append((occ, not_apply, na, severity))

# Sort by severity (worst first), then alphabetically
sev_rank = {"ALL N/A (not a building)":0, "HIGH (villa-like)":1, "MODERATE":2, "MINOR":3, "OK":4}
rows.sort(key=lambda r: (sev_rank.get(r[3], 9), r[0]))

for occ, no_apply, na, sev in rows:
    display = ", ".join(no_apply) if no_apply else "ALL FLAGS N/A"
    print(f"{occ:<25} | {display[:55]:<55} | {sev}")

print()
print("=" * 110)
ok_occs = [o for o in ALL_OCC if o not in [r[0] for r in rows]]
print(f"\nOccupancies with NO concerns ({len(ok_occs)}):")
for o in ok_occs:
    print(f"  OK  {o}")
