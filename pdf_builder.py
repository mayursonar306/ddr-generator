# pdf_builder.py — build the DDR PDF report

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus.flowables import Flowable

from config import (
    PDF_WHITE, PDF_BLACK, PDF_GREY, PDF_LIGHT,
    PDF_RED, PDF_AMBER, PDF_GREEN,
)

PAGE_W = A4[0] - 3.6 * cm   # usable width


# ── Paragraph styles ──────────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"],
            fontSize=22, textColor=PDF_WHITE, fontName="Helvetica-Bold",
            alignment=TA_CENTER),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"],
            fontSize=11, textColor=PDF_GREY, fontName="Helvetica",
            alignment=TA_CENTER, spaceAfter=4),
        "heading": ParagraphStyle("heading", parent=base["Normal"],
            fontSize=10.5, textColor=PDF_WHITE, fontName="Helvetica-Bold"),
        "body": ParagraphStyle("body", parent=base["Normal"],
            fontSize=9.5, fontName="Helvetica", leading=14,
            spaceAfter=4, alignment=TA_JUSTIFY),
        "caption": ParagraphStyle("caption", parent=base["Normal"],
            fontSize=7.5, fontName="Helvetica-Oblique",
            alignment=TA_CENTER, spaceAfter=2),
        "tbl_hdr": ParagraphStyle("tbl_hdr", parent=base["Normal"],
            fontSize=9, textColor=PDF_WHITE, fontName="Helvetica-Bold"),
        "footer": ParagraphStyle("footer", parent=base["Normal"],
            fontSize=7.5, fontName="Helvetica", alignment=TA_CENTER),
    }


# ── Section header: dark bar with bold title ──────────────────────────────────
class SectionHeader(Flowable):
    def __init__(self, number: str, title: str):
        super().__init__()
        self.number = number
        self.title  = title
        self.height = 28

    def draw(self):
        c = self.canv
        c.setFillColor(PDF_BLACK)
        c.rect(0, 0, PAGE_W, self.height, fill=1, stroke=0)
        c.setFillColor(PDF_WHITE)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(12, 9, f"{self.number}.  {self.title}")


# ── Table style ───────────────────────────────────────────────────────────────
def _tbl_style():
    return TableStyle([
        ("BACKGROUND",    (0, 0), (-1,  0), PDF_BLACK),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [PDF_WHITE, PDF_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.3, PDF_GREY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ])


# ── Photo grid ────────────────────────────────────────────────────────────────
def _photo_grid(story, photos, captions, s, cols=3, w=5.5*cm, h=4.2*cm):
    rows = []
    for i in range(0, len(photos), cols):
        img_row = []
        cap_row = []
        for path, cap in zip(photos[i:i+cols], captions[i:i+cols]):
            try:
                img_row.append(RLImage(path, width=w, height=h, kind="proportional"))
            except Exception:
                img_row.append(Paragraph("N/A", s["caption"]))
            cap_row.append(Paragraph(cap, s["caption"]))
        while len(img_row) < cols:
            img_row.append("")
            cap_row.append("")
        rows += [img_row, cap_row]
    tbl = Table(rows, colWidths=[(w + 4)] * cols)
    tbl.setStyle(TableStyle([
        ("ALIGN",  (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(tbl)


# ── Severity colour ───────────────────────────────────────────────────────────
def _sev_colour(sev: str):
    s = sev.lower()
    if "high" in s:     return PDF_RED
    if "moderate" in s: return PDF_AMBER
    return PDF_GREEN


# ── Sections ──────────────────────────────────────────────────────────────────
def _cover(story, ddr, s):
    story.append(Spacer(1, 2 * cm))

    tbl = Table([[Paragraph("DETAILED DIAGNOSTIC REPORT", s["title"])]],
                colWidths=[PAGE_W])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), PDF_BLACK),
        ("TOPPADDING",    (0,0), (-1,-1), 22),
        ("BOTTOMPADDING", (0,0), (-1,-1), 22),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))

    ps = ddr.get("property_summary", {})
    story.append(Paragraph(
        f"Property: {ps.get('property_type','N/A')}  |  "
        f"Floors: {ps.get('floors','N/A')}  |  "
        f"Date: {ps.get('inspection_date','N/A')}",
        s["subtitle"]
    ))
    story.append(Paragraph(
        f"Inspected By: {ps.get('inspected_by','N/A')}  |  "
        f"Score: {ps.get('overall_score','N/A')}  |  "
        f"Flagged: {ps.get('flagged_items','N/A')}",
        s["subtitle"]
    ))
    story.append(Spacer(1, 0.6 * cm))
    story.append(HRFlowable(width=PAGE_W, color=PDF_BLACK, thickness=1))
    story.append(Spacer(1, 0.4 * cm))

    # Issue summary box
    box = Table([[Paragraph(ddr.get("issue_summary", ""), s["body"])]],
                colWidths=[PAGE_W])
    box.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), PDF_LIGHT),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("RIGHTPADDING",  (0,0), (-1,-1), 14),
        ("BOX",           (0,0), (-1,-1), 0.5, PDF_GREY),
    ]))
    story.append(box)
    story.append(Spacer(1, 0.8 * cm))

    # Property details
    rows = [
        ["Property Type",   ps.get("property_type",  "N/A"), "Floors",          ps.get("floors",          "N/A")],
        ["Inspection Date", ps.get("inspection_date","N/A"), "Inspected By",    ps.get("inspected_by",    "N/A")],
        ["Previous Audit",  ps.get("previous_audit", "N/A"), "Previous Repair", ps.get("previous_repair", "N/A")],
        ["Score",           ps.get("overall_score",  "N/A"), "Flagged Items",   ps.get("flagged_items",   "N/A")],
    ]
    data = [[Paragraph(f"<b>{r[0]}</b>", s["body"]), Paragraph(r[1], s["body"]),
             Paragraph(f"<b>{r[2]}</b>", s["body"]), Paragraph(r[3], s["body"])]
            for r in rows]
    tbl2 = Table(data, colWidths=[PAGE_W * 0.22] * 4)
    tbl2.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), PDF_LIGHT),
        ("BACKGROUND",    (2,0), (2,-1), PDF_LIGHT),
        ("GRID",          (0,0), (-1,-1), 0.3, PDF_GREY),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(tbl2)
    story.append(PageBreak())


