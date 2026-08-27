# AnalyticEngine Java

Sample Java project used to exercise BuildPulse's Java pipeline end-to-end:
config-driven via `buildpulse.toml` (`language = java`, `test_format = auto`),
built with plain `javac` + `jar`, tested with the JUnit 5 console standalone
launcher (see `../../tools/junit`).

The release history is stored as **snapshots** under `releases/v1..v3`. Each
release intentionally degrades software metrics so the dashboard shows real,
human-interpretable regressions:

| release | work units | javac warnings | tests | defect |
|---------|-----------|----------------|-------|--------|
| v1      | 1x        | 0              | 8/8   | none (baseline) |
| v2      | 2x        | 1              | 7/8   | `maxTracksValue` search-horizon regression (flaky: passes again in v3) |
| v3      | 4x        | 3              | 7/8   | bloom hash-truncation + membership blotch |

How a release works:

- `version.txt` selects the behaviour (`run-tests.bat` passes `-Davlog.version`).
- `build.bat` compiles with `javac -Xlint:all` and packs `build/analytic-engine.jar`.
- `run-tests.bat` compiles the JUnit tests and runs them through the console
  launcher, writing surefire-style XML into `build/test-results/`.
- `run-benchmarks.bat` prints `BENCHMARK <name> mean median stddev cpu throughput iters`
  lines that the collector's benchmark analyzer parses.

Ingest the whole release history into a live backend with:

```
python scripts\eval_sample_java.py
```

The eval script stages each snapshot into `build/eval/` (where the JUnit jar is
also mirrored, keeping the `..\..\tools\junit` reference in `run-tests.bat` valid)
and uploads the resulting reports.