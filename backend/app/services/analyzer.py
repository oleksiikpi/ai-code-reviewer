import ast
import re
import builtins
from typing import Dict, Any, Set

BUILTIN_NAMES = set(dir(builtins))

class StudentCodeVisitor(ast.NodeVisitor):
    def __init__(self):
        self.errors = []
        self.current_loop_depth = 0
        self.max_loop_depth = 0
        self.defined_variables: Set[str] = set()

    def _register_target(self, target):
        if isinstance(target, ast.Name):
            self.defined_variables.add(target.id)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for elt in target.elts:
                self._register_target(elt)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.defined_variables.add(node.name)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.defined_variables.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        for alias in node.names:
            self.defined_variables.add(alias.asname or alias.name)
        self.generic_visit(node)

    def _register_comprehension_vars(self, node):
        generators = getattr(node, 'generators', [])
        for comp in generators:
            if hasattr(comp, 'target'):
                self._register_target(comp.target)
        self.generic_visit(node)

    def visit_GeneratorExp(self, node): self._register_comprehension_vars(node)
    def visit_ListComp(self, node): self._register_comprehension_vars(node)
    def visit_SetComp(self, node): self._register_comprehension_vars(node)
    def visit_DictComp(self, node): self._register_comprehension_vars(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.defined_variables.add(node.name)
        args = getattr(node, 'args', None)
        if args and hasattr(args, 'args'):
            for arg in args.args:
                if hasattr(arg, 'arg'):
                    self.defined_variables.add(arg.arg)
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        if hasattr(node, 'target'):
            self._register_target(node.target)

        self.current_loop_depth += 1
        if self.current_loop_depth > self.max_loop_depth:
            self.max_loop_depth = self.current_loop_depth
        self.generic_visit(node)
        self.current_loop_depth -= 1

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            self._register_target(target)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if getattr(node, 'name', None):
            self.defined_variables.add(node.name)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            node_id = getattr(node, 'id', '')
            is_dunder = node_id.startswith("__") and node_id.endswith("__")

            if node_id and node_id not in self.defined_variables and node_id not in BUILTIN_NAMES and not is_dunder:
                self.errors.append({
                    "type": "undefined_variable",
                    "line": getattr(node, 'lineno', 1),
                    "message": f"Спроба використання ідентифікатора '{node_id}', який не був оголошений раніше."
                })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if hasattr(node, 'func') and isinstance(node.func, ast.Name):
            func_id = getattr(node.func, 'id', '')
            if func_id in ['eval', 'exec']:
                self.errors.append({
                    "type": "security_vulnerability",
                    "line": getattr(node, 'lineno', 1),
                    "message": f"Використання функцій динамічного виконання коду '{func_id}' заборонено."
                })
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        test = getattr(node, 'test', None)
        if isinstance(test, ast.Constant) and test.value is True:
            has_break = any(isinstance(child, ast.Break) for child in ast.walk(node))
            if not has_break:
                self.errors.append({
                    "type": "infinite_loop",
                    "line": getattr(node, 'lineno', 1),
                    "message": "Виявлено потенційно нескінченний цикл."
                })

        self.current_loop_depth += 1
        if self.current_loop_depth > self.max_loop_depth:
            self.max_loop_depth = self.current_loop_depth
        self.generic_visit(node)
        self.current_loop_depth -= 1

class LocalCodeAnalyzer:
    @staticmethod
    def analyze(code: str) -> Dict[str, Any]:
        if len(code) > 10000:
            return {
                "is_valid_syntax": False,
                "local_errors": [{
                    "type": "size_limit",
                    "line": 1,
                    "message": "Код превышает лимит (10000 символов)"
                }],
                "metrics": {}
            }

        try:
            tree = ast.parse(code)
            visitor = StudentCodeVisitor()

            try:
                visitor.visit(tree)
            except Exception as e:
                return {
                    "is_valid_syntax": True,
                    "local_errors": [{
                        "type": "analysis_error",
                        "message": f"Ошибка анализа: {str(e)}"
                    }],
                    "metrics": {}
                }

            if visitor.max_loop_depth > 3:
                visitor.errors.append({
                    "type": "complexity_anomaly",
                    "line": 1,
                    "message": "Слишком глубокая вложенность циклов"
                })

            return {
                "is_valid_syntax": True,
                "local_errors": visitor.errors,
                "metrics": {"max_loop_depth": visitor.max_loop_depth}
            }

        except SyntaxError as se:
            return {
                "is_valid_syntax": False,
                "local_errors": [{
                    "type": "syntax_error",
                    "line": getattr(se, 'lineno', 1),
                    "message": se.msg
                }],
                "metrics": {}
            }

class SemanticNormalizer(ast.NodeTransformer):
    """
    Агресивний трансформер AST-дерева для семантичного кешування.
    Вирізає принти, типізацію та перетворює змінні на абстрактні ідентифікатори.
    """
    def __init__(self):
        self.name_mapping = {}
        self.counter = 1

    def _get_generic_name(self, original_name: str) -> str:
        if original_name in BUILTIN_NAMES:
            return original_name
        if original_name not in self.name_mapping:
            self.name_mapping[original_name] = f"ident_{self.counter}"
            self.counter += 1
        return self.name_mapping[original_name]

    def visit_Name(self, node: ast.Name):
        self.generic_visit(node)
        if hasattr(node, 'id'):
            node.id = self._get_generic_name(node.id)
        return node

    def visit_arg(self, node: ast.arg):
        node.annotation = None
        self.generic_visit(node)
        if hasattr(node, 'arg') and isinstance(node.arg, str):
            node.arg = self._get_generic_name(node.arg)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef):
        node.returns = None
        if hasattr(node, 'name'):
            node.name = self._get_generic_name(node.name)
        self.generic_visit(node)
        return node

    def visit_Expr(self, node: ast.Expr):
        self.generic_visit(node)
        if isinstance(node.value, ast.Constant):
            return None
        if isinstance(node.value, ast.Call) and getattr(node.value.func, 'id', '') == 'print':
            return None
        return node

    def visit_Constant(self, node: ast.Constant):
        self.generic_visit(node)
        if isinstance(node.value, str):
            node.value = "STR"
        elif isinstance(node.value, (int, float)):
            node.value = 0
        return node

    def visit_AnnAssign(self, node: ast.AnnAssign):
        self.generic_visit(node)
        if node.value:
            return ast.Assign(targets=[node.target], value=node.value)
        return None

