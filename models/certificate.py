
import re

from pydantic import BaseModel, Field, field_validator


class User(BaseModel):
    userId: str | None = None
    gender: str = Field(max_length=32)
    firstName: str = Field(max_length=128)
    lastName: str = Field(max_length=128)
    nationalId: str = Field(max_length=32)
    position: str | None = Field(default=None, max_length=128)
    signature: str | None = None


class Course(BaseModel):
    courseId: str | None = Field(default=None, max_length=64)
    courseCode: str = Field(max_length=16)
    name: str = Field(max_length=256)
    organizingUnit: str = Field(max_length=256)
    organizingUnit2: str | None = Field(default=None, max_length=256)
    date: str = Field(max_length=32)
    time: str = Field(max_length=32)
    signatory: User
    signatory2: User | None = None
    unitStamp: str | None = None
    unitStamp2: str | None = None

    @field_validator("courseCode")
    @classmethod
    def validate_course_code(cls, v: str) -> str:
        # Mirrors the app-side 5-digit code; it also prefixes the S3 key.
        if not re.fullmatch(r"\d{5}", v):
            raise ValueError("courseCode must be a 5-digit number")
        return v


class Signatory(BaseModel):
    name: str = Field(max_length=256)
    position: str = Field(max_length=256)
    signature: str | None = None


class CertificateRequest(BaseModel):
    category: str = Field(max_length=8)
    issuedAt: str = Field(max_length=32)
    user: User
    course: Course
    certificateNumber: str = Field(max_length=32)
    # Always the enrollment _id in the real flow. Constraining it to a
    # Mongo ObjectId prevents path traversal via generated filenames and
    # status spoofing against arbitrary enrollments.
    certificationId: str | None = Field(default=None, max_length=64)
    qr_url: str | None = Field(default=None, max_length=512)

    @field_validator("certificationId")
    @classmethod
    def validate_certification_id(cls, v: str | None) -> str | None:
        if v is not None and not re.fullmatch(r"[0-9a-fA-F]{24}", v):
            raise ValueError("certificationId must be a 24-char hex ObjectId")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in ("1", "2"):
            raise ValueError("category must be '1' or '2'")
        return v

    @field_validator("qr_url")
    @classmethod
    def validate_qr_url(cls, v: str | None) -> str | None:
        if v is not None and not v.startswith(("http://", "https://")):
            raise ValueError("qr_url must be an http(s) URL")
        return v
