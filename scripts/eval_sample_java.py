"""Evaluation script: ingest the analytic-engine-java sample history end-to-end.

For each release commit v1..v3 (in git order), check the sample repo out at that
commit, run the buildpulse collector (config-driven: language=java, JUnit XML),
and POST the report to a live backend started on a fresh SQLite database. Prints
the per-build health trend plus the failing test details captured by the backend.

Requires: backend deps in the active venv (uvicorn, alembic) and `buildpulse`
collector importable from that venv. JUnit console jar is referenced from
buildpulse/tools/junit by the sample's run-tests.bat.

Intended for Windows/cmd; change SHELL/args if porting to POSIX.
"""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample-projects" / "analytic-engine-java"
BACKEND = ROOT / "backend"
PORT = 8778
API = f"http://127.0.0.1:{PORT}"
DB = BACKEND / "eval-java.db"


def run(args, cwd=None, capture=True):
    return subprocess.run(args, cwd=cwd, capture_output=capture, text=True, shell=False, check=False)


def collect_and_upload(project_id: str, release: str):
    run(["git", "checkout", "-q", "--detach", release], cwd=SAMPLE)
    report = SAMPLE / f"build_report_{release}.json"
    collect = run(
        [sys.executable, "-m", "buildpulse.cli", "collect", "--repo", str(SAMPLE), "--out", str(report)]
    )
    if collect.returncode != 0:
        print(collect.stdout + collect.stderr)
        raise SystemExit(f"collect failed for {release}")
    upload = run(
        [
            sys.executable,
            "-m",
            "buildpulse.cli",
            "upload",
            "--api",
            API,
            "--project",
            project_id,
            "--report",
            str(report),
        ]
    )
    print(f"  {release[:8]}: " + (upload.stdout + upload.stderr).strip())
    if upload.returncode != 0:
        raise SystemExit(f"upload failed for {release}")


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
    os.environ["BUILDPULSE_DATABASE_URL"] = f"sqlite:///{DB.as_posix()}"
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

        reco = run(["git", "log", "--all", "--reverse", "--pretty=%h %s"], cwd=SAMPLE, capture=True)
        releases = [line.split()[0] for line in reco.stdout.splitlines()]
        for release in releases:
            collect_and_upload(project_id, release)

        print("\nbuild trend:")
        with sqlite3.connect(DB) as con:
            rows = con.execute(
                "select b.build_number, b.commit_hash, h.overall_score, h.grade, b.status, "
                "b.compiler_warnings, "
                "(select count(*) from test_results tr where tr.build_id=b.id and tr.status='failed') "
                "from builds b join health_scores h on h.build_id=b.id order by b.build_number"
            ).fetchall()
        for num, commit, score, grade, status, warnings, fails in rows:
            print(f"  build {num}: score {score:.1f} ({grade}) {status} warnings={warnings} failed_tests={fails} {commit[:8]}")

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())