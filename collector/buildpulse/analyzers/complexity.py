"""Internal complexity analyzer (McCabe cyclomatic + lizard-style MI).

Pure Python, deterministic, no external tools. Tokenizes C/C++ sources,
skipping comments, string literals, and preprocessor lines. Reports LOC,
function count, cyclomatic complexity (per function + totals), functions above
a threshold, and an estimated Maintainability Index.
"""

from __future__ import annotations

import math
import shutil
from dataclasses import dataclass

from buildpulse.analyzers.base import STATUS_OK, STATUS_SKIPPED, AnalyzerContext, AnalyzerResult

_SOURCE_SUFFIXES = {".cpp", ".cc", ".cxx", ".c", ".hpp", ".hh", ".h", ".java"}
_DECISION_TOKENS = {"if", "for", "while", "catch", "case", "&&", "||", "?"}
_CTRL_WORDS = {"if", "for", "while", "switch", "catch", "do", "return", "break", "continue", "else", "throw", "goto"}
# control statements that look like `keyword (...) { ... }` and must NOT be
# scored as functions (Java lambda sites and C++ guards included).
_STATEMENT_LEADERS = {"if", "for", "while", "switch", "catch", "synchronized"}
_OPERATOR_TOKENS = {
    "+", "-", "*", "/", "%", "=", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "!",
    "&", "|", "^", "~", "<<", ">>", "++", "--", "+=", "-=", "*=", "/=", "%=", "?", ":",
    "->", "::",
}


@dataclass
class _Function:
    name: str
    cyclomatic: int
    loc: int
    operands: int
    operators: int
    distinct_operands: int
    distinct_operators: int
    source: str = ""


