# HANDOFF — UAE FLSC Streamlit tool (uae-flsc-tool-02)

Cross-PC and cross-session resume point. Update after every change.
Code basis: UAE Fire & Life Safety Code 2018 (CDGH-OP-25). PDF page = printed page.
Audit: `AUDIT_UAE_FLSC_TOOL_12.10.2026.md` (189 findings, rulings R1-R13), kept in the
project files, not in this repo.

A push or merge to `master` redeploys the live app. Nothing merges without Hussein's go.

## Log (newest first)

### 2026-10-12 — R14 ruled (#4.1.5) — Lift Machine Room sprinkler in sprinklered buildings only

Hussein chose "Sprinklered only" (07:24Z). `aux_M_lift_machine` carries
`requires_sprinkler_system: true`; `evaluate_fp` gates it on the same sprinkler test as
Table 9.29 and prints a not_required line citing #4.1.5 (p.694) otherwise. Snapshot vs
the previous commit: 940 of 6552 cases change, every one only this line. Test
`test_R14_lift_machine_room_sprinkler_only_in_sprinklered_buildings`. The other Table 9.30
rooms are not gated yet: #4.1.5 prints the same rule for every Table 9.30 system, asked
as a separate ruling.

### 2026-10-12 — Phase 1 (engine core + Ch 9 pumps and tables) — draft PR, NOT merged

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
- **Tests:** `tests/test_phase1_findings.py` (49, one per finding) + `tests/test_cases.py`
  (112) + `_structural_check.py` (0 errors). ALTA case (midrise, 3 basements) stays
  750 gpm @ 6.9 bar, 45 min, per Table 9.20.a row H (ruling 12.10.2026).

**Edge choices stated in the report details (no ruling asked):** plot exactly 20,000 m2
stays in row 1; 900 m2 stays in 9.21.d row 1; 20,000 m2 stays in D.1; 1 exit stair takes
the 750 gpm row of 9.24.C.2.

## Open rulings (block the parts named)

| Ruling | Question | State |
| --- | --- | --- |
| R1 | 23.0 m exactly: midrise or highrise (CH10-03) | waiting |
| R2 | Lowrise with 3+ basements (CH9B-07) | waiting |
| R3 | 9.24.A.3 "more than 3 standpipes" | coded on option a (exactly 3 = 1000 gpm), marked "R3 pending" |
| R4 | 9.21.b.3.i cross-refers to 9.21.a tiers (CH9B-06 sub-3600 part) | waiting |
| R5 | LPG aboveground tank: Ch 11 vs Ch 9 | waiting (later phase) |
| R6 | Malls above 23 m (CH9A-18) | waiting |
| R7 | FA protocol above 23 m for hotels/healthcare/detention (CH8-11) | waiting |
| R8-R13 | see audit | waiting (later phases) |
| R14 | #4.1.5 Lift Machine Room sprinkler in unsprinklered buildings (CH9A-09) | ruled 12.10: sprinklered only; coded |
| R14b | #4.1.5 for the other Table 9.30 rooms (electrical, generator, telephone, server and so on) | asked 12.10 |

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
