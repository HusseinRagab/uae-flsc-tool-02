"""UAE FLSC 2018 - Word (.docx) and PDF exporters - multi-chapter."""
from __future__ import annotations

from io import BytesIO
from typing import List

from flsc_schema import ComplianceReport, Requirement, OCCUPANCY_DEFS, SectionBlock, DISCLAIMER
from figures import figure_caption, figures_for


def report_to_docx_bytes(r: ComplianceReport) -> bytes:
    from docx import Document
    from docx.shared import Pt, Cm
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.section import WD_ORIENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    def _fixed_table_layout(table, widths_cm):
        """Force Word to honour explicit column widths instead of auto-fitting
        to content. Two things are required: (1) w:tblLayout type='fixed', and
        (2) the w:tblGrid column widths — fixed layout renders from the GRID,
        not from per-cell widths, so without this the table falls back to
        equal columns."""
        tblPr = table._tbl.tblPr
        layout = tblPr.find(qn("w:tblLayout"))
        if layout is None:
            layout = OxmlElement("w:tblLayout")
            tblPr.append(layout)
        layout.set(qn("w:type"), "fixed")
        # 1 cm = 1440/2.54 twips. Set each grid column's width.
        grid = table._tbl.tblGrid
        cols = grid.findall(qn("w:gridCol"))
        for col, wcm in zip(cols, widths_cm):
            col.set(qn("w:w"), str(int(round(wcm * 1440 / 2.54))))

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)

    # Landscape A4 — wide page so the middle "Spec / Detail" column has room.
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Cm(29.7)
    section.page_height = Cm(21.0)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)
    section.top_margin = Cm(1.8)
    section.bottom_margin = Cm(1.8)

    # 3-column requirement-table widths (System / Spec-Detail / Code Ref).
    # x : 2x : x arrangement (6.5 / 13 / 6.5 cm = 26 cm, fits landscape A4) —
    # middle column stays the widest (carries the spec + detail text) while the
    # outer two get enough room that System names and long Code Refs no longer
    # wrap into 3+ lines.
    COL_SYSTEM = Cm(6.5)
    COL_SPEC = Cm(13.0)
    COL_CITE = Cm(6.5)

    title = doc.add_heading("UAE FLSC 2018 - Fire & Life Safety Requirements", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run("CDGH-OP-25, September 2018").italic = True

    b = r.building
    if b.project_name:
        p = doc.add_paragraph()
        run = p.add_run(f"Project: {b.project_name}")
        run.bold = True
        run.font.size = Pt(12)

    doc.add_heading("Building Profile", level=1)
    profile = [
        ("Occupancy", b.occupancy),
        ("Definition", OCCUPANCY_DEFS.get(b.occupancy, "")),
        ("Height", f"{b.height_m} m  ({b.height_class})"),
        ("Storeys", f"{b.floors_above_grade} above + {b.floors_below_grade} basement"),
        ("Plot area", f"{b.plot_area_m2} m2"),
        ("Ground-floor BUA", f"{b.ground_floor_bua_m2} m2"),
        ("Basement BUA", f"{b.basement_bua_m2} m2"),
        ("Total GFA", f"{b.gross_floor_area_m2} m2"),
        ("Hazard class", f"{b.hazard_class} (auto-derived)"),
    ]
    if b.has_high_ceiling:
        profile.append(("High ceiling", f"{b.ceiling_height_m} m"))
    if r.requires_wet_riser:
        profile.append(("Wet riser standpipes", str(b.wet_riser_standpipes)))
    tbl = doc.add_table(rows=len(profile), cols=2)
    tbl.style = "Light Grid Accent 1"
    for i, (k, v) in enumerate(profile):
        tbl.rows[i].cells[0].text = k
        tbl.rows[i].cells[1].text = str(v)

    def req_block(title: str, items: List[Requirement]):
        if not items:
            return
        doc.add_heading(title, level=1)
        t = doc.add_table(rows=1, cols=3)
        t.style = "Light Grid Accent 1"
        t.autofit = False
        t.allow_autofit = False
        _fixed_table_layout(t, [6.5, 13.0, 6.5])
        hdr = t.rows[0].cells
        hdr[0].text = "System"; hdr[1].text = "Spec / Detail"; hdr[2].text = "Code Ref"
        for cell in hdr:
            for par in cell.paragraphs:
                for run in par.runs:
                    run.bold = True
        for req in items:
            row = t.add_row().cells
            tag = "" if req.status == "required" else f" [{req.status}]"
            row[0].text = f"{req.system}{tag}"
            parts = []
            if req.spec:    parts.append(f"Spec: {req.spec}")
            if req.detail:  parts.append(req.detail)
            row[1].text = "\n\n".join(parts) if parts else "-"
            cite = " - ".join(p for p in (req.code_ref, req.page_ref) if p)
            row[2].text = cite or "-"
        # Word column widths must be set on every cell of the column to stick.
        for row in t.rows:
            row.cells[0].width = COL_SYSTEM
            row.cells[1].width = COL_SPEC
            row.cells[2].width = COL_CITE

    for ch in r.chapters:
        doc.add_heading(f"{ch.chapter_code} - {ch.chapter_title}", level=1)
        if ch.selected_branch:
            p = doc.add_paragraph()
            p.add_run("Matched branch: ").bold = True
            p.add_run(f"{ch.selected_branch}  -  {ch.selected_branch_section}")
        for block in ch.blocks:
            req_block(block.title, block.items)

    if r.high_ceiling and r.high_ceiling.applies:
        hc = r.high_ceiling
        doc.add_heading("FP - High Ceiling Sprinkler Design (Table 9.29.A)", level=1)
        rows = [
            ("Ceiling height", f"{hc.ceiling_height_m} m"),
            ("Hazard class", hc.hazard_class),
            ("Height band", hc.height_range or "out of tabulated range"),
            ("K-factor", hc.k_factor or "-"),
            ("Min pressure", hc.min_pressure or "-"),
            ("Min sprinklers", str(hc.min_sprinklers) if hc.min_sprinklers else "-"),
            ("Density", hc.density or "-"),
            ("Design area", hc.design_area or "-"),
            ("Pump (no hydrant)", f"{hc.pump_without_hydrant_gpm} gpm" if hc.pump_without_hydrant_gpm else "-"),
            ("Pump (with hydrant)", f"{hc.pump_with_hydrant_gpm} gpm" if hc.pump_with_hydrant_gpm else "-"),
        ]
        t = doc.add_table(rows=len(rows), cols=2)
        t.style = "Light Grid Accent 1"
        for i, (k, v) in enumerate(rows):
            t.rows[i].cells[0].text = k
            t.rows[i].cells[1].text = v
        if hc.note:
            doc.add_paragraph().add_run(f"Note: {hc.note}").italic = True

    doc.add_paragraph()
    doc.add_heading("Disclaimer", level=2)
    disc_p = doc.add_paragraph()
    disc_run = disc_p.add_run(DISCLAIMER)
    disc_run.italic = True
    disc_run.font.size = Pt(9)

    foot = doc.add_paragraph()
    foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = foot.add_run("Generated by UAE FLSC compliance tool. Not an official Civil Defence document.")
    run.italic = True
    run.font.size = Pt(8)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def report_to_pdf_bytes(r: ComplianceReport, kind: str = "detailed") -> bytes:
    if kind == "compact":
        return _compact_pdf(r)
    return _detailed_pdf(r)


def _rl_figure(fig, max_w, max_h):
    from reportlab.platypus import Image as RLImage, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib import colors

    path = fig["path"]
    if not path.exists():
        return []
    img = RLImage(str(path))
    iw, ih = float(img.imageWidth), float(img.imageHeight)
    scale = min(max_w / iw, max_h / ih)
    img.drawWidth = iw * scale
    img.drawHeight = ih * scale
    cap = ParagraphStyle(
        "figcap",
        fontName="Helvetica-Oblique",
        fontSize=8,
        textColor=colors.HexColor("#163A3A"),
        leading=10,
        spaceAfter=8,
    )
    return [img, Spacer(1, 4), Paragraph(figure_caption(fig).replace("—", "-"), cap)]


def _compact_pdf(r: ComplianceReport) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, ListFlowable, ListItem,
    )

    TEAL = colors.HexColor("#163A3A")
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.7 * cm, rightMargin=1.7 * cm,
        topMargin=1.6 * cm, bottomMargin=1.5 * cm,
        title="UAE FLSC compact report",
    )
    ss = getSampleStyleSheet()
    title_s = ParagraphStyle("t", parent=ss["Title"], fontSize=16, textColor=TEAL, spaceAfter=4)
    sub_s = ParagraphStyle("s", parent=ss["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=8)
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=11, textColor=TEAL, spaceBefore=10, spaceAfter=4)
    normal = ParagraphStyle("n", parent=ss["Normal"], fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8, textColor=colors.dimgrey, leading=10)

    b = r.building
    story = [
        Paragraph("UAE FIRE & LIFE SAFETY CODE 2018", title_s),
        Paragraph("CDGH-OP-25 | September 2018 | Compact report - required systems", sub_s),
        Paragraph(f"<b>{b.project_name or 'Fire & life safety report'}</b>", normal),
        Spacer(1, 8),
        Paragraph("Building profile", h1),
    ]
    profile = [
        ["Occupancy", b.occupancy],
        ["Height", f"{b.height_m} m ({b.height_class})"],
        ["Storeys", f"{b.floors_above_grade} above + {b.floors_below_grade} basement"],
        ["GFA", f"{b.gross_floor_area_m2} m2"],
        ["Hazard class", b.hazard_class],
    ]
    t = Table(profile, colWidths=[4.5 * cm, 12 * cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)

    req_n = rec_n = cond_n = na_n = 0
    for ch in r.chapters:
        for blk in ch.blocks:
            for it in blk.items:
                if it.status == "required":
                    req_n += 1
                elif it.status == "recommended":
                    rec_n += 1
                elif it.status == "conditional":
                    cond_n += 1
                else:
                    na_n += 1
    story.append(Spacer(1, 8))
    story.append(Paragraph("Requirement counts", h1))
    story.append(Paragraph(
        f"<b>Required {req_n}</b> &nbsp; Recommended {rec_n} &nbsp; "
        f"Conditional {cond_n} &nbsp; Not required {na_n}",
        normal,
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Required systems - headers only", h1))

    for ch in r.chapters:
        items = [it for blk in ch.blocks for it in blk.items if it.status == "required"]
        if not items:
            continue
        story.append(Paragraph(f"{ch.chapter_code} &nbsp; {ch.chapter_title}", h1))
        bullets = [ListItem(Paragraph(it.system, normal), leftIndent=12) for it in items]
        story.append(ListFlowable(bullets, bulletType="bullet", start="•"))

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=0.4, color=colors.grey))
    story.append(Paragraph(
        "Compact export. Use Detailed PDF for figures and full clauses.",
        small,
    ))
    story.append(Paragraph(f"<i>{DISCLAIMER}</i>", small))
    doc.build(story)
    return buf.getvalue()


def _detailed_pdf(r: ComplianceReport) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage,
    )
    from reportlab.lib.enums import TA_CENTER

    NAVY = colors.HexColor("#0B3D91")
    LIGHT = colors.HexColor("#E8EEF7")

    # Landscape A4 — gives the middle "Spec / Detail" column room to breathe.
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.8*cm, rightMargin=1.8*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm,
                            title="UAE FLSC Fire & Life Safety Report")
    ss = getSampleStyleSheet()
    title_s = ParagraphStyle("t", parent=ss["Title"], alignment=TA_CENTER,
                              fontSize=18, leading=22, spaceAfter=4, textColor=NAVY)
    sub_s = ParagraphStyle("s", parent=ss["Normal"], alignment=TA_CENTER,
                            fontSize=10, textColor=colors.grey, spaceAfter=10)
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=13, leading=16,
                        spaceBefore=12, spaceAfter=6, textColor=NAVY, fontName="Helvetica-Bold")
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11, leading=14,
                        spaceBefore=8, spaceAfter=4, textColor=NAVY, fontName="Helvetica-Bold")
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8,
                            textColor=colors.dimgrey, leading=10)
    normal = ParagraphStyle("n", parent=ss["Normal"], fontSize=9, leading=11)
    cite_s = ParagraphStyle("cite", parent=normal, fontSize=8,
                             textColor=colors.dimgrey, fontName="Helvetica-Oblique")
    # White header text — TableStyle TEXTCOLOR does NOT apply to Paragraph cell
    # content, so the navy header row needs its own white paragraph style.
    hdr_s = ParagraphStyle("hdr", parent=normal, fontSize=9,
                            textColor=colors.white, fontName="Helvetica-Bold")

    story = []
    story.append(Paragraph("UAE FLSC 2018 - Fire & Life Safety Requirements", title_s))
    story.append(Paragraph("CDGH-OP-25, September 2018", sub_s))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceBefore=0, spaceAfter=6))

    b = r.building
    if b.project_name:
        story.append(Paragraph(f"<b>Project:</b> {b.project_name}", normal))
        story.append(Spacer(1, 6))

    story.append(Paragraph("Building Profile", h1))
    profile = [
        ["Occupancy", Paragraph(b.occupancy, normal)],
        ["Definition", Paragraph(OCCUPANCY_DEFS.get(b.occupancy, ""), small)],
        ["Height", f"{b.height_m} m  ({b.height_class})"],
        ["Storeys", f"{b.floors_above_grade} above + {b.floors_below_grade} basement"],
        ["Plot area", f"{b.plot_area_m2} m²"],
        ["GF BUA / Basement BUA", f"{b.ground_floor_bua_m2} m² / {b.basement_bua_m2} m²"],
        ["Total GFA", f"{b.gross_floor_area_m2} m²"],
        ["Hazard class", f"{b.hazard_class} (auto-derived)"],
    ]
    if b.has_high_ceiling:
        profile.append(["High ceiling", f"{b.ceiling_height_m} m"])
    if r.requires_wet_riser:
        profile.append(["Wet riser standpipes", str(b.wet_riser_standpipes)])
    t = Table(profile, colWidths=[5*cm, 21*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    def req_block(title: str, items: List[Requirement]):
        if not items:
            return
        story.append(Paragraph(title, h2))
        data = [[Paragraph("System", hdr_s),
                 Paragraph("Spec / Detail", hdr_s),
                 Paragraph("Code Ref", hdr_s)]]
        for req in items:
            tag = "" if req.status == "required" else f" <font color=grey>[{req.status}]</font>"
            sys_p = Paragraph(f"<b>{req.system}</b>{tag}", normal)
            parts = []
            if req.spec:    parts.append(f"<b>Spec:</b> {req.spec}")
            if req.detail:  parts.append(req.detail)
            spec_p = Paragraph("<br/><br/>".join(parts), small) if parts else Paragraph("-", small)
            cite_t = " - ".join(p for p in (req.code_ref, req.page_ref) if p)
            cite_p = Paragraph(cite_t, cite_s) if cite_t else Paragraph("-", cite_s)
            data.append([sys_p, spec_p, cite_p])
        # x : 2x : x column arrangement (6.5 / 13 / 6.5 cm = 26 cm, landscape A4).
        # Middle (Spec / Detail) stays the widest; outer columns get enough room
        # that System names and long Code Refs stop wrapping into 3+ lines.
        t = Table(data, colWidths=[6.5*cm, 13*cm, 6.5*cm], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.white, colors.HexColor("#F6F8FC")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

    for ch in r.chapters:
        story.append(Paragraph(f"{ch.chapter_code} - {ch.chapter_title}", h1))
        if ch.selected_branch:
            story.append(Paragraph(
                f"<b>Matched branch:</b> {ch.selected_branch} - {ch.selected_branch_section}", normal))
            story.append(Spacer(1, 4))
        for fig in figures_for(ch.chapter_code):
            story.extend(_rl_figure(fig, 16 * cm, 8.5 * cm))
        for block in ch.blocks:
            req_block(block.title, block.items)

    if r.high_ceiling and r.high_ceiling.applies:
        hc = r.high_ceiling
        story.append(Paragraph("FP - High Ceiling Sprinkler Design (Table 9.29.A)", h1))
        hc_data = [
            ["Ceiling height", f"{hc.ceiling_height_m} m"],
            ["Hazard class", hc.hazard_class],
            ["Height band", hc.height_range or "out of tabulated range"],
            ["K-factor", hc.k_factor or "-"],
            ["Min pressure", hc.min_pressure or "-"],
            ["Min sprinklers", str(hc.min_sprinklers) if hc.min_sprinklers else "-"],
            ["Density", hc.density or "-"],
            ["Design area", hc.design_area or "-"],
            ["Pump (no hydrant)", f"{hc.pump_without_hydrant_gpm} gpm" if hc.pump_without_hydrant_gpm else "-"],
            ["Pump (with hydrant)", f"{hc.pump_with_hydrant_gpm} gpm" if hc.pump_with_hydrant_gpm else "-"],
        ]
        t = Table(hc_data, colWidths=[5*cm, 21*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), LIGHT),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ]))
        story.append(t)
        if hc.note:
            story.append(Paragraph(f"<i>Note: {hc.note}</i>", small))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 4))
    disc_style = ParagraphStyle("disc", parent=normal, fontSize=8, leading=10,
                                 textColor=colors.dimgrey,
                                 fontName="Helvetica-Oblique")
    story.append(Paragraph(f"<b>Disclaimer.</b> {DISCLAIMER}", disc_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Generated by UAE FLSC compliance tool. Not an official Civil Defence document.",
        small))

    doc.build(story)
    return buf.getvalue()
