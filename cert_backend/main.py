from datetime import datetime, timedelta
from typing import Optional
from fastapi import Body, FastAPI, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import qrcode
from cert_backend.repository.models import (
    User,
    Department,
    Signatory,
    Course,
    Certificate,
)
from cert_backend.repository import models
from cert_backend.repository.schema import UserCreate, UserLogin, UserRead
from werkzeug.security import generate_password_hash, check_password_hash
from cert_backend.repository.database import SessionLocal, engine
from sqlalchemy.orm import Session
from .repository.utils import get_db
from .repository.database import Base
import pyotp
import os
from fastapi.middleware.cors import CORSMiddleware

# Generate a unique secret for the user
# JWT settings
SECRET_KEY = "your-secret-key-keep-it-secret"  # Change this in production!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
# Base.metadata.create_all(bind=engine)
# fix cores

app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://5.190.131.231:5173",
    ],  # Adjust this to your frontend's URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


@app.get("/")
def home():
    return {"message": "Hello, World!"}


@app.post("/signup")
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    if dbuser := db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=409, detail="User already exists")
        # return {"user":{
        #     "id": dbuser.id
        # }}
    if user_in.password != user_in.confirmPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    secret = pyotp.random_base32()
    hashed_password = generate_password_hash(user_in.password)
    user = User(username=user_in.username, password=hashed_password, otp_secret=secret)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "msg": "User created successfully",
        "user": {"id": user.id, "username": user.username},
    }


@app.get("/otp/generate")
async def generate_otp(user_id=Query(), db: Session = Depends(get_db)):
    current_user = db.query(User).filter(User.id == user_id).first()
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    totp = pyotp.TOTP(str(current_user.otp_secret))
    otp = totp.now()
    otp_uri = totp.provisioning_uri(
        name=str(current_user.username), issuer_name="lar_university"
    )
    img = qrcode.make(otp_uri, error_correction=qrcode.ERROR_CORRECT_L)
    if not os.path.exists("cert_ui/public/"):
        os.makedirs("cert_ui/public/")
    img_path = f"cert_ui/public/{current_user.username}_otp.png"
    with open(img_path, "wb") as img_file:
        img.save(img_file, "PNG")

    # send this image to frontend and dont save it
    return {
        "otp": otp,
        "otp_uri": otp_uri,
        "qrcode": img_path.split("/")[-1],  # This will return the QR code image
    }


@app.post("/otp/verify")
async def verify_otp(
    user_id: Optional[str] = Query(None),  # Make user_id optional
    otp: str = Query(...),  # Ensure otp is required
    username: Optional[str] = Query(None),  # Make username optional
    db: Session = Depends(get_db),
):
    if not user_id and not username:
        raise HTTPException(
            status_code=400, detail="Either user_id or username is required"
        )
    if not otp:
        raise HTTPException(status_code=400, detail="OTP is required")

    if username:
        current_user = db.query(User).filter(User.username == username).first()
    else:
        current_user = db.query(User).filter(User.id == user_id).first()
        

    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")

    totp = pyotp.TOTP(str(current_user.otp_secret))
    if not totp.verify(otp, valid_window=16):
        raise HTTPException(status_code=403, detail="Invalid OTP")
    setattr(current_user, 'is_active', True)
    db.commit()
    db.refresh(current_user)
    return {"msg": "OTP verified successfully"}


@app.post("/change-password")
async def change_password(data: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == data.username).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.password != data.confirmPassword:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if check_password_hash(str(db_user.password), data.password):
        raise HTTPException(status_code=400, detail="Incorrect password")

    setattr(db_user,'password',generate_password_hash(data.password))
    db.commit()
    return {"msg": "Password changed successfully"}


@app.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    # print(user)
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not check_password_hash(str(db_user.password), user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": db_user.id}, expires_delta=access_token_expires
    )
    refresh_token = create_access_token(
        data={"user_id": db_user.id}, expires_delta=timedelta(days=30)
    )
    return {"accessToken": access_token, "refreshToken": refresh_token}


@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "id": current_user.id}


def admin_user_details(
    db_user: models.User,
):
    return {
        "id": db_user.id,
        "firstname":db_user.full_name,
        "role": db_user.role,
        "is_active": db_user.is_active,
    }


@app.get("/admin-user-managment")
def get_users(
    user_id: Optional[str] = Query(None),  # Make username optional
    page: Optional[int] = Query(None),  # Make username optional
    db: Session = Depends(get_db),
):
    if user_id:

        db_user: models.User | None = (
            db.query(models.User).filter(models.User.id == user_id).first()
        )
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        # return admin_user_details(db_user)
        return db_user
    page_size = 20
    page_num = page or 1
    offset = (int(page_num) - 1) * page_size
    db_users: list[models.User] = (
        db.query(models.User).offset(offset).limit(page_size).all()
    )
    # total_users = crud.get_total_users(db)
    return JSONResponse([admin_user_details(user) for user in db_users])


# # Create tables if they don't exist (uncomment if needed)
# Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("cert_backend.main:app", host="0.0.0.0", port=8000, reload=True)
