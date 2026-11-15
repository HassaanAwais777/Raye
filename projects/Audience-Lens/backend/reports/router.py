"""FastAPI router for report generation + PDF/DOCX export."""
from __future__ import annotations

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from .engine import build_report
from .generator import to_pdf, to_docx

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


class ReportReq(BaseModel):
    texts: list[str] = Field(..., min_length=1)
    meta: dict = Field(default_factory=dict)
    aspect_catalog: str = "general"
    cluster_method: str = "kmeans"


class ExportReq(ReportReq):
    format: str = "pdf"  # pdf | docx


@router.post("/generate")
def generate_endpoint(req: ReportReq):
    """Build a structured report (JSON) from comments."""
    return build_report(req.texts, req.meta, req.aspect_catalog, req.cluster_method)


@router.post("/export")
def export_endpoint(req: ExportReq):
    """Generate and download a report as PDF or DOCX."""
    report = build_report(req.texts, req.meta, req.aspect_catalog, req.cluster_method)
    fmt = req.format.lower()
    if fmt == "docx":
        content = to_docx(report)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="audience-intelligence-report.docx"'},
        )
    # default pdf
    content = to_pdf(report)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="audience-intelligence-report.pdf"'},
    )
