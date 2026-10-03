# AnalyticEngine Java

Sample Java project used to exercise CODEFORGE's Java pipeline end-to-end:
config-driven via `codeforge.toml` (`language = java`, `test_format = auto`),
built with plain `javac` + `jar`, tested with the JUnit 5 console standalone
launcher (see `codeforge/tools/junit`).

Three release commits tell the degradation story:

| release | work units | javac warnings | tests   | defect                                |
|---------|-----------|----------------|---------|---------------------------------------|
| v1      | 1x        | 0              | 8/8     | none (baseline)                       |
| v2      | 2x        | 1              | 7/8     | `maxTracksValue` search horizon       |
| v3      | 4x        | 3              | 6/8     | hor. regression? + bloom mask + membership |

- `version.txt` selects the behaviour (read by `run-tests.bat` via `-Davlog.version`).
- `build.bat` compiles with `javac -Xlint:all` and packs `build/analytic-engine.jar`.
- `run-tests.bat` compiles the JUnit tests and runs them through the console
  launcher, writing surefire-style XML into `build/test-results/`.
- `run-benchmarks.bat` prints `BENCHMARK <name> mean median stddev cpu throughput iters` lines.