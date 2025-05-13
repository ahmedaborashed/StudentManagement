from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from aiocache import cached
from datetime import datetime

# Database Configuration (PostgreSQL recommended for high load)
DATABASE_URL = "sqlite:///./Attendance.db"  # Use PostgreSQL in production

e_engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=300
)

Base = declarative_base()
SessionLocal = scoped_session(sessionmaker(bind=e_engine))

app = FastAPI()

origins = ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

# Models
class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    grade = Column(String)
    group_name = Column(String)
    phone_parent = Column(String)
    phone_student = Column(String)
    qr_code = Column(String)

class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    date = Column(String)
    time = Column(String)

class Grade(Base):
    __tablename__ = "grades"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    subject = Column(String)
    score = Column(Float)

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    grade = Column(String)
    group_name = Column(String)

Base.metadata.create_all(bind=e_engine)

# Pydantic Schemas
class StudentCreate(BaseModel):
    name: str
    grade: str
    group_name: str
    phone_parent: str
    phone_student: str
    qr_code: str = ""

# Routes
@app.post("/students/")
def create_student(student: StudentCreate, background_tasks: BackgroundTasks, db=Depends(lambda: SessionLocal())):
    try:
        db_student = Student(**student.dict())
        db.add(db_student)
        db.commit()
        db.refresh(db_student)

        # Send welcome message in background
        background_tasks.add_task(send_welcome_message, db_student)
        return db_student
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# Background Task Example
async def send_welcome_message(student: Student):
    print(f"Welcome message sent to {student.name}")

@app.get("/students/")
@cached(ttl=60)
async def list_students(db=Depends(lambda: SessionLocal())):
    return db.query(Student).all()

# Run with multiple workers for better performance:
# uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4