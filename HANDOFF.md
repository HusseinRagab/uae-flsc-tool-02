# HANDOFF — UAE FLSC Streamlit tool (uae-flsc-tool-02)

Cross-PC and cross-session resume point. Update after every change.
Code basis: UAE Fire & Life Safety Code 2018 (CDGH-OP-25). PDF page = printed page.
Audit: `AUDIT_UAE_FLSC_TOOL_12.10.2026.md` (189 findings, rulings R1-R13), kept in the
project files, not in this repo.

A push or merge to `master` redeploys the live app. Nothing merges without Hussein's go.

## Log (newest first)

### 2026-10-12 — Phase 3 owner answers coded (24 cards, 16:27Z, all on the recommended option)

Log: project files `uae_flsc_tool/phase3/ANSWERS_12.10.2026.md`; reports REPORT_a1/a2/a3.
- Ch 10: 90 m tunnel = jet fan (higher band); high-depth underground gets the #2.9.4.a fire lift
  without a basement count; mall/assembly stair (inference) and "such as" corridor cite the rulings.
- Ch 11 / 19 / 15: written EAP required for every non-villa building; villas get assembly point,
  drills, wheelchairs as conditional (p.1090, p.1233 unread); new inputs: new or modified building
  + CD approval (cylinders stop without it, #2.2.4-#2.2.5), aboveground at-grade tanks (Table 11.5),
  indoor / outdoor flame-effect show (indoor in an unsprinklered building stops, #3.2.2).
- Ch 4 / 6: Class A for parking / underground = p.374 types as a tool decision, none for
  infrastructure, mixed follows R13 (NOT EVALUATED with none listed); Business / Mercantile Group C
  stand-alone checkboxes (Table 6.5 item 11/12 below 23 m).
- Storey table: identical-storeys count, counts must cover every floor or Table 3.14 is NOT
  EVALUATED. Secondary animal housing needs a group (R13).
- Ch 9: converted villa (9.21.d) suppresses the 9.23 villa rows; parking above 23 m merges the
  9.19 / 9.24 riser, sprinkler, pump and tank lines (one each, both tables cited); attached parking
  has its own height and basement levels (blank = lines that depend on them NOT EVALUATED); LPG
  spray line reads the at-grade input (underground only = not required).
- Grid vs the previous push: pump / tank unchanged; parking 50 m and 95 m lose the duplicate 9.24
  sprinkler and riser lines. Tests: 268 pytest, 112 cases, structural 0.
- Mercantile C and Business A/B/C: phase 4 (App Q4).
- Follow-up cards open: cylinder "new building" default, villa EAP line, flame effect alarm
  condition, amusement vs Group C EL row.

### 2026-10-12 — Phase 3 (Ch 4-7, 10, 11, 15, 19, Annexure 2, app, per-storey egress, animal housing) on the branch (draft)

Five packages built off master 825e900 and merged on `claude/project-thread-0zjltx`; reports in
the project files `uae_flsc_tool/phase3/REPORT_<pkg>_12.10.2026.md`.
- **Ch 4-7** (CH47-01, 03-05, 07-09, 11-19): Class B by occupancy (Table 4.3 row 2), Class A by printed
  page, nursery strips conditional, EVC 75 dB sleeping areas and Table 7.1/7.2 items, one EL system
  type for offices/shops, EL wiring per system, Table 6.7/6.8 tests, printed exit-sign colours.
- **Ch 10** (CH10-05, 14-17, 27, 28, 35, 38, 39): corridor rule for any lowrise/midrise, hospital rows
  for healthcare_a only, schools below 23 m stair not mandatory, hall-area purge, tunnel length tiers,
  parking stair at 23 m. New input: theatre / cinema kind.
- **Ch 11, 15, 19, Annexure 2** (CH10-06 to 13, 18-26, 29-34, 36, 39 LPG part): Ch 11 re-read against
  Tables 11.1-11.14, refuge conditional (#3.8.1), drills/assembly point/wheelchairs in every non-villa
  building, Table A2.1 checklist.
- **App** (ENG-02, 11, 12, 13, 16, 17, 19, 21, 22, 23; CH9A-17, 19, 20; CH9B-14; Scenario B): Load
  replaces the session, occupancy restored, category change resets flags, infrastructure selectable,
  mercantile over 3600 m2 multi-tenant = Mall, attached parking OFF by default (no fallback area),
  water-reactive #4.1.2 input, Table 9.21.e outlet and 9.21.f tent inputs, Scenario B asks the
  storage hazard.
- **F6** optional per-storey per-use table (OL and Table 3.14 per storey, governing storey named);
  **Ch9 Q6** animal housing Groups A (LH), B (OH2), C (LH) per #1.1.13 p.528-529, group required.
- Merge fix: Ch 9 LPG spray required for roof tanks beside underground tanks (matches Ch 11).
- Grid (6552 cases vs 825e900): fire pump / tank change only in 16 midrise low-depth underground
  cases (now NOT EVALUATED, CH9A-19); attached-parking chapters drop out because parking is now
  opt-in; every case changes in FE, most in EAP/EL/ACC/ES/EVC.
- Tests: 247 pytest, 112 cases, structural 0 (538 rule IDs).
- Open: 24 owner cards (below); needs PDF pages listed in the reports.

### 2026-10-12 — Phase 2 merged to master on Hussein's go (PR #22, 825e900)

Card "Merge, then phase 3". Master verified: 167 pytest, 112 cases, structural 0. PC clone: `git pull`.

### 2026-10-12 — Phase 2 follow-up answers coded (8 cards, 14:58Z)

- **F1** plant nursery prints only the Table 8.13 item 28 line (no Table 8.1 lines).
- **F7** Tables 3.15.a and 3.15.b print one S or NS column (values re-read on p.288, p.291).
- **F8** attached parking takes the parent building's sprinkler status for its columns.
- F2 robotic EH2 parking only, F3 densest-row default, F4 row 4.vi excluded, F5 mall OL on
  floor area: as coded. F6 per-storey per-use input: phase 3.
- Tests: 167 pytest (4 new in tests/test_phase2_followups.py, all fail without the change),
  112 cases, structural 0.

### 2026-10-12 — Phase 2 owner answers coded (24 cards, 12:29-12:30Z)

All 24 phase 2 cards answered on the recommended option; log
`phase2/ANSWERS_12.10.2026.md` (project files). Tests: 163 pytest, 112 cases, structural 0.

- **Ch 8:** 10.0 m / 20.0 m ceilings take the higher Table 8.14 row, required (Q3); a plant
  nursery prints no Table 8.14 / 8.15 lines (Q4); item 22 (vii) read as "shall not trigger
  the evacuation alarm", enclosed and (by analogy) open parking (Q6). Q1, Q2, Q5 as coded.
- **Ch 9:** plot GF BUA sum required for storage (app stops; engine blank = row 4 plus a
  NOT EVALUATED line) (Q1); 900 m2 and Group U small yard edges cited (Q2, Q3); assembly B/C
  LH with OH1 caption (Q5); robotic / mechanical parking forced HH + EH2 (Q7, parking only,
  pending a follow-up card); secondary storage needs its own hazard, else Table 9.27 NOT
  EVALUATED (Q9). Q4, Q8 as coded; Q6 (split animal housing) is phase 3.
- **Ch 3 / Ch 2:** largest storey area input, blank = GFA (Q1, replaces the interim bound);
  per-use (Table 3.13 row, m2) areas, blank = densest row, proxy occupancies "not evaluated"
  (Q2); mall GLA factor 2.8 / 3.3 + 0.1 per full 1,290 m2 / max 5.1 m2 (Q3); Table 2.7 overlap
  3/4 perimeter (Q4); building volume input (Q5); waterfront / theme park / tower set-back
  checkboxes (Q6); villas get Tables 3.1, 3.2, 3.4 (Q7); Table 3.16 single S or NS column (Q8);
  Ch 10 "Firefighting Lift (NOT mandatory)" gated on #2.9.4.a (Q9).
- Pages still needed: p.255 (Table 3.4 widths), p.324 (Table 3.28).
- Follow-up cards open: nursery general Table 8.1 lines; robotic box on a warehouse;
  densest-row default; Table 3.13 row 4.vi; mall OL area; storey bound; Tables 3.15.a/b
  columns; attached parking column.

### 2026-10-12 — Phase 2 (Ch 8, Ch 9 storage/hazards, Ch 3 + Ch 2) merged on the branch (draft)

Three packages built in parallel off master `f6ae7bb` and merged into
`claude/project-thread-0zjltx`. Package reports (every finding, direction of change):
`phase2/REPORT_ch8_12.10.2026.md`, `REPORT_ch9_...`, `REPORT_ch3_...` in the project files.
Tests: 139 pytest (64 + 16 Ch 8 + 37 Ch 9 + 22 Ch 3), 112 cases, structural 0.
Not merged: 24 owner questions are open (table below), and Ch 3 carries interim LESS-onerous
exit counts until Ch 3 Q1-Q3 are answered.

- **Ch 8** (17 findings): Table 8.1 general items (wiring, secondary power, audible/visual,
  MCP), PAS 15/180/240 s escalation, System Interfaces lines, permitted options shown as
  conditional, Civil Defence link per Ch 16 Table 16.1, converted villa row (item 14), new
  inputs `has_roof_restaurant_assembly`, `has_food_trucks`.
- **Ch 9** (34 findings): Table 9.27 storage rows A-U rebuilt (EH2, Groups F, K, L-O, P, R,
  S, T, U, hangar Groups I-IV); new inputs storage commodity, largest unit area, plot GF BUA
  sum, hangar group, aboveground tank storage, exterior balconies; the app stops until a
  storage hazard is chosen; hazard defaults per #1.1.13 (hotels LH to OH1, animal housing
  OH1 to OH2; assembly B/C, labour accommodation, detention to LH; mercantile B and enclosed
  parking to OH1); Table 9.29 rows B, F.i, G.ii, G.iii; Table 9.29.M starts above 10 m;
  tool-added text removed (VESDA, UL-300, NFPA 1/IFC).
- **Ch 3 / Ch 2** (20 findings): occupant load rounded up (#4.1.2), Table 3.14 per storey,
  OL by actual use for proxy occupancies, villa Tables 3.27/3.28, labour accommodation Table
  3.16 row 7, sprinkler status from Ch 9 (`engine.building_sprinklered`), #2.8.4.a 45 m
  rule for lowrise up to 15 m, Fire Lift and ECC lines, Table 2.1 and #2.5.1 items.
- export.py prints Table 3.14 exits "per storey".
- Grid diff vs master (6552 cases): no Fire Pump or Fire Water Tank line changes outside
  storage; every case gains the new general FA, FSA and FP lines.

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
| R1-R13, R2b | see audit and RULINGS_12.10.2026.md (project files) | ruled 12.10, merged (PR #21) |
| P2 Ch 8 Q1-Q6 | MCP 25/16 m, cold storage lines, ceiling 10/20 m edges, nursery, cable trays, item 22 (vii) | answered 12.10, coded |
| P2 Ch 9 Q1-Q9 | plot GF BUA sum blank, 900 m2 edge, Group U small yard, Table 9.29 H/I/J gate, assembly B/C LH, animal housing, robotic parking EH2, hotel G.ii/G.iii, secondary storage hazard | answered 12.10, coded (Q6 phase 3) |
| P2 Ch 3 Q1-Q9 | storey area input, OL by actual use, mall GLA, Table 2.7 overlap, volume input, site flags, villa tables, S/NS column, Ch 10 lift line | answered 12.10, coded |
| P2 follow-ups (8) | nursery Table 8.1 lines, robotic warehouse, densest-row default, row 4.vi, mall OL area, storey bound, Tables 3.15.a/b columns, attached parking column | answered 12.10 14:58Z, coded (F6 phase 3) |
| P3 cards (24) | Ch 10 Q1-Q4, Ch 11 Q1-Q7, Ch 4-7 Q1-Q3, storey Q1-Q4, app Q1-Q6 | answered 12.10 16:27Z, coded (App Q4 = phase 4) |
| P3 follow-ups (4) | cylinder new-building default, villa EAP, flame effect alarm, amusement vs Group C | open |
| R14 | #4.1.5 Lift Machine Room sprinkler in unsprinklered buildings (CH9A-09) | ruled 12.10: sprinklered only; coded |
| R14b | #4.1.5 for the other Table 9.30 rooms | ruled 12.10: all rooms (9.30.D needs none); coded |

Phase 3 is on the branch (draft PR); see the log entry.

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
