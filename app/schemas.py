from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RecipientData(BaseModel):
    """Rules for ONE recipient. We apply these ourselves, per recipient."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class JobCreateRequest(BaseModel):
    """The whole request body. Only the outer shape is checked here."""

    model_config = ConfigDict(str_strip_whitespace=True)

    course_name: str = Field(min_length=1, max_length=100)
    recipients: list[dict] = Field(min_length=1, max_length=1000)


class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recipient_name: str | None
    recipient_email: str | None
    status: str
    error_message: str | None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    total: int
    succeeded: int
    failed: int
    created_at: datetime


class JobDetailOut(JobOut):
    certificates: list[CertificateOut]