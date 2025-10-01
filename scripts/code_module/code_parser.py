"""Python code parser using AST for extracting structure and functionality."""

import ast
import os
from typing import Dict, List, Any, Optional
from pathlib import Path


class CodeParser:
    """Parse Python code to extract structure, functions, classes, and dependencies."""

    def __init__(self, file_path: str):
        """Initialize parser.

        Args:
            file_path: Path to Python file
        """
        self.file_path = file_path
        self.content = None
        self.tree = None
        self.module_name = Path(file_path).stem

    def parse(self) -> Dict[str, Any]:
        """Parse the Python file.

        Returns:
            Dictionary with parsed code structure
        """
        with open(self.file_path, 'r', encoding='utf-8') as f:
            self.content = f.read()

        try:
            self.tree = ast.parse(self.content, filename=self.file_path)
        except SyntaxError as e:
            return {
                "error": f"Syntax error: {e}",
                "file_path": self.file_path
            }

        return {
            "module_name": self.module_name,
            "file_path": self.file_path,
            "imports": self.extract_imports(),
            "classes": self.extract_classes(),
            "functions": self.extract_functions(),
            "globals": self.extract_globals(),
            "docstring": ast.get_docstring(self.tree),
            "line_count": len(self.content.split('\n')),
            "char_count": len(self.content)
        }

    def extract_imports(self) -> List[Dict[str, Any]]:
        """Extract all imports."""
        imports = []

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append({
                        "type": "from_import",
                        "module": node.module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })

        return imports

    def extract_classes(self) -> List[Dict[str, Any]]:
        """Extract all class definitions."""
        classes = []

        for node in self.tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "bases": [self._get_name(base) for base in node.bases],
                    "methods": self._extract_class_methods(node),
                    "docstring": ast.get_docstring(node),
                    "decorators": [self._get_name(dec) for dec in node.decorator_list],
                    "line_start": node.lineno,
                    "line_end": node.end_lineno
                })

        return classes

    def _extract_class_methods(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Extract methods from a class."""
        methods = []

        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append({
                    "name": item.name,
                    "args": [arg.arg for arg in item.args.args],
                    "returns": self._get_name(item.returns) if item.returns else None,
                    "docstring": ast.get_docstring(item),
                    "decorators": [self._get_name(dec) for dec in item.decorator_list],
                    "is_async": isinstance(item, ast.AsyncFunctionDef),
                    "line_start": item.lineno,
                    "line_end": item.end_lineno
                })

        return methods

    def extract_functions(self) -> List[Dict[str, Any]]:
        """Extract all top-level function definitions."""
        functions = []

        for node in self.tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({
                    "name": node.name,
                    "args": [arg.arg for arg in node.args.args],
                    "defaults": len(node.args.defaults),
                    "returns": self._get_name(node.returns) if node.returns else None,
                    "docstring": ast.get_docstring(node),
                    "decorators": [self._get_name(dec) for dec in node.decorator_list],
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                    "line_start": node.lineno,
                    "line_end": node.end_lineno,
                    "calls": self._extract_function_calls(node)
                })

        return functions

    def _extract_function_calls(self, func_node: ast.FunctionDef) -> List[str]:
        """Extract function calls within a function."""
        calls = []

        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                call_name = self._get_name(node.func)
                if call_name:
                    calls.append(call_name)

        return list(set(calls))  # Remove duplicates

    def extract_globals(self) -> List[Dict[str, Any]]:
        """Extract global variable assignments."""
        globals_list = []

        for node in self.tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        globals_list.append({
                            "name": target.id,
                            "value_type": type(node.value).__name__,
                            "line": node.lineno
                        })

        return globals_list

    def _get_name(self, node) -> Optional[str]:
        """Get name from AST node."""
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        parsed = self.parse()

        return {
            "module_name": parsed.get("module_name"),
            "file_path": parsed.get("file_path"),
            "line_count": parsed.get("line_count", 0),
            "class_count": len(parsed.get("classes", [])),
            "function_count": len(parsed.get("functions", [])),
            "import_count": len(parsed.get("imports", [])),
            "has_docstring": bool(parsed.get("docstring"))
        }


class CodebaseParser:
    """Parse an entire codebase directory."""

    def __init__(self, codebase_path: str):
        """Initialize codebase parser.

        Args:
            codebase_path: Path to codebase directory
        """
        self.codebase_path = codebase_path

    def parse_all(self, pattern: str = "*.py") -> List[Dict[str, Any]]:
        """Parse all Python files in codebase.

        Args:
            pattern: File pattern to match

        Returns:
            List of parsed module data
        """
        modules = []
        path = Path(self.codebase_path)

        for py_file in path.glob(pattern):
            if py_file.is_file():
                parser = CodeParser(str(py_file))
                try:
                    parsed = parser.parse()
                    modules.append(parsed)
                except Exception as e:
                    print(f"Error parsing {py_file}: {e}")

        return modules

    def get_codebase_summary(self) -> Dict[str, Any]:
        """Get summary of entire codebase."""
        modules = self.parse_all()

        total_lines = sum(m.get("line_count", 0) for m in modules)
        total_functions = sum(len(m.get("functions", [])) for m in modules)
        total_classes = sum(len(m.get("classes", [])) for m in modules)

        return {
            "module_count": len(modules),
            "total_lines": total_lines,
            "total_functions": total_functions,
            "total_classes": total_classes,
            "modules": [
                {
                    "name": m.get("module_name"),
                    "lines": m.get("line_count"),
                    "functions": len(m.get("functions", [])),
                    "classes": len(m.get("classes", []))
                }
                for m in modules
            ]
        }


def parse_code_file(file_path: str) -> Dict[str, Any]:
    """Convenience function to parse a single code file.

    Args:
        file_path: Path to Python file

    Returns:
        Parsed code structure
    """
    parser = CodeParser(file_path)
    return parser.parse()


def parse_codebase(codebase_path: str) -> List[Dict[str, Any]]:
    """Convenience function to parse entire codebase.

    Args:
        codebase_path: Path to codebase directory

    Returns:
        List of parsed modules
    """
    parser = CodebaseParser(codebase_path)
    return parser.parse_all()
