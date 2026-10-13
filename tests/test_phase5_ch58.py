"""Phase 5 Ch 5-8 (13.10.2026): page requirements added, owner card 13.10.2026 05:45Z
("Add all", option A). Text read off the rendered 2018 pages p.389, 400, 413, 437,
461, 462. G4 (#8.1.9 cable standards) was already applied in 226e1fd.

G1 Table 5.1 item 2 directional sign (p.389); G2 Ch 5 #4.4.1-#4.4.3 (p.400);
G3 Table 6.2 item 4.ii 5% central battery spare capacity (p.413); G5 Table 7.2
item 1 and item 3.1 (v)-(vi) (p.437); G6 Table 8.1 item 15 (i)-(x) (p.461) with
(xiii)-(xv) (p.462).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_phase1_findings import items, report  # noqa: E402

G1 = "Directional Exit Sign - Chevron Arrow Identifiable at 12 m"
G2 = "Exit / Directional Sign Inspection and Maintenance (every 30 days)"
G5 = "Two-way Telephone System - Civil Defence Use, Collocated with EVC"
G6 = "FA Power Supplies - Primary and Secondary Sources"
G6_OLD = "FA Secondary Power Supply and Battery Calculations"


def named(r, code, name):
    return [it for it in items(r, code) if it.system == name]


# ---------------------------------------------------------------- G1 -----
def test_p5_g1_directional_sign_chevron_12_m_present():
    r = report(occupancy="business", height_m=10)
    (s,) = named(r, "ES", G1)
    assert s.status == "required"
    assert s.code_ref == "Ch 5, #2 / Table 5.1 item 2" and s.page_ref == "p.389"
    for v in ("chevron type", "at a distance of 12 m", "not less than 9.5 mm (3/8 inch) from any letter",
              "located at the end of the sign for the direction indicated",
              "towards the same direction as the directional 'arrow' mark",
              "directional 'ARROW' shall be in White colour on Green background",
              "Owner ruling 13.10.2026"):
        assert v in s.detail, v


def test_p5_g1_g2_absent_for_unconverted_villa_and_ground_floor_fuel_station():
    for kw in (dict(occupancy="villa_private", height_m=6),
               dict(occupancy="villa_commercial", height_m=6),
               dict(occupancy="motor_fuel_dispensing", height_m=5)):
        r = report(**kw)
        assert not named(r, "ES", G1), kw
        assert not named(r, "ES", G2), kw


def test_p5_g1_g2_present_for_converted_villa_and_multistorey_fuel_station():
    for kw in (dict(occupancy="villa_private", height_m=6, villa_converted_use=True),
               dict(occupancy="motor_fuel_dispensing", height_m=8,
                    fuel_dispensing_multistorey=True)):
        r = report(**kw)
        assert [i.status for i in named(r, "ES", G1)] == ["required"], kw
        assert [i.status for i in named(r, "ES", G2)] == ["required"], kw


# ---------------------------------------------------------------- G2 -----
def test_p5_g2_30_day_visual_check_present():
    r = report(occupancy="residential", height_m=40)
    (s,) = named(r, "ES", G2)
    assert s.status == "required"
    assert s.code_ref == "Ch 5, #4.4.1-#4.4.3" and s.page_ref == "p.400"
    assert "Every 30 days, owner appointed facility management shall verify visually" in s.spec
    for v in ("#4.4.1 the building owner", "#4.4.2 every 30 days",
              "#4.4.3 Exit signs and Directional Signs connected to, or provided with, a "
              "battery-operated emergency illumination source", "Chapter 6"):
        assert v in s.detail, v


# ---------------------------------------------------------------- G3 -----
G3_TEXT = ("5% spare capacity shall be included when selecting the central battery system "
           "rating (Table 6.2 #4.ii, p.413; owner ruling 13.10.2026)")


def _central_battery_lines(r):
    return [it for it in items(r, "EL") if it.status == "required" and it.detail
            and "CENTRAL BATTERY option" in it.detail]


def test_p5_g3_central_battery_5_percent_on_every_table_6_5_tier():
    for kw in (dict(occupancy="residential", height_m=120),
               dict(occupancy="residential", height_m=40),
               dict(occupancy="mall_covered", height_m=15),
               dict(occupancy="assembly_a", height_m=10, has_amusement_confounding=True),
               dict(occupancy="business", height_m=10, has_amusement_confounding=True)):
        r = report(**kw)
        cb = _central_battery_lines(r)
        assert cb, kw
        for it in cb:
            assert it.detail.count(G3_TEXT) == 1, kw
            # stays on the central battery option, ahead of the #8.1.9 cable list (G4)
            d = it.detail
            assert d.index("CENTRAL BATTERY option") < d.index(G3_TEXT) < d.index("#8.1.9")
            assert d.count("IEC 60331-2") == 1


def test_p5_g3_absent_where_no_central_battery_option():
    r = report(occupancy="business", height_m=10)
    assert not _central_battery_lines(r)
    assert all(G3_TEXT not in (it.detail or "") for it in items(r, "EL"))


# ---------------------------------------------------------------- G5 -----
def test_p5_g5_two_way_usage_collocated_verbatim_where_evc_required():
    r = report(occupancy="residential", height_m=40)
    (s,) = named(r, "EVC", G5)
    assert s.status == "required"
    assert s.code_ref == "Ch 7, #2.5 / Table 7.2 item 1" and s.page_ref == "p.437"
    assert ("'Two-way Communication Systems or Two-way Telephone Systems shall be provided for "
            "Civil Defence personnel use. And it shall be collocated with the Emergency Voice "
            "Evacuation and Communication System.'") in s.detail


def test_p5_g5_item_3_v_vi_on_features_line():
    r = report(occupancy="residential", height_m=40)
    (f,) = [it for it in items(r, "EVC") if it.system == "Two-way Telephone System Features"]
    assert f.code_ref == "Ch 7, #2.5 / Table 7.2 item 3" and f.page_ref == "p.437"
    for v in ("v. a means for silencing the audible call-in signal sounding appliance shall be "
              "permitted, provided that it is key operated or located in a locked cabinet",
              "sound a trouble signal whenever the means is in the silence position and no "
              "telephone circuits are in an off-hook condition",
              "vi. if a selective talk system is used, means mentioned above shall be permitted, "
              "provided that subsequent telephone circuits going off-hook operate the distinctive "
              "off-hook signal"):
        assert v in f.detail, v


def test_p5_g5_absent_where_evc_not_required():
    r = report(occupancy="business", height_m=10)
    assert not named(r, "EVC", G5)


# ---------------------------------------------------------------- G6 -----
def test_p5_g6_power_sources_i_to_x():
    r = report(occupancy="business", height_m=10)
    (s,) = named(r, "FA", G6)
    assert s.status == "required"
    assert s.code_ref == "Ch 8, Table 8.1 item 15 (i)-(x)" and s.page_ref == "p.461"
    for v in ("(i) at least two power supply sources", "'FIRE ALARM/DO NOT DISCONNECT'",
              "2 hour fire rated and protected from mechanical damages",
              "in accordance with NFPA 70", "approved UPS in accordance with NFPA 111",
              "(x) operation on secondary power shall not affect"):
        assert v in s.detail, v


def test_p5_g6_xiii_to_xv_on_battery_line():
    r = report(occupancy="business", height_m=10)
    (b,) = named(r, "FA", G6_OLD)
    assert b.code_ref == "Ch 8, Table 8.1 item 15 (xi)-(xv)" and b.page_ref == "p.462"
    for v in ("minimum of 24 hours", "30 minutes", "20 percent safety margin",
              "(xiii) batteries shall be marked with the month and year of manufacture using "
              "the month/year format", "Article 480 of NFPA 70",
              "within 48 hours after fully charged batteries have been subject to a single "
              "discharge cycle"):
        assert v in b.detail, v
    assert "also apply" not in b.detail
    assert "Article 480 of NFPA 70" in b.spec and "48 hours" in b.spec


def test_p5_g6_prints_wherever_the_battery_line_prints():
    for kw in (dict(occupancy="business", height_m=10),
               dict(occupancy="residential", height_m=120),
               dict(occupancy="villa_private", height_m=6),
               dict(occupancy="motor_fuel_dispensing", height_m=5)):
        r = report(**kw)
        assert len(named(r, "FA", G6)) == len(named(r, "FA", G6_OLD)), kw
