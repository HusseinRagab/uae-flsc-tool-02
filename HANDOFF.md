# HANDOFF — UAE FLSC Streamlit tool (uae-flsc-tool-02)

Cross-PC and cross-session resume point. Update after every change.
Code basis: UAE Fire & Life Safety Code 2018 (CDGH-OP-25). PDF page = printed page.
Audit: `AUDIT_UAE_FLSC_TOOL_12.10.2026.md` (189 findings, rulings R1-R13), kept in the
project files, not in this repo.

A push or merge to `master` redeploys the live app. Nothing merges without Hussein's go.

## Log (newest first)

### 2026-10-12 — Rulings R1-R13 and R2b coded (rulings PR, draft)

Branch `claude/project-thread-0zjltx` restarted on master `18a0342`. Hussein answered every
ruling on decision cards (10:02-10:03Z, R2b 10:22Z), all on the recommended option. Not
merged: a merge redeploys the live app. Issued reports may change; re-run before relying.

- **R1** 23.0 m is highrise in every chapter (`height_class`, app, Ch 3/6/7/8/9/10 YAML).
- **R2 / R2b** a lowrise building with 3 or more basements, or deeper than 7 m, or the
  high-depth occupancy takes Table 9.20.a row H (`is_high_depth`), and its Table 9.21 rows
  are suppressed.
- **R3** Table 9.24.A.3: exactly 3 standpipes = 1000 gpm (printed "more than 3" read as a
  typo).
- **R4** Table 9.21.b.3.i: building systems by Table 9.21.a tiers (GF BUA up to 500 / 501 to
  3,600 / more than 3,600 m2); combined 1000 gpm pump and 60 min tank stay.
- **R5** aboveground LPG tank: Ch 11 Table 11.5 item 5 fixed water spray governs; the Table
  9.31.B "no protection" text is a noted conflict.
- **R6** malls of 23 m or more keep Table 9.22 flows and take Table 9.6 item 13 zoning (45 m
  pump head) and the second pump set (90 m).
- **R7** Ch 8: Sub-FACP every 45 m and highrise FACP redundancy (Table 8.1 item 14.1 ii) for
  every building of 23 m or more; hotels leave the highrise rows; hotel, healthcare,
  detention, education and covered/mixed malls keep their own protocol with a not_required
  line naming the highrise protocol not applied.
- **R8** every Table 9.29 sprinkler row (A, C, D, E, G, H, I, J, L) and 9.29.M high ceiling
  only in a building whose table row requires sprinklers; #4.13.1 not_required note
  otherwise. 9.29.K (wet riser to roof) is not gated: it is a wet riser item.
- **R9** open parking travel S 122 m / NS 91 m (Table 3.16 row 20.ii) with the Table 3.15.b
  item iv conflict printed.
- **R10** open mall: no Table 8.13 row, item 13 MERCANTILE through the height rows; open
  parking: item 22 by analogy, every line labelled.
- **R11** Table 9.29.A edges 13.5 m and 18 m take the higher band, stated on the report.
- **R12** new `has_mv_room` flag (app checkbox "MV room"): wheeled CO2 12 kg, labelled an
  engineering decision; Table 9.30.J is printed "LV ROOMS AND MV ROOMS" so it fires on
  either flag; Table 8.14 item 11 by analogy. The old `has_lv_mv_room` key now means LV
  room: an old saved file with an MV room must tick "MV room".
- **R13** most-restrictive mixed mode: app multiselect "Other occupancies"; every listed
  occupancy is evaluated at the highest hazard class listed and merged, keeping the most
  onerous status per system; lines a secondary brings name it; one pump and tank line.
  Mode and secondaries are now saved and checked on Load.
- **Tests:** `tests/test_rulings.py` (14) + phase 1 (50) = 64 pytest; `test_cases.py` 112
  (2 cases re-pointed for R7 and R10); `_structural_check.py` 0 errors.
- **Grid diff vs master (6552 cases):** 5956 change. 23 m cases change in every chapter
  (R1). FA: height items at 30-95 m, hotel/healthcare protocol, open mall/parking. FP: R2b
  and high-depth occupancy now row H (sprinklers, wet riser, 45 min tank), R4 tiers, R6
  zoning/second pump, R8 not_required lines. MOE: the Table 3.15.b text line in every
  building with basements, and open parking.

### 2026-10-12 — Phase 1 merged to master on Hussein's go (09:39Z)

PR #20 merged; the live app redeploys from master. Reports issued with the earlier app
may change (pump/tank rows, parking, Table 9.30 rooms): re-run any issued job before
relying on it. Rulings were then answered and coded (entry above); phases 2-3 not started. The PC
clone (Created\24.Fire Protection Mind map\python tool\) needs a pull.

### 2026-10-12 — R14b ruled (#4.1.5) — gate on every Table 9.30 room

Hussein chose "All Table 9.30 rooms" (07:33Z). Every `auxiliary_rooms` row in
`rules/ch9_fire_protection.yaml` except 9.30.D (battery room, prints "None") carries
`requires_sprinkler_system: true`. Snapshot vs the R14 commit: the same 940 of 6552 cases
change, and each change is a Table 9.30 line going from required to a #4.1.5 not_required
note (Main Electrical Room and Main Telephone Room, which are on by default). Test
`test_R14b_every_table_9_30_room_gated_by_4_1_5`.

### 2026-10-12 — R14 ruled (#4.1.5) — Lift Machine Room sprinkler in sprinklered buildings only

Hussein chose "Sprinklered only" (07:24Z). `aux_M_lift_machine` carries
`requires_sprinkler_system: true`; `evaluate_fp` gates it on the same sprinkler test as
Table 9.29 and prints a not_required line citing #4.1.5 (p.694) otherwise. Snapshot vs
the previous commit: 940 of 6552 cases change, every one only this line. Test
`test_R14_lift_machine_room_sprinkler_only_in_sprinklered_buildings`. The other Table 9.30
rooms followed under R14b (above).

### 2026-10-12 — Phase 1 (engine core + Ch 9 pumps and tables) — PR #20

Branch `claude/project-thread-0zjltx` off master `fc479a1`. Results change for many
building types; issued reports made with the live app may need a re-run once merged.

- **Engine:** `any_of` / `not` match combinators; `suppresses:` lets a specific table row
  replace the generic one; `duty: pump|tank` keeps one governing Fire Pump and one Fire
  Water Tank line (most onerous gpm then bar, or minutes) and names the other rules that
  also require one; merge skipped when a candidate has no numeric duty (robotic deluge
  pump). Run-time patches moved into the YAML. Derived `is_high_depth` (3 or more
  basements, depth more than 7 m, or the high-depth occupancy) and `pump_head_height_m`
  (height + depth unless the pump room is at grade).
- **Ch 9:** 9.18 super highrise first pump 1000 gpm @ 17 bar + upper sets and 30 min upper
  tanks; 9.19 A/B vs C/D on pump head height 45 m; 9.20.a row H for midrise residential
  with high depth (ruling 12.10.2026); 9.20.b split into its four printed rows; 9.20.c
  replaces row 1; 9.21.a.4 public plot > 20,000 m2 row added; 9.21 tiers fire on any plot;
  single-exit and converted-villa (9.21.d) rows replace the generic tiers; 9.22.B open
  mall tenants, 120 m exemption and yard-hydrant pump; 9.23.B.3 vii note; 9.24 parking
  A.1-A.4, B.1-B.2, C.1-C.4, D.1-D.2 as printed (non-table Class I and smoke items
  dropped); Table 9.6 item 13.iv second pump set at 90 m pump head; #4.1.6 storage yard
  hydrants beyond 100 m; pump specs cite the UAE tables and the 250 gpm @ 7 bar basis.
- **Ch 5/6/7/8/10:** one report line per requirement (exit-sign villa/fuel exclusions,
  single EL line "central battery OR monitored self-contained", EVC not-required rows
  limited to h <= 23 m, storage FA excludes nursery/cold store/robotic parking, basement
  smoke control any-depth + deep (> 7 m) rules, business open-plan highrise split, FF lift
  as its own branch).
- **App:** new inputs (exit stairs, covered/shaded parking, single exit stair, pump room at
  grade, storage GF beyond 100 m from hydrant), saved and shown as chips; height 0 stops
  with an error; Load refuses impossible values by name and loads nothing.
- **Text:** "#" replaces the section sign in rules and UI.
- **Tests:** `tests/test_phase1_findings.py` (50, one per finding) + `tests/test_cases.py`
  (112) + `_structural_check.py` (0 errors). ALTA case (midrise, 3 basements) stays
  750 gpm @ 6.9 bar, 45 min, per Table 9.20.a row H (ruling 12.10.2026).

**Edge choices stated in the report details (no ruling asked):** plot exactly 20,000 m2
stays in row 1; 900 m2 stays in 9.21.d row 1; 20,000 m2 stays in D.1; 1 exit stair takes
the 750 gpm row of 9.24.C.2.

## Open rulings (block the parts named)

| Ruling | Question | State |
| --- | --- | --- |
| R1-R13, R2b | see audit and RULINGS_12.10.2026.md (project files) | ruled 12.10, coded in the rulings PR (draft, not merged) |
| R14 | #4.1.5 Lift Machine Room sprinkler in unsprinklered buildings (CH9A-09) | ruled 12.10: sprinklered only; coded |
| R14b | #4.1.5 for the other Table 9.30 rooms | ruled 12.10: all rooms (9.30.D needs none); coded |

Phase 2 (the rest of the 189 findings) comes as its own PR after the rulings PR.

## Known, not fixed in phase 1

- The approximately sign and the tilde remain in a few texts (`fire_access.py` "Footprint",
  Ch 5 "15 m" note); label sweep is a later phase.
- Villa 9.23 rows still fire beside 9.21.d converted-villa rows; the duty merge keeps the
  governing pump/tank, other items may repeat.
- Scenario matrix "!!" gaps are unchanged from master.

## Verify

```
python3 -m pytest tests/ -q
python3 tests/test_cases.py
python3 _structural_check.py
```

*Last updated: 2026-10-12*
