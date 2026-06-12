import json
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from crud import create_submission, list_submissions
from schemas import CodeAnalyzeRequest, AnalysisResult, Issue, SubmissionResponse
from app.services.ai_service import analyze_code_structured, generate_local_feedback_text
from app.services.analyzer import (
    LocalCodeAnalyzer,
    get_ast_hash,
    analyze_complexity,
    template_ai_feedback,
    restore_ai_feedback,
    get_semantic_fingerprint
)
import models

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

@router.post("/analyze")
async def analyze(request: CodeAnalyzeRequest, db: Session = Depends(get_db)):
    start_time = time.perf_counter()
    
    lang = (request.language or "python").strip().lower()
    code = request.code or ""

    if not code.strip():
        raise HTTPException(status_code=400, detail="Порожній код. Будь ласка, вставте програмний код для перевірки.")

    if lang == "python":
        ast_res = LocalCodeAnalyzer.analyze(code)

        if not ast_res["is_valid_syntax"]:
            err_msg = ast_res["local_errors"][0]["message"]
            analysis = AnalysisResult(
                summary="Синтаксична помилка: неможливо побудувати абстрактне синтаксичне дерево (AST)",
                issues=[Issue(severity="error", title="Синтаксична помилка", explanation=err_msg, recommendation="Виправте синтаксичні помилки та повторіть спробу")],
                score=0
            )
            teacher = f"Критична помилка синтаксису: {err_msg}"
            exec_time = round(time.perf_counter() - start_time, 3)
            return create_submission(db=db, student_name=request.student_name, code=code, language=lang, teacher_feedback=teacher, analysis=analysis, execution_time=exec_time)

        all_issues = []
        teacher_feedback_lines = []

        depth = analyze_complexity(code)
        if depth >= 3:
            all_issues.append(
                Issue(severity="warning", title="Вкладеність циклів", explanation=f"Глибина вкладеності: {depth}", recommendation="Оптимізуйте алгоритм")
            )
            teacher_feedback_lines.append(f"Попередження: Виявлено глибину вкладеності циклів {depth}. Спробуйте оптимізувати алгоритм.")

        if ast_res["local_errors"]:
            for error in ast_res["local_errors"]:
                pattern = db.query(models.EducationalFaultPattern).filter(
                    models.EducationalFaultPattern.error_type == error["type"]
                ).first()

                explanation = error["message"]
                
                if pattern:
                    teacher_feedback_lines.append(f"Рядок {error.get('line', '?')}: {pattern.socratic_template}")
                else:
                    teacher_feedback_lines.append(f"Рядок {error.get('line', '?')}: {explanation}")

                all_issues.append(
                    Issue(
                        severity="error" if "vulnerability" in error["type"] else "warning", 
                        title=error["type"], 
                        explanation=explanation, 
                        recommendation="Ознайомтеся з правилами безпеки або синтаксису Python для усунення дефекту.",
                        line_start=error.get('line')
                    )
                )

        if all_issues and not any(err.get('type') == 'analysis_error' for err in ast_res["local_errors"]):
            analysis = AnalysisResult(
                summary="Локальний аналіз: виявлено зауваження до структури коду",
                issues=all_issues,
                score=40
            )
            teacher = "\n\n".join(teacher_feedback_lines)
            exec_time = round(time.perf_counter() - start_time, 3)
            return create_submission(db=db, student_name=request.student_name, code=code, language=lang, teacher_feedback=teacher, analysis=analysis, execution_time=exec_time)

    exact_ast_hash = get_ast_hash(code)
    semantic_fingerprint = get_semantic_fingerprint(code)
    sub = None

    if exact_ast_hash:
        sub = db.query(models.Submission).filter(
            models.Submission.language == lang,
            models.Submission.ast_hash == exact_ast_hash,
            models.Submission.feedback_json.isnot(None)
        ).order_by(models.Submission.created_at.desc()).first()

    is_complex_algorithm = ("'structure_scale': 0" not in semantic_fingerprint)
    
    if not sub and is_complex_algorithm and semantic_fingerprint != "invalid_syntax":
        sub = db.query(models.Submission).filter(
            models.Submission.language == lang,
            models.Submission.semantic_fingerprint == semantic_fingerprint,
            models.Submission.feedback_json.isnot(None)
        ).order_by(models.Submission.created_at.desc()).first()

    if sub and isinstance(sub, models.Submission):
        try:
            analysis_dict = json.loads(sub.feedback_json)
            
            if "summary" in analysis_dict and analysis_dict["summary"]:
                templated = template_ai_feedback(analysis_dict["summary"], sub.code)
                analysis_dict["summary"] = restore_ai_feedback(templated, code)
            
            if "issues" in analysis_dict and isinstance(analysis_dict["issues"], list):
                for issue in analysis_dict["issues"]:
                    if "explanation" in issue and issue["explanation"]:
                        templated_exp = template_ai_feedback(issue["explanation"], sub.code)
                        issue["explanation"] = restore_ai_feedback(templated_exp, code)
                    if "recommendation" in issue and issue["recommendation"]:
                        templated_rec = template_ai_feedback(issue["recommendation"], sub.code)
                        issue["recommendation"] = restore_ai_feedback(templated_rec, code)
            
            if "improvements" in analysis_dict and isinstance(analysis_dict["improvements"], list):
                updated_improvements = []
                for imp in analysis_dict["improvements"]:
                    if imp:
                        templated_imp = template_ai_feedback(imp, sub.code)
                        updated_improvements.append(restore_ai_feedback(templated_imp, code))
                    else:
                        updated_improvements.append(imp)
                analysis_dict["improvements"] = updated_improvements

            analysis = AnalysisResult.model_validate(analysis_dict)
            
            old_feedback = sub.teacher_feedback or ""
            cache_tag = "[Кеш] "
            if old_feedback.startswith(cache_tag):
                old_feedback = old_feedback.replace(cache_tag, "")

            templated_text = template_ai_feedback(old_feedback, sub.code)
            personalized_text = restore_ai_feedback(templated_text, code)
            
            exec_time = round(time.perf_counter() - start_time, 3)
            return create_submission(
                db=db, student_name=request.student_name, code=code, language=lang,
                teacher_feedback=f"{cache_tag}{personalized_text}", analysis=analysis,
                execution_time=exec_time
            )
        except Exception:
            pass

    try:
        _raw_text, analysis = analyze_code_structured(code, lang, max_retries=2)
    except Exception as e:
        error_message = str(e)
        if "429" in error_message or "quota" in error_message.lower():
            raise HTTPException(
                status_code=429,
                detail="Перевищено квоту запитів до LLM-сервісу. Будь ласка, спробуйте пізніше."
            )
        raise HTTPException(
            status_code=500,
            detail=f"Помилка взаємодії з LLM-сервісом: {error_message}"
        )

    try:
        teacher = generate_local_feedback_text(analysis, max_issues=3)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Помилка під час формування текстових рекомендацій: {str(e)}"
        )

    exec_time = round(time.perf_counter() - start_time, 3)
    return create_submission(
        db=db,
        student_name=request.student_name,
        code=code,
        language=lang,
        teacher_feedback=teacher,
        analysis=analysis,
        execution_time=exec_time
    )

@router.get("/history", response_model=List[SubmissionResponse])
async def history(db: Session = Depends(get_db)):
    rows = list_submissions(db)
    result: List[SubmissionResponse] = []

    for row in rows:
        parsed: AnalysisResult | None = None
        if row.feedback_json:
            try:
                parsed = AnalysisResult.model_validate(json.loads(row.feedback_json))
            except Exception:
                parsed = None

        result.append(
            SubmissionResponse(
                id=row.id,
                student_name=row.student_name,
                code=row.code,
                language=row.language,
                teacher_feedback=row.teacher_feedback,
                feedback_json=parsed,
                created_at=str(row.created_at) if row.created_at else None,
                execution_time=row.execution_time
            )
        )
    return result