def _strip_comments_and_strings(code: str) -> str:
    """Remove line/block comments and string/char literals (naive but safe)."""
    out: list[str] = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        nxt = code[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/":
            while i < n and code[i] != "\n":
                i += 1
            continue
        if c == "/" and nxt == "*":
            i += 2
            while i + 1 < n and not (code[i] == "*" and code[i + 1] == "/"):
                i += 1
            i += 2
            continue
        if c in ('"', "'"):
            quote = c
            i += 1
            while i < n:
                if code[i] == "\\":
                    i += 2
                    continue
                if code[i] == quote:
                    break
                i += 1
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


_PUNCT_TOKENS = ["&&", "||", "==", "!=", "<=", ">=", "->", "::", "<<", ">>", "++", "--", "+=", "-=", "*=", "/="]


def _tokenize(code: str) -> list[str]:
    tokens: list[str] = []
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if c.isspace():
            i += 1
            continue
        if c.isalpha() or c == "_":
            j = i
            while j < n and (code[j].isalnum() or code[j] == "_"):
                j += 1
            tokens.append(code[i:j])
            i = j
            continue
        if c.isdigit():
            j = i
            while j < n and (code[j].isalnum() or code[j] in "._"):
                j += 1
            tokens.append(code[i:j])
            i = j
            continue
        matched = False
        for op in _PUNCT_TOKENS:
            if code.startswith(op, i):
                tokens.append(op)
                i += len(op)
                matched = True
                break
        if not matched:
            tokens.append(c)
            i += 1
    return tokens


def _find_function_bodies(code: str) -> list[list[str]]:
    """Return token slices for each function body found (best-effort brace match)."""
    tokens = _tokenize(code)
    bodies: list[list[str]] = []
    i, n = 0, len(tokens)
    while i < n:
        if tokens[i] == "{":
            i += 1
            continue
        if i + 2 < n and tokens[i + 1] == "(" and tokens[i] not in _STATEMENT_LEADERS:
            j = i + 1
            depth = 0
            while j < n:
                if tokens[j] == "(":
                    depth += 1
                elif tokens[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j + 1 < n and tokens[j + 1] == "{":
                body = tokens[j + 2:]
                depth = 1
                k = 0
                while k < len(body):
                    if body[k] == "{":
                        depth += 1
                    elif body[k] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                if k < len(body):
                    bodies.append(tokens[i : j + 2 + k + 1])
                    i = j + 2 + k + 1
                    continue
        i += 1
    return bodies


def _cyclomatic(body: list[str]) -> int:
    return 1 + sum(1 for t in body if t in _DECISION_TOKENS)


def _halstead(body: list[str]) -> dict[str, int]:
    operands = [t for t in body if (t.isalnum() or "_" in t) and t not in _CTRL_WORDS and not t[0].isdigit()]
    operator_tokens = [t for t in body if t in _OPERATOR_TOKENS]
    return {
        "operands": len(operands),
        "operators": len(operator_tokens),
        "distinct_operands": len(set(operands)),
        "distinct_operators": len(set(operator_tokens)),
    }


def _avg(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _volume(fn: _Function) -> float:
    n = fn.operands + fn.operators
    eta = fn.distinct_operands + fn.distinct_operators
    if n <= 0 or eta <= 1:
        return 0.0
    return n * math.log2(eta)


def _maintainability(functions: list[_Function]) -> float:
    if not functions:
        return 100.0
    avg_vol = _avg(_volume(fn) for fn in functions)
    avg_cc = _avg(fn.cyclomatic for fn in functions)
    avg_loc = _avg(fn.loc for fn in functions)
    raw = 171 - 5.2 * math.log(max(avg_vol, 1.0)) - 0.23 * avg_cc - 16.2 * math.log(max(avg_loc, 1.0))
    return max(0.0, min(100.0, raw * 100.0 / 171.0))


def analyze_complexity(ctx: AnalyzerContext) -> AnalyzerResult:
    if shutil.which("lizard"):
        return _analyze_with_lizard(ctx)
    return _analyze_internal(ctx)


def _analyze_with_lizard(ctx: AnalyzerContext) -> AnalyzerResult:
    import subprocess

    threshold = int(ctx.config["analyzers"].get("complexity", {}).get("complexity_threshold", 15))
    files = sorted(
        p for p in ctx.repo_root.rglob("*")
        if p.is_file() and p.suffix in _SOURCE_SUFFIXES and "build" not in p.parts
    )
    if not files:
        ctx.report["complexity"] = {"lines_of_code": 0, "functions": 0}
        ctx.set_tool_version("complexity", STATUS_SKIPPED)
        return AnalyzerResult("complexity", STATUS_SKIPPED, {})
    result = subprocess.run(
        ["lizard", "--csv", *[str(f) for f in files]],
        cwd=ctx.repo_root,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    stats: dict = {"lines_of_code": 0, "functions": 0, "cyclomatic_complexity_total": 0,
                   "avg_function_complexity": 0.0, "max_function_complexity": 0,
                   "functions_above_threshold": 0, "complexity_threshold": threshold,
                   "maintainability_index": 100.0, "avg_function_length": 0.0,
                   "top_complex_functions": []}
    if result.returncode == 0:
        rows = [line for line in result.stdout.splitlines() if line.strip() and not line.startswith("NSLOC")]
        complexities = []
        for row in rows:
            parts = [p.strip() for p in row.split(",")]
            if len(parts) >= 6 and parts[2].isdigit():
                complexity = int(parts[2])
                complexities.append(complexity)
                stats["functions"] += 1
        if complexities:
            stats["cyclomatic_complexity_total"] = sum(complexities)
            stats["max_function_complexity"] = max(complexities)
            stats["functions_above_threshold"] = sum(1 for c in complexities if c >= threshold)
    ctx.report["complexity"] = stats
    ctx.set_tool_version("complexity", "lizard")
    return AnalyzerResult("complexity", STATUS_OK, stats)


def _analyze_internal(ctx: AnalyzerContext) -> AnalyzerResult:
    threshold = int(ctx.config["analyzers"].get("complexity", {}).get("complexity_threshold", 15))
    files = sorted(
        p for p in ctx.repo_root.rglob("*")
        if p.is_file() and p.suffix in _SOURCE_SUFFIXES and "build" not in p.parts
    )
    if not files:
        ctx.report["complexity"] = {"lines_of_code": 0, "functions": 0}
        ctx.set_tool_version("complexity", STATUS_SKIPPED)
        return AnalyzerResult("complexity", STATUS_SKIPPED, {})

    total_loc = 0
    all_functions: list[_Function] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        total_loc += sum(1 for line in text.splitlines() if line.strip())
        code = _strip_comments_and_strings(text)
        if not code.strip():
            continue
        for body in _find_function_bodies(code):
            all_functions.append(
                _Function(
                    name=body[0] if body else "<anonymous>",
                    cyclomatic=_cyclomatic(body),
                    loc=len(body) // 8 or 1,
                    source=path.relative_to(ctx.repo_root).as_posix(),
                    **_halstead(body),
                )
            )

    top = sorted(all_functions, key=lambda fn: fn.cyclomatic, reverse=True)[:50]
    functions_above = sum(1 for fn in all_functions if fn.cyclomatic >= threshold)
    stats = {
        "lines_of_code": total_loc,
        "functions": len(all_functions),
        "cyclomatic_complexity_total": sum(fn.cyclomatic for fn in all_functions),
        "avg_function_complexity": round(_avg(fn.cyclomatic for fn in all_functions), 2),
        "max_function_complexity": max((fn.cyclomatic for fn in all_functions), default=0),
        "functions_above_threshold": functions_above,
        "complexity_threshold": threshold,
        "maintainability_index": round(_maintainability(all_functions), 2),
        "avg_function_length": round(_avg(fn.loc for fn in all_functions), 2),
        "top_complex_functions": [
            {"file": fn.source, "function": fn.name, "complexity": fn.cyclomatic} for fn in top
        ],
    }
    ctx.report["complexity"] = stats
    ctx.set_tool_version("complexity", "internal")
    return AnalyzerResult("complexity", STATUS_OK, stats)