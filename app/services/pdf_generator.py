"""Generación simple de solicitudes PDF con ReportLab."""

import re
from datetime import date
from pathlib import Path
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.rag.knowledge_base import Tramite


def _safe_filename(value: str) -> str:
    """Crea un fragmento de nombre de archivo sin caracteres especiales."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _draw_wrapped_text(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_characters: int = 90,
    line_height: int = 14,
) -> float:
    """Dibuja texto con un ajuste de línea suficiente para la plantilla del MVP."""
    words = text.split()
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if len(candidate) > max_characters and line:
            pdf.drawString(x, y, line)
            y -= line_height
            line = word
        else:
            line = candidate
    if line:
        pdf.drawString(x, y, line)
        y -= line_height
    return y


def generate_application_pdf(
    tramite: Tramite,
    applicant_name: str,
    output_directory: Path,
) -> Path:
    """Crea y devuelve un PDF de solicitud para uno de los trámites definidos."""
    output_directory.mkdir(parents=True, exist_ok=True)
    filename = f"solicitud-{_safe_filename(tramite.nombre)}-{uuid4().hex[:8]}.pdf"
    file_path = output_directory / filename

    pdf = canvas.Canvas(str(file_path), pagesize=A4)
    page_width, page_height = A4
    margin = 2 * cm
    y = page_height - margin

    pdf.setFillColor(colors.HexColor("#0B4F6C"))
    pdf.rect(0, page_height - 3.2 * cm, page_width, 3.2 * cm, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margin, page_height - 1.7 * cm, "GAD Municipal de Portoviejo")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin, page_height - 2.35 * cm, "Solicitud generada por PortoAsiste IA")

    y = page_height - 4.4 * cm
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin, y, "Solicitud de trámite municipal")
    y -= 1.1 * cm

    pdf.setFont("Helvetica", 11)
    pdf.drawString(margin, y, f"Fecha: {date.today().isoformat()}")
    y -= 0.7 * cm
    pdf.drawString(margin, y, f"Solicitante: {applicant_name.strip()}")
    y -= 0.7 * cm
    pdf.drawString(margin, y, f"Trámite solicitado: {tramite.nombre}")
    y -= 1.0 * cm

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, y, "Descripción")
    y -= 0.5 * cm
    pdf.setFont("Helvetica", 10)
    y = _draw_wrapped_text(pdf, tramite.descripcion, margin, y)
    y -= 0.4 * cm

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(margin, y, "Requisitos referenciales")
    y -= 0.5 * cm
    pdf.setFont("Helvetica", 10)
    for requirement in tramite.requisitos:
        y = _draw_wrapped_text(pdf, f"- {requirement}", margin, y, max_characters=85)

    y -= 0.3 * cm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(margin, y, "Costo estimado:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin + 3.4 * cm, y, tramite.costo_estimado)
    y -= 0.6 * cm
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(margin, y, "Tiempo estimado:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margin + 3.8 * cm, y, tramite.tiempo_estimado)

    y -= 2.2 * cm
    pdf.line(margin, y, margin + 7 * cm, y)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(margin, y - 0.45 * cm, "Firma del solicitante")
    pdf.setFillColor(colors.grey)
    pdf.drawRightString(page_width - margin, 1.5 * cm, "Documento referencial para el MVP")
    pdf.save()
    return file_path
