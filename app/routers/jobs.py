import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.schemas import JobCreateRequest, JobDetailOut, JobOut
from app.services.processor import create_job, process_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/", response_model=JobOut, status_code=202)
def submit_job(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = create_job(db, payload.course_name, payload.recipients)
    if job.status == JobStatus.PENDING:
        background_tasks.add_task(process_job, job.id)
    return job


@router.get("/{job_id}/", response_model=JobDetailOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/certificates/{certificate_id}/")
def download_certificate(
    job_id: str, certificate_id: str, db: Session = Depends(get_db)
):
    cert = (
        db.query(Certificate)
        .filter(Certificate.id == certificate_id, Certificate.job_id == job_id)
        .first()
    )
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if (
        cert.status != CertificateStatus.SUCCESS
        or not cert.file_path
        or not os.path.exists(cert.file_path)
    ):
        raise HTTPException(status_code=404, detail="Certificate file not available")

    return FileResponse(
        cert.file_path,
        media_type="application/pdf",
        filename=f"certificate_{cert.id[:8]}.pdf",
    )