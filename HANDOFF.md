# HANDOFF — UAE FLSC Streamlit tool (uae-flsc-tool-02)

Cross-PC and cross-session resume point. Update after every change.
Code basis: UAE Fire & Life Safety Code 2018 (CDGH-OP-25). PDF page = printed page.
Audit: `AUDIT_UAE_FLSC_TOOL_12.10.2026.md` (189 findings, rulings R1-R13), kept in the
project files, not in this repo.

A push or merge to `master` redeploys the live app. Nothing merges without Hussein's go.

## Log (newest first)

### 2026-10-28 — Owner rulings on the 12 open items of the audit fix round ("all as recommended")

Hussein 28.10.2026: all 12 as recommended. Recorded only; no code changed in this entry.
No code change needed (current output already matches): 2 labour / staff accommodation / hostel
2.5 kg kitchen extinguisher stays required; 3 robotic logistics warehouse 23 m+ keeps the note;
4 Ch 2 #2.10 yard hydrants / hose cabinets stay conditional, Ch 9 governs; 7 villa EAP and
accessibility stay conditional; 8 kitchen ventilation in parking 23 m+ stays conditional;
9 highrise open parking keeps the Table 10.20 corridor line; 12 blank-input exemptions and
preset values as coded. 11 Dubai ESL note: Hussein to check the wording against the issued
document (no code until then).
TO CODE in a fresh session (each with failing-first tests, grid diff, HANDOFF entry):
1. Converted villa (villa_converted_use): Class A extinguishers per the new use's Table 4.3
   row 1 item (drop the villa "recommended" line; Ch 4 L11).
5. Unsprinklered hospital sleeping areas (Table 3.16 row 4.i prints S only): sprinklers
   required; replace the NOT EVALUATED line with a required line.
