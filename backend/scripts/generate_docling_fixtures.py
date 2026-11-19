"""Generate small synthetic, redistributable parser fixtures with known facts."""

from pathlib import Path
import json
from docx import Document
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

ROOT = Path(__file__).resolve().parents[1] / "tests/fixtures/docling"
ROOT.mkdir(parents=True, exist_ok=True)
cases = []


def register(name, expected, **extra):
    cases.append({"file": name, "expected": expected, **extra})


c = canvas.Canvas(str(ROOT / "single.pdf"))
c.setFont("Helvetica-Bold", 18)
c.drawString(60, 760, "Authentication")
c.setFont("Helvetica", 12)
c.drawString(60, 725, "AUTH_KEY_INVALID returns HTTP 401.")
c.save()
register("single.pdf", ["AUTH_KEY_INVALID", "401"], page=1)
c = canvas.Canvas(str(ROOT / "double.pdf"))
for x, title, text in [
    (40, "Authentication", "401 means invalid API token."),
    (320, "Rate limits", "429 means requests are throttled."),
]:
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x, 760, title)
    c.setFont("Helvetica", 10)
    c.drawString(x, 730, text)
c.save()
register("double.pdf", ["Authentication", "401", "Rate limits", "429"], page=1)
styles = getSampleStyleSheet()
table = Table([["Parameter", "Value"]] + [[f"limit_{i}", str(100 + i)] for i in range(65)], repeatRows=1)
table.setStyle(
    [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]
)
SimpleDocTemplate(str(ROOT / "crosspage-table.pdf")).build(
    [Paragraph("Quota parameters", styles["Heading1"]), table]
)
register("crosspage-table.pdf", ["Parameter", "limit_0", "100", "limit_64", "164"], table=True)
c = canvas.Canvas(str(ROOT / "code.pdf"))
c.setFont("Helvetica-Bold", 18)
c.drawString(50, 760, "API request example")
c.setFont("Courier", 10)
for i, line in enumerate(
    ["POST /v1/chat/completions", "Authorization: Bearer TOKEN", '{"model": "demo-model", "stream": true}']
):
    c.drawString(50, 720 - i * 20, line)
c.save()
register("code.pdf", ["/v1/chat/completions", "Bearer TOKEN", "demo-model"], page=1)
d = Document()
d.add_heading("Authentication", 0)
d.add_heading("Errors", 1)
d.add_paragraph("AUTH_KEY_INVALID returns HTTP 401.")
d.add_paragraph("Check the Authorization header.", style="List Bullet")
d.save(ROOT / "headings.docx")
register("headings.docx", ["AUTH_KEY_INVALID", "401", "Authorization"])
image = Image.new("RGB", (300, 100), "white")
ImageDraw.Draw(image).text((20, 40), "Example status diagram", fill="black")
image.save(ROOT / "diagram.png")
d = Document()
d.add_heading("Quota parameters", 0)
t = d.add_table(rows=1, cols=2)
t.rows[0].cells[0].text = "Parameter"
t.rows[0].cells[1].text = "Value"
row = t.add_row()
row.cells[0].text = "max_requests"
row.cells[1].text = "100"
d.add_picture(str(ROOT / "diagram.png"))
d.save(ROOT / "table-image.docx")
register("table-image.docx", ["max_requests", "100"], table=True)
c = canvas.Canvas(str(ROOT / "scanned.pdf"))
c.drawImage(str(ROOT / "diagram.png"), 50, 650, width=300, height=100)
c.save()
register("scanned.pdf", [], error="OCR_REQUIRED")
(ROOT / "corrupt.pdf").write_bytes(b"broken pdf")
register("corrupt.pdf", [], error="PARSE_TYPE")
(ROOT / "manifest.json").write_text(
    json.dumps({"license": "Synthetic project test fixtures", "cases": cases}, indent=2), encoding="utf-8"
)
# The same facts in three formats for a separate real embedding plumbing check.
body = "AUTH_KEY_INVALID returns HTTP 401. Use Authorization: Bearer TOKEN."
(ROOT / "equivalent.md").write_text("# Authentication\n" + body + "\n", encoding="utf-8")
c = canvas.Canvas(str(ROOT / "equivalent.pdf"))
c.setFont("Helvetica-Bold", 18)
c.drawString(50, 760, "Authentication")
c.setFont("Helvetica", 10)
c.drawString(50, 720, body)
c.save()
d = Document()
d.add_heading("Authentication", 1)
d.add_paragraph(body)
d.save(ROOT / "equivalent.docx")
print(f"Generated {len(cases)} fixtures in {ROOT}")
