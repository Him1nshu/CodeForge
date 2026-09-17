# analytic-engine

Demo project used to evaluate the CODEFORGE pipeline. One git history, five
releases. Each release intentionally degrades software metrics so the dashboard
shows real, human-interpretable regressions:

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

Build with: `codeforge collect` at this directory (see `codeforge.toml`).