6. Table 3.32 item 2 (p.331): 1525 mm corridor always; 1 h rating only if unsprinklered.
10. R-G for Groups T / U: the hazard-class rows A-J apply only as conditional ("enclosed
   buildings on the site"), as R-B.

### 2026-10-28 — Audit 28.10.2026 fix round: all findings, rulings R-A to R-J, Q-1 to Q-4 (PR #38, draft)

Audit: `AUDIT_UAE_FLSC_TOOL_28.10.2026.md` (15 HIGH, 53 MEDIUM, 87 LOW; source = the HTML reading copy
of CDGH-OP-25 Sept 2018 committed in 975ea96, split per page; Ch 1-11, 15, 19, Annex 1-2, app / exports;
16,078-building scenario sweep; Cursor PRs #1-#37 re-tested). Kept with the project files, not in
this repo, with the per-chapter ledgers. Branch `claude/vibrant-edison-l0fscc`, draft PR #38.
Nothing merged to master (the live app is unchanged until Hussein's go).

Owner rulings 28.10.2026 (cards, all on the recommended option):
- R-A ECC 1 h sprinklered / 2 h unsprinklered (Ch 1 Table 1.9 item 1 p.73, FAQ Q8 p.1273; Ch 2
  #2.9.3.c p.219 named as the conflict).
- R-B Groups T (aboveground tanks) / U (open yard): Ch 5 / 6 / 7 / 8 / 10 warehouse packages stay as
  CONDITIONAL "applies to any enclosed building on the site"; Cursor PRs #28-31, #33-37 not merged.
- R-C Table 9.21.e outlet AND the host Table 9.21.a / 9.21.b row both apply; most onerous governs.
- R-D Table 10.27 item 16.iii kitchens: required in malls, hospitals, highrise non-residential;
  conditional for apartment / hotel-room kitchens.
- R-E Diesel generator room: Table 9.31.E governs regardless of sprinklers.
- R-F Mixed most-restrictive mode: one EL package (#4.2), one FA protocol (extends R7), one EVC line.
- R-G Specialty storage tick and hazard / commodity rows both evaluated; most onerous governs.
- R-H Detention 23 m or more: Table 9.19 + conditional note on Table 9.20.d. R-J 90.0 m stays 9.19 +
  note. R-I Robotic parking: Table 8.13 item 23 detection + item 22 notification / interfaces.
- Q-1 #4.1.7 G+3 trigger kept + pump-sizing warning (#4.1.9). Q-2 Group R also gets the Table 4.3
  wheeled foam. Q-3 one governing pump / tank for host + attached parking (#4.1.17). Q-4 storage
  tenancy is a required choice, no default.

Lead-session changes (this branch, besides the six fixer merges listed below):
- R-F in `engine._merge_most_restrictive`: `_r13_one_el_package`, `_r13_one_fa_protocol`,
  `_r13_one_evc_package` (mixed grid 2520 pairs: FA / EL / EVC change only).
- UX-03: `Requirement.status` gains `not_evaluated`; `engine.evaluate` marks every "... - NOT
  EVALUATED" line (engine builds them as required internally, so no gap is taken as a pass); app
  badge / legend / status bar, "Report incomplete" warning, REPORT INCOMPLETE block in every PDF /
  Word export; 28 test assertions in 11 files moved from "required" to "not_evaluated".
- R-B consistency: Ch 8 Table 8.1 lines conditional for Groups T / U (Table 8.15 item 3 stays
  required).
- F9A-03 completed: blank plot NOT EVALUATED for Tables 9.18 / 9.19 / 9.20.a / 9.23.B.
- Q-4 wiring: Ch 8 FACP lines read `storage_tenancy`; app radio "Storage tenancy (required)",
  named stop, legacy `is_single_tenant_storage: true` loads as single.
- README: exactly 23.0 m is highrise (R1); "#" for clauses.
- Commit message correction: 13cb240 says 561 pytest; measured 559.

Verification at the HANDOFF entry (282d45a): 590 pytest, 115 cases (tests/test_cases.py),
_structural_check no errors / warnings. Full grid vs 4b69f4f (grid 9870, flags 832, storage 2856,
mixed 2520): 0 crashes, 0 new refusals; every removed required line traced to a finding or ruling
(renamed lines, required -> conditional per the code's "permitted / where", R-B / R-F / Q-4 /
blank-input NOT EVALUATED, infrastructure no building FA, trucks no room extinguishers).
Independent verifier (read-only, base 4b69f4f vs HEAD, 6,544 buildings, all HIGH + 41 MEDIUM
findings traced to page text): round 1 on 24e6579 NOT CLEAR (5 items), round 2 on fbfdd08 NOT
CLEAR (1 residual), round 3 on 390c1dd CLEAR: 603 pytest, 115 cases, structural 0, 0 crashes,
every removed / demoted required line (124) justified. Fixed between rounds: secondary storage
tenancy input + stop; conditional NOT EVALUATED lines -> not_evaluated; sprinkler-gated Table
9.29 / 9.30 lines NOT EVALUATED when any Ch 9 input is missing and no sprinkler line is
required (blank outlet area stops in the app); unranked pump / tank lines name each other;
R-D hotels' own kitchens required; attached parking carries the cinema kind / flame-effect
show / new-or-modified choice; complete first-load sample and presets. Cursor Bugbot on PR
#38: 4 findings, all real, all fixed with failing-first tests (villa EL line in mixed mode,
lone parking duty, exports counting NOT EVALUATED as required, blank tenancy gating).
Verifier note (accepted, not changed): a blank tunnel length also marks the gated Table 9.29 /
9.30 lines NOT EVALUATED (over-cautious, never a pass). Report: VERIFY.md with the project files.

Open for Hussein (needs a ruling; each is a conditional / note line now, routing unchanged):
1. Converted villa Class A extinguishers (Ch 4 L11). 2. Labour / staff accommodation / hostel keep
the 2.5 kg homes-kitchen line required (M5 applied to hotels only). 3. Robotic logistics warehouse of
23 m or more: no printed protocol (Ch 8). 4. Ch 2 #2.10.1.a yard hydrants "mandatory in all
developments" and #2.10.3.a hose cabinets "in all buildings" (wider than Ch 9; conditional now).
5. Unsprinklered hospital sleeping areas: Table 3.16 row 4.i prints S only (NOT EVALUATED now).
6. Table 3.32 item 2: does "if not sprinklered" govern the 1525 mm width too? 7. Villa EAP and
accessibility scope (Ch 19 #2.1.1, Ch 15 #2.2.1 print no villa exclusion or inclusion).
8. R-D for parking of 23 m or more (conditional now). 9. Ch 10 highrise open parking: Table 10.20
item 4 corridor line kept over Table 10.23 item 2.2.i. 10. R-G for Groups T / U (hazard rows are
building rows). 11. Dubai ESL pump note wording (scanned source). 12. Blank-stop exemptions (trucks:
plot; underground: GF BUA when basement BUA given) and preset values listed under Assumptions.
13. Cursor PRs to close (none merged): fixed on master #1, #4-#10, #12, #15, #16, #32; against
ruling / print #2, #3, #11, #13, #17; ported here #18, #19, #27; superseded by R-C #26; R-B #28-31,
#33-37; R-I #14.

Re-run issued jobs (all chapters gained lines; most significant): every report (fire pump set =
1 electric + 1 diesel + 1 jockey, Table 9.3 item 1.xii); enclosed parking (CO detection); unsprinklered
buildings with an ECC; theme parks; Group R / T / U storage; storage with blank GFA; business / mosque
with an outlet; Table 9.21.f row F; high-ceiling warehouses; HH storage without EH2; highrise
kitchens; LPG tanks and flame effects; attached parking (one pump / tank); mixed most-restrictive
jobs; any job with plot, GF BUA or GFA left blank (now NOT EVALUATED / stop).

#### Fixer notes (one per area, as delivered; branch names are the worktree branches merged above)

##### 2026-10-28 - Audit fix round, area ch123 (Ch 1 / Ch 2 / Ch 3 / Ch 15)

Ledger findings/CH01-03.md CH123-01 to CH123-25, audit H1 (CO detection) and H2 = CH123-02.
Rulings applied: **R-A** (ECC 1 h sprinklered / 2 h not). Earlier rulings kept: R1 (23.0 m
highrise, CH123-14 no change), R9 (open podium NS 91 m, CH123-13 no change), Ch3 Q2 (densest
row), Ch3 Q7 (Tables 3.1 / 3.2 / 3.4 on villas), P3 Ch11 Q2 (villa wheelchairs conditional).
Branch `worktree-agent-a6bfc0e57c0459928`.

Changes (finding, page, direction):
- **H1 / CH123-01** Table 3.37 item 7.i (p.338): required "Carbon Monoxide Detection - Enclosed
  Parking" on `moe_parking_enclosed` (stand-alone and the attached enclosed parking sub-run).
  MORE onerous. Ch 10 cross-reference left to the Ch 10 fixer.
- **H2 / CH123-02 (R-A)** fsa_ecc: "1-hour fire barrier" when Ch 9 sprinklers the building,
  "2-hour" when not; cites Ch 2 #2.9.3.a-e, Ch 1 Table 1.9 item 1 (p.73), FAQ Table A.1.2 Q8
  (p.1273); detail names #2.9.3.c (p.219) as the conflict. MORE onerous (unsprinklered).
- **CH123-03** HH storage without the EH2 tick (Extra Hazard Group 1 = Storage / Industrial
  Group B, #1.1.13.4.a p.529) now takes Table 3.13 rows 16 / 18 (stair 7.6 mm) and Table 3.16
  rows 17 / 19 (S 30/30/122 m, NS 15/15/61 m): new branch `moe_storage_industrial_eh1`;
  `moe_storage_industrial_high_hazard` (rows 15-18 Group A, 18 mm) needs EH2 (#1.1.13.5.a,
  p.530). occupant_load `_STORAGE_ROWS` keyed on HH and EH2. LESS onerous for EH1 (as printed).
- **CH123-04** daycare groups by use (Table 1.1 row 10, p.50; #1.1.13.1.k-l, p.527): OCCUPANCY_DEFS
  daycare_a / _b text; daycare_c relabelled "Daycare (group not printed)"; YAML comments and
  detail rewritten. Neutral.
- **CH123-05** unsprinklered hospital: spec_ns says the sleeping-area limits are not evaluated,
  plus a NS-only "... (Hospital Sleeping Areas, Non-sprinklered) - NOT EVALUATED" line (p.293).
  MORE onerous (was silent).
- **CH123-06** Table 3.24 items 1-7 on `moe_residential` (+ item 2 single exit stair: required with
  `has_single_exit_stair`, conditional without); new branches Table 3.25 (staff accommodation,
  hostel; item 6 smoke compartments over 2000 m2 required / conditional pair) and Table 3.26
  (labour accommodation) (p.317-322). MORE onerous.
- **CH123-07** Table 3.30 hotel items 1-12, Table 3.31 daycare items 1-7 (item 7 Group A with 3+
  floors required; daycare_c conditional), Table 3.32 mercantile items 1-6 (new branch
  `moe_mercantile_table_3_32`; parking separation required with `has_parking_area`), Tables
  3.20 item 5-6 / 3.21 item 4 and 7 (93 m2 rooms conditional; rescue windows NS only)
  (p.305-332). MORE onerous.
- **CH123-08** Table 3.37 items 1, 5 (conditional), 6, 8 (required) on enclosed and open
  parking; item 3 on new branch `moe_parking_robotic` (p.338). MORE onerous.
- **CH123-09** Table 3.4 item 7 (block-work lowrise low depth / RCC otherwise, 2 h, 3 m above top
  landing, no common lift shaft) and item 8 (penetrations, no FHR / landing valve cabinets in
  stair) as general lines (p.259). MORE onerous.
- **CH123-10 / CH123-23** robotic OLF line only with `has_robotic_parking`; robotic parking OL
  takes Table 3.13 row 20.i 46.5 m2 (was 27.9) and Table 3.16 row 21 (S 60 / NS 46 m) is printed.
  OL LESS onerous (as printed), travel 1 m MORE onerous.
- **CH123-11** fire lift: #2.9.4.i (passenger lift recall, doors open) and #2.9.4.l (BS EN 81-72
  5.3, 5.6-5.12) added, cite #2.9.4.a-l (p.220). MORE onerous.
- **CH123-12** #2.10.1-#2.10.4 (p.222-224): yard hydrant (conditional), breeching inlets
  (required with sprinklers or wet riser), FHC (required with wet riser), pump room access
  (required with water system + pump room). Ch 9 holds no #2.10 lines; no Ch 9 duty repeated.
  MORE onerous.
- **CH123-15** open-parking definition line has a spec (Table 3.37 item 2, Table 1.9 item 34).
- **CH123-16** HH mercantile detail: swing only, no panic-hardware claim (p.248, 250).
- **CH123-17** Table 3.19 permission printed with its limits (4570 mm, 280 m2, other stories,
  S 30 / NS 23 m mezzanine); "over-provisioning" text removed. MORE onerous.
- **CH123-18** private villa Table 3.27 item 1 (conditional).
- **CH123-19** waterfront lowrise private villa takes the Table 2.8 lowrise row (60 m).
- **CH123-20** #2.4.4 gate locks in the gateways line; #2.6.4 / #2.6.5 conditional line;
  #2.3.1 100 m2 exemption in the width detail.
- **CH123-21** lowrise (#2.8.4.a): "Fire access road width + clearance", accessway not required.
- **CH123-22** villa Ch 15 scope wording per #2.2.1 (p.1090); stale "not yet read" removed;
  status stays conditional pending a ruling.
- **CH123-24** Table 3.13 parking row labels name both letterings (Table 3.13 vs Table 1.1).
- **CH123-25** general lines: Table 3.3.a door ratings, Table 3.3.b unit doors by occupancy
  (office / classroom S/NS), Table 3.6 (required with `has_horizontal_exits`, else conditional),
  3.7, 3.8, 3.9 (conditional), 3.11 (required with `has_evacuation_elevator`, else conditional),
  3.12 exit discharge (S/NS columns). Not on villas. MORE onerous.
- CH123-13, CH123-14: rulings R9 / R1 stand; no change.

Tests: new tests/test_audit28_ch123.py (40 tests; 35 RED before the change, 5 guards green).
Updated in place: tests/test_cases.py "Storage HH -> 0m ..." and "HH storage uses 18mm" now set
`is_extra_hazard_2=True` (+ new EH1 case expecting `moe_storage_industrial_eh1`);
tests/test_phase2_ch3_answers.py::test_CH3_Q6_site_flags_print_required_lines_only_when_ticked
checks only the site-flag lines for conditional status. Counts: pytest 400 passed (was 360), test_cases 115 passed
(was 114), structural no errors / no warnings. Grid diff vs master (4 grids, 16,078 cases): 0 crashes;
fingerprint changes only MOE branch HH storage -> moe_storage_industrial_eh1 (714 storage, 2 mixed)
and +1 NOT EVALUATED line on 4 unsprinklered healthcare_a cases. Full-item diff on a 5,256-case
sample: only the MOE, FSA and ACC (villa) chapters change; no other chapter, no occupant-load change.

Needs ruling: #2.10.1.a yard hydrants "mandatory in all developments" vs Ch 9 triggers;
#2.10.3.a FHC "in all buildings" vs Ch 9 rows; unsprinklered hospital sleeping areas (S values
or sprinklers); villa Ch 15 items / wheelchairs now that #2.2.1 is read; Table 3.32 item 2
"if building is not sprinklered" scope.

Re-run issued jobs: any job with an enclosed parking (CO line), an ECC in an unsprinklered
building, HH storage without EH2, an unsprinklered hospital, robotic parking (OL), and every
report for the added Ch 3 / Ch 2 lines.

##### 2026-10-28 — Fix round 28.10.2026, area ch47: Ch 4-7 (CH04-07 H1-H3, M2-M6, L1-L11; rulings R-B, Q-2) (worktree branch `worktree-agent-af1b579f2c853c6ab`, commit 1612156, not pushed)

Rulings applied: R-B (Groups T / U keep the Ch 5 / 6 / 7 warehouse packages as conditional,
with the R-B wording), Q-2 (Group R also gets the Table 4.3 row 3 item 2.i wheeled foam line).
Standing rules: a blank never passes (H3, M2 NOT EVALUATED lines); direction stated per item.
Not changed: M1 (mixed EL, lead under R-F), RT1 / RT2 (ruled, info only). Every page re-read
from scratchpad/pages before writing.

Ch 7 (rules/ch7_evc.yaml, engine.evaluate_evc + new `_evc_one_package`, `_mixed_evc_not_evaluated`)
- H1 (p.439 Table 7.3 item 5 "AMUSEMENT AND THEME PARKS"): `evc_amusement` matches
  `is_theme_park` OR `has_amusement_confounding`. MORE onerous (theme park ticked: EVC + two-way
  now required, e.g. infrastructure, business, storage, villa).
- H3 (p.439 item 9 "BUILT-UP AREA MORE THAN 5000 m2"): item 9 rows key on
  `Building.storage_total_bua_m2` (larger of GFA and GF BUA). Both blank below 23 m: new
  required line "Emergency Voice Evacuation (EVC) - Storage / Industrial - NOT EVALUATED"
  (`evc_storage_industrial_bua_not_evaluated`). MORE onerous (GFA blank, GF BUA 8000 m2 was
  "not required").
- M2 (p.439): `mixed_multiple` with no occupancy listed (not an R13 run) and no Table 7.3 row
  requiring EVC: "Emergency Voice Evacuation (EVC) - NOT EVALUATED" (source
  `audit28_m2_mixed_evc`), same rule as Ch 4 Class A (P3 Ch47 Q2). MORE onerous (was "not
  required"). At 23 m or more the highrise row still prints EVC required.
- L1 + Cursor PR #19 + sweep class 3: Table 7.3 prints one requirement for all nine rows; one
  EVC line and one two-way line, citing every matching row ("Table 7.3 items 2 and 9", "items 4
  and 5"), each row's detail kept; a not_required "not listed" row or the item 9 NOT EVALUATED
  line no longer prints beside a row that requires EVC. The amusement row's EVC line now has
  the standard name "Emergency Voice Evacuation or Communication System (EVC)". Neutral
  (package unchanged). Limit: in R13 most-restrictive mode `_merge_most_restrictive` still
  keeps two EVC lines when two occupancies' merged specs differ (e.g. residential + mall at
  30 m); the lead may call `_evc_one_package` on the merged Table 7.3 block.
- L2 (p.436 Table 7.1 item 10.i prints "maximum of 122 mm"): detail states the tool reads it as
  1220 mm (Table 7.2 item 5.ii p.438). Neutral.
- L3 (p.433 item 3, p.434 item 4.1 "shall be permitted"): PAS and sleeping-risk tone lines
  conditional. LESS onerous (wording; they were never requirements).
- L4: new general lines (only where EVC is required): #2.2.5 automatic response (p.431); Table
  7.1 item 2.2 microphone instructions (p.433); item 7.1 i-iii control system (p.435); item 8
  ancillary functions incl. 8.iii annual test (p.435, conditional); #5.1 / Table 7.4 acceptance
  intelligibility (p.441, with #4.3.2 p.440); #4.4.1-#4.4.2 inspection per Ch 8 (p.440). MORE.
- M6 / R-B: Ch 7 lines of a storage building with `is_open_yard_storage` or
  `is_aboveground_tank_storage` become conditional with "Applies to any enclosed building on the
  site (warehouse, pump house, office). Ch 7 prints no row for open yards / aboveground tank
  farms (owner ruling R-B, 28.10.2026)." (`engine._rb_yard_tank_conditional`; NOT EVALUATED and
  not_required lines untouched). LESS onerous vs master (required -> conditional), as ruled.

Ch 6 (rules/ch6_emergency_lighting.yaml, engine.evaluate_el)
- M6 / R-B: same conversion, "Ch 6 prints no row ...". LESS (as ruled).
- L5 (p.408 Table 6.1 item 1.ii-iv, 1.viii; p.420 Table 6.6): coverage line renamed
  "Mandatory EL Coverage Locations (Table 6.6 items 1-27 + Table 6.1 item 1)", cites both, lists
  the Table 6.6 items as printed (incl. "large plant rooms"). Neutral.

Ch 5 (rules/ch5_exit_signs.yaml, engine.evaluate_es)
- M4 (p.397 item 6.vi; Table 1.1 p.48 Assembly Group B items 1 "Amusement Park", 7 "Indoor
  Kid's Play Areas"): strips line fires on `is_theme_park` too; Assembly Group B with neither
  box ticked gets the same line as conditional (`es_assembly_b_amusement_photoluminescent`). MORE.
- M3 (p.399 item 15.ii): strips line also fires in a storage building on `is_cold_storage`,
  `has_cable_spread_areas`, `floors_below_grade` > 0 or `basement_bua_m2` > 0 (robotic storage
  and HH areas stay on the existing HH box, whose label already names them). MORE.
- M6 / R-B: same conversion, "Ch 5 prints no row ...". LESS (as ruled).
- L7 (p.387 #2.2.5, p.390 Table 5.1 item 4, p.401 #5.1.5): "Photoluminescent Sign
  Specifications (UL 1994)" conditional (where used or required), cites #5.1.5 / p.401. LESS
  (wording).
- L9 (p.395 Table 5.2 item 3 VISIBILITY): new required universal line `es_g_visibility`. MORE.

Ch 4 (rules/ch4_fire_extinguishers.yaml, engine.evaluate_fe)
- H2 + Q-2 (p.376 row 3 item 2.i): `fe_class_b_wheeled_bulk_flammable` also fires on
  `is_aboveground_tank_storage` and `is_flammable_liquid_warehouse`. MORE.
- M5 (p.377 row 6 KITCHEN, HOMES): hotels get the 2.5 kg line as conditional "Where guest rooms /
  apartments have kitchens" (`fe_g_class_k_hotel_rooms`); residential, villas, labour / staff
  accommodation, hostel keep it required. LESS for hotels (row 7 commercial kitchen line still
  on the 'Commercial kitchen' tick).
- L6 (p.376 row 4 items 4-5): AHU line renamed "Class C Extinguisher - AHU Room / Mechanical
  Plant Room", cites items 4-5. Neutral.
- L8 (p.373 row 1 item 5; p.377 row 6): villa Class A recommendation states villas are not
  listed, 4 kg row 1 type; 2.5 kg is the row 6 kitchen unit. Neutral (recommended line).
- L10 (p.376 row 4 items 1-3 are rooms): a food / mercantile truck no longer prints the main
  electrical, main telephone and lift machine room lines (defaults True). LESS (correct).
- L11 UNSURE: conditional note line `fe_g_class_a_villa_converted` for a converted villa;
  routing unchanged. Needs a ruling.

Tests: new tests/test_audit28_ch47.py, 20 tests, all 20 RED on the unchanged code, GREEN after.
No existing test changed. pytest 380 passed; tests/test_cases.py 114 passed, 0 failed;
_structural_check.py 560 rule IDs, no errors, no warnings.

Grid diff (vs scratchpad/sweep master baseline; 0 crashes, refused counts unchanged):
flags: EVC_ITEM_STACK cleared (108 cases, L1); `is_theme_park` flips EVC to required for
business / storage / villa bases (H1). storage: EVC_ITEM_STACK cleared (616); Groups T and U
EVC no longer "required" (256 cases, conditional per R-B). mixed: EVC_ITEM_STACK cleared (all
pairs at 30 m). grid: EVC_ITEM_STACK cleared (assembly, detention, education, hotel, mall,
storage at 23 m or more); mixed_multiple below 23 m +1 NOT EVALUATED line (84 cases, M2). No
FP / FA / SC / pump / tank / sprinkler change anywhere.

Re-run issued jobs: any issued report with a theme park tick (Ch 5, Ch 7), a storage building
with GFA blank and GF BUA over 5000 m2 (Ch 7), Group R / T storage (Ch 4), cold-storage /
cable-spread / basement warehouses (Ch 5), Group T / U storage (Ch 5-7 now conditional),
mixed_multiple with no occupancy listed below 23 m (Ch 7), hotels (Ch 4 Class K status).

##### 2026-10-28 — Fix round, area ch8 (Ch 8 Fire Detection and Alarm): audit CH8-01 to CH8-19 (not CH8-04), rulings R-B and R-I

Rulings applied: R-B (Groups T / U keep the items 19-20 package as conditional, R-B wording),
R-I (robotic / mechanical parking: item 23 governs detection, item 22 notification, interfaces
and delayed evacuation kept). CH8-04 (one FA protocol in mixed mode) is left to the lead (R-F,
`_merge_most_restrictive`). Files: `rules/ch8_fire_alarm.yaml`, `engine.py` (`evaluate_fa` and two
new helpers `_fa_sprinklered`, `_fa_parking_detection`; one call-site change in
`_attached_parking_run` passing `sprinklered=host_spr` to `evaluate_fa`), `tests/test_cases.py`,
new `tests/test_audit28_ch8.py`.

- CH8-01 (p.512-513): Table 8.15 item 3 IS flame (#4.9) + IS linear heat on the tank roof (#4.8)
  also fires on `is_aboveground_tank_storage` (Group T, Table 9.27 T p.745). Items 10-11 print the
  same two systems; named in the one line, not printed twice. MORE onerous.
- CH8-02 / R-B (p.506, p.511): open yard (U) and aboveground tanks (T) take `fa_storage_yard_tank`:
  items 19-20 lines (smoke throughout, external AV, GFA = evacuation, interfaces, FACP location
  iv-v) all conditional with the R-B wording. Table 8.14 item 37 open storage shed now conditional
  "where a shed / structure exists". LESS onerous (required to conditional), as ruled.
- CH8-03 (p.502-508): infrastructure prints one conditional line (Table 8.13 has no yard hydrant
  network / infrastructure row; any building on the site, pump house or control building, takes its
  own occupancy row). No Table 8.1 / 8.13 / 8.14 / 8.15 lines. LESS onerous (no building system).
- CH8-05 / 06 / 10 (p.510-512): the cooling tower, kitchen hood, laundry / storage, pantry, pump
  room and garbage room lines now state the printed Ch 8 row (no material, burner count, occupancy,
  pump type or chute condition) and name the Ch 9-only condition. Text only; the app labels still
  gate the flags (UX fixer). Neutral in the engine; MORE onerous once the labels change.
- CH8-07 (p.511, p.712): tent kind temporary takes Table 8.14 item 32 (battery operated smoke
  detectors) required; site office short / long takes item 33 (smoke detector, Section 4.3)
  required. For those three kinds the Table 8.13 building row is replaced by one not_required line
  naming the routing, and the Table 8.1 system lines are not printed; Table 8.14 / 8.15 lines stay.
  Permanent tents, desert camps and row F keep their occupancy row. LESS onerous for the system,
  MORE onerous for item 32 / 33 (conditional to required).
- CH8-08 (p.502, p.506): warehouse and parking of 23 m or more get the R7 "highrise protocol not
  applied" note naming their own protocol (items 19-20 (vii); item 22 (vii)-(viii)). Robotic
  logistics warehouse of 23 m or more: conditional open-question line (item 23 prints no protocol).
  Neutral.
- CH8-09 (p.510): villas with 2 or more floors above grade get the Table 8.14 item 14 stair-top
  smoke detector from the storey count when `has_stairs` is cleared. MORE onerous.
- R-I (p.506): robotic parking (enclosed and open) drops item 22's sprinkler-dependent detection
  line (named not_required), keeps item 22 (iv), (v), (vii), (viii). `fa_robotic_parking` FACP line
  re-cited to Table 8.1 item 14.1 (vi), p.458 (item 23 prints only i-ii). LESS onerous (one
  detection line fewer), as ruled.
- CH8-11: cold storage "owner ruling pending" text replaced by "owner ruling 12.10.2026, Ch8 Q2".
- CH8-12 (p.509, p.512): one diesel generator heat detection line citing Table 8.14 item 8 and
  Table 8.15 item 5 (`fa_eq_diesel_gen_area` removed). Neutral.
- CH8-13 (p.508): private villa line "FACP or Monitoring Panel at Continuously Attended Location"
  (item 26 iii). Neutral.
- CH8-14 (p.503, p.507-508): villa wiring line conditional, naming the Section 4.11 wireless
  alternative of items 14 / 25 / 26 (i). LESS onerous for villas (as printed).
- CH8-15 (p.455, p.514): FACP line cites Table 8.1 item 1 (i)-(ii) and #6.2.1 for the contractor
  text. Citation only.
- CH8-16 (p.503): `fa_midrise_lowrise` (items 3-4 + 9-13) only for assembly, business,
  residential, day care, mercantile (and open mall, R10); animal housing, mixed and multiple,
  high / low depth underground take `fa_midrise_lowrise_height_only` (items 3-4). Same lines,
  citation only.
- CH8-17 (p.45): highrise text "23 m or more up to 90 m" (R1). Text only.
- CH8-18 (p.506): the parking item 22 line now names the branch that applies from the Ch 9
  sprinkler result (own rows, the host's for an attached parking, any listed occupancy under R13):
  "Manual Fire Detection and Alarm System - parking sprinklered, no fire detectors" (i-ii) or
  "Heat Detection and Alarm System - parking not sprinklered" (iii), the other branch named. Neutral.
- CH8-19 (p.456-466): new general lines with values as printed: item 4 (ii) 10 s; item 6 (iii)-(iv)
  stair voice speakers / no sounders; item 9 (i) 1 m from diffusers; item 14.1 (v)-(viii) 20% spare,
  attended location, not in service rooms; item 14.3 (i)-(iv) 10 s / 200 s; items 14.12 (i) and
  18 (i) notification on each floor; item 17 (ii)-(v), (ix) 1-2 Hz, 0.2 s, 40%, 1000 cd, 150 mm.
  MORE onerous (new lines).

Tests: 21 new (tests/test_audit28_ch8.py), 20 RED on master, 1 pins unchanged behaviour (permanent
tent). Updated in place: tests/test_cases.py "FA: Diesel generator + Commercial kitchen" (no
"Heat Detection (Diesel Generator Area)" equipment line, CH8-12) and "FA: Open parking -> item 22
by analogy" (the resolved "Manual Fire Detection and Alarm System - parking sprinklered ..." line in
place of "Conditional FA System ...", CH8-18). Counts: pytest 381 passed, cases 114 passed,
structural 0 errors / 0 warnings.

Grid diff vs master (0 crashes in 16,078 cases): FA branch only. Animal housing, mixed_multiple,
high / low depth underground: fa_midrise_lowrise -> fa_midrise_lowrise_height_only (CH8-16);
infrastructure: height rows -> fa_infrastructure and FA automatic detection True -> False (CH8-03);
storage Groups T / U: fa_storage_industrial -> fa_storage_yard_tank (R-B). No change in any other
chapter, pump, tank, sprinkler or check.

Re-run issued jobs: open yard storage and aboveground tank farms (FA package now conditional,
Group T gains Table 8.15 item 3); infrastructure jobs (no building FA); temporary tents and site
offices (item 32 / 33 in place of the addressable system); robotic parking; villas of G+1 and above
(stair-top detector); highrise warehouses and parkings (R7 note).

##### 28.10.2026 - Fix round, area ch9 (Ch 9 Tables 9.18-9.36, pumps, storage tenancy)

Branch `worktree-agent-a586391b853f291c8`, commit 576940b (base 4b69f4f + 975ea96).
Rulings applied: R-C, R-E, R-G, R-H, R-J, Q-1, Q-3, Q-4 (owner, 28.10.2026). Sources: ledgers
CH09A.md (F9A-01..13), CH09B.md (CH9B2-01..21), CURSOR_PRS.md (#18, #26, #27). Page text re-read
for every value (p.567-568, 580, 582, 589, 694-695, 696, 698, 704-717, 721, 723-731, 746-747,
750-753, 756, 770; Ch 3 p.304, 317, 327, 331).

Changes (direction vs printed text):
- F9A-01 / R-C (p.707, p.711): Table 9.21.e rows no longer suppress the host Table 9.21.a / 9.21.b
  row; both print, `_merge_duties` keeps the most onerous pump / tank and names the other. MORE.
  Cursor PR #26 NOT ported: it suppressed the host tier on a blank outlet area, against R-C; the
  host row stays and the outlet line is NOT EVALUATED (test pins it).
- F9A-13 (p.711): row A villas G+1 only (floors_above_grade <= 2); a villa above G+1 with an outlet
  gets a conditional "no printed row" line; rows' wording names A villas (G+1), B business,
  C mosques (Assembly Group C = mosque row). Neutral / MORE.
- F9A-07 + Cursor PR #27 ported (p.712): Table 9.21.f rows A-E gated to height <= 15 m (#4.5.6
  under 4.5 Lowrise); row F to GF BUA > 0 and <= 150 m2 and <= 2 floors, else NOT EVALUATED;
  a tent choice above 15 m prints a conditional "not applied" line. MORE.
- F9A-04 / PR #18 residual (p.709): 9.21.c.2 also suppresses 9.21.a.3 / 9.21.b.2. LESS (as
  printed). Ch 3 checked: Table 3.24 item 2.1 ii/iii (p.317) and Table 3.19 item 2 (p.304) have no
  area limit for a single exit stair; Table 3.30 item 3.i (p.327, hotel) and Table 3.32 item 5.i
  (p.331, mercantile) do not permit one. Stated in the line.
- F9A-03 (blank input class): lowest rows of Tables 9.20.b, 9.20.c, 9.21.a, 9.21.b, 9.21.c, 9.21.d,
  9.22.B, 9.24 A/C/D get `_gt: 0`; NOT EVALUATED branches for blank GF BUA (9.20.b, 9.21.a,
  9.21.b, 9.21.d, 9.24) and blank plot (9.21.b rows 1-2 need plot > 0; 9.22.B; add-on rows
  9.20.b.4, 9.21.a.4, 9.24 A.4/B.2/C.4). MORE.
- F9A-02 (p.721): attached covered / shaded parking evaluated at its own single level (Table 9.24.D).
  LESS (correct row).
- F9A-05 / Q-3 (p.695 #4.1.17): one governing fire pump and fire water tank for host + attached
  parking, in the host FP chapter, citing both tables and #4.1.17; the parking's line is removed.
  Neutral (most onerous kept).
- F9A-06, CH9B2-03, CH9B2-15 / Q-1 (p.694): #4.1.7 kept at G+3, reading stated, NFPA 13 density text
  removed; a required warning line when the Table 9.27 row gives only a hose-reel pump / tank
  (#4.1.9). MORE (warning).
- F9A-08 / F9A-09 / F9A-11 (p.704-705, 708, 713, 716-717): tool-added text removed (detention head
  type, villa podiums / two-compartment tank / multiple breeching, mall Class III); villa rows print
  iii dry landing valves and risers not required, iv developer pump room / tank (conditional),
  A.1.b roof; 9.21.a.3 "including basements and podiums (open as well as closed)"; 9.21.b.3 iv.
- F9A-10 / R-J: exactly 90.0 m stays Table 9.19 with a conditional edge note (p.696, p.698).
- R-H: detention 23 m or more, conditional line naming Table 9.20.d items (p.704).
- F9A-12: #4.1.9 on every governing pump line; #4.1.17 / #4.1.18 recommended line for
  infrastructure and plots over 20,000 m2 (p.695).
- CH9B2-01 / 06 / 07 (H9, p.567-568, 580, 582, 589, 770): every governing pump line states the set
  1 electric + 1 diesel + 1 jockey pump with controllers (Table 9.3 item 1.xii; Tables 9.5 / 9.6 /
  9.7 item 3.i), diesel 8 h (2.iii), location 1.xv, power 2.i, Civil Defence listing (#6.1.1 /
  #6.1.3); super highrise upper sets: 2 electric from different sources (1.xiii, 2.ii). "Electric
  or diesel" and "UL/FM" removed. Villa rows keep their printed "fire pump set ... 250 gpm" text.
  MORE.
- CH9B2-02 (H10, p.750-751): Table 9.29.A pump (with hydrants when the FP result requires yard
  hydrants or a yard line is NOT EVALUATED, else without) enters `_merge_duties`. MORE.
- CH9B2-04 / R-G: specialty groups K, P-V and hazard rows A-J / commodity rows L-O both evaluated;
  pump / tank merged with an R-G note; the specialty row names the selected branch. MORE.
- CH9B2-05 + sweep: `_reconcile_not_required` drops a not-required line when another table requires
  that system, and names it in the governing line (Table 9.19 vs Table 9.27 row 4 wet riser;
  highrise / G+4 plant nursery; specialty vs hazard rows). Neutral.
- R-E (p.752, p.756): diesel generator room Table 9.31.E governs regardless of sprinklers, cites
  Table 9.30.G; no #4.1.5 note for that room. MORE.
- Q-4 / CH9B2-19: new `Building.storage_tenancy` (single / multi / None); legacy
  `is_single_tenant_storage: true` maps to single, false / absent to None and the legacy key
  follows the choice; blank = "Storage Tenancy (Table 9.27 Groups A-J) - NOT EVALUATED". MORE.
- CH9B2-08 / 09 (pump_specs.yaml): Table 9.6 item 6.i.a / 6.ii text, p.582; fixed_1000 cites
  Table 9.26 A.vi p.723 and Table 9.23.B.2 ii p.717.
- CH9B2-10: Groups F / G / H print their not-required riser lines; one #4.11.1 MSDS line for every
  storage report. CH9B2-13 / 14 / 20: Table 9.30.K, 9.31.C wording; 9.30.F reading labelled.
  CH9B2-16 / 17: tunnel 60 m edge stated; blank tunnel length is a required NOT EVALUATED line.
  CH9B2-18: #4.1.8 conditional line for HH storage. CH9B2-21: Dubai ESL note on pumps of 500 gpm
  or more (source is a scanned copy; owner to confirm the wording).
- Kitchen hood (p.756 Table 9.31.A i): spec "Automatic wet chemical system (Section 3.12) and
  grease filters, for commercial kitchens having 3 or more burners".

Tests: tests/test_audit28_ch9.py, 31 tests; 30 RED before the change, 1 green (PR #26 re-check,
pins master behaviour kept under R-C). pytest 391 passed; tests/test_cases.py 114 passed;
_structural_check.py no errors / warnings. Updated in place (old -> new): test_phase1_findings
ENG_09 (tenancy multi), attached_parking_carries_routing_inputs (Q-3: pump in host chapter),
R14b (R-E diesel room); test_phase2_ch9 / _answers / test_phase5_ch9 store() helpers (Q-4 multi;
specialty tests leave tenancy blank), CH9C_27 (CH9B2-17 name), Q9 (tenancy multi); test_phase3_app
CH9B_14 (R-C pump); test_phase4 lowrise kiosk (plot entered, F9A-03); test_phase5 item4 (tenancy);
test_cases 3 storage cases (tenancy) and plant nursery line name.

Grid diff (scratchpad/fix/ch9/out_*.jsonl vs scratchpad/sweep/out_*.jsonl): 0 crashes. Changes in
FP only: storage cases without a tenancy choice (Q-4 NOT EVALUATED), business flag base without a
plot (F9A-03 plot NOT EVALUATED, 104 cases), mixed pairs with a lowrise residential-group or
storage occupancy (plot / tenancy NOT EVALUATED). REQ_AND_NOTREQ FP: flags 2 -> 0, storage 68 -> 0.

Re-run issued jobs: any saved storage project (tenancy now required); lowrise residential /
business / healthcare B-C / kiosk projects without a plot area; projects with an attached commercial
outlet (host table now kept); projects with Table 9.21.f choices; attached parking projects (one pump
/ tank line); high-ceiling storage; storage with a specialty tick.

##### 2026-10-28 — Fix round ch1011: Ch 10 smoke control, Ch 11 LPG, Ch 19 EAP, Annexure 2 checklist (worktree branch `worktree-agent-ae56c99e1c527dbaa`, not pushed)

Rulings applied: R-B (Groups T / U, Table 10.26 rows conditional; Cursor PRs #29, #30), R-D
(Table 10.27 item 16.iii kitchens), standing rule "a blank never passes". Ledger:
scratchpad/findings/CH10-11.md (C10-01..12, C11-01..10, EAP-01..05, A2-01..02). Page text re-read
for every value (pages/pNNNN.txt).

Ch 10 (rules/ch10_smoke_control.yaml, engine.evaluate_sc + `_sc_reconcile`, `_sc_ruling_rb`)
- C10-01 / R-D (p.866): new `sc_aux_kitchen_16iii` REQUIRED for malls, healthcare_a and every
  non-residential building of 23 m or more, no tick needed (MORE onerous); new
  `sc_aux_kitchen_16iii_residential_highrise` CONDITIONAL for residential / labour / staff /
  hostel / hotel_a-c of 23 m or more (MORE); parking of 23 m or more gets a CONDITIONAL line
  (`sc_aux_kitchen_16iii_parking_highrise`, needs ruling). The tick line now cites 16.i-16.ii
  with the printed text.
- C10-02 (p.864, p.860): storage with GF BUA 0 prints "Factory / Warehouse Smoke Extract
  (Table 10.26 item 1) - NOT EVALUATED" (was the < 230 m2 row; MORE); open parking with GFA 0
  prints "Open Parking Smoke Purging ... - NOT EVALUATED" (was "NOT Required"; MORE).
- C10-03 (p.857-860): #3.2.1 has no parking exclusion (only Table 10.22 is "other than Parking
  usage"), #3.5.1 sends parking to Table 10.23: both apply. Stair pressurization printed once
  (parking line, carrying the Table 10.20 / 10.19 item 1 text and both citations). Open parking
  of 23 m or more up to 4000 m2: the code does not say which table governs; the more onerous
  Table 10.20 item 4 corridor line is kept, Table 10.23 item 2.2.i named in it, and the
  "Smoke Purging / Ventilation NOT Required" line is not printed at 23 m or more (neutral; no
  required / not-required pair).
- C10-04 (p.860): enclosed parking line prints 1.ii (no make-up air, single basement < 3600 m2)
  and 1.iii (no jet fans). CO cross-reference line, Ch 3 Table 3.37 item 7.i (p.338),
  required for enclosed parking (MORE; the Ch 3 fixer adds the main line).
- C10-05 (p.866): items 5-7 print Section 2.17 and item ii (temperature control, AHU
  recommended). C10-06: Table 10.21 rows need a building (height > 0); infrastructure with
  no building loses the four lines (neutral). C10-07: lobby text as printed, no "preferred".
  C10-08: business 23 m+: separate conditional stair line removed; Table 10.27 item 3.iii cited
  on the one required stair line. C10-09: new general block (Section 2.5 / Table 10.3:
  secondary power, 2 h wiring, 60 s, 400°C / 2 h fans) printed whenever a Ch 10 system line is
  required (MORE, text only); Table 10.26 back-up power column on the warehouse rows.
  C10-10: 6 ACH (Table 10.6 3.i, FAQ #30) on corridor lines; 10 ACH / 3600 m2 (Table 10.11 3.i)
  governing over FAQ #31 9 ACH on Section 2.13 purge lines; jet fans 10 ACH (Table 10.12 3.i).
  C10-11: hybrid option, 4000 m2 zoning, open-parking definition. C10-12: mall tenant
  > 1000 m2 line CONDITIONAL (LESS; no tenant-area input).
- R-B: Table 10.26 rows CONDITIONAL with the ruling wording for Groups T and U (LESS than
  required, never "not required").

Ch 11 (rules/ch11_lpg.yaml)
- C11-01 (p.925-926, p.929): tanker parking (#4.8: 14 x 4 m up to 3,300 Gal, 20 x 4 m above,
  both printed with the condition; no capacity input) and Table 11.13 point of transfer lines
  REQUIRED with any LPG tank (MORE). C11-02 (p.924): Table 11.12 #3 separations and #4 / #7
  management lines added; the unprinted "low-pressure interlock" text removed (MORE).
  C11-03 (p.915-917): underground rows #1.i-viii, #2.i-xv, explosion-proof detector #2.xvi
  added; monitoring shaft / vent riser / annual corrosion text removed. C11-04: ASME reduction
  CONDITIONAL (LESS, optional per Table 11.10.a 3.b). C11-05: listing line cites #2.2.1-#2.2.3
  (p.883), contractor-exclusion sentence removed. C11-06: "Exterior Emergency Shut-off Valve
  per Building (#2.3.14.6)", p.890 (was "Section 2.5"). C11-07: cylinder regulators print the
  5 psi commercial stage and #2.3.12.3 hose text. C11-08: new general line #2.2.7 areas and
  #2.3.9.11 pipe colours (MORE). C11-09: roof tank above 90 m prints only "Not Allowed"
  (Table 11.7 / 11.8 rows dropped, neutral). C11-10: Tables 11.6.b-d values printed.

Ch 19 (eap.py) and Annexure 2 (submission_checklist.py)
- EAP-01 (p.1246-1248): drills per Table 19.2 row (#3.2 assembly ... #3.9 mall; #3.4 / #3.5 /
  #3.6 highrise business / hotel / residential incl. labour, staff, hostel), plus the #3.1 FM
  drill in every building; lowrise rows name that no occupant frequency is printed (MORE).
- EAP-02 (p.1237): command roles a-e and the strategy line in every building (MORE).
- EAP-03: strategy wording as printed ("would be a suitable strategy"; CD certification of
  remain-in-place / refuge). EAP-04: villa notes say p.1233 #2.1.1 is read and prints no villa
  exclusion or inclusion; villa routing unchanged (needs ruling). EAP-05: Arabic / English,
  Ch 5 Table 5.1.8 plan, vests line (item 9, p.1244), one-week notice (#2.1.iii).
- A2-01 (p.1284-1288): #3 file names, #4 do-not-submit, #5.ii b-n (i, j, k by height),
  #5.iii-#5.vii discipline rejection lists, #6 legend figures. A2-02: unprinted "Consultant
  declaration / HoE endorsement" item removed.

Tests: tests/test_audit28_ch1011.py, 77 new (77 failed on HEAD 975ea96 before the change).
Re-pointed: tests/test_phase3_followups.py::test_F_a1_2_villa_written_eap_conditional_pending_p1233
(was "not yet read" in the villa EAP detail; now "#2.1.1" and not "not yet read"; EAP-04).
Totals: 437 pytest passed, 114 cases, structural 0 errors / 0 warnings.
Grid vs master baseline (grid 9870, flags 832, storage 2856, mixed 2520): 0 crashes; only the
SC required-line count changes (general line +1 wherever a Ch 10 system is required; kitchen
16.iii +1; CO cross-reference +1 enclosed parking; parking 23 m+ stair -1; T / U rows to
conditional). No FP / FA / EVC / branch / NOT EVALUATED-count change in any grid.

Needs ruling: (1) R-D for parking buildings of 23 m or more (tool: conditional); (2) EAP-04
villa scope (p.1233 read, silent; lines stay conditional); (3) C10-03 open parking of 23 m or
more up to 4000 m2: Table 10.20 item 4 kept over Table 10.23 item 2.2.i (more onerous).

Re-run issued jobs: every report's SC chapter (general block); malls, hospitals, highrise
non-residential (kitchen line); parking of 23 m or more; enclosed parking; Group T / U
warehouses; storage or open parking entered with GF BUA / GFA 0; any LPG tank, flame effect,
underground or roof tank job above 90 m; every EAP chapter and CD checklist export.

##### 2026-10-28 — Fix round, area ux (app / exports / UI): audit UX-01 to UX-27 (not UX-03), CH8-05 / CH8-06 / CH8-10 labels, blank geometry stops

Rulings applied: standing rules "a blank never counts as a pass" (geometry stops) and "no pre-fill
the user did not type" (every default the report rests on is now listed in an "Assumptions used"
box and in every export); R-B wording in the open-yard help; R-I and Ch9 Q7 in the robotic parking
help; Q-3 named in the attached parking help. UX-03 (NOT EVALUATED status + banner) left to the
lead. No engine, rule or schema change: the four sweep grids are identical to the master baseline.
Files: `app.py`, `export.py`, `ui.py`, `requirements.txt`, new `tests/test_audit28_ux.py`.

- UX-01 (p.695 #4.1.13): the plot GF BUA sum and every Table 9.27 input (single tenant, K, P, Q +
  hangar group, R, S, T + tank area / capacity, U, V, commodity L-O, unit compartment #4.1.14) are
  drawn under "Storage hazard class", before any stop; the stop names that place. A stand-alone
  warehouse evaluates (was a dead end). The Warehouse preset now states OH2 and the plot sum
  (title "Warehouse (multi-tenant OH2, 4000 m², only building on the plot)"). Neutral.
- UX-09: input stops are collected and shown after the WHOLE sidebar (FP, SC, LPG settings stay
  drawn during a stop); several stops show together. Neutral.
- Blank geometry (fix round rule): a building with a height (not infrastructure) stops by name when
  GF BUA (#4.1.12 p.695), GFA (Ch 3 #1.4.6 p.242) or plot area (#4.1.10 p.695) is 0. Exempt: an
  underground occupancy with a basement BUA (no GF BUA), a food / mercantile truck (no plot area).
  MORE onerous (stop instead of a silent 0). Every preset fills its values: basement parking area /
  height 0 / levels, depth 3.5 m per basement, hospital open parking 3000 m2 at grade, office
  Business Group B (Table 1.1 row 2 p.48: offices are Group B).
- UX-02: "?print=1" link removed (it opened a new session = the sample building); a "Print layout"
  toggle hides sidebar and export column in the same session. Neutral.
- UX-04: executive PDF / Word print one governing line per chapter (headline system, else the
  matched row's first line), FP with pump and tank, FSA extent, MOE OL + exits; no truncation;
  NOT EVALUATED lines named, never chosen as the headline. Neutral.
- UX-05: flags cleared by an occupancy change are remembered and re-ticked on return; the sidebar
  names what was cleared / restored. Presets and Load start afresh. LESS silent loss (MORE lines
  kept on a round trip).
- UX-06: every input that appears / disappears above an expander sits in a fixed container
  (occupancy inputs, geometry warnings, hazard notes, storage block, parking, high ceiling, theatre
  kind); open expanders stay open (checked in Chromium: depth 8 m, basements 0). Neutral.
- UX-07: exports built on click (download_button callable, kept in a cache_resource store),
  `on_click="ignore"` on every download; rerun 0.6-1.3 s (was 2.6-4.7 s). Neutral.
- UX-08: "Assumptions used in this report" box (sample building, preset, first-load pre-ticks never
  touched, standpipes / motor fuel group / parking type / hangar group / tunnel kind / exit stairs
  left on default, blank optional inputs and their fallbacks, working hazard class); "Sample
  building" banner on first load; the list is printed in every export. Neutral.
- UX-10 / 11 / 12: save name follows `<project>_<date>` until typed; notes, "Generated <date> |
  FLSC tool revision <git sha>", an "Inputs used" table (every entered value and ticked box, blank
  parking inputs "not entered") and the assumptions in compact / detailed / executive PDF and Word
  and in the XLSX (Profile rows + Inputs sheet); detailed tables carry a Status column; file names
  `<project>_FLSC_<kind>_<YYYY-MM-DD>.<ext>`. PDF text is escaped (a "<" in a project name broke the
  PDF). Neutral.
- UX-13 / 22: compact table view is the default (Cards keep "Why triggered"); filter default all
  statuses except not required; "Required only" toggle; a search with no match says so. Neutral.
- UX-14: classification chips, chapter captions and exports print the table / row (e.g. "Ch 9,
  #4.3.1 / Table 9.19.B") not rule IDs; empty chip reads "general rules"; occupancy names, not codes,
  in captions, mixed note, "Why this row" and sanity texts; rule IDs and raw YAML behind "Show rule
  IDs". Neutral.
- UX-15 / 17 / 27: robotic parking moved to the parking block, theatre / cinema kind next to its
  box; special rooms in one column; "(required)" in the parking height / levels labels.
- UX-16: every input has help (data_editor has no help parameter; caption kept). Yes/no inputs cite
  the code_ref / page_ref of every rule line they switch on, read off the rule YAMLs at run time
  (stays in step with rule fixes); hand-written leads cite Ch 1 #1.7.39-#1.7.45 p.44-45, Ch 9
  #4.1.4 / #4.1.6 / #4.1.7 p.694, #4.1.10-#4.1.14 p.695, Ch 3 #1.4.5 / #1.4.6 p.242, Table 3.13
  p.283-287, Table 9.27 groups p.724-746, Table 9.29 / 9.29.A p.749-751, Table 9.30 p.752-755,
  Table 9.31 p.756-757, Table 8.14 p.509-511, Table 8.15 p.512-513, Tables 9.18-9.20 pump notes
  p.696-701. No tilde, approximately sign or section sign.
- CH8-05 / 06 / 10 (p.510-512, p.756): labels "Cooling towers (G)", "Commercial kitchen with
  cooking hood (A)", "Laundry / storage rooms", "Pantries", "Pump room (fire pump or other)",
  "Garbage room / chute"; help states the Ch 8 row has no condition and names the Ch 9-only one.
  MORE onerous in use (users with non-combustible towers / small hoods now tick the box).
- UX-18 / 19 / 20 / 21 / 23 / 24 / 25 / 26: sidebar "auto" (closed on a phone), compact hero and no
  mid-word title break under 640 px, "Contents and exports" anchor; unsaved-inputs hint + Save
  button by the exports; `streamlit==1.66.1`, `use_container_width` gone, pickers state-driven (no
  index + state warning); dead code-excerpt path removed; "what changed" list + delta on Required
  systems; muted text #475569, larger legend; fire access metric "1/6" with full text in caption;
  advisory (LPG roof above 90 m) is a warning, not a red stop; sanity expanders collapsed.

Tests: new `tests/test_audit28_ux.py`, 29 tests (28 RED on the unchanged code, 1 guard test green
by design: infrastructure / truck exemption). No existing test changed. pytest 389 passed (was
360), tests/test_cases.py 114 passed, _structural_check no errors / no warnings.
Grid diff (grid 9870, flags 832, storage 2856, mixed 2520): 0 crashes, 0 changed keys.
Re-run issued jobs: none from the engine (no result changed). Projects saved as .flsc load as
before; a file with GF BUA, GFA or plot area 0 now stops by name until filled.

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
