"""Helpers for .flsc scenario save/load.

Kept out of app.py so the occupancy-restore logic can be unit-tested without
importing Streamlit (app.py runs the full UI at import time).
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence, Tuple


def normalize_occupancy_chosen(chosen: Any) -> Optional[Tuple[str, str]]:
    """Accept the tuple used at runtime or the list written by JSON dumps."""
    if isinstance(chosen, (list, tuple)) and len(chosen) == 2:
        cat, occ = chosen
        if cat and occ:
            return str(cat), str(occ)
    return None


def apply_loaded_occupancy(
    state: Dict[str, Any],
    chosen: Any,
    occupancy_options: Mapping[str, Sequence[str]],
) -> None:
    """Write occupancy_chosen plus the two-stage picker widget keys.

    Streamlit selectboxes ignore their `index=` argument once the widget key
    already exists in session_state. Restoring only occupancy_chosen therefore
    leaves Category / Specific occupancy on the previously displayed values;
    the next render overwrites occupancy_chosen from those stale widgets and
    the loaded building is evaluated as the wrong occupancy.
    """
    pair = normalize_occupancy_chosen(chosen)
    if pair is None:
        return
    cat, occ = pair
    if cat in occupancy_options and occ in occupancy_options[cat]:
        state["occupancy_chosen"] = (cat, occ)
        state["occupancy_category_select"] = cat
        state["occupancy_sub_select"] = occ
        return
    for cat_label, occ_list in occupancy_options.items():
        if occ in occ_list:
            state["occupancy_chosen"] = (cat_label, occ)
            state["occupancy_category_select"] = cat_label
            state["occupancy_sub_select"] = occ
            return
