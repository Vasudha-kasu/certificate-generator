import os

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


def fit_font_size(text, font_name, max_size, max_width):
    """Shrink the font until the text fits inside max_width."""
    size = max_size
    while stringWidth(text, font_name, size) > max_width and size > 10:
        size -= 1
    return size


def generate_certificate(recipient_name, course_name, issue_date, output_path):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    width, height = landscape(A4)
    c = canvas.Canvas(output_path, pagesize=(width, height))

    # Double border
    c.setLineWidth(4)
    c.rect(30, 30, width - 60, height - 60)
    c.setLineWidth(1)
    c.rect(40, 40, width - 80, height - 80)

    center = width / 2
    usable_width = width - 160

    c.setFont("Helvetica-Bold", 40)
    c.drawCentredString(center, height - 130, "Certificate of Completion")

    c.setFont("Helvetica", 18)
    c.drawCentredString(center, height - 190, "This is to certify that")

    name_size = fit_font_size(recipient_name, "Helvetica-Bold", 36, usable_width)
    c.setFont("Helvetica-Bold", name_size)
    c.drawCentredString(center, height - 260, recipient_name)

    c.setFont("Helvetica", 18)
    c.drawCentredString(center, height - 310, "has successfully completed")

    course_size = fit_font_size(course_name, "Helvetica-Bold", 26, usable_width)
    c.setFont("Helvetica-Bold", course_size)
    c.drawCentredString(center, height - 360, course_name)

    c.setFont("Helvetica", 14)
    c.drawCentredString(center, 90, f"Issued on {issue_date}")

    c.save()