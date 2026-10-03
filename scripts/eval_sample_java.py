r"""Evaluation script: ingest the analytic-engine-java sample history end-to-end.

For each release snapshot `sample-projects/analytic-engine-java/releases/vN`,
rebuild the release's git history inside a temp work tree, run the codeforge
collector (config-driven: language=java, JUnit XML), and POST the report to a
live backend started on a fresh SQLite database. Prints the per-build health
trend plus the failing test details captured by the backend.

Staging: the work tree lives under the OS temp dir (`codeforge-eval/`), never
inside the CODEFORGE repo, so the collector's git analyzer (repo lookup, the
complexity analyzer's `build/` path filter) sees only the release — and the
sample's `..\..\tools\junit` reference stays valid with the jar mirrored into
`codeforge-eval/tools/junit`.

Requires: backend deps in the active venv (uvicorn, alembic) and `codeforge`
collector importable from that venv, plus JDK 26 (javac/jar/java) on PATH.

Intended for Windows/cmd; change the command strings if porting to POSIX.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample-projects" / "analytic-engine-java"
RELEASES = SAMPLE / "releases"
BACKEND = ROOT / "backend"
EVAL_ROOT = Path(tempfile.mkdtemp(prefix="codeforge-eval-"))
WORK = EVAL_ROOT / "repos" / "analytic-engine-java"
JUNIT_JAR = ROOT / "tools" / "junit" / "junit-platform-console-standalone-1.11.4.jar"
PORT = 8778
API = f"http://127.0.0.1:{PORT}"
DB = BACKEND / "eval-java.db"

GIT_AUTHOR = ["-c", "user.name=CODEFORGE Eval", "-c", "user.email=codeforge-eval@local"]


def run(args, cwd=None, capture=True):
    return subprocess.run(args, cwd=cwd, capture_output=capture, text=True, shell=False, check=False)


def build_history() -> dict[str, str]:
    """Create EVAL_ROOT/<sample> with the JUnit jar two levels up, then replay
    each release snapshot into the work tree as one commit (v1, v2, v3).
    Returns {tag: commit sha}."""
    shutil.copytree(JUNIT_JAR.parent, EVAL_ROOT / "tools" / "junit")
    (EVAL_ROOT / "repos").mkdir()
    WORK.mkdir()
    run(["git", "init", "-q", "-b", "main"], cwd=WORK)
    tags = sorted(p.name for p in RELEASES.iterdir() if p.is_dir())
    commits: dict[str, str] = {}
    for tag in tags:
        for child in WORK.iterdir():
            if child.name != ".git":
                _rm(child)
        for item in (RELEASES / tag).iterdir():
            shutil.copytree(item, WORK / item.name) if item.is_dir() else shutil.copy2(item, WORK / item.name)
        run(["git", "add", "-A"], cwd=WORK)
        run(["git", *GIT_AUTHOR, "commit", "-qm", f"{tag} release"], cwd=WORK)
        commits[tag] = run(["git", "rev-parse", "HEAD"], cwd=WORK).stdout.strip()
    return commits


def _rm(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def collect_and_upload(project_id: str, tag: str, sha: str):
    run(["git", "checkout", "-q", "--detach", sha], cwd=WORK)
    report = ROOT / "build" / f"java-{tag}.json"
    collect = run(
        [sys.executable, "-m", "codeforge.cli", "collect", "--repo", str(WORK), "--out", str(report)]
    )
    if collect.returncode != 0:
        print(collect.stdout + collect.stderr)
        raise SystemExit(f"collect failed for {tag}")
    upload = run(
        [
            sys.executable,
            "-m",
            "codeforge.cli",
            "upload",
            "--api",
            API,
            "--project",
            project_id,
            "--report",
            str(report),
        ]
    )
    print(f"  {tag}: " + (upload.stdout + upload.stderr).strip())
    if upload.returncode != 0:
        raise SystemExit(f"upload failed for {tag}")


def wait_server() -> None:
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"{API}/api/projects", timeout=1):
                return
        except (OSError, ValueError):
            time.sleep(0.5)
    raise SystemExit("backend did not start in time")


def main() -> int:
    if DB.exists():
        DB.unlink()
    os.environ["CODEFORGE_DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
    run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND)

    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=BACKEND,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_server()
        body = b'{"project_name":"AnalyticEngine Java","description":"sample Java release history","repository_url":""}'
        req = urllib.request.Request(
            f"{API}/api/projects", data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            project_id = json.loads(resp.read().decode("utf-8"))["id"]
        print(f"project: {project_id}")

        commits = build_history()
        for tag, sha in commits.items():
            collect_and_upload(project_id, tag, sha)

        print("\nbuild trend:")
        with sqlite3.connect(DB) as con:
            rows = con.execute(
                "select b.build_number, b.commit_hash, h.overall_score, h.grade, b.status, "
                "b.compiler_warnings, "
                "(select count(*) from test_results tr where tr.build_id=b.id and tr.status='failed') "
                "from builds b join health_scores h on h.build_id=b.id order by b.build_number"
            ).fetchall()
        for num, commit, score, grade, status, warnings, fails in rows:
            print(f"  build {num}: score {score:.1f} ({grade}) {status} warnings={warnings} failed_tests={fails} commit={(commit or 'n/a')[:8]}")

        tests = json.loads(urllib.request.urlopen(f"{API}/api/projects/{project_id}/tests", timeout=10).read())
        print("  failed tests:", tests["failed"], "| pass_rate:", round(tests["pass_rate"], 3))
        for f in tests.get("failures", []):
            print("    FAIL", f["name"])
            print("      msg:", (f.get("message") or "")[:110])

        insights = json.loads(
            urllib.request.urlopen(f"{API}/api/projects/{project_id}/insights?limit=20", timeout=10).read()
        )
        for ins in insights:
            print("  insight", ins["priority"], "|", ins["title"])
    finally:
        server.terminate()
        server.wait(timeout=10)
        shutil.rmtree(EVAL_ROOT, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())