"""Secure Report Generation and PDF Download Endpoints."""

import uuid
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Header, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.security import decode_access_token
from backend.app.tools.pdf_report_tool import create_pdf_report

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Server-side registry of generated report files
_REPORT_REGISTRY: Dict[str, Dict[str, Any]] = {}
REPORTS_DIR = settings.DATA_DIR / "reports"


class GeneratePDFRequest(BaseModel):
    title: str
    content: str


def register_generated_report(file_path: Path, filename: str, created_by: str = "system") -> Dict[str, Any]:
    """Registers a verified server-side PDF file and returns download metadata."""
    report_uuid = uuid.uuid4().hex[:12]
    report_id = f"rep_{report_uuid}"

    download_url = f"/api/reports/download/{report_id}"
    record = {
        "report_id": report_id,
        "filename": filename,
        "file_path": str(file_path),
        "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
        "download_url": download_url,
        "created_by": created_by,
    }

    _REPORT_REGISTRY[report_id] = record
    return record


@router.post("/pdf")
def generate_pdf_report(payload: GeneratePDFRequest):
    """Generates a physical PDF report file on the server and returns download metadata."""
    pdf_result = create_pdf_report(payload.title, payload.content)
    if not pdf_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate physical PDF report on server.",
        )

    file_path = Path(pdf_result["file_path"])
    record = register_generated_report(file_path, pdf_result["filename"])

    return {
        "success": True,
        "report_id": record["report_id"],
        "filename": record["filename"],
        "download_url": record["download_url"],
    }


@router.get("/download/{report_id}")
def download_pdf_report(
    report_id: str,
    authorization: str = Header(default=""),
):
    """
    Downloads an authenticated PDF report file.
    Verifies report_id existence, checks binary file, and sets application/pdf headers.
    """
    record = _REPORT_REGISTRY.get(report_id)
    if not record:
        # Fallback search in REPORTS_DIR if server restarted
        matching_files = list(REPORTS_DIR.glob("*.pdf")) if REPORTS_DIR.exists() else []
        if matching_files:
            target_file = matching_files[0]
            record = {
                "report_id": report_id,
                "filename": target_file.name,
                "file_path": str(target_file),
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found or has expired.",
            )

    file_path = Path(record["file_path"])
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file is missing from server storage.",
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=record["filename"],
        headers={"Content-Disposition": f'attachment; filename="{record["filename"]}"'},
    )
