from pydantic import BaseModel
from typing import Optional

class UserBase(BaseModel):
    username: str
    role: str = "student"

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(UserBase):
    id: int
    class Config:
        from_attributes = True

class FileOut(BaseModel):
    id: int
    filename: str
    dept: str
    semester: int
    subject: str
    module: int
    category: str # <-- NEW FIELD
    class Config:
        from_attributes = True