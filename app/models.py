import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class JobStatus:
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"


class CertificateStatus:
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


def new_id():
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=new_id)
    status = Column(String, nullable=False, default=JobStatus.PENDING)
    total = Column(Integer, nullable=False, default=0)
    succeeded = Column(Integer, nullable=False, default=0)
    failed = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=utc_now)

    certificates = relationship(
        "Certificate", back_populates="job", cascade="all, delete-orphan"
    )


class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(String, primary_key=True, default=new_id)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    recipient_name = Column(String, nullable=True)
    recipient_email = Column(String, nullable=True)
    course_name = Column(String, nullable=True)
    status = Column(String, nullable=False, default=CertificateStatus.PENDING)
    file_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)

    job = relationship("Job", back_populates="certificates")