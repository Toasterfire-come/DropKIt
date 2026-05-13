"""Pack slip + QR-code PDF generator.

Produces a single-page A6-ish pack slip with order info, BOM checklist,
and a QR code that opens the fulfillment-confirmation page in the
warehouse phone scanner. Merges cleanly with EasyPost shipping label PDFs
via pypdf.
"""
from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import List, Optional

import qrcode
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _draw_qr(c: canvas.Canvas, url: str, x: float, y: float, size: float) -> None:
    img = qrcode.QRCode(box_size=8, border=2)
    img.add_data(url)
    img.make(fit=True)
    pil = img.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    pil.save(buf, format="PNG")
    buf.seek(0)
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(buf), x, y, width=size, height=size, mask="auto")


def render_pack_slip(
    *,
    order_id: str,
    shopify_order_id: Optional[str],
    recipient_name: str,
    recipient_address_lines: List[str],
    project_title: str,
    project_board: Optional[str],
    bom_lines: List[str],
    scan_url: str,
    tracking_code: Optional[str] = None,
    carrier: Optional[str] = None,
) -> bytes:
    """Return raw PDF bytes for a single pack slip (US-Letter portrait)."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    W, H = LETTER

    # Header band
    c.setFillColorRGB(0.91, 0.32, 0.04)  # circuit orange
    c.rect(0, H - 1.0 * inch, W, 1.0 * inch, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(0.5 * inch, H - 0.65 * inch, "DropKit")
    c.setFont("Helvetica", 10)
    c.drawString(0.5 * inch, H - 0.88 * inch, f"Pack slip · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    # Order identifiers (top right)
    c.setFont("Helvetica", 9)
    label = f"Order {(shopify_order_id or order_id)[-10:]}"
    c.drawRightString(W - 0.5 * inch, H - 0.65 * inch, label)
    if tracking_code:
        c.drawRightString(W - 0.5 * inch, H - 0.85 * inch, f"{carrier or 'CARRIER'} · {tracking_code}")

    # Ship-to
    y = H - 1.45 * inch
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.5 * inch, y, "SHIP TO")
    y -= 0.22 * inch
    c.setFont("Helvetica", 12)
    c.drawString(0.5 * inch, y, recipient_name or "—")
    c.setFont("Helvetica", 10)
    for line in recipient_address_lines:
        y -= 0.18 * inch
        c.drawString(0.5 * inch, y, line)

    # QR code (top right of body)
    _draw_qr(c, scan_url, W - 2.0 * inch, H - 3.0 * inch, 1.6 * inch)
    c.setFont("Helvetica", 8)
    c.drawCentredString(W - 1.2 * inch, H - 3.15 * inch, "Scan to fulfill")

    # Project block
    y = H - 3.6 * inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.5 * inch, y, "THIS MONTH'S KIT")
    y -= 0.28 * inch
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.5 * inch, y, project_title or "TBA")
    if project_board:
        y -= 0.22 * inch
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawString(0.5 * inch, y, project_board)

    # BOM checklist
    y -= 0.4 * inch
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.5 * inch, y, "PACK CHECKLIST")
    y -= 0.2 * inch
    c.setFont("Helvetica", 10)
    for line in bom_lines:
        if y < 1.2 * inch:
            c.showPage()
            y = H - 1.0 * inch
        c.rect(0.5 * inch, y - 0.02 * inch, 0.14 * inch, 0.14 * inch, fill=0, stroke=1)
        c.drawString(0.75 * inch, y, line)
        y -= 0.22 * inch

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColorRGB(0.45, 0.45, 0.45)
    c.drawString(0.5 * inch, 0.5 * inch,
                 "All schematics & firmware open-source at github.com/Toasterfire-come/DropKit-Projects · "
                 "Issues: support@dropkit · MIT / CC BY-SA")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def merge_pdfs(pdf_blobs: List[bytes]) -> bytes:
    """Merge a list of PDF byte blobs into one PDF."""
    from pypdf import PdfReader, PdfWriter
    out = PdfWriter()
    for blob in pdf_blobs:
        try:
            reader = PdfReader(BytesIO(blob))
            for page in reader.pages:
                out.add_page(page)
        except Exception:
            # Bad PDF — skip but don't fail the batch
            continue
    buf = BytesIO()
    out.write(buf)
    buf.seek(0)
    return buf.getvalue()
