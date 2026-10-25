# HANDOFF — UAE FLSC Streamlit tool (uae-flsc-tool-02)

Cross-PC and cross-session resume point. Update after every change.
Code basis: UAE Fire & Life Safety Code 2018 (CDGH-OP-25). PDF page = printed page.
Audit: `AUDIT_UAE_FLSC_TOOL_12.10.2026.md` (189 findings, rulings R1-R13), kept in the
project files, not in this repo.

A push or merge to `master` redeploys the live app. Nothing merges without Hussein's go.

## Log (newest first)

### 2026-10-25 — Ch 6: highrise warehouse takes the height row only; one EL line cites every row (local branch, not pushed)

Rulings: Hussein 25.10.2026 12:37Z "Both A" (warehouses 23 m or taller: show one package) and
12:40Z "All A" (the height row governs; the one line cites both items). Branch
`fix-ch6-highrise-warehouse-el-25.10.2026` off master 5093e69 (the amusement fix, pushed by
Grok on Hussein's go 12:36Z; PR #32 to be closed by Hussein).
- Source: Table 6.5 p.419 read off the rendered page of
  `24.Fire Protection Mind map\UAEFIRECODE_ENG_SEPTEMBER_2018.pdf` (CDGH-OP-25, September
  2018, 1348 pages, MD5 563D41E3E9F41745441A042F57255BCD). That is NOT the library copy named
  in the Phase 5 entry (MD5 49a371a6...), which was not found under 04.CODES AND BOOKS.
  Items 1-4 (super highrise, highrise, mall, amusement): Central Battery (Section 3.2) OR
  Monitored Self-Contained (Section 3.3). Items 5-8 (midrise, low rise, warehouses,
  factories): Monitored Self-Contained only. The table and #4.1-#4.4 state no precedence
  between rows.
- (1) Warehouse / factory of 23 m or more: the height row (item 2, or item 1 above 90 m)
  governs; items 7-8 are not printed (`el_storage_industrial` gains `height_m_lt: 23`). This is
  the LESS restrictive reading: it permits Central Battery, which items 7-8 do not list; ruled
  by Hussein (option A), consistent with the Group C (items 11-12 below 23 m) and amusement
  (item 4 over items 7-8) rulings. Mixed buildings that list `storage_industrial` (R13 most
  restrictive) follow, since the listed occupancy runs the same rows.
- (2) Where two Table 6.5 rows print the identical line (height row + amusement, mall +
  highrise, mall + amusement), the one line kept now cites every row, e.g. "Table 6.5 items 2
  and 4", and its detail says each row requires the same package
  (`engine._el_cite_every_row`, Ch 6 only; the shared `_dedupe` is unchanged). Before, the
  line cited only the first row in the YAML (item 1, 2 or 3). Package unchanged.
  Limit: this works inside one `evaluate_el` run only; in R13 most-restrictive mixed mode
  `engine._merge_most_restrictive` still keeps the main occupancy's citation when two
  occupancies print the same line (e.g. storage_industrial + mall_covered at 30 m cites "item
  2" only; Business B + storage_industrial at 10 m cites "item 6" only); the package is right.
- Tests: 9 new pytest in tests/test_phase3_followups.py (8 failed before the change; the
  single-row citation guard passes both ways) and test case "EL: Highrise warehouse takes
  Table 6.5 item 2 only" (failed before). 360 pytest, 114 cases, structural 0 (549 rule IDs).
- Grid vs master (40 occupancies x 8 heights incl. 22.9 / 23 m x amusement x LH/OH1, each
  also with `storage_industrial` listed most restrictive = 2528 cases, 32 identical schema
  refusals): 984 change, EL only. 312 lose only the items 7-8 line (all at 23 m or more, no
  amusement: storage_industrial alone, 8; each other occupancy with storage listed, 8). 672
  change only the citation (648 amusement cases; 24 malls of 23 m or more, "items 2 and 3" or
  "items 1 and 3"). Case list: the session's grid_changed_cases.txt (not kept in the repo).
- Re-run issued jobs: warehouses / factories of 23 m or more; mixed buildings (most
  restrictive) that list storage_industrial, 23 m or more; reports where the cited Table 6.5
  item matters (amusement buildings, malls of 23 m or more).

### 2026-10-25 — Ch 6 warehouse EL: items 7-8 no longer stack onto item 4 (local branch, not pushed)

Ruling: Hussein 25.10.2026 11:07Z, card "FLSC Ch 6 warehouse EL bug: how to land the fix",
option A (fix on the PC clone in a local branch; push later via Grok on his go).
- Bug: a `storage_industrial` building with the amusement box ticked printed BOTH Table 6.5
  item 4 (Central Battery OR Monitored, `el_amusement_standalone`) and items 7-8 (Monitored
  Self-Contained, `el_storage_industrial`), p.419. Item 4 governs irrespective of primary
  occupancy (owner ruling 12.10.2026, P3 follow-up F-a2).
- Fix: `el_storage_industrial` carries `has_amusement_confounding_is: false`, the same gate as
  the midrise, lowrise and Group C rows; the same logic as PR #32
  (cursor/critical-bug-detection-58f0), comment wording differs.
- Tests: `test_F_a2_amusement_warehouse_keeps_table_6_5_item_4` (pytest) and test case "EL:
  Warehouse with amusement stays on Table 6.5 item 4" with a new `expect_el_absent` check; both
  failed before the YAML change. 351 pytest, 113 cases, structural 0 (549 rule IDs).
- Grid (40 occupancies x 5 heights x amusement x LH/OH1 = 800 cases vs master 33ab682): 10
  change, all `storage_industrial` with amusement, each losing only the items 7-8 line.
- Independent verifier: CLEAR (2,344-case grid; only `storage_industrial` + amusement
  changes, item 4 kept).
- Re-run issued jobs: warehouses / factories with the amusement box ticked, and mixed
  buildings (most_restrictive mode) that list `storage_industrial` as a secondary occupancy
  with the amusement box ticked (10 such cases in the verifier's grid change too).
- Seen, not changed (needs a ruling): a warehouse / factory of 23 m or more still prints the
  highrise row (items 1-2, `el_highrise`) and items 7-8 together.
- Open note, no code change (predates this fix, all occupancies): at 23 m or more the
  surviving "Central Battery OR Monitored" line cites Table 6.5 item 2 (`el_highrise`), because
  the engine keeps the first of two identical lines; the required package is right, only the
  clause shown differs (item 4 is not cited when amusement is ticked).
- PC clone: master fast-forwarded 8e752d0 to 33ab682; the 3 files shown modified (eap.py,
  occupant_load.py, submission_checklist.py) were byte-identical to 8e752d0 (stale index stat
  only), so nothing was parked; branch `hussein-pc-edits-25.10.2026` marks 8e752d0.

### 2026-10-13 — Phase 5: 2018 page gaps closed (10 cards, 05:23-05:45Z, all option A)

Card "Close gaps" (05:23Z). Every deferred page read off the rendered 2018 PDF (library copy,
MD5 49a371a64bd689216f9443a0f91b10e4). Reports: project files `uae_flsc_tool/phase5/`.
- CH9D-15 "Pointer lines": FP block "Testing, Inspection and Maintenance (Ch 9, Section 5)",
  one line per required system type: Tables 9.32 pumps, 9.33 standpipes and hose, 9.34
  sprinkler and deluge, 9.35 foam, 9.36 clean agent (p.758-769); rows not itemised.
- Class A (no verdict change): Ch 2 #2.6.6 / #2.8.1 / #2.6.8 citations; door forces wording
  (p.249); Table 5.1 sub-item numbers; #8.1.9 cable test standards (p.425); Table 9.30 R-V
  printed text (p.755); Table 9.28 B Class III riser (p.748); Groups B/C not-required riser
  lines (p.725-726); Table 9.14 item 3.ii (p.675, not p.674); Table 10.25 rail under 90 m and
  cable rows (p.863).
- Ch 2-3 "Add all 9" + G6 "Fire lift buildings" + G12 "Add item 4.iii": fire engine 2 m to
  10 m (#2.8.2); 1 m inspection pathway (#2.6.7); turning facility (#2.7.1-#2.7.4); super
  highrise lift lobby (#2.9.5); #2.9.6 fire exit stair where a fire lift is required;
  fireboat berth on the waterfront tick (#3.2, Table 2.9); Table 3.4 widths 1200 / 1420 mm as
  text; Table 3.28 commercial villa; Tables 3.22 item 7 / 3.23 item 6 smoke compartments;
  Table 3.37 item 4.iii ramp allowance (LESS onerous).
- Ch 5-8 "Add all": directional sign chevron (p.389); 30-day illumination check (#4.4,
  p.400); 5% central battery spare capacity (Table 6.2 item 4.ii, p.413); EVC Civil Defence
  equipment "collocated" (Table 7.2 item 1, p.437); FA power sources (Table 8.1 item 15
  i-x, p.461).
- Ch 9: Group I split into two rows (p.732): under 3600 m2 750 gpm @ 4.5 bar, 60 min (LESS
  onerous); 3600 m2 and above 1250 gpm @ 6.9 bar, 90 min, hydrant loop required (MORE).
  Exactly 3600 m2 takes row 2 in Groups D, E, I, J ("Higher row"); the blank-sum NOT
  EVALUATED note no longer prints at a ground floor of exactly 3600 m2. Nursery keeps the
  #4.1.6 hydrant lines; "no fixed water-based system" wording removed.
- Ch 10: rail tunnels over 90 m state jet fan OR ducted purge OR CFD-justified (LESS
  onerous, rail only). Table 10.26 item 2 line (renamed sc_aux_hazardous_chemical_room) fires
  on the chemical warehouse / bulk flammable storage ticks with Section 2.20 / Table 10.18
  values, not on LPG tanks (LPG-only buildings lose it).
- Re-run issued jobs: Group D/E/I/J storage at exactly 3600 m2 or Group I at any size; LPG
  tank buildings; rail tunnels; buildings with chemical or bulk flammable storage.
- Tests: 350 pytest (47 new in tests/test_phase5*.py), 112 cases, structural 0.

### 2026-10-13 — Phase 4 merged to master on Hussein's go (PR #24, 2f4aee2)

- Card "Merge now" (05:12Z). Head 150d037 re-verified before merge: 291 pytest, 112 cases,
  structural 0; master tree identical to the PR head. The live app redeploys from master.
- Re-run issued jobs whose results changed: post offices (now OH2), kiosks entered as Mercantile
  A/B (now Mercantile C, Table 9.21.b), saved Business files (stop until a group is chosen).
  PC clone: git pull.

### 2026-10-13 — Phase 4 defaults confirmed (4 cards, 02:52Z, all option A)

Hussein confirmed the four defaults picked while coding phase 4; no code change (PR #24 already
does each): kiosk area read from the GF BUA, stop above 18 m2 (item 48 v); a Business listed as
another occupancy keeps Table 6.5 items 5-6; Mercantile C refused as another occupancy and cannot
list others; trucks get Table 6.5 item 12. Default 5 (item 48 iii blank = NOT EVALUATED) follows
the standing rule that a blank never counts as a pass.

### 2026-10-13 — Phase 4: Mercantile Group C and Business Groups A/B/C (6 cards, 00:49Z, all option A)

Log: project files `uae_flsc_tool/phase4/ANSWERS_13.10.2026.md`; scope `SCOPE_phase4_13.10.2026.md`.
- Q1 Business: required A/B/C selector, no default (`business_group`). Group C = Table 6.5 item 11
  (p.419) below 23 m. No group: the app stops by name; the report prints the Ch 6 system type
  NOT EVALUATED. A Business listed as another occupancy (R13) has no group input and keeps the
  height row (items 5-6, the more onerous), named. Old "Business Group C (stand-alone)" tick is
  not carried into the group; the stop names it.
- Q2 hazard: LH for every group; "Post office" (Group B only) = OH2 (#1.1.13.3.c, p.529).
- Q3 Mercantile C: OH1, override available.
- Q4 new occupancy `mercantile_c`: midrise Table 9.20.b row C (p.701); lowrise Table 9.21.b by
  inference (cited on every row line) plus Ch 1 Table 1.9 item 48 (p.98) lines i-v; item 48 iii
  sprinklers needs the new kiosk location input (blank = NOT EVALUATED; yes = sprinklered building).
- Q5 type required: kiosk permanent / temporary (temporary adds Table 8.14 item 31), food truck,
  mercantile truck. Trucks keep Ch 4 (as mercantile), Ch 8 item 34 / 35 (p.511), Ch 6 item 12
  (default picked: Table 6.5 names Mercantile Group C) and Ch 11 (Table 11.3 when LPG); every
  other chapter "Not applicable" by name. No type: every chapter NOT EVALUATED. Mercantile C is
  refused as a listed other occupancy and cannot list others (default picked). App: kiosk area
  (GF BUA) above 18 m2 stops (item 48 v).
- Q6 old files with the "Mercantile Group C (stand-alone)" tick load, then stop by name until the
  tick is cleared or the occupancy is set to Mercantile C.
- Ch 3 / 4 / 5 / 7 mercantile rows and Table 3.13 row 13 now include Mercantile C (printed without
  a group).
- Grid vs master (6552 cases): only Ch 6 changes. Business with no group: EL type NOT EVALUATED
  (72 cases). Business with a group, Mercantile A and B: the conditional "Group C only" prompt is
  gone (72 cases each). Pump, tank, sprinkler, FA lines unchanged. 168 new mercantile_c cases, 0
  errors.
- Tests: 291 pytest (16 new in tests/test_phase4.py, 4 re-pointed from the two ticks; app tests
  that use Business now choose Group B), 112 cases (1 re-pointed), structural 0.

### 2026-10-13 — Phase 3 merged to master on Hussein's go (PR #23, eb9faa9)

- Card "Merge, then phase 4" (00:29Z). Master verified: 275 pytest, 112 cases, structural 0;
  tree identical to the PR head 8950da0. The live app redeploys from master.
- Re-run issued jobs whose results changed (PR #23 body lists them). PC clone: git pull.
- Branch restarted from master for phase 4: Mercantile Group C and Business Groups A/B/C.

### 2026-10-13 — Phase 3 last two follow-up answers coded (2 cards, 00:08Z)

- F-a4-1 "All occupancies": the #3.2.2 (p.923) indoor flame-effect sprinkler condition is checked
  on every R13-listed occupancy (each at the R13 hazard class); each unsprinklered one is named,
  and a listed storage / animal housing with its Ch 9 lines NOT EVALUATED is named, never passed.
  More onerous (example: 12 m mercantile + business now stops). The report line now reads the
  whole R13 building, as the app stop already did: 24 of 540 R13 check cases (sprinklered
  enclosed parking listed with an occupancy that needs automatic detection) lose a "NOT
  allowed" line text that contradicted the stop (F-a1-3 rule unchanged).
- F-a4-2 "Refuse it": parking depth above 0 m with 0 parking basement levels is refused (schema
  validator + named app stop).
- Engine: `_r13_base` / `_r13_single` factored out of `evaluate()` (no result change: 6552-case
  grid 0 differences); `_R13_SOURCE` context for the flame line in R13 sub-runs.
- Tests: 275 pytest (2 new, both fail without the change), 112 cases, structural 0.

### 2026-10-12 — Phase 3 follow-up answers coded (5 cards, 17:07Z)

- Cylinders: "new or modified / existing" is a required choice with no pre-fill (app stops,
  report NOT EVALUATED); new without CD approval still stops (#2.2.4-#2.2.5 p.884).
- Villa written EAP: conditional, like the villa drills (p.1233 unread).
- Indoor flame-effect show also stops when Ch 8 does not require automatic detection (#3.2.2
  p.923); sprinklered parking is newly stopped (Table 8.13 item 22). FA results unchanged.
- Attached parking depth input (#1.7.45); blank = building depth, named in the report.
- Amusement + Group C: Table 6.5 item 4 governs (cite only).
- Tests: 273 pytest, 112 cases, structural 0. Two more cards open: flame-effect sprinkler check
  across R13 occupancies; parking depth with 0 levels.

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
| P3 follow-ups (5) | cylinder new-building default, villa EAP, flame effect alarm, amusement vs Group C, parking depth | answered 17:07Z, coded |
| P3 follow-ups (2) | flame-effect sprinkler check across R13 occupancies; parking depth with 0 levels | ruled 13.10 (All occupancies; Refuse it), coded |
| P4 Q1-Q6 | Business group form and hazard, Mercantile C hazard, lowrise kiosk row, Mercantile C type, old files with the Group C tick | ruled 13.10 00:49Z (all option A), 4 coding defaults confirmed 02:52Z (option A), coded on PR #24 |
| P5 (10 cards) | CH9D-15 Section 5, Ch 2-3 additions, #2.9.6 scope, Table 3.37 4.iii, Ch 5-8 additions, Group I split, 3600 m2 edge, nursery hydrants, rail tunnel routes, Table 10.26 item 2 | ruled 13.10 05:23-05:45Z (all option A), coded on PR #25 |
| Ch 6 warehouse EL | how to land the items 7-8 vs item 4 fix (PR #32 bug) | ruled 25.10 11:07Z option A, coded on local branch fix-ch6-warehouse-el-25.10.2026, push via Grok on Hussein's go |
| Ch 6 highrise warehouse EL | items 1-2 and items 7-8 both print at 23 m or more | ruled 25.10 12:37Z / 12:40Z option A (height row governs, less restrictive reading), coded on branch fix-ch6-highrise-warehouse-el-25.10.2026 |
| Ch 6 item 4 citation at 23 m+ | surviving Central Battery OR Monitored line cites item 2 (el_highrise), not item 4, when amusement is ticked (first of two identical lines kept; package right) | ruled 25.10 12:40Z option A (cite every row), coded on the same branch |
| R14 | #4.1.5 Lift Machine Room sprinkler in unsprinklered buildings (CH9A-09) | ruled 12.10: sprinklered only; coded |
| R14b | #4.1.5 for the other Table 9.30 rooms | ruled 12.10: all rooms (9.30.D needs none); coded |

Phases 1-4 are on master; phase 5 is on draft PR #25 (see the log entry).

## Known, not fixed in phase 1

- (Phase 3 closed the tilde / approximately-sign sweep and the villa 9.23 vs 9.21.d repeat.)
- Group V plant nursery above 3600 m2 prints "Portable Fire Extinguishers (only)" and a
  not-required fire pump beside the required #4.1.6 hydrant line (left as is in phase 5).
- Scenario matrix "!!" gaps are unchanged from master.

## Verify

```
python3 -m pytest tests/ -q
python3 tests/test_cases.py
python3 _structural_check.py
```

*Last updated: 2026-10-25*
