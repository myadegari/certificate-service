
from pydantic import BaseModel


class User(BaseModel):
    userId:str | None=None
    gender: str
    firstName: str
    lastName: str
    nationalId: str
    position: str | None = None
    signature: str | None = None


class Course(BaseModel):
    courseId: str | None = None  # MongoDB _id, stored on the generated File
    courseCode: str
    name: str
    organizingUnit: str
    date: str
    time: str
    signatory: User
    signatory2: User | None = None
    unitStamp: str
    unitStamp2: str | None = None


class Signatory(BaseModel):
    name: str
    position: str
    signature: str


class CertificateRequest(BaseModel):
    category: str
    issuedAt: str
    user: User
    course: Course
    certificateNumber: str
    certificationId: str | None = None  # Optional; generate if None
    qr_url: str | None = None