def _section1(story, ddr, s):
    story.append(SectionHeader("1", "PROPERTY ISSUE SUMMARY"))
    story.append(Spacer(1, 8))
    story.append(Paragraph(ddr.get("issue_summary", ""), s["body"]))
    story.append(Spacer(1, 0.5 * cm))


def _section2(story, ddr, s, site_photos, ir_photos):
    story.append(SectionHeader("2", "AREA-WISE OBSERVATIONS"))
    story.append(Spacer(1, 8))

    areas   = ddr.get("area_observations", [])
    n       = max(len(areas), 1)
    s_chunk = max(1, len(site_photos) // n)
    t_chunk = max(1, len(ir_photos)   // n)

    for i, obs in enumerate(areas):
        # Area title bar
        hdr = Table([[Paragraph(f"<b>{obs.get('area', f'Area {i+1}')}</b>", s["heading"])]],
                    colWidths=[PAGE_W])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), PDF_BLACK),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ]))
        story.append(KeepTogether([hdr]))
        story.append(Spacer(1, 5))

        # Details table
        details = [
            ("Issue",           obs.get("problem",         "Not Available")),
            ("Source",          obs.get("source",          "Not Available")),
            ("Thermal Reading", obs.get("thermal_reading", "Not Available")),
        ]
        det = Table([[Paragraph(f"<b>{k}</b>", s["body"]), Paragraph(v, s["body"])]
                     for k, v in details],
                    colWidths=[PAGE_W * 0.2, PAGE_W * 0.8])
        det.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (0,-1), PDF_LIGHT),
            ("GRID",          (0,0), (-1,-1), 0.3, PDF_GREY),
            ("TOPPADDING",    (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        story.append(det)
        story.append(Spacer(1, 6))

        # Site photos
        sp = [p for p in site_photos[i*s_chunk:(i+1)*s_chunk] if os.path.exists(p)]
        if sp:
            story.append(Paragraph("<b>Site Photos</b>", s["body"]))
            _photo_grid(story, sp[:6], [f"Photo {i*s_chunk+j+1}" for j in range(len(sp[:6]))], s)
            story.append(Spacer(1, 4))
        else:
            story.append(Paragraph("<i>Site photos: Not Available</i>", s["caption"]))

        # Thermal photos
        tp = [p for p in ir_photos[i*t_chunk:(i+1)*t_chunk] if os.path.exists(p)]
        if tp:
            story.append(Paragraph("<b>Thermal Images</b>", s["body"]))
            _photo_grid(story, tp[:3], [f"Thermal {i*t_chunk+j+1}" for j in range(len(tp[:3]))], s)
        else:
            story.append(Paragraph("<i>Thermal images: Not Available</i>", s["caption"]))

        story.append(Spacer(1, 0.4 * cm))
        story.append(HRFlowable(width=PAGE_W, color=PDF_GREY, thickness=0.3))
        story.append(Spacer(1, 0.3 * cm))

    story.append(PageBreak())


def _section3(story, ddr, s):
    story.append(SectionHeader("3", "PROBABLE ROOT CAUSE"))
    story.append(Spacer(1, 8))
    rows = [[Paragraph(f"<b>{i}</b>",
                ParagraphStyle("n", fontSize=9, textColor=PDF_WHITE,
                               fontName="Helvetica-Bold", alignment=TA_CENTER)),
             Paragraph(rc, s["body"])]
            for i, rc in enumerate(ddr.get("root_causes", []), 1)]
    style = [
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [PDF_WHITE, PDF_LIGHT]),
        ("GRID",          (0,0), (-1,-1), 0.3, PDF_GREY),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]
    for i in range(len(rows)):
        style.append(("BACKGROUND", (0,i), (0,i), PDF_BLACK))
    tbl = Table(rows, colWidths=[PAGE_W*0.06, PAGE_W*0.94])
    tbl.setStyle(TableStyle(style))
    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))


