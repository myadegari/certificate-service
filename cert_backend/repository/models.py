import uuid
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Table,
    func
)
# برای استفاده از نوع داده UUID، این را از dialect دیتابیس خود import کنید
# مثال زیر برای PostgreSQL است
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .database import Base

# جدول واسط برای رابطه چند-به-چند (این بخش عالی و بدون تغییر است)
course_signatory = Table(
    'course_signatory',
    Base.metadata,
    Column('course_id', Integer, ForeignKey('courses.id'), primary_key=True),
    Column('signatory_id', Integer, ForeignKey('signatories.id'), primary_key=True)
)

class Department(Base):
    __tablename__ = 'departments'
    id = Column(Integer, primary_key=True, index=True)
    # اضافه کردن طول برای رشته‌ها رویه خوبی است
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    # فرض بر این است که مسیر فایل مُهر در اینجا ذخیره می‌شود
    seal = Column(String, nullable=True)

    signatories = relationship("Signatory", back_populates="department")


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    # ✅ ایمیل برای ارتباطات و بازیابی رمز عبور ضروری است
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String, nullable=False) # باید هش شده باشد
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    otp_secret = Column(String(255), nullable=False, default=None)

    is_active = Column(Boolean, nullable=False, default=True)
    role = Column(String(50), nullable=False, default="USER")

    # اطلاعات شناسایی کارمندان که باید یکتا باشند
    personnel_id = Column(Integer, unique=True, nullable=True)
    national_id = Column(String(50), unique=True, nullable=True)

    # ✅ ستون‌های زمانی برای رهگیری
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    signatories = relationship("Signatory", back_populates="user")
    certificates = relationship("Certificate", back_populates="user")

    # استفاده از property باعث می‌شود بتوانید مثل یک فیلد به آن دسترسی داشته باشید (user.full_name)
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Signatory(Base):
    __tablename__ = 'signatories'
    id = Column(Integer, primary_key=True, index=True)
    # ✅ هر کاربر فقط یک پروفایل امضاکننده دارد، پس این فیلد باید یکتا باشد
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)

    position = Column(String(255), nullable=False)
    # فرض بر این است که مسیر فایل عکس امضا ذخیره می‌شود
    signature = Column(String, nullable=False)

    user = relationship("User", back_populates="signatories")
    department = relationship("Department", back_populates="signatories")
    courses = relationship("Course", secondary=course_signatory, back_populates="signatories")

    @property
    def full_name(self):
        # نام کامل را از کاربر مرتبط میخواند تا از تکرار کد جلوگیری شود
        if self.user:
            return self.user.full_name
        return None

class Course(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    # ✅ نام‌گذاری واضح‌تر
    organization = Column(String(255), nullable=True)
    # ✅ استفاده از نوع داده صحیح برای تاریخ
    course_date = Column(Date, nullable=True)
    # ✅ نام‌گذاری واضح‌تر برای ساعت دوره
    duration_hours = Column(Integer, nullable=False)
    
    # آدرس ثبت‌نام دوره که شما به آن اشاره کردید
    verification_url = Column(String, nullable=True)
    # کد تایید که به آن اشاره کردید
    secret_code = Column(String, nullable=True)

    certificates = relationship("Certificate", back_populates="course")
    signatories = relationship("Signatory", secondary=course_signatory, back_populates="courses")


class Certificate(Base):
    __tablename__ = 'certificates'
    id = Column(Integer, primary_key=True, index=True)
    # 🔑 کلید اصلی برای دسترسی عمومی و غیرقابل حدس
    unique_code = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4, index=True)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)

    # ✅ استفاده از نوع داده Date و مقدار پیش‌فرض سمت دیتابیس
    issue_date = Column(Date, nullable=False, default=func.current_date())
    certificate_number = Column(String(100), unique=True, nullable=False)
    cert_type = Column(Integer, nullable=False)

    user = relationship("User", back_populates="certificates")
    course = relationship("Course", back_populates="certificates")