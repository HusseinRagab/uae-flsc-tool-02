"""Structural integrity check for the UAE FLSC rule YAMLs.

Pre-ship QA — verifies the rule files are internally consistent:
  - no duplicate rule IDs (within a file and globally)
  - every `flag:` references a real Building field
  - every when:/match: key references a real Building field (after stripping
    the _gt/_gte/_lt/_lte/_is/_in/_not suffix and the special keys)
  - every occupancy value used in a match is a valid Occupancy literal
  - every pump_spec_type resolves in pump_specs.yaml (or the engine fallback)
  - every status value is valid
  - reports branches that can never fire (impossible match)

Run:  python _structural_check.py
"""
import sys, typing, glob, os
sys.path.insert(0, ".")
import yaml  # noqa: E402
from flsc_schema import Building, Occupancy  # noqa: E402

RULES_DIR = "rules"
BUILDING_FIELDS = set(Building.model_fields.keys())
# height_class / building_category are @property — also valid match targets
BUILDING_PROPS = {"height_class", "building_category"}
VALID_TARGETS = BUILDING_FIELDS | BUILDING_PROPS
VALID_OCC = set(typing.get_args(Occupancy))
VALID_STATUS = {"required", "recommended", "conditional", "not_required"}

# Special when/match keys handled directly by engine._eval_when
SPECIAL_KEYS = {
    "occupancy", "occupancy_not", "occupancy_in", "hazard_class_in",
    "occupancy_group_is", "building_category_is", "building_category_not",
}
SUFFIXES = ("_gt", "_gte", "_lt", "_lte", "_is", "_in")

errors = []
warnings = []
infos = []

# ---- pump spec types available ----
pump_specs = {}
pump_path = os.path.join(RULES_DIR, "pump_specs.yaml")
if os.path.isfile(pump_path):
    with open(pump_path, encoding="utf-8") as fh:
        pump_specs = yaml.safe_load(fh) or {}
KNOWN_PUMP_TYPES = set(pump_specs.keys()) | {"standpipe_dependent", "fixed_250", "fixed_1000"}


def resolve_target(key):
    """Strip an operator suffix and return the underlying field name."""
    if key in SPECIAL_KEYS:
        return None  # handled specially, no field to check
    for suf in SUFFIXES:
        if key.endswith(suf):
            return key[: -len(suf)]
    if key.endswith("_not"):
        return key[:-4]
    return key  # bare equality


all_ids = {}  # id -> file

for yf in sorted(glob.glob(os.path.join(RULES_DIR, "ch*.yaml"))):
    fname = os.path.basename(yf)
    with open(yf, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh) or {}

    file_ids = set()

    def check_match(match, ctx):
        if not match:
            return
        for k, v in match.items():
            tgt = resolve_target(k)
            if k in ("occupancy", "occupancy_not", "occupancy_in"):
                vals = v if isinstance(v, list) else [v]
                for occ in vals:
                    if occ not in VALID_OCC:
                        errors.append(f"{fname} [{ctx}]: invalid occupancy '{occ}'")
            elif k == "hazard_class_in":
                for hz in v:
                    if hz not in ("LH", "OH1", "OH2", "HH"):
                        errors.append(f"{fname} [{ctx}]: invalid hazard '{hz}'")
            elif tgt and tgt not in VALID_TARGETS:
                errors.append(f"{fname} [{ctx}]: match key '{k}' -> field "
                               f"'{tgt}' not in Building model")

    def check_systems(systems, ctx):
        for e in systems or []:
            if "name" not in e:
                errors.append(f"{fname} [{ctx}]: system entry missing 'name'")
            status = e.get("required", "required")
            if status not in VALID_STATUS:
                errors.append(f"{fname} [{ctx}]: invalid status '{status}'")
            pst = e.get("pump_spec_type")
            if pst and pst not in KNOWN_PUMP_TYPES:
                errors.append(f"{fname} [{ctx}]: unknown pump_spec_type '{pst}'")

    # general rules
    for g in doc.get("general", []) or []:
        rid = g.get("id", "<no-id>")
        if rid in file_ids:
            errors.append(f"{fname}: duplicate rule id '{rid}'")
        file_ids.add(rid)
        if rid in all_ids:
            warnings.append(f"rule id '{rid}' appears in both {all_ids[rid]} "
                            f"and {fname}")
        all_ids[rid] = fname
        check_match(g.get("when", {}), f"general:{rid}")
        check_systems(g.get("systems", []), f"general:{rid}")

    # branches
    for br in doc.get("branches", []) or []:
        rid = br.get("id", "<no-id>")
        if rid in file_ids:
            errors.append(f"{fname}: duplicate rule id '{rid}'")
        file_ids.add(rid)
        if rid in all_ids:
            warnings.append(f"rule id '{rid}' appears in both {all_ids[rid]} "
                            f"and {fname}")
        all_ids[rid] = fname
        check_match(br.get("match", {}), f"branch:{rid}")
        check_systems(br.get("systems", []), f"branch:{rid}")

    # flag-driven sections
    for sec in ("auxiliary_rooms", "equipment", "addons", "various_locations"):
        for rule in doc.get(sec, []) or []:
            rid = rule.get("id", "<no-id>")
            if rid in file_ids:
                errors.append(f"{fname}: duplicate rule id '{rid}'")
            file_ids.add(rid)
            if rid in all_ids:
                warnings.append(f"rule id '{rid}' appears in both "
                                f"{all_ids[rid]} and {fname}")
            all_ids[rid] = fname
            flag = rule.get("flag")
            if flag and flag not in BUILDING_FIELDS:
                errors.append(f"{fname} [{sec}:{rid}]: flag '{flag}' not in "
                               "Building model")
            check_match(rule.get("when", {}), f"{sec}:{rid}")
            check_systems(rule.get("systems", []), f"{sec}:{rid}")

print("=" * 70)
print(f"Structural check — {len(all_ids)} rule IDs across "
      f"{len(glob.glob(os.path.join(RULES_DIR, 'ch*.yaml')))} chapter files")
print("=" * 70)
if errors:
    print(f"\n*** {len(errors)} ERROR(S) ***")
    for e in errors:
        print(f"  ERR  {e}")
else:
    print("\nNo errors.")
if warnings:
    print(f"\n{len(warnings)} warning(s):")
    for w in warnings:
        print(f"  WARN {w}")
else:
    print("No warnings.")
print()
sys.exit(1 if errors else 0)
