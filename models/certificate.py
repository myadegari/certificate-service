from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class User(BaseModel):
    gender: str
    firstName: str
    lastName: str
    nationalId: str
    position:Optional[str]=None
    signature: Optional[str] = None

class Course(BaseModel):
    name: str
    organizingUnit: str
    date: str
    time: str
    signatory: User
    signatory2: Optional[User] = None
    unitStamp: str
    unitStamp2: Optional[str] = None

class Signatory(BaseModel):
    name: str
    position: str
    signature: str

class CertificateRequest(BaseModel):
    category: str
    user: User
    course: Course
    certificateNumber: str
    certificateId: str | None = None  # Optional; generate if None
    qr_url: str | None = None
