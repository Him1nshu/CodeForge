# analytic-engine

Demo project used to evaluate the CODEFORGE pipeline. One git history, five
releases. Each release intentionally degrades software metrics so the dashboard
shows real, human-interpretable regressions:

| Version | Warnings | Complex fn. count | Tests failing | Benchmark trend |
|---------|----------|-------------------|---------------|-----------------|
| v1      | 0        | 0                 | 0             | baseline        |
| v2      | +1       | 0                 | 0             | ~2x work        |
| v3      | +2       | 1                 | 1 (flaky)     | ~4x work        |
| v4      | +3       | 2                 | 2             | ~7x work        |
| v5      | +4       | 3                 | 3 (flaky)     | ~12x work       |

Workload growth is compiled in (`kWorkUnits`), so throughput regressions are
real, measured timings of more per-iteration work.

- `build.bat` compiles with `g++ -O2 -Wall` and reports the real warning count.
- `pulse.exe --selftest` prints ctest-style test lines (real pass/fail logic).
- `pulse.exe --bench` times real workloads with `std::chrono`.

Build with: `codeforge collect` at this directory (see `codeforge.toml`).