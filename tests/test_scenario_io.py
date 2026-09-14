"""Save/load occupancy restore — Streamlit selectboxes ignore index= once keyed."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scenario_io import apply_loaded_occupancy, normalize_occupancy_chosen

# Mirror of app.OCCUPANCY_OPTIONS — keep the helper independent of Streamlit.
OCCUPANCY_OPTIONS = {
    "Villa": ["villa_private", "villa_commercial"],
    "Residential / Lodging": ["residential", "hotel_a", "hotel_b", "hotel_c",
                               "hostel", "labour_accommodation", "staff_accommodation"],
    "Business / Office": ["business"],
    "Storage / Industrial": ["storage_industrial", "motor_fuel_dispensing"],
}


def test_normalize_accepts_json_list():
    assert normalize_occupancy_chosen(["Villa", "villa_private"]) == (
        "Villa", "villa_private"
    )
    assert normalize_occupancy_chosen(("Residential / Lodging", "residential")) == (
        "Residential / Lodging", "residential"
    )
    assert normalize_occupancy_chosen(None) is None
    assert normalize_occupancy_chosen(["only_one"]) is None


def test_load_overwrites_stale_picker_widgets():
    """Concrete trigger: user is on the default residential highrise, then
    loads a saved private-villa .flsc. Without writing the picker keys,
    Streamlit keeps Category=Residential and the next render evaluates the
    villa file as a residential tower (wet riser, phased evac, FFL)."""
    state = {
        "occupancy_chosen": ("Residential / Lodging", "residential"),
        "occupancy_category_select": "Residential / Lodging",
        "occupancy_sub_select": "residential",
        "height_m_input": 45.0,
    }
    apply_loaded_occupancy(
        state,
        ["Villa", "villa_private"],  # JSON list, as written by save
        OCCUPANCY_OPTIONS,
    )
    assert state["occupancy_chosen"] == ("Villa", "villa_private")
    assert state["occupancy_category_select"] == "Villa"
    assert state["occupancy_sub_select"] == "villa_private"


def test_load_resolves_occupancy_when_category_label_drifted():
    """Older files may store a stale category label; recover from the occupancy id."""
    state = {}
    apply_loaded_occupancy(
        state,
        ["Old Villa Label", "villa_commercial"],
        OCCUPANCY_OPTIONS,
    )
    assert state["occupancy_chosen"] == ("Villa", "villa_commercial")
    assert state["occupancy_category_select"] == "Villa"
    assert state["occupancy_sub_select"] == "villa_commercial"


def test_load_ignores_empty_payload():
    state = {"occupancy_sub_select": "residential"}
    apply_loaded_occupancy(state, None, OCCUPANCY_OPTIONS)
    assert state["occupancy_sub_select"] == "residential"


if __name__ == "__main__":
    test_normalize_accepts_json_list()
    test_load_overwrites_stale_picker_widgets()
    test_load_resolves_occupancy_when_category_label_drifted()
    test_load_ignores_empty_payload()
    print("4 passed")
