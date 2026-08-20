"""Authentic UAE FLSC 2018 plates (screenshots from the code)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, TypedDict

ROOT = Path(__file__).parent
FIG_DIR = ROOT / "assets" / "flsc-figures"


class CodeFigure(TypedDict):
    chapter_code: str
    path: Path
    figure: str
    title: str
    page: Optional[int]


CHAPTER_FIGURES: dict[str, List[CodeFigure]] = {
    "MOE": [
        {
            "chapter_code": "MOE",
            "path": FIG_DIR / "moe-3.1.png",
            "figure": "Figure 3.1",
            "title": "Head room in means of egress",
            "page": 246,
        },
        {
            "chapter_code": "MOE",
            "path": FIG_DIR / "moe-3.2.png",
            "figure": "Figure 3.2",
            "title": "Measuring Door Assembly width",
            "page": 247,
        },
    ],
    "FE": [
        {
            "chapter_code": "FE",
            "path": FIG_DIR / "fe-water-ext.png",
            "figure": "Illustration",
            "title": "Water Type Extinguisher (red colour code)",
            "page": None,
        },
    ],
    "ES": [
        {
            "chapter_code": "ES",
            "path": FIG_DIR / "es-5.5.png",
            "figure": "Figure 5.5",
            "title": "EXIT SIGN and DIRECTIONAL EXIT SIGN MOUNTING",
            "page": 396,
        },
    ],
    "EL": [
        {
            "chapter_code": "EL",
            "path": FIG_DIR / "el-6.5.png",
            "figure": "Figure 6.5",
            "title": "Typical Central Battery Emergency Lighting",
            "page": 414,
        },
    ],
    "EVC": [
        {
            "chapter_code": "EVC",
            "path": FIG_DIR / "evc-firefighter-phone.png",
            "figure": "Illustration",
            "title": "Two-way telephone jack for fire fighters",
            "page": None,
        },
    ],
    "FA": [
        {
            "chapter_code": "FA",
            "path": FIG_DIR / "fa-8.24.png",
            "figure": "Figure 8.24",
            "title": "Installation of Manual Call Points",
            "page": 498,
        },
    ],
    "FP": [
        {
            "chapter_code": "FP",
            "path": FIG_DIR / "fp-horizontal-pump.png",
            "figure": "Illustration",
            "title": "Horizontal fire pump for illustration",
            "page": 569,
        },
    ],
    "SC": [
        {
            "chapter_code": "SC",
            "path": FIG_DIR / "sc-10.24.png",
            "figure": "Schematic 10.24",
            "title": "Typical Corridor and Open circulation area Mechanical Smoke Purge System",
            "page": 823,
        },
    ],
    "LPG": [
        {
            "chapter_code": "LPG",
            "path": FIG_DIR / "lpg-11.7.png",
            "figure": "Figure 11.7",
            "title": "Aboveground LPG Tank installation",
            "page": 905,
        },
    ],
}


def figures_for(code: str) -> List[CodeFigure]:
    return CHAPTER_FIGURES.get(code, [])


def figure_caption(fig: CodeFigure) -> str:
    loc = f"p.{fig['page']} of 1348" if fig["page"] else "code illustration"
    return f"{fig['figure']} — {fig['title']} | UAE FLSC 2018 {loc}"
