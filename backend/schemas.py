from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class CodeAnalyzeRequest(BaseModel):
    code: str = Field(..., description="Програмний код для аналізу")
    language: str = Field(default="python", description="Мова програмування")
    student_name: str = Field(default="Гість", description="Ідентифікатор профілю студента")

class Issue(BaseModel):
    severity: Literal["info", "warning", "error"]
    title: str
    explanation: str
    recommendation: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None

class Complexity(BaseModel):
    time: Optional[str] = None
    space: Optional[str] = None
    notes: Optional[str] = None

class AnalysisResult(BaseModel):
    summary: str
    issues: List[Issue] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    complexity: Optional[Complexity] = None
    score: Optional[int] = None

class SubmissionResponse(BaseModel):
    id: int
    student_name: str
    code: str
    language: str
    teacher_feedback: Optional[str] = None
    feedback_json: Optional[AnalysisResult] = None
    created_at: Optional[str] = None
    execution_time: Optional[float] = None

    class Config:
        from_attributes = True