from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str
    confirmPassword:str

class UserLogin(BaseModel):
    username: str
    password: str

# class ChangePassword(BaseModel):
#     username: str
#     password: str
#     confirmPassword: str

class UserRead(BaseModel):
    id: int
    username: str

    class Config:
        orm_mode = True