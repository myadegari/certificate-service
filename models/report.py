from typing import Optional,List

from pydantic import BaseModel


class User(BaseModel):
    userId:Optional[str]=None
    gender: str
    firstName: str
    lastName: str
    nationalId: str



class EnrollmentItem(BaseModel):
    course_name:str
    course_org:str
    course_date:str
    course_duration:str
    issuedAt:str

class ReportDate(BaseModel):
    year:str
    issue:str

class TotalEnrollments(BaseModel):
    duration:str
    count:str
    
class ReportRequest(BaseModel):
    user: User
    issuedAt: str
    enrollments: List[EnrollmentItem]
    labels:List[str]
    date:ReportDate
    total:TotalEnrollments
    reportuniqueid:str