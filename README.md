# UAE FLSC 2018 — Fire & Life Safety Requirements

Streamlit compliance tool for the UAE Fire & Life Safety Code of Practice
(September 2018, CDGH-OP-25). Enter a building profile and get the minimum
systems required by Chapters 3–11, with section and page citations.

Live app: https://uae-flsc-tool-02-itxfbnyhtfm8omkrezp5be.streamlit.app/

PDF export:
- **Compact** — required system headers only
- **Detailed** — full evaluation plus authentic UAE FLSC 2018 code plates

This tool is a **design aid**. It does not replace UAE Civil Defence review or
the judgement of a registered Fire Protection Engineer.

## Install & run

```bash
pip install -r requirements.txt
python run.py        # launches Streamlit
```

Or:

```bash
streamlit run app.py
```

## Verify

```bash
python tests/test_cases.py
```

## Structure

```
├── app.py                          Streamlit UI
├── engine.py                       YAML rule evaluator + markdown renderer
├── flsc_schema.py                  Pydantic Building / Requirement models
├── export.py                       DOCX / PDF exporters
├── rules/
│   ├── ch3_means_of_egress.yaml
│   ├── ch4_fire_extinguishers.yaml
│   ├── ch5_exit_signs.yaml
│   ├── ch6_emergency_lighting.yaml
│   ├── ch7_evc.yaml
│   ├── ch8_fire_alarm.yaml
│   ├── ch9_fire_protection.yaml
│   ├── ch10_smoke_control.yaml
│   ├── ch11_lpg.yaml
│   └── pump_specs.yaml
├── tests/test_cases.py
└── README.md
```

## Coverage

| Chapter | Subject | Tables encoded |
| --- | --- | --- |
| 3 | Means of Egress | 3.13, 3.14, 3.15, 3.16 |
| 4 | Fire Extinguishers | 4.3 |
| 5 | Exit Signs | 5.3 |
| 6 | Emergency Lighting | 6.1, 6.5, 6.6 |
| 7 | Emergency Voice Evacuation | 7.1–7.3 |
| 8 | Fire Detection & Alarm | 8.13, 8.14, 8.15 |
| 9 | Fire Protection | 9.18–9.31, 9.29.A |
| 10 | Smoke Control | 10.19–10.27 |
| 11 | LPG | 11.1–11.14 |

## Height classes (Ch 1 §1.7.39–1.7.42)

| Class | Height (excluding parapets, from lowest grade / Fire Service access) |
| --- | --- |
| Lowrise | ≤ 15 m |
| Midrise | 15 m < h ≤ 23 m |
| Highrise | 23 m < h ≤ 90 m |
| Super-highrise | > 90 m |

Exactly 23 m is midrise (highrise starts *more than* 23 m). Exactly 90 m is
highrise (super-highrise starts *more than* 90 m). FAQ Annexure 1 (p.1273)
alternatively measures occupiable-ceiling height — use the same datum the
Civil Defence reviewer will use.

## Occupancy routing notes (Ch 9)

- **Healthcare Group A** (hospitals) → Table 9.20.a / 9.21.a (public / assembly-like).
- **Healthcare Group B/C** (clinics / ambulatory) → Table 9.20.b / 9.21.b
  (with residential / business), not 9.20.a.
- **Commercial villa** is a developer-built villa community (Ch 1 §1.7.35), not a
  private villa converted to a shop. Converted villas use the
  `villa converted to other use` flag (Table 8.13 item 14 / Table 9.21.d).

## 2026-08 alignment pass vs UAE FLSC 2018

- Fire-alarm highrise overlay (5-floor phased evac, sub-FACPs) now starts
  **above 23 m**, matching Table 8.13 items 1–4. Midrise 15–23 m uses items 3–4.
- Closed the 23 m / 90 m match gaps in Ch 6 / 9 / 10 (`lt` → `lte`).
- Healthcare B/C mid- and low-rise fire protection routed to Tables 9.20.b /
  9.21.b.
- Means-of-egress travel for labour / hostel / staff accommodation split from
  apartments (Table 3.16 rows 6 vs 7: NS 61 m vs NS 30 m).
- Commercial-villa definition corrected to Ch 1 §1.7.35.

## Extending the rules

Edit the YAML under `rules/`. Each branch has:

```yaml
- id: unique_id
  match:
    occupancy: residential
    height_m_gt: 23
    height_m_lte: 90
    plot_area_m2_lte: 20000
  section: "§4.3.1 / Table 9.19.B"
  page: "p.698"
  systems:
    - name: "Automatic Sprinkler System"
      spec: "Full coverage incl. basements and podiums"
```

Supported `match` operators: `_gt _gte _lt _lte _in _is _not`, plus
`occupancy`, `occupancy_in`, `occupancy_not`, `occupancy_group_is`.
