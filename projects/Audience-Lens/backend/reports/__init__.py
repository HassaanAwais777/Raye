"""Reports module — structured reports + PDF/DOCX export."""
from .engine import build_report
from .generator import to_pdf, to_docx

__all__ = ["build_report", "to_pdf", "to_docx"]
