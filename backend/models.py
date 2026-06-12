from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.sql import func
from database import Base

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    student_name = Column(String, default="Гість", nullable=False, index=True)
    code = Column(Text, nullable=False)
    language = Column(String, default="python", nullable=False)
    
    teacher_feedback = Column(Text, nullable=True)
    feedback_json = Column(Text, nullable=True)
    
    ast_hash = Column(String, index=True, nullable=True)
    semantic_fingerprint = Column(String, index=True, nullable=True)
    
    execution_time = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EducationalFaultPattern(Base):
    __tablename__ = "educational_fault_patterns"

    id = Column(Integer, primary_key=True, index=True)
    error_type = Column(String, unique=True, nullable=False, index=True)  
    socratic_template = Column(Text, nullable=False)