def get_ast_hash(code: str) -> str:
    try:
        tree = ast.parse(code)
        normalizer = SemanticNormalizer()
        normalized_tree = normalizer.visit(tree)
        return ast.dump(normalized_tree)
    except Exception:
        return ""

def analyze_complexity(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0

    def get_max_depth(node, depth=0):
        max_d = depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While, ast.AsyncFor)):
                max_d = max(max_d, get_max_depth(child, depth + 1))
            else:
                max_d = max(max_d, get_max_depth(child, depth))
        return max_d

    return get_max_depth(tree)

def extract_identifiers(code: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    identifiers = []

    def add_id(name):
        if name not in identifiers and name not in BUILTIN_NAMES:
            identifiers.append(name)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            add_id(node.name)
        elif isinstance(node, ast.ClassDef):
            add_id(node.name)
        elif isinstance(node, ast.arg):
            add_id(node.arg)
        elif isinstance(node, ast.Name):
            add_id(node.id)

    return identifiers

def template_ai_feedback(feedback_text: str, code: str):
    identifiers = extract_identifiers(code)
    templated_text = feedback_text

    sorted_ids = sorted(identifiers, key=len, reverse=True)

    for name in sorted_ids:
        pattern = r'\b' + re.escape(name) + r'\b'
        original_index = identifiers.index(name)
        placeholder = f"{{{{ID_{original_index}}}}}"
        templated_text = re.sub(pattern, placeholder, templated_text)

    return templated_text

def restore_ai_feedback(templated_text: str, code: str):
    identifiers = extract_identifiers(code)
    restored_text = templated_text

    for i, name in enumerate(identifiers):
        placeholder = f"{{{{ID_{i}}}}}"
        restored_text = restored_text.replace(placeholder, name)

    restored_text = re.sub(r'\{\{ ?ID_\d+ ?\}\}', 'елемент коду', restored_text)

    return restored_text

def get_semantic_fingerprint(code: str) -> str:
    """
    Генерирует гибридный семантический отпечаток кода.
    Точно фиксирует типы критических операций и масштаб кода для предотвращения коллизий.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return "invalid_syntax"

    fingerprint = {
        "has_loops": False,
        "nesting_level": 0,
        "mutation_methods": set(),
        "math_operators": set(),  
        "compare_operators": set(), 
        "io_operations": False,
        "structure_scale": 0,
        "has_context_manager": False,
        "builtins_called": set()
    }

    class HybridFingerprintVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_depth = 0

        def visit_For(self, node):
            fingerprint["has_loops"] = True
            fingerprint["structure_scale"] += 1
            self.current_depth += 1
            fingerprint["nesting_level"] = max(fingerprint["nesting_level"], self.current_depth)
            self.generic_visit(node)
            self.current_depth -= 1

        def visit_While(self, node):
            fingerprint["has_loops"] = True
            fingerprint["structure_scale"] += 1
            self.current_depth += 1
            fingerprint["nesting_level"] = max(fingerprint["nesting_level"], self.current_depth)
            self.generic_visit(node)
            self.current_depth -= 1

        def visit_If(self, node):
            fingerprint["structure_scale"] += 1
            self.generic_visit(node)

        def visit_With(self, node):
            fingerprint["has_context_manager"] = True
            fingerprint["structure_scale"] += 1
            self.generic_visit(node)

        def visit_BinOp(self, node):
            op_type = type(node.op).__name__
            fingerprint["math_operators"].add(op_type)
            self.generic_visit(node)

        def visit_Compare(self, node):
            for op in node.ops:
                fingerprint["compare_operators"].add(type(op).__name__)
            self.generic_visit(node)

        def visit_Call(self, node):
            if isinstance(node.func, ast.Attribute):
                method_name = getattr(node.func, 'attr', '')
                if method_name in ['remove', 'pop', 'append', 'extend', 'insert', 'clear']:
                    fingerprint["mutation_methods"].add(method_name)

            if isinstance(node.func, ast.Name):
                func_id = getattr(node.func, 'id', '')
                if func_id == 'print':
                    fingerprint["io_operations"] = True
                elif func_id in ['open', 'len', 'range', 'sum', 'min', 'max']:
                    fingerprint["builtins_called"].add(func_id)

            self.generic_visit(node)

    HybridFingerprintVisitor().visit(tree)

    # Канонизация списков
    fingerprint["mutation_methods"] = sorted(list(fingerprint["mutation_methods"]))
    fingerprint["math_operators"] = sorted(list(fingerprint["math_operators"]))
    fingerprint["compare_operators"] = sorted(list(fingerprint["compare_operators"]))
    fingerprint["builtins_called"] = sorted(list(fingerprint["builtins_called"]))

    return str(fingerprint)