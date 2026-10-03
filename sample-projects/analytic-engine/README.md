# analytic-engine

Demo C++ project used to evaluate the CODEFORGE pipeline. The release history
is stored as **snapshots** under `releases/v1..v5`. Each release intentionally
degrades software metrics so the dashboard shows real, human-interpretable
regressions:

| Version | Warnings | Max cyclomatic | Tests failing | Work units |
|---------|----------|----------------|---------------|------------|
| v1      | 0        | 5              | 0             | 1x         |
| v2      | 1        | 5              | 0             | 2x         |
| v3      | 3        | 10             | 1 (flaky)     | 4x         |
| v4      | 4        | 10             | 1             | 7x         |
| v5      | 5        | 12             | 3 (flaky)     | 12x        |

Workload growth is compiled in (`kWorkUnits`), so throughput regressions are
real, measured timings of more per-iteration work.

- `build.bat` compiles with `g++ -O2 -Wall` and reports the real warning count.
- `pulse.exe --selftest` prints ctest-style test lines (real pass/fail logic).
- `pulse.exe --bench` times real workloads with `std::chrono`.

Ingest the whole release history into a live backend with:

```
python scripts\eval_sample.py
```

The eval script stages each snapshot under `build/eval/` and runs the collector
against it. Note: the snapshots carry no git metadata, so the collector's git
analyzer reports `skipped` and `commit_hash` stays null; build numbers and the
health trend come from the backend.