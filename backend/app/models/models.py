from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="admin")

class File(Base):
    __tablename__ = "files"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    dept = Column(String)
    semester = Column(String)  # Changed to String for flexibility
    subject = Column(String)
    module = Column(Integer)
    category = Column(String)
    file_path = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))