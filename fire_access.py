"""UAE FLSC 2018 Chapter 2 — Fire Service Access (Tables 2.2–2.7)."""
from __future__ import annotations
from typing import List, Tuple
from flsc_schema import Building, ChapterReport, FireAccessSummary, Requirement, SectionBlock

def _sprinklered(b: Building, requires_wet_riser: bool = False) -> bool:
    if b.height_class in ("highrise", "super_highrise"):
        return True
    if b.occupancy.startswith("villa_"):
        return False
    if b.height_class == "midrise":
        return True
    return requires_wet_riser or b.height_m > 15

def _footprint_m2(b: Building) -> float:
    if b.ground_floor_bua_m2 and b.ground_floor_bua_m2 > 0:
        return float(b.ground_floor_bua_m2)
    if b.gross_floor_area_m2 and b.floors_above_grade:
        return float(b.gross_floor_area_m2) / max(1, b.floors_above_grade)
    return float(b.gross_floor_area_m2 or 0)

def _volume_m3(b: Building) -> float:
    area = float(b.gross_floor_area_m2 or _footprint_m2(b))
    return area * 3.5 if area else 0.0

def _extent_midrise_nonsprinklered(footprint: float) -> Tuple[str, str]:
    if footprint < 2000:
        return "Minimum 1/6 perimeter (at least 15 m)", "Table 2.3 < 2,000 m²"
    if footprint <= 4000:
        return "1/4 perimeter", "Table 2.3 2,000–4,000 m²"
    if footprint <= 8000:
        return "1/2 perimeter", "Table 2.3 4,001–8,000 m²"
    if footprint <= 16000:
        return "3/4 perimeter", "Table 2.3 8,001–16,000 m²"
    return "Whole perimeter (100%)", "Table 2.3 > 16,000 m²"

def _extent_mid_high_sprinklered(footprint: float) -> Tuple[str, str]:
    if footprint < 4000:
        return "Minimum 1/6 perimeter (at least 15 m)", "Table 2.4 < 4,000 m²"
    if footprint <= 8000:
        return "1/4 perimeter", "Table 2.4 4,001–8,000 m²"
    if footprint <= 16000:
        return "1/2 perimeter", "Table 2.4 8,001–16,000 m²"
    if footprint <= 32000:
        return "3/4 perimeter", "Table 2.4 16,001–32,000 m²"
    return "Whole perimeter (100%)", "Table 2.4 > 32,000 m²"

def _extent_industrial(volume: float, sprinklered: bool) -> Tuple[str, str]:
    if not sprinklered:
        if volume < 28400:
            return "Minimum 1/6 perimeter (at least 15 m)", "Table 2.6 < 28,400 m³"
        if volume <= 56800:
            return "1/4 perimeter", "Table 2.6 28,400–56,800 m³"
        if volume <= 85200:
            return "1/2 perimeter", "Table 2.6 56,801–85,200 m³"
        if volume <= 113600:
            return "3/4 perimeter", "Table 2.6 85,201–113,600 m³"
        return "Whole perimeter (100%)", "Table 2.6 > 113,600 m³"
    if volume < 56800:
        return "Minimum 1/6 perimeter (at least 15 m)", "Table 2.7 < 56,800 m³"
    if volume <= 85200:
        return "1/4 perimeter", "Table 2.7 56,801–85,200 m³"
    if volume <= 113600:
        return "1/2 perimeter", "Table 2.7 85,201–113,600 m³"
    if volume <= 170400:
        return "3/4 perimeter", "Table 2.7 113,601–170,400 m³"
    return "Whole perimeter (100%)", "Table 2.7 > 170,400 m³"

def compute_fire_access(b: Building, requires_wet_riser: bool = False) -> FireAccessSummary:
    spr = _sprinklered(b, requires_wet_riser)
    fp = _footprint_m2(b)
    notes: List[str] = [
        "Accessway min width 6 m; vertical clearance 4.5 m (Table 2.2 / §2.6).",
        "Max parking distance: 15 m from building entrance, 18 m from breeching inlet.",
        "Max road grade 10%.",
    ]
    is_mall = b.occupancy.startswith("mall_")
    is_storage = b.occupancy == "storage_industrial"
    is_super = b.height_class == "super_highrise"
    is_low = b.height_class == "lowrise" and b.height_m <= 15
    if is_super or is_mall:
        extent, ref = "3/4 perimeter (min.)", "Table 2.5 super-highrise / malls / theme parks"
        notes.append("Not less than Table 2.3 or 2.4 where those give a greater extent.")
    elif is_storage:
        vol = _volume_m3(b)
        extent, ref = _extent_industrial(vol, spr)
        notes.append(f"Gross cubical extent proxy ≈ {vol:,.0f} m³ (GFA × 3.5 m storey).")
    elif is_low and not spr:
        extent, ref = "Provide fire access road to within 15 m of entrance", "§2.6 / Table 2.2 (lowrise)"
    elif not spr and b.height_class == "midrise":
        extent, ref = _extent_midrise_nonsprinklered(fp)
    else:
        extent, ref = _extent_mid_high_sprinklered(fp)
    return FireAccessSummary(
        extent=extent, extent_ref=ref, footprint_m2=fp,
        sprinklered_assumed=spr, notes=notes,
    )

def evaluate_fire_access(b: Building, requires_wet_riser: bool = False) -> ChapterReport:
    s = compute_fire_access(b, requires_wet_riser)
    items = [
        Requirement(system="Fire vehicle accessway width + clearance", status="required",
            spec=f"Min width {s.accessway_width_m:g} m; vertical clearance {s.vertical_clearance_m:g} m",
            detail="; ".join(s.notes[:3]), code_ref="Ch 2, §2.6 / Table 2.2", page_ref="p.207",
            source_rule="fsa_table_2_2"),
        Requirement(system="Parking distance to entrance / breeching inlet", status="required",
            spec=f"≤ {s.max_distance_entrance_m:g} m from entrance; ≤ {s.max_distance_breeching_m:g} m from breeching inlet",
            code_ref="Ch 2, Table 2.2", page_ref="p.207", source_rule="fsa_table_2_2_distances"),
        Requirement(system="Extent of fire vehicle access around building", status="required",
            spec=s.extent,
            detail=f"Footprint ≈ {s.footprint_m2:,.0f} m²; sprinklered assumed: {s.sprinklered_assumed}. {s.extent_ref}.",
            code_ref=s.extent_ref.split()[0] if s.extent_ref else "Ch 2, §2.8", page_ref="p.213–215",
            source_rule="fsa_extent"),
        Requirement(system="Access road grade", status="required",
            spec=f"Maximum road grade {s.max_road_grade_pct:g}%",
            code_ref="Ch 2, Table 2.2", page_ref="p.207", source_rule="fsa_grade"),
    ]
    if b.height_m > 15:
        items.append(Requirement(
            system="Accessway within 18 m of breeching inlet", status="required",
            spec="Required for midrise and highrise exceeding 15 m habitable height",
            code_ref="Ch 2, §2.6.2", page_ref="p.207", source_rule="fsa_breeching_18m"))
    return ChapterReport(
        chapter_code="FSA", chapter_title="Fire Service Access (Ch 2)",
        selected_branch="fsa_auto", selected_branch_section=s.extent_ref,
        blocks=[SectionBlock(title="FSA - Vehicle access & extent (Ch 2)", items=items)],
        extras={"fire_access": s.model_dump()},
    )