def _section4(story, ddr, s):
    story.append(SectionHeader("4", "SEVERITY ASSESSMENT"))
    story.append(Spacer(1, 8))
    h = s["tbl_hdr"]
    rows = [[Paragraph("<b>Area</b>", h), Paragraph("<b>Severity</b>", h), Paragraph("<b>Reasoning</b>", h)]]
    for item in ddr.get("severity_assessments", []):
        colour = _sev_colour(item.get("severity", ""))
        rows.append([
            Paragraph(item.get("area", ""),      s["body"]),
            Paragraph(f'<font color="white"><b>{item.get("severity","")}</b></font>',
                ParagraphStyle("sv", fontSize=9, fontName="Helvetica-Bold",
                               backColor=colour, borderPadding=3, alignment=TA_CENTER)),
            Paragraph(item.get("reasoning", ""), s["body"]),
        ])
    tbl = Table(rows, colWidths=[PAGE_W*0.30, PAGE_W*0.13, PAGE_W*0.57])
    tbl.setStyle(_tbl_style())
    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))


def _section5(story, ddr, s):
    story.append(SectionHeader("5", "RECOMMENDED ACTIONS"))
    story.append(Spacer(1, 8))
    h = s["tbl_hdr"]
    pri_colour = {"Immediate": PDF_RED, "Short-term": PDF_AMBER, "Long-term": PDF_GREEN}
    rows = [[Paragraph("<b>Priority</b>", h), Paragraph("<b>Action</b>", h)]]
    for act in ddr.get("recommended_actions", []):
        pri    = act.get("priority", "Short-term")
        colour = pri_colour.get(pri, PDF_AMBER)
        rows.append([
            Paragraph(f'<font color="white"><b>{pri}</b></font>',
                ParagraphStyle("pr", fontSize=8.5, fontName="Helvetica-Bold",
                               backColor=colour, borderPadding=3, alignment=TA_CENTER)),
            Paragraph(act.get("action", ""), s["body"]),
        ])
    tbl = Table(rows, colWidths=[PAGE_W*0.16, PAGE_W*0.84])
    tbl.setStyle(_tbl_style())
    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))


def _section6(story, ddr, s):
    story.append(SectionHeader("6", "ADDITIONAL NOTES"))
    story.append(Spacer(1, 8))
    for note in ddr.get("additional_notes", []):
        story.append(Paragraph(f"• {note}", s["body"]))
    story.append(Spacer(1, 0.5 * cm))


def _section7(story, ddr, s):
    story.append(SectionHeader("7", "MISSING INFORMATION"))
    story.append(Spacer(1, 8))
    for item in ddr.get("missing_information", []):
        story.append(Paragraph(f"• {item}", s["body"]))
    story.append(Spacer(1, 0.8 * cm))


# ── Main entry point ──────────────────────────────────────────────────────────
def build_pdf(ddr: dict, site_photos: list, ir_photos: list, output_path: str):
    """Build all 7 DDR sections into a single PDF file."""
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=1.8*cm, rightMargin=1.8*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title="Detailed Diagnostic Report",
    )
    s     = _styles()
    story = []

    _cover(story, ddr, s)
    _section1(story, ddr, s)
    _section2(story, ddr, s, site_photos, ir_photos)
    _section3(story, ddr, s)
    _section4(story, ddr, s)
    _section5(story, ddr, s)
    _section6(story, ddr, s)
    _section7(story, ddr, s)

    story.append(HRFlowable(width=PAGE_W, color=PDF_GREY, thickness=0.5))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Report based on visual and thermal observations only. "
        "Engage a licensed structural engineer for critical assessments.",
        s["footer"]
    ))

    doc.build(story)