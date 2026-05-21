"""Multi-scenario verification matrix for the UAE FLSC tool.

Runs ~40 realistic UAE building scenarios through the engine and prints,
per scenario:
  - the matched branch for every chapter
  - per-chapter requirement counts (required / recommended / conditional)
  - any chapter that produced ZERO requirements (potential gap)
  - any chapter with NO matched branch (potential gap)

Also flags scenarios where the high-ceiling / wet-riser / attached-parking
sub-evaluations behave unexpectedly.

Run:  python _scenario_matrix.py
"""
import sys
sys.path.insert(0, ".")
from flsc_schema import Building  # noqa: E402
from engine import evaluate  # noqa: E402

CHAP = ["MOE", "FE", "ES", "EL", "EVC", "FA", "FP", "SC", "LPG"]

SCENARIOS = [
    # ---- Villas ----
    ("Private villa G+1", dict(occupancy="villa_private", height_m=6,
        floors_above_grade=2, ground_floor_bua_m2=250, plot_area_m2=600,
        has_stairs=False, has_elevator=False, has_diesel_generator_room=False,
        has_main_electrical_room=False, has_main_telephone_room=False,
        has_lift_machine_room=False, has_fire_pump_room=False)),
    ("Private villa G+2 1800 m2", dict(occupancy="villa_private", height_m=9,
        floors_above_grade=3, ground_floor_bua_m2=1800, plot_area_m2=2200,
        has_stairs=False, has_elevator=False)),
    ("Commercial villa (clinic)", dict(occupancy="villa_commercial", height_m=9,
        floors_above_grade=2, ground_floor_bua_m2=400, plot_area_m2=700,
        villa_converted_use=True)),

    # ---- Residential ----
    ("Lowrise residential G+3", dict(occupancy="residential", height_m=14,
        floors_above_grade=4, floors_below_grade=1, ground_floor_bua_m2=800,
        basement_bua_m2=800, gross_floor_area_m2=3200, plot_area_m2=2000)),
    ("Midrise residential G+6 21m", dict(occupancy="residential", height_m=21,
        floors_above_grade=7, floors_below_grade=1, ground_floor_bua_m2=1000,
        basement_bua_m2=1000, gross_floor_area_m2=7000, plot_area_m2=3000)),
    ("Highrise residential 55m", dict(occupancy="residential", height_m=55,
        floors_above_grade=18, floors_below_grade=2, ground_floor_bua_m2=1200,
        basement_bua_m2=1200, gross_floor_area_m2=22000, plot_area_m2=5000,
        wet_riser_standpipes=3)),
    ("Super-highrise residential 120m", dict(occupancy="residential",
        height_m=120, floors_above_grade=35, floors_below_grade=3,
        ground_floor_bua_m2=1800, basement_bua_m2=1800,
        gross_floor_area_m2=60000, plot_area_m2=25000, wet_riser_standpipes=3)),
    ("Labour accommodation lowrise", dict(occupancy="labour_accommodation",
        height_m=14, floors_above_grade=4, ground_floor_bua_m2=4500,
        plot_area_m2=8000, wet_riser_standpipes=3)),
    ("Staff accommodation midrise", dict(occupancy="staff_accommodation",
        height_m=20, floors_above_grade=6, ground_floor_bua_m2=900,
        plot_area_m2=2500)),
    ("Hostel lowrise", dict(occupancy="hostel", height_m=12,
        floors_above_grade=3, ground_floor_bua_m2=600, plot_area_m2=1200,
        has_parking_area=False)),

    # ---- Hotels ----
    ("Hotel A highrise 60m", dict(occupancy="hotel_a", height_m=60,
        floors_above_grade=18, floors_below_grade=2, ground_floor_bua_m2=1500,
        basement_bua_m2=1500, gross_floor_area_m2=25000, plot_area_m2=5000,
        has_commercial_kitchen=True, wet_riser_standpipes=3)),
    ("Hotel B midrise 22m", dict(occupancy="hotel_b", height_m=22,
        floors_above_grade=7, ground_floor_bua_m2=900, plot_area_m2=2000,
        has_commercial_kitchen=True)),
    ("Hotel C lowrise apartments", dict(occupancy="hotel_c", height_m=14,
        floors_above_grade=4, ground_floor_bua_m2=700, plot_area_m2=1500)),

    # ---- Business ----
    ("Office highrise 30m", dict(occupancy="business", height_m=30,
        floors_above_grade=8, floors_below_grade=2, ground_floor_bua_m2=800,
        basement_bua_m2=800, gross_floor_area_m2=6400, plot_area_m2=2500)),
    ("Office lowrise small", dict(occupancy="business", height_m=10,
        floors_above_grade=2, ground_floor_bua_m2=400, plot_area_m2=1000)),

    # ---- Assembly ----
    ("Assembly A stadium", dict(occupancy="assembly_a", height_m=25,
        floors_above_grade=3, ground_floor_bua_m2=8000, plot_area_m2=20000,
        assembly_area_m2=6000, has_permanent_stages=True)),
    ("Assembly B banquet hall", dict(occupancy="assembly_b", height_m=12,
        floors_above_grade=2, ground_floor_bua_m2=2000, plot_area_m2=5000,
        assembly_area_m2=1500, has_commercial_kitchen=True)),
    ("Assembly C restaurant", dict(occupancy="assembly_c", height_m=8,
        floors_above_grade=1, ground_floor_bua_m2=400, plot_area_m2=900,
        has_commercial_kitchen=True)),

    # ---- Education ----
    ("Education A nursery", dict(occupancy="education_a", height_m=8,
        floors_above_grade=2, ground_floor_bua_m2=600, plot_area_m2=1500)),
    ("Education B school", dict(occupancy="education_b", height_m=14,
        floors_above_grade=3, ground_floor_bua_m2=3000, plot_area_m2=8000)),
    ("Education C university", dict(occupancy="education_c", height_m=24,
        floors_above_grade=6, ground_floor_bua_m2=4000, plot_area_m2=12000)),

    # ---- Healthcare ----
    ("Healthcare A hospital lowrise", dict(occupancy="healthcare_a",
        height_m=12, floors_above_grade=3, floors_below_grade=1,
        ground_floor_bua_m2=3000, basement_bua_m2=2000,
        gross_floor_area_m2=9000, plot_area_m2=8000,
        has_operation_theater=True, has_mri_scanning_room=True,
        has_anesthetizing_room=True)),
    ("Healthcare A hospital highrise", dict(occupancy="healthcare_a",
        height_m=40, floors_above_grade=12, ground_floor_bua_m2=2000,
        plot_area_m2=6000, has_operation_theater=True,
        has_mri_scanning_room=True, wet_riser_standpipes=3)),
    ("Healthcare B clinic", dict(occupancy="healthcare_b", height_m=12,
        floors_above_grade=3, ground_floor_bua_m2=600, plot_area_m2=1200)),
    ("Healthcare C ambulatory", dict(occupancy="healthcare_c", height_m=8,
        floors_above_grade=2, ground_floor_bua_m2=400, plot_area_m2=900)),

    # ---- Daycare ----
    ("Daycare A 15 clients", dict(occupancy="daycare_a", height_m=8,
        floors_above_grade=2, ground_floor_bua_m2=500, plot_area_m2=1000)),
    ("Daycare B 10 clients", dict(occupancy="daycare_b", height_m=6,
        floors_above_grade=2, ground_floor_bua_m2=300, plot_area_m2=600)),
    ("Daycare C family 5 clients", dict(occupancy="daycare_c", height_m=6,
        floors_above_grade=1, ground_floor_bua_m2=200, plot_area_m2=500)),

    # ---- Mall / Mercantile ----
    ("Covered mall 3 floors", dict(occupancy="mall_covered", height_m=18,
        floors_above_grade=3, floors_below_grade=2, ground_floor_bua_m2=25000,
        basement_bua_m2=25000, gross_floor_area_m2=75000, plot_area_m2=50000,
        has_atrium=True, has_commercial_kitchen=True, has_theater_cinema=True,
        wet_riser_standpipes=3)),
    ("Open mall strip", dict(occupancy="mall_open", height_m=10,
        floors_above_grade=2, ground_floor_bua_m2=8000, plot_area_m2=20000)),
    ("Mercantile A small shop", dict(occupancy="mercantile_a", height_m=8,
        floors_above_grade=2, ground_floor_bua_m2=600, plot_area_m2=1200)),
    ("Mercantile B hypermarket", dict(occupancy="mercantile_b", height_m=14,
        floors_above_grade=3, ground_floor_bua_m2=5000, plot_area_m2=12000,
        wet_riser_standpipes=3)),

    # ---- Parking ----
    ("Enclosed parking 3 floors", dict(occupancy="parking_enclosed",
        height_m=12, floors_above_grade=3, ground_floor_bua_m2=3000,
        plot_area_m2=5000)),
    ("Open parking large", dict(occupancy="parking_open", height_m=10,
        floors_above_grade=2, gross_floor_area_m2=6000,
        ground_floor_bua_m2=6000, plot_area_m2=8000)),

    # ---- Storage / Industrial ----
    ("Warehouse OH2 4000m2", dict(occupancy="storage_industrial", height_m=10,
        floors_above_grade=1, ground_floor_bua_m2=4000, plot_area_m2=10000,
        hazard_class="OH2")),
    ("Warehouse LH small", dict(occupancy="storage_industrial", height_m=8,
        floors_above_grade=1, ground_floor_bua_m2=500, plot_area_m2=2000,
        hazard_class="LH")),
    ("Cold storage", dict(occupancy="storage_industrial", height_m=12,
        floors_above_grade=1, ground_floor_bua_m2=3000, plot_area_m2=6000,
        hazard_class="OH2", is_cold_storage=True)),
    ("Aircraft hanger", dict(occupancy="storage_industrial", height_m=15,
        floors_above_grade=1, ground_floor_bua_m2=5000, plot_area_m2=12000,
        hazard_class="OH2", is_aircraft_hanger=True)),

    # ---- Motor fuel ----
    ("Petrol station Group A", dict(occupancy="motor_fuel_dispensing",
        height_m=4, floors_above_grade=1, ground_floor_bua_m2=300,
        plot_area_m2=2000, motor_fuel_group="A")),
    ("Petrol station Group B", dict(occupancy="motor_fuel_dispensing",
        height_m=4, floors_above_grade=1, ground_floor_bua_m2=300,
        plot_area_m2=2000, motor_fuel_group="B")),
    ("Petrol station Group C", dict(occupancy="motor_fuel_dispensing",
        height_m=4, floors_above_grade=1, ground_floor_bua_m2=300,
        plot_area_m2=2000, motor_fuel_group="C")),

    # ---- Detention ----
    ("Detention A max security", dict(occupancy="detention_a", height_m=14,
        floors_above_grade=3, ground_floor_bua_m2=2000, plot_area_m2=6000)),
    ("Detention C police holding", dict(occupancy="detention_c", height_m=10,
        floors_above_grade=2, ground_floor_bua_m2=800, plot_area_m2=2000)),

    # ---- Misc ----
    ("Animal housing stable", dict(occupancy="animal_housing", height_m=6,
        floors_above_grade=1, ground_floor_bua_m2=400, plot_area_m2=1500)),
    ("Infrastructure development", dict(occupancy="infrastructure",
        height_m=0, plot_area_m2=20000)),
]


