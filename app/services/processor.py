from datetime import date

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Certificate, CertificateStatus, Job, JobStatus
from app.schemas import RecipientData
from app.services.pdf_generator import generate_certificate

OUTPUT_DIR = "generated"


def _as_text(value):
    """Turn whatever the client sent into a short string we can safely store."""
    if value is None:
        return None
    return str(value)[:100]


def _format_errors(error: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
        for err in error.errors()
    )


def create_job(db: Session, course_name: str, recipients: list[dict]) -> Job:
    job = Job(
        total=len(recipients),
        succeeded=0,
        failed=0,
        status=JobStatus.PENDING,
    )

    for raw in recipients:
        try:
            data = RecipientData.model_validate(raw)
        except ValidationError as exc:
            job.certificates.append(
                Certificate(
                    recipient_name=_as_text(raw.get("name")),
                    recipient_email=_as_text(raw.get("email")),
                    course_name=course_name,
                    status=CertificateStatus.FAILED,
                    error_message=_format_errors(exc),
                )
            )
            job.failed += 1
        else:
            job.certificates.append(
                Certificate(
                    recipient_name=data.name,
                    recipient_email=data.email,
                    course_name=course_name,
                    status=CertificateStatus.PENDING,
                )
            )

    if job.failed == job.total:
        job.status = JobStatus.COMPLETED  # nothing left to generate

    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def process_job(job_id: str) -> None:
    db = SessionLocal()  # our own session: the request's one is already closed
    try:
        job = db.get(Job, job_id)
        if job is None:
            return

        job.status = JobStatus.PROCESSING
        db.commit()

        pending = [
            c for c in job.certificates if c.status == CertificateStatus.PENDING
        ]
        issue_date = date.today().strftime("%d %B %Y")

        for cert in pending:
            try:
                path = f"{OUTPUT_DIR}/{job_id}/{cert.id}.pdf"
                generate_certificate(
                    cert.recipient_name, cert.course_name, issue_date, path
                )
                cert.status = CertificateStatus.SUCCESS
                cert.file_path = path
                job.succeeded += 1
            except Exception as exc:
                cert.status = CertificateStatus.FAILED
                cert.error_message = f"Certificate generation failed: {exc}"
                job.failed += 1
            db.commit()  # save progress after every certificate

        job.status = JobStatus.COMPLETED
        db.commit()
    finally:
        db.close()