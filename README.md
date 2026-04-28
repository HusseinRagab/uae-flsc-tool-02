# UAE FLSC 2018 — Chapter 9 Prototype

Streamlit compliance tool for UAE Fire & Life Safety Code (Sept 2018, CDGH-OP-25).
Input a building profile, get the minimum Fire Protection systems required by
Chapter 9 with section/page citations.

## Install & run

```bash
pip install -r requirements.txt
python run.py        # launches Streamlit headless + opens Chrome
```

Or, to use your system default browser instead:

```bash
streamlit run app.py
```

## Verify

```bash
python tests/test_cases.py
```

## Structure

```
uae_flsc/
├── app.py                          Streamlit UI
├── engine.py                       YAML rule evaluator + markdown renderer
├── schema.py                       Pydantic Building / Requirement models
├── rules/
│   └── ch9_fire_protection.yaml    Chapter 9 knowledge base (editable)
├── tests/
│   └── test_cases.py               7 archetype verification cases
├── requirements.txt
└── README.md
```

## Coverage (prototype scope)

Chapter 9 sections implemented:
- §4.1 General requirements (yard hydrant triggers by plot / storage floors)
- §4.2 Super Highrise (>90 m) — Table 9.18
- §4.3 Highrise (23–90 m) — Table 9.19
- §4.4 Midrise (15–23 m) — Tables 9.20.a / 9.20.b
- §4.5 Lowrise (≤15 m) — Table 9.21.a
- §4.6 Mall (covered / open / mixed) — Table 9.22
- §4.7 Villa (private / commercial) — Table 9.23
- §4.8 Parking (abbreviated) — §4.8
- §4.14 Auxiliary Rooms — Table 9.30

Deferred (pending prototype sign-off):
- §4.9 Motor Fuel Dispensing
- §4.10 Infrastructure
- §4.11 Storage / Warehouse / Industrial (biggest sub-section — 100+ KB)
- §4.12 Tunnel
- §4.13 Various Locations & Extensions
- §4.15 Equipment
- Table 9.21.b (lowrise residential sub-table)

## Extending the rules

Edit `rules/ch9_fire_protection.yaml`. Each branch has:

```yaml
- id: unique_id
  match:
    occupancy: residential
    height_m_gt: 45
    height_m_lt: 90
    plot_area_m2_lte: 20000
  section: "§4.3.1 / Table 9.19.B"
  page: "p.697"
  systems:
    - name: "Automatic Sprinkler System"
      spec: "Full coverage incl. basements and podiums"
      detail: "Per Section 3.5"
```

Supported `match` operators: `_gt _gte _lt _lte