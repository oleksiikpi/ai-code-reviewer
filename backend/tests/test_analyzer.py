import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.analyzer import LocalCodeAnalyzer, get_ast_hash, get_semantic_fingerprint

def test_local_analyzer_syntax_error():
    """Тест 1: Перевірка реакції локального аналізатора на грубу синтаксичну помилку"""
    invalid_code = "def broken_function(x)\n    return x"
    result = LocalCodeAnalyzer.analyze(invalid_code)
    
    assert result["is_valid_syntax"] is False
    assert len(result["local_errors"]) > 0
    assert result["local_errors"][0]["type"] == "syntax_error"


def test_local_analyzer_security_vulnerability():
    """Тест 2: Перевірка блокування небезпечних функцій (динамічний код через eval/exec)"""
    unsafe_code = "def execute_payload(user_data):\n    eval(user_data)\n    exec('print(123)')"
    result = LocalCodeAnalyzer.analyze(unsafe_code)
    
    assert result["is_valid_syntax"] is True
    security_errors = [err for err in result["local_errors"] if err["type"] == "security_vulnerability"]
    assert len(security_errors) == 2


def test_ast_hash_variable_normalization():
    """Тест 3: Перевірка роботи L1 кешу (SemanticNormalizer). 
    Коди з різними іменами змінних повинні мати ідентичний AST-хэш.
    """
    code_student_1 = "def calc(a, b):\n    res = a + b\n    return res"
    code_student_2 = "def process(x, y):\n    total = x + y\n    return total"
    
    hash_1 = get_ast_hash(code_student_1)
    hash_2 = get_ast_hash(code_student_2)
    
    assert hash_1 != ""
    assert hash_2 != ""
    assert hash_1 == hash_2, "L1 Кеш зламано: нормалізатор не зміг уніфікувати назви змінних!"


def test_semantic_fingerprint_equivalence():
    """Тест 4: Перевірка роботи L2 кешу (get_semantic_fingerprint).
    Алгоритми з різними типами циклів (for vs while), але однаковою бізнес-логікою
    (наприклад, додавання елементів у список всередині циклу з умовою розгалуження)
    повинні генерувати ідентичні структурні відбитки.
    """
    code_for_loop = (
        "def filter_data(items):\n"
        "    output = []\n"
        "    for item in items:\n"
        "        if item > 0:\n"
        "            output.append(item)\n"
        "    return output"
    )
    
    code_while_loop = (
        "def clean_array(matrix):\n"
        "    result = []\n"
        "    idx = 0\n"
        "    while idx < len(matrix):\n"
        "        if matrix[idx] > 0:\n"
        "            result.append(matrix[idx])\n"
        "        idx += 1\n"
        "    return result"
    )
    
    fingerprint_for = get_semantic_fingerprint(code_for_loop)
    fingerprint_while = get_semantic_fingerprint(code_while_loop)
    
    assert "has_loops': True" in fingerprint_for
    assert "has_loops': True" in fingerprint_while
    assert "mutation_methods': ['append']" in fingerprint_for
    assert "mutation_methods': ['append']" in fingerprint_while