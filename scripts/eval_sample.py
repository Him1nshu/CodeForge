"""Evaluation script: ingest the analytic-engine sample history end-to-end.

For each release snapshot `sample-projects/analytic-engine/releases/vN`,
rebuild the release's git history inside a temp work tree, run the buildpulse
collector (config-driven), and POST the report to a live backend started on a
fresh SQLite database. Prints the per-build health trend.

Staging: the work tree lives under the OS temp dir (`buildpulse-eval/`), never
inside the BuildPulse repo, so the collector's git analyzer (repo lookup, the
complexity analyzer's `build/` path filter) sees only the releases.

Requires: backend deps installed in the active venv (uvicorn, alembic) and
`buildpulse` importable from that venv, plus g++ on PATH.

Intended for Windows/cmd. Change the command strings if porting to POSIX.
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
SAMPLE = ROOT / "sample-projects" / "analytic-engine"
RELEASES = SAMPLE / "releases"
BACKEND = ROOT / "backend"
EVAL_ROOT = Path(tempfile.mkdtemp(prefix="buildpulse-eval-"))
WORK = EVAL_ROOT / "repos" / "analytic-engine"
PORT = 8777
API = f"http://127.0.0.1:{PORT}"
DB = BACKEND / "eval.db"

GIT_AUTHOR = ["-c", "user.name=BuildPulse Eval", "-c", "user.email=buildpulse-eval@local"]


def run(args, cwd=None, capture=True):
    return subprocess.run(args, cwd=cwd, capture_output=capture, text=True, shell=False, check=False)


def build_history() -> dict[str, str]:
    """Replay each release snapshot into the work tree as one commit (v1..v5).
    Returns {tag: commit sha}."""
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
    report = ROOT / "build" / f"cpp-{tag}.json"
    collect = run(
        [sys.executable, "-m", "buildpulse.cli", "collect", "--repo", str(WORK), "--out", str(report)]
    )
    if collect.returncode != 0:
        print(collect.stdout + collect.stderr)
        raise SystemExit(f"collect failed for {tag}")
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
    print(f"  {tag:>3}: " + (upload.stdout + upload.stderr).strip())
    if upload.returncode != 0:
        raise SystemExit(f"upload failed for {tag}")


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
            project_id = json.loads(resp.read().decode("utf-8"))["id"]
        print(f"project: {project_id}")

        commits = build_history()
        for tag, sha in commits.items():
            collect_and_upload(project_id, tag, sha)

        print("\nbuild numbers:")
        with sqlite3.connect(DB) as con:
            rows = con.execute(
                "select b.build_number, b.commit_hash, h.overall_score, h.grade, b.status "
                "from builds b join health_scores h on h.build_id=b.id order by b.build_number"
            ).fetchall()
        for row in rows:
            print("  build", row[0], "score", f"{row[2]:.1f}", "grade", row[3], row[4], (row[1] or "n/a")[:8])
    finally:
        server.terminate()
        server.wait(timeout=10)
        shutil.rmtree(EVAL_ROOT, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())