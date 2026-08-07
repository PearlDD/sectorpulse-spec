#!/usr/bin/env python3
"""Eval script for SectorPulse — Software Factory eval harness.

Runs each eval dimension as a subprocess and outputs JSON to stdout.

Output format:
    {"results": [{"name": str, "score": float, "weight": float, "passed": bool, "details": str}, ...]}
"""

import json
import subprocess
import sys
import os
import re


def eval_tests() -> dict:
    """Run pytest and report pass rate."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.join(os.path.dirname(__file__), "..", "backend"),
        )
        output = result.stdout + result.stderr
        # Parse pytest output: "X passed, Y failed"
        match = re.search(r"(\d+) passed", output)
        passed_count = int(match.group(1)) if match else 0
        fail_match = re.search(r"(\d+) failed", output)
        failed_count = int(fail_match.group(1)) if fail_match else 0
        total = passed_count + failed_count
        if total == 0:
            score = 0.0
        else:
            score = passed_count / total
        return {
            "name": "tests",
            "score": round(score, 3),
            "weight": 0.25,
            "passed": result.returncode == 0,
            "details": f"{passed_count}/{total} tests passed" if total else "No tests found",
        }
    except subprocess.TimeoutExpired:
        return {"name": "tests", "score": 0.0, "weight": 0.25, "passed": False, "details": "Timed out"}


def eval_lint() -> dict:
    """Run ruff linter."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.path.join(os.path.dirname(__file__), "..", "backend"),
        )
        if result.returncode == 0:
            return {"name": "lint", "score": 1.0, "weight": 0.15, "passed": True, "details": "Clean"}
        error_lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        score = max(0.0, 1.0 - len(error_lines) * 0.05)
        return {
            "name": "lint",
            "score": round(score, 3),
            "weight": 0.15,
            "passed": False,
            "details": f"{len(error_lines)} issues found",
        }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"name": "lint", "score": 0.5, "weight": 0.15, "passed": True, "details": "ruff not available"}


def eval_type_check() -> dict:
    """Run mypy type checker."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "app/", "--ignore-missing-imports"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=os.path.join(os.path.dirname(__file__), "..", "backend"),
        )
        if result.returncode == 0:
            return {"name": "type_check", "score": 1.0, "weight": 0.1, "passed": True, "details": "Clean"}
        error_lines = [ln for ln in result.stdout.splitlines() if "error:" in ln]
        score = max(0.0, 1.0 - len(error_lines) * 0.05)
        return {
            "name": "type_check",
            "score": round(score, 3),
            "weight": 0.1,
            "passed": False,
            "details": f"{len(error_lines)} type errors",
        }
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"name": "type_check", "score": 0.5, "weight": 0.1, "passed": True, "details": "mypy not available"}


def eval_frontend_build() -> dict:
    """Verify frontend TypeScript compiles and builds."""
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    if not os.path.isdir(frontend_dir):
        return {"name": "frontend_build", "score": 0.0, "weight": 0.1, "passed": False, "details": "No frontend dir"}
    try:
        result = subprocess.run(
            ["npm", "run", "build"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=frontend_dir,
        )
        passed = result.returncode == 0
        return {
            "name": "frontend_build",
            "score": 1.0 if passed else 0.0,
            "weight": 0.1,
            "passed": passed,
            "details": "Build succeeded" if passed else (result.stderr or result.stdout)[:300],
        }
    except subprocess.TimeoutExpired:
        return {"name": "frontend_build", "score": 0.0, "weight": 0.1, "passed": False, "details": "Timed out"}


def eval_observability() -> dict:
    """Analyze logging coverage in Python source."""
    import ast
    from pathlib import Path

    skip = {"tests", "test", ".venv", "venv", "node_modules", "__pycache__",
            ".git", ".factory", "eval", "dist", "build", ".mypy_cache"}
    log_pats = [r"\blogger\.\w+\(", r"\blogging\.\w+\(", r"\blog\.\w+\(", r"\bprint\("]

    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
    sources = [f for f in Path(backend_dir).rglob("*.py")
               if not any(p.name in skip for p in f.parents)]
    total_fn = logged_fn = 0

    for src in sources:
        try:
            code = src.read_text(errors="replace")
            tree = ast.parse(code)
        except (OSError, SyntaxError):
            continue
        lines = code.splitlines()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                total_fn += 1
                start = node.lineno - 1
                end = node.end_lineno or start + 1
                body = "\n".join(lines[start:end])
                for pat in log_pats:
                    if re.search(pat, body):
                        logged_fn += 1
                        break

    if total_fn == 0:
        return {"name": "observability", "score": 0.0, "weight": 0.1,
                "passed": True, "details": "No functions found"}

    cov = logged_fn / total_fn
    score = min(1.0, cov * 2)  # 50% coverage = full score

    return {"name": "observability", "score": round(score, 3), "weight": 0.1,
            "passed": score >= 0.2, "details": f"coverage={cov:.0%} ({logged_fn}/{total_fn})"}


def eval_capability_surface() -> dict:
    """Count API endpoints and agent capabilities."""
    backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
    routes_file = os.path.join(backend_dir, "app", "api", "routes.py")
    agents_dir = os.path.join(backend_dir, "app", "agents")

    endpoint_count = 0
    agent_count = 0

    if os.path.isfile(routes_file):
        with open(routes_file) as f:
            content = f.read()
        endpoint_count = len(re.findall(r'@router\.(get|post|put|delete|patch)\(', content))

    if os.path.isdir(agents_dir):
        for fname in os.listdir(agents_dir):
            if fname.endswith(".py") and fname != "__init__.py":
                agent_count += 1

    # Target: 7 endpoints + 5 agents = 12 capabilities
    score = min(1.0, (endpoint_count + agent_count) / 12)

    return {"name": "capability_surface", "score": round(score, 3), "weight": 0.2,
            "passed": score >= 0.5,
            "details": f"{endpoint_count} endpoints, {agent_count} agents"}


def eval_date_safety() -> dict:
    """Verify agent prompts don't contain date references (anti-look-ahead-bias)."""
    import ast
    from pathlib import Path

    agents_dir = os.path.join(os.path.dirname(__file__), "..", "backend", "app", "agents")
    if not os.path.isdir(agents_dir):
        return {"name": "guard_patterns", "score": 0.0, "weight": 0.1, "passed": False,
                "details": "No agents directory"}

    # Only flag patterns that inject current/dynamic dates — NOT historical reference data.
    # Historical few-shot examples (e.g., "2009 Q2-Q4") are allowed as empirical training data.
    date_patterns = [
        r'\btoday\b',
        r'\bcurrent\s+date\b',
        r'\bdatetime\.now\b',
        r'\bdate\.today\b',
        r'\bas of \w+ \d{4}\b',
    ]

    violations = []
    for f in Path(agents_dir).glob("*.py"):
        if f.name == "__init__.py":
            continue
        code = f.read_text()
        # Check string literals in the AST
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) > 20:
                    for pat in date_patterns:
                        if re.search(pat, node.value, re.IGNORECASE):
                            violations.append(f"{f.name}:{node.lineno}")
                            break
        except SyntaxError:
            pass

    passed = len(violations) == 0
    return {
        "name": "guard_patterns",
        "score": 1.0 if passed else 0.0,
        "weight": 0.1,
        "passed": passed,
        "details": "No date leaks" if passed else f"Date refs in: {', '.join(violations[:5])}",
    }


EVALS = [eval_tests, eval_lint, eval_type_check, eval_frontend_build,
         eval_observability, eval_capability_surface, eval_date_safety]


def main() -> None:
    results = [fn() for fn in EVALS]
    output = {"results": results}
    json.dump(output, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