def _counts(ch):
    c = {"required": 0, "recommended": 0, "conditional": 0, "not_required": 0}
    for blk in ch.blocks:
        for it in blk.items:
            c[it.status] = c.get(it.status, 0) + 1
    return c


flags = []  # accumulate concerns

for name, inp in SCENARIOS:
    try:
        b = Building(occupancy=inp["occupancy"], **{k: v for k, v in inp.items()
                                                    if k != "occupancy"})
        r = evaluate(b)
    except Exception as e:
        print(f"\n### {name}")
        print(f"  *** EXCEPTION: {type(e).__name__}: {e}")
        flags.append(f"{name}: EXCEPTION {e}")
        continue

    print(f"\n### {name}  [{b.height_class} / {b.building_category} / "
          f"hazard {b.hazard_class}]")
    for code in CHAP:
        ch = r.chapter(code)
        if not ch:
            print(f"  {code:4} : (chapter not produced)")
            flags.append(f"{name}: chapter {code} not produced")
            continue
        c = _counts(ch)
        total = sum(c.values())
        branch = ch.selected_branch or "-"
        line = (f"  {code:4} : branch={branch:<34} "
                f"R={c['required']} r={c['recommended']} "
                f"c={c['conditional']} n={c['not_required']}")
        print(line)
        # Sanity flags
        if total == 0 and code not in ("LPG",):
            flags.append(f"{name}: chapter {code} produced ZERO items")
        if branch == "-" and code in ("MOE", "FE", "ES", "EL", "FA", "FP", "SC"):
            flags.append(f"{name}: chapter {code} matched NO branch")
    # Wet riser / high ceiling / attached parking
    extras = []
    if r.requires_wet_riser:
        extras.append(f"wet-riser({b.wet_riser_standpipes} standpipes)")
    if r.high_ceiling and r.high_ceiling.applies:
        extras.append(f"high-ceiling({r.high_ceiling.height_range})")
    if r.attached_parking_chapters:
        extras.append(f"attached-parking({len(r.attached_parking_chapters)} ch)")
    if extras:
        print(f"         extras: {', '.join(extras)}")

print("\n" + "=" * 70)
if flags:
    print(f"{len(flags)} SANITY FLAG(S):")
    for f in flags:
        print(f"  !! {f}")
else:
    print("No sanity flags — every scenario produced a branch + items for "
          "every applicable chapter.")
print("=" * 70)
