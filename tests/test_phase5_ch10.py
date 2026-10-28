"""Phase 5 Ch 10 (13.10.2026): owner cards 13.10.2026 05:45Z, both option A.

1. "Name both routes": the road / rail tunnel line for more than 90 m also states
   Table 10.25 row 2 item 2 (rail, p.863): jet fan per Section 2.14 OR a mechanical
   smoke purging system using dedicated ducting per Section 2.13. Road text kept.
2. "Move to chemicals": Table 10.26 item 2 (p.864) / Section 2.20 / Table 10.18
   (p.853-854) fires on the chemical warehouse and bulk flammable liquid, gas, solid
   storage inputs, no longer on LPG tanks.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_phase1_findings import items, report  # noqa: E402

SC_YAML = (ROOT / "rules" / "ch10_smoke_control.yaml").read_text(encoding="utf-8")
TUNNEL = dict(occupancy="business", height_m=10, has_tunnel=True, ground_floor_bua_m2=1000)
CHEM = "Hazardous + Flammable Chemical Room Ventilation"


def named(r, code, prefix):
    return [it for it in items(r, code) if it.system.startswith(prefix)]


# ------------------------------------------------------------ 1. rail tunnels > 90 m
@pytest.mark.parametrize("length", [90, 200, 1500])
def test_rail_tunnel_over_90_names_jet_fan_or_ducted_purge(length):
    (t,) = named(report(tunnel_length_m=length, **TUNNEL), "SC", "Tunnel Smoke Management")
    assert t.status == "required"
    assert "more than 90 m" in t.system and "rail: jet fan system OR ducted smoke purging" in t.system
    # road row 1 item 3 text kept
    assert t.spec.startswith("Road: jet fan system per Section 2.14 for the entire tunnel; "
                             "other systems or combinations permitted")
    assert ("Rail: jet fan system per Section 2.14 for the entire tunnel OR a mechanical smoke "
            "purging system using dedicated ducting per Section 2.13") in t.spec
    assert ("A jet fan system, in accordance with Section 2.14. shall be provided for the entire "
            "tunnel. OR a mechanical smoke purging system using dedicated ducting shall be "
            "provided in accordance with Section 2.13.") in t.detail
    assert ("Other systems or combinations of systems shall be permitted, where justified by an "
            "engineering analysis and CFD modeling.") in t.detail
    assert "owner ruling 13.10.2026" in t.detail and "P3 Ch10 Q2" in t.detail
    assert t.code_ref == ("Ch 10, #3.7 / Table 10.25 row 1 (road tunnel) item 3; "
                          "row 2 (rail tunnel) item 2")
    assert t.page_ref == "p.862-863"


def test_rail_route_absent_under_90_not_entered_and_cable():
    (u,) = named(report(tunnel_length_m=89.9, **TUNNEL), "SC", "Tunnel Smoke Management")
    assert "dedicated ducting" not in u.spec and "less than 90 m" in u.system
    (n,) = named(report(**TUNNEL), "SC", "Tunnel Smoke Management")
    assert n.status == "not_evaluated" and "NOT EVALUATED" in n.system  # UX-03
    (c,) = named(report(tunnel_kind="cable", tunnel_length_m=200, **TUNNEL), "SC",
                 "Tunnel Smoke Management")
    assert c.system == "Tunnel Smoke Management - Service / Cable"
    assert not named(report(occupancy="business", height_m=10, ground_floor_bua_m2=1000),
                     "SC", "Tunnel Smoke Management")


# ------------------------------------------------- 2. Table 10.26 item 2 trigger
CHEM_INPUTS = ["has_chemical_warehouse", "has_bulk_flammable_liquid_storage",
               "has_bulk_flammable_gas_storage", "has_bulk_flammable_solid_storage"]


@pytest.mark.parametrize("flag", CHEM_INPUTS)
def test_chemical_storage_input_gives_table_10_26_item_2_line(flag):
    r = report(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=1000, **{flag: True})
    (c,) = named(r, "SC", CHEM)
    assert c.status == "required"
    assert c.code_ref == "Ch 10, #3.8 / Table 10.26 item 2; #2.20 / Table 10.18"
    assert c.page_ref == "p.864, p.853-854"
    assert "20 air-changes per hour" in c.spec and "below 25% of the low flammable limit" in c.spec
    assert "85 % of the required exhaust" in c.spec and "emergency power" in c.spec
    assert "STAND BY FAN row" in c.detail and "STAND BY POWER row" in c.detail
    assert "minimum 15 m" in c.detail and "not less than 5 m" in c.detail
    assert "50% of LFL/LEL to start the ventilation system" in c.detail
    assert "Move to chemicals" in c.detail


def test_chemical_line_fires_outside_warehouse_occupancy_and_once_for_all_inputs():
    r = report(occupancy="business", height_m=10, ground_floor_bua_m2=1000,
               **{f: True for f in CHEM_INPUTS})
    assert len(named(r, "SC", CHEM)) == 1


def test_lpg_tank_only_building_no_longer_gets_the_line():
    r = report(occupancy="business", height_m=10, ground_floor_bua_m2=1000, has_lpg_tanks=True)
    assert not named(r, "SC", CHEM)
    assert not named(r, "SC", "LPG / Hazardous")
    r = report(occupancy="storage_industrial", height_m=10, ground_floor_bua_m2=1000)
    assert not named(r, "SC", CHEM)


def test_old_rule_id_and_trigger_gone():
    assert "sc_aux_lpg_hazardous" not in SC_YAML
    assert "sc_aux_hazardous_chemical_room" in SC_YAML
    assert "Table 10.26.2" not in SC_YAML
