import os
import json
import re
import google.generativeai as genai
from schemas import AnalysisResult

_MODEL = None

def _get_model():
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY не задано. Будь ласка, додайте його у конфігураційний файл .env")

    model_name = os.getenv("GEMINI_MODEL", "models/gemini-3.1-flash-lite")
    genai.configure(api_key=api_key)
    _MODEL = genai.GenerativeModel(model_name)
    return _MODEL

def _json_schema_hint() -> str:
    return """
Поверніть РІВНО ОДИН JSON-об'єкт (без форматування Markdown, без ```).
ВАЖЛИВО: якщо виявлено хоча б 1 логічну проблему — масив "issues" НЕ може бути порожнім, а score має бути меншим за 100.

Формат:
{
"summary": "короткий опис работы коду",
"issues": [
{
"severity": "info|warning|error",
"title": "назва проблеми",
"explanation": "детальне пояснення логічної помилки",
"recommendation": "рекомендація щодо виправлення",
"line_start": 1,
"line_end": 3
}
],
"improvements": ["рекомендація 1"],
"complexity": { "time": "O(...)", "space": "O(...)", "notes": "..." },
"score": 80
}
""".strip()

def _build_prompt_structured(code: str, language: str) -> str:
    return f"""
Ви — суворий, об'єктивний технічний ментор та Senior Software Engineer. Ваше завдання — провести глибокий семантичний аналіз коду студента на наявність РЕАЛЬНИХ логічних дефектів, нескінченних циклів, витоків пам'яті або крашів програми.

ПРАВИЛА ОЦІНЮВАННЯ (КРИТИЧНО):
1. Якщо код технічно робочий, виконує поставлене завдання і не має явних багів — ставте оцінку 100 і повертайте ПОРОЖНІЙ масив `issues`: [].
2. КАТЕГОРИЧНО ЗАБОРОНЕНО прискіпуватися до:
   - Мікрооптимізацій архітектури (наприклад, вимагати `Decimal` замість `float` для базових задач).
   - Ідеального дотримання PEP-8 чи код-стайлу.
   - Вигадувати надумані крайні випадки (edge cases), якщо базова алгоритмічна логіка вірна.

ПРАВИЛА ГЕНЕРАЦІЇ ФІДБЕКУ (DOMAIN-AGNOSTIC - АБСТРАКТНІСТЬ):
Твій аналіз, пояснення помилок (explanation) та рекомендації (recommendation) ПОВИННІ бути абсолютно нейтральними до предметної області. Цей текст буде кешуватися системою для повторного використання!
1. ЗАБОРОНЕНО використовувати слова з реального світу, що описують бізнес-логіку програми (наприклад: "магазин", "товари", "книги", "прайс-лист", "бібліотека", "гравці", "зарплата", "студенти" тощо).
2. Описуй проблему ВИКЛЮЧНО абстрактними термінами інформатики та програмування: "структура даних", "словник", "список", "ітерація", "ключ", "значення", "умова", "масив", "елемент", "колекція", "змінна".
3. Для конкретизації дозволяється використовувати ТІЛЬКИ точні імена змінних та функцій з наданого коду студента, обов'язково беручи їх у зворотні апострофи (наприклад, `calculate_total`, `items`).

ОБМЕЖЕННЯ ФОРМАТУ:
- Пояснюй помилку прямо, структурно та технічно.
- КАТЕГОРИЧНО ЗАБОРОНЕНО вести Сократівський діалог (не став жодних навідних питань, не пиши "А що буде, якщо...").
- ЗАБОРОНЕНО надавати студенту готовий виправлений код. Надавай лише вказівку на дефект та алгоритмічний підхід до його виправлення.
- ЗАБОРОНЕНО використовувати будь-які вступні фрази, привітання або markdown-форматування поза межами необхідної JSON-структури. Повертай суто валідний JSON.

{_json_schema_hint()}

Мова програмування: {language}
Код:
{code}
""".strip()

def _extract_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    if text.startswith("{") and text.endswith("}"):
        return text
    m = re.search(r"\{.*\}", text, flags=re.S)
    return m.group(0) if m else text

def analyze_code_structured(code: str, language: str, max_retries: int = 2) -> tuple[str, AnalysisResult]:
    model = _get_model()
    prompt = _build_prompt_structured(code, language)
    last_text = ""
    last_err = None

    for _attempt in range(max_retries + 1):
        resp = model.generate_content(prompt)
        last_text = getattr(resp, "text", "") or ""
        candidate = _extract_json(last_text)
        try:
            data = json.loads(candidate)
            analysis = AnalysisResult.model_validate(data)
            return last_text, analysis
        except Exception as e:
            last_err = e
            prompt = f"Помилка валідації JSON: {str(e)}. Повторіть запит суворо у форматі JSON:\n{_json_schema_hint()}\nКод:\n{code}"

    raise RuntimeError(f"Помилка отримання валідного формату JSON від моделі Gemini: {str(last_err)}")


def generate_local_feedback_text(analysis: AnalysisResult, max_issues: int = 3) -> str:
    """
    Генерує лише коротке вступне повідомлення.
    Детальний рендеринг проблем, рекомендацій та складності тепер повністю делеговано фронтенду (через JSON).
    """
    issue_count = len(analysis.issues)
    
    if issue_count == 0:
        return " **Чудова робота!** Програмний код успішно пройшов перевірку. Жодних логічних чи семантичних помилок не виявлено."
    else:
        return f"**Вітаю, студенте!** Програмний код успішно пройшов етап семантичного аналізу ШІ.\n\nСистемою виявлено **{issue_count}** зауважень/помилок. Детальний інтерактивний звіт сформовано у графічній панелі нижче."