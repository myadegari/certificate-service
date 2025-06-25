from uuid import uuid4
from sqlalchemy import Column, Integer, String,Boolean
from .database import Base
from sqlalchemy import ForeignKey, Table
from sqlalchemy.orm import relationship

# Association table for many-to-many relationship between Certificate and Signatory
course_signatory = Table(
    'course_signatory',
    Base.metadata,
    Column('course_id', Integer, ForeignKey('courses.id'), primary_key=True),
    Column('signatory_id', Integer, ForeignKey('signatories.id'), primary_key=True)
)

class Department(Base):
    __tablename__ = 'departments'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    seal = Column(String, nullable=True)
    signatories = relationship("Signatory", back_populates="department")


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    is_active = Column(Boolean,nullable=False,default=False)
    role = Column(String, nullable=False, default="USER")  # Added role field
    otp_secret = Column(String, nullable=True)  # Added otp_secret for 2FA
    gender = Column(String, nullable=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    personnel_id = Column(Integer, nullable=True)
    national_id = Column(String, nullable=True)  # Added national_id
    first_name = Column(String, nullable=True)  # Fixed typo: changed first_name to first_name
    last_name = Column(String, nullable=True)  # Fixed typo: changed last_name to last_name
    signatories = relationship("Signatory", back_populates="user")
    certificates = relationship("Certificate", back_populates="user")
    
    
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Signatory(Base):
    __tablename__ = 'signatories'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    position = Column(String, nullable=False)
    signature = Column(String, nullable=False)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    department = relationship("Department", back_populates="signatories")
    user = relationship("User", back_populates="signatories")
    courses = relationship("Course", secondary=course_signatory, back_populates="signatories")

    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

class Course(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    org = Column(String, nullable=True)
    date = Column(String, nullable=True)
    duration = Column(Integer, nullable=False)  # Duration in hours
    certificates = relationship("Certificate", back_populates="course")
    signatories = relationship("Signatory", secondary=course_signatory, back_populates="courses")



class Certificate(Base):
    __tablename__ = 'certificates'
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)
    issue_date = Column(String, nullable=False)
    certificate_number = Column(String, unique=True, nullable=False)
    unique_code = Column(String, unique=True, nullable=False, default=uuid4())  #use uuid4() for unique code
    cert_type = Column(Integer, nullable=False)
    user = relationship("User", back_populates="certificates")
    course = relationship("Course", back_populates="certificates")
