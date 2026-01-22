"""
Autonomous Debugging AI Agent
Scans the codebase for errors and fixes them automatically.
"""
import os
import sys
import re
import ast
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class ErrorType(Enum):
    SYNTAX = "syntax"
    IMPORT = "import"
    TYPE = "type"
    MISSING_FILE = "missing_file"
    MISSING_INIT = "missing_init"
    CIRCULAR = "circular"
    UNDEFINED = "undefined"

@dataclass
class CodeError:
    file: str
    line: int
    error_type: ErrorType
    message: str
    suggestion: str = ""
    auto_fixable: bool = False

class DebugAgent:
    """
    Autonomous debugging agent that scans and fixes code errors.
    """
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.errors: List[CodeError] = []
        self.fixes_applied: List[str] = []
        
    def scan_all(self) -> Dict[str, Any]:
        """Run all scans and return summary."""
        print("=" * 60)
        print("AUTONOMOUS DEBUGGING AGENT")
        print("=" * 60)
        
        # Scan Python files
        print("\n[1/4] Scanning Python files...")
        self._scan_python_files()
        
        # Scan for missing __init__.py
        print("\n[2/4] Checking __init__.py files...")
        self._check_init_files()
        
        # Scan imports
        print("\n[3/4] Validating imports...")
        self._validate_imports()
        
        # Scan TypeScript (basic syntax)
        print("\n[4/4] Scanning TypeScript/TSX files...")
        self._scan_typescript_files()
        
        return self._generate_report()
    
    def _scan_python_files(self):
        """Scan Python files for syntax errors."""
        python_files = list(self.root_dir.rglob("*.py"))
        
        for py_file in python_files:
            if "__pycache__" in str(py_file) or ".venv" in str(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                ast.parse(source)
            except SyntaxError as e:
                self.errors.append(CodeError(
                    file=str(py_file.relative_to(self.root_dir)),
                    line=e.lineno or 0,
                    error_type=ErrorType.SYNTAX,
                    message=str(e.msg),
                    suggestion=f"Fix syntax at line {e.lineno}"
                ))
            except Exception as e:
                self.errors.append(CodeError(
                    file=str(py_file.relative_to(self.root_dir)),
                    line=0,
                    error_type=ErrorType.SYNTAX,
                    message=str(e)
                ))
    
    def _check_init_files(self):
        """Check for missing __init__.py in package directories."""
        for dir_path in self.root_dir.rglob("*"):
            if not dir_path.is_dir():
                continue
            if "__pycache__" in str(dir_path) or ".venv" in str(dir_path):
                continue
            if "node_modules" in str(dir_path) or ".next" in str(dir_path):
                continue
            
            # Check if directory contains .py files but no __init__.py
            py_files = list(dir_path.glob("*.py"))
            init_file = dir_path / "__init__.py"
            
            if py_files and not init_file.exists():
                # Check if it looks like a package (has subdirectories with .py)
                parent_has_init = (dir_path.parent / "__init__.py").exists()
                if parent_has_init or "backend" in str(dir_path):
                    self.errors.append(CodeError(
                        file=str(dir_path.relative_to(self.root_dir)),
                        line=0,
                        error_type=ErrorType.MISSING_INIT,
                        message="Missing __init__.py in package directory",
                        suggestion="Create __init__.py",
                        auto_fixable=True
                    ))
    
    def _validate_imports(self):
        """Validate Python imports."""
        python_files = list(self.root_dir.rglob("*.py"))
        
        for py_file in python_files:
            if "__pycache__" in str(py_file) or ".venv" in str(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    source = f.read()
                
                tree = ast.parse(source)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._check_import(py_file, node.lineno, alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self._check_import(py_file, node.lineno, node.module, from_import=True)
            except:
                pass
    
    def _check_import(self, py_file: Path, line: int, module: str, from_import: bool = False):
        """Check if an import is valid."""
        # Skip standard library and common packages
        stdlib = ['os', 'sys', 're', 'json', 'time', 'datetime', 'typing', 'enum', 
                  'dataclasses', 'collections', 'math', 'uuid', 'asyncio', 'pathlib']
        external = ['fastapi', 'pydantic', 'redis', 'httpx', 'uvicorn', 'pytest', 'numpy', 'pandas']
        
        base_module = module.split('.')[0]
        
        if base_module in stdlib or base_module in external:
            return
        
        # Check internal imports
        if base_module == 'backend':
            module_path = module.replace('.', '/')
            possible_paths = [
                self.root_dir / f"{module_path}.py",
                self.root_dir / module_path / "__init__.py"
            ]
            
            if not any(p.exists() for p in possible_paths):
                self.errors.append(CodeError(
                    file=str(py_file.relative_to(self.root_dir)),
                    line=line,
                    error_type=ErrorType.IMPORT,
                    message=f"Cannot resolve import: {module}",
                    suggestion="Check if module path is correct"
                ))
    
    def _scan_typescript_files(self):
        """Basic scan of TypeScript/TSX files."""
        ts_files = list(self.root_dir.rglob("*.tsx")) + list(self.root_dir.rglob("*.ts"))
        
        for ts_file in ts_files:
            if "node_modules" in str(ts_file) or ".next" in str(ts_file):
                continue
            
            try:
                with open(ts_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for common issues
                lines = content.split('\n')
                
                for i, line in enumerate(lines, 1):
                    # Check for unmatched braces (simple heuristic)
                    if line.count('{') != line.count('}'):
                        if not line.strip().endswith('{') and not line.strip().startswith('}'):
                            if '{' in line or '}' in line:
                                # Might be a multi-line, skip
                                pass
                    
                    # Check for missing imports (simple pattern)
                    if "from '" not in line and "from \"" not in line:
                        # Check for common undefined components
                        undefined_patterns = [
                            (r'\bRouter\b', 'next/router'),
                            (r'\bLink\b', 'next/link'),
                            (r'\bImage\b', 'next/image'),
                        ]
                        for pattern, suggested_import in undefined_patterns:
                            if re.search(pattern, line) and 'import' not in line:
                                # Check if imported at top
                                if suggested_import.split('/')[-1] not in content[:500]:
                                    pass  # Potential missing import
                
            except Exception as e:
                self.errors.append(CodeError(
                    file=str(ts_file.relative_to(self.root_dir)),
                    line=0,
                    error_type=ErrorType.SYNTAX,
                    message=f"Error reading file: {e}"
                ))
    
    def auto_fix(self) -> int:
        """Apply automatic fixes where possible."""
        fixed = 0
        
        for error in self.errors:
            if error.auto_fixable:
                if error.error_type == ErrorType.MISSING_INIT:
                    init_path = self.root_dir / error.file / "__init__.py"
                    try:
                        init_path.touch()
                        self.fixes_applied.append(f"Created {error.file}/__init__.py")
                        fixed += 1
                    except:
                        pass
        
        return fixed
    
    def _generate_report(self) -> Dict[str, Any]:
        """Generate error report."""
        by_type = {}
        for error in self.errors:
            error_type = error.error_type.value
            if error_type not in by_type:
                by_type[error_type] = []
            by_type[error_type].append(error)
        
        print("\n" + "=" * 60)
        print("SCAN RESULTS")
        print("=" * 60)
        print(f"Total errors found: {len(self.errors)}")
        print(f"Auto-fixable: {sum(1 for e in self.errors if e.auto_fixable)}")
        print()
        
        for error_type, errors in by_type.items():
            print(f"\n{error_type.upper()} ERRORS ({len(errors)}):")
            for e in errors[:10]:  # Show first 10
                print(f"  - {e.file}:{e.line} - {e.message}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more")
        
        return {
            "total": len(self.errors),
            "by_type": {k: len(v) for k, v in by_type.items()},
            "auto_fixable": sum(1 for e in self.errors if e.auto_fixable),
            "errors": [{"file": e.file, "line": e.line, "type": e.error_type.value, "message": e.message} 
                       for e in self.errors]
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Autonomous Debugging Agent")
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--fix", action="store_true", help="Apply automatic fixes")
    args = parser.parse_args()
    
    agent = DebugAgent(args.root)
    report = agent.scan_all()
    
    if args.fix:
        print("\n" + "=" * 60)
        print("APPLYING AUTOMATIC FIXES")
        print("=" * 60)
        fixed = agent.auto_fix()
        print(f"Fixed {fixed} issues:")
        for fix in agent.fixes_applied:
            print(f"  [FIXED] {fix}")
    
    # Return non-zero if errors found
    return 1 if report["total"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
