"""codeforge CLI: collect, upload, init, config."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from codeforge import __version__
from codeforge.analyzers import run_all
from codeforge.analyzers.base import AnalyzerContext
from codeforge.config import load_config
from codeforge.report import save_report


def _fresh_report(project: dict, collector_run_id: str) -> dict:
    import uuid

    return {
        "build": {
            "status": "UNKNOWN",
            "collector_run_id": collector_run_id or str(uuid.uuid4()),
            "environment": {
                "os": sys.platform,
                "tool_versions": {},
            },
        },
        "metrics": {
            "binary_size": None,
            "binary_size_change": None,
            "pct_binary_growth": None,
            "artifact_count": 0,
            "artifact_paths": [],
        },
        "tests": [],
        "benchmarks": [],
        "static_analysis": [],
        "complexity": {},
        "dependencies": [],
        "architecture": {"module_count": 0, "edge_count": 0, "edges": [], "layer_mapping": {}},
    }


def cmd_collect(args: argparse.Namespace) -> int:
    root = Path(args.repo).resolve()
    if not root.is_dir():
        print(f"error: repo path is not a directory: {root}", file=sys.stderr)
        return 2
    cfg = load_config(Path(args.config) if args.config and args.config != "autodetect" else root / "codeforge.toml")
    project = cfg["project"]
    report = _fresh_report(project, args.run_id or project.get("collector_run_id"))
    if project.get("repository_url"):
        report["build"]["environment"]["repository_url"] = project["repository_url"]
    ctx = AnalyzerContext(repo_root=root, config=cfg, report=report)
    results = run_all(ctx, skip=set(args.skip))
    out_path = Path(args.out)
    save_report(report, out_path)
    for result in results:
        note = result.note or result.request.get("note", "")
        print(f"[{result.status:>12}] {result.name:<16} {note}".rstrip())
    print(f"report written to {out_path}")
    return 0


def cmd_upload(args: argparse.Namespace) -> int:
    import urllib.error
    import urllib.request

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"error: report not found: {report_path}", file=sys.stderr)
        return 2
    with report_path.open(encoding="utf-8") as fh:
        payload = fh.read()

    url = args.api.rstrip("/") + f"/api/projects/{args.project}/builds"
    headers = {"Content-Type": "application/json"}
    if args.api_key:
        headers["X-API-Key"] = args.api_key
    req = urllib.request.Request(url, data=payload.encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        print(f"error: server returned {exc.code}: {exc.read().decode(errors='replace')}", file=sys.stderr)
        return 1
    print(body)
    return 0


_INIT_TOML = """\
[project]
name = "SampleCppProject"
repository_url = ""
branch = "main"
build_command = "cmake -S . -B build && cmake --build build -j"
test_command = "ctest --test-dir build --output-on-failure"
benchmark_command = "./build/bin/benchmarks"
binary_path = "build/bin/sample_app"

[analyzers.complexity]
tool = "auto"
complexity_threshold = 15

[analyzers.architecture.layers]
presentation = ["src/presentation"]
application = ["src/application"]
domain = ["src/domain"]
infrastructure = ["src/infrastructure"]
"""

_JAVA_INIT_TOML = """\
[project]
name = "SampleJavaProject"
language = "java"
repository_url = ""
branch = "main"

# no build tool is installed for this example; plain javac + JUnit console.
build_command = "cmd /c build.bat"
test_command = "cmd /c run-tests.bat"
benchmark_command = "cmd /c run-benchmarks.bat"

# auto-located JAR when binary_path is unset; or point at an explicit jar:
binary_path = "build/analytic-engine.jar"
build_dir = "build"

[analyzers.complexity]
tool = "auto"
complexity_threshold = 15

[analyzers.architecture.layers]
presentation = ["src/main/java/avlog/presentation"]
application = ["src/main/java/avlog/application"]
domain = ["src/main/java/avlog/domain"]
infrastructure = ["src/main/java/avlog/infrastructure"]
"""


def cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if path.exists():
        print(f"error: {path} already exists", file=sys.stderr)
        return 2
    template = _JAVA_INIT_TOML if args.language == "java" else _INIT_TOML
    path.write_text(template, encoding="utf-8")
    print(f"wrote {path}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    import json

    root = Path(args.repo).resolve()
    cfg = load_config(root / "codeforge.toml")
    print(json.dumps(cfg, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="codeforge", description="CODEFORGE collector CLI")
    parser.add_argument("--version", action="version", version=f"codeforge {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("collect", help="run analyzers and write build_report.json")
    p.add_argument("--repo", default=".", help="repository root (default: current dir)")
    p.add_argument("--config", default="autodetect", help="path to codeforge.toml (default: <repo>/codeforge.toml)")
    p.add_argument("--out", default="build_report.json", help="output path")
    p.add_argument("--run-id", default="", help="collector run id (default: random)")
    p.add_argument("--skip", nargs="*", default=[], help="analyzers to skip (git build tests static_analysis complexity benchmarks dependencies architecture)")
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("upload", help="POST a build_report.json to the CODEFORGE API")
    p.add_argument("--api", default="http://localhost:8000", help="API base URL")
    p.add_argument("--project", required=True, help="project UUID")
    p.add_argument("--report", default="build_report.json", help="report file to upload")
    p.add_argument("--api-key", default="", help="optional X-API-Key for the project")
    p.set_defaults(func=cmd_upload)

    p = sub.add_parser("init", help="write a starter codeforge.toml")
    p.add_argument("--path", default="codeforge.toml", help="destination path")
    p.add_argument("--language", default="cpp", choices=["cpp", "java"], help="starter template language")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("config", help="print the effective configuration")
    p.add_argument("--repo", default=".", help="repository root (default: current dir)")
    p.set_defaults(func=cmd_config)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())