"""Evaluation script: ingest the analytic-engine sample history end-to-end.

For each release commit v1..v5 (in git order), check the sample repo out at that
commit, run the buildpulse collector, and POST the report to a live backend
started on a fresh SQLite database. Prints the per-build health trend.

Requires: backend deps installed in the active venv (uvicorn, alembic, a
build-report-ready DB via BUILDPULSE_DATABASE_URL) and `buildpulse` on PATH.

Intended for Windows/cmd. Change SHELL/args if porting to POSIX.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "sample-projects" / "analytic-engine"
BACKEND = ROOT / "backend"
PORT = 8777
API = f"http://127.0.0.1:{PORT}"
DB = BACKEND / "eval.db"


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
    print(f"  {release:>3}: " + (upload.stdout + upload.stderr).strip())
    if upload.returncode != 0:
        raise SystemExit(f"upload failed for {release}")


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
        for _ in range(30):
            try:
                with urllib.request.urlopen(f"{API}/api/projects", timeout=1):
                    break
            except (OSError, ValueError):
                time.sleep(0.5)
        body = b'{"project_name":"AnalyticEngine","description":"sample release history","repository_url":""}'
        req = urllib.request.Request(
            f"{API}/api/projects", data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            project_id = resp.read().decode("utf-8")
        import json

        project_id = json.loads(project_id)["id"]
        print(f"project: {project_id}")

        reco = run(["git", "log", "--reverse", "--pretty=%h %s"], cwd=SAMPLE, capture=True)
        releases = [line.split()[0] for line in reco.stdout.splitlines()]
        for release in releases:
            collect_and_upload(project_id, release)

        print("\nbuild numbers:")
        with sqlite3.connect(DB) as con:
            rows = con.execute(
                "select b.build_number, b.commit_hash, h.overall_score, h.grade, b.status "
                "from builds b join health_scores h on h.build_id=b.id order by b.build_number"
            ).fetchall()
        for row in rows:
            print("  build", row[0], "score", f"{row[2]:.1f}", "grade", row[3], row[4], row[1][:8])
    finally:
        server.terminate()
        server.wait(timeout=10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())