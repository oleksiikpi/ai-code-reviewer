from sqlalchemy.orm import Session
import models
from schemas import AnalysisResult
from app.services.analyzer import get_ast_hash, get_semantic_fingerprint

def create_submission(db: Session, student_name: str, code: str, language: str, teacher_feedback: str, analysis: AnalysisResult, execution_time: float = 0.0):
    
    ast_hash = get_ast_hash(code)
    fingerprint = get_semantic_fingerprint(code)
    
    json_data = analysis.model_dump_json() if hasattr(analysis, 'model_dump_json') else analysis.json()
    
    db_sub = models.Submission(
        student_name=student_name,
        code=code,
        language=language,
        teacher_feedback=teacher_feedback,
        feedback_json=json_data,
        ast_hash=ast_hash,
        semantic_fingerprint=fingerprint,
        execution_time=execution_time
    )
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub

def list_submissions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Submission).order_by(models.Submission.created_at.desc()).offset(skip).limit(limit).all()