"""Report renderers — produce downloadable PDF (reportlab) and DOCX (python-docx)
files from a structured report. Returns bytes.
"""
from __future__ import annotations

import io
from typing import Any

PROV_COLORS = {
    "LIVE_DATA": "#0f7b53",
    "MODEL_PREDICTION": "#b8860b",
    "ESTIMATED_SCENARIO": "#cc5500",
    "INFERENCE": "#9b1f9b",
    "USER_INPUT": "#555555",
    "INSUFFICIENT_DATA": "#b91c1c",
}


def _prov_color(p: str) -> str:
    return PROV_COLORS.get(p, "#555555")


# ---------------------------------------------------------------------------
# PDF (reportlab)
# ---------------------------------------------------------------------------

def to_pdf(report: dict[str, Any]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    from reportlab.lib.enums import TA_LEFT

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=18, textColor=colors.HexColor("#0f7b53"), spaceAfter=4)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, textColor=colors.HexColor("#1a1a1a"), spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=10, leading=14, alignment=TA_LEFT, spaceAfter=4)
    small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=8, textColor=colors.HexColor("#666666"))
    meta = report.get("meta", {})

    flow = []
    flow.append(Paragraph(meta.get("title", "Audience Intelligence Report"), h1))
    flow.append(Paragraph(f"Objective: {meta.get('objective') or '—'}", small))
    flow.append(Paragraph(
        f"Prepared by: {meta.get('prepared_by') or '—'}  ·  Country: {meta.get('country') or '—'}  ·  "
        f"Industry: {meta.get('industry') or '—'}  ·  Generated: {meta.get('generated_at','')[:10]}",
        small))
    flow.append(Paragraph(f"Sample size: {report.get('n_comments', 0)} comments  ·  {report.get('n_findings', 0)} findings", small))
    flow.append(Spacer(1, 6))
    flow.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc")))
    flow.append(Spacer(1, 8))

    for sec in report.get("sections", []):
        flow.append(Paragraph(sec["title"], h2))
        prov = sec.get("provenance", "")
        flow.append(Paragraph(f'<font color="{_prov_color(prov)}">[{prov}]</font>  confidence: {sec.get("confidence", "—")}', small))
        if sec.get("body"):
            flow.append(Paragraph(str(sec["body"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), body))

        metrics = sec.get("metrics", [])
        if metrics:
            data = [["Metric", "Value"]] + [[m.get("label", ""), m.get("value", "")] for m in metrics]
            t = Table(data, colWidths=[80*mm, 60*mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f7b53")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]))
            flow.append(t)

        for ev in sec.get("evidence", []):
            flow.append(Paragraph(f'<i>{ev.get("label","")}: “{ev.get("value","")}”</i>', small))

        if sec.get("recommended_action"):
            flow.append(Paragraph(f'<b>Recommended action:</b> {sec["recommended_action"]}', body))
        if sec.get("note"):
            flow.append(Paragraph(f'<i>{sec["note"]}</i>', small))
        flow.append(Spacer(1, 6))

    flow.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc")))
    flow.append(Paragraph(report.get("disclaimer", ""), small))

    doc.build(flow)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# DOCX (python-docx)
# ---------------------------------------------------------------------------

def to_docx(report: dict[str, Any]) -> bytes:
    from docx import Document
    from docx.shared import Pt, RGBColor, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    meta = report.get("meta", {})

    title = doc.add_heading(meta.get("title", "Audience Intelligence Report"), level=0)
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x0F, 0x7B, 0x53)

    p = doc.add_paragraph()
    p.add_run(f"Objective: ").bold = True
    p.add_run(meta.get("objective") or "—")
    p = doc.add_paragraph()
    p.add_run("Prepared by: ").bold = True
    p.add_run(f"{meta.get('prepared_by') or '—'}    ")
    p.add_run("Country: ").bold = True
    p.add_run(f"{meta.get('country') or '—'}    ")
    p.add_run("Industry: ").bold = True
    p.add_run(meta.get("industry") or "—")
    p = doc.add_paragraph()
    p.add_run("Generated: ").bold = True
    p.add_run(f"{meta.get('generated_at','')[:10]}    ")
    p.add_run("Sample size: ").bold = True
    p.add_run(f"{report.get('n_comments', 0)} comments    ")
    p.add_run("Findings: ").bold = True
    p.add_run(str(report.get("n_findings", 0)))

    doc.add_paragraph()._p.add_sibling_after = None  # spacer

    for sec in report.get("sections", []):
        h = doc.add_heading(sec["title"], level=1)
        for run in h.runs:
            run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
        prov = sec.get("provenance", "")
        pp = doc.add_paragraph()
        r = pp.add_run(f"[{prov}]")
        r.font.size = Pt(8)
        r.font.color.rgb = RGBColor.from_string(_prov_color(prov).lstrip("#"))
        r2 = pp.add_run(f"   confidence: {sec.get('confidence', '—')}")
        r2.font.size = Pt(8)
        r2.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

        if sec.get("body"):
            doc.add_paragraph(str(sec["body"]))

        metrics = sec.get("metrics", [])
        if metrics:
            tbl = doc.add_table(rows=1, cols=2)
            tbl.style = "Light List Accent 1"
            hdr = tbl.rows[0].cells
            hdr[0].text = "Metric"
            hdr[1].text = "Value"
            for m in metrics:
                row = tbl.add_row().cells
                row[0].text = str(m.get("label", ""))
                row[1].text = str(m.get("value", ""))

        for ev in sec.get("evidence", []):
            ep = doc.add_paragraph()
            ep.add_run(f'{ev.get("label","")}: ').italic = True
            q = ep.add_run(f'“{ev.get("value","")}”')
            q.italic = True
            q.font.size = Pt(9)

        if sec.get("recommended_action"):
            ap = doc.add_paragraph()
            ap.add_run("Recommended action: ").bold = True
            ap.add_run(sec["recommended_action"])
        if sec.get("note"):
            np = doc.add_paragraph(sec["note"])
            for run in np.runs:
                run.italic = True
                run.font.size = Pt(9)

    doc.add_paragraph()
    fp = doc.add_paragraph(report.get("disclaimer", ""))
    for run in fp.runs:
        run.italic = True
        run.font.size = Pt(8)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
