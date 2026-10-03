"""codeforge.toml loading (standard library tomllib)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "project": {
        "name": "SampleCppProject",
        "language": "cpp",
        "test_format": "auto",
        "repository_url": "",
        "branch": "main",
        "build_command": "cmake -S . -B build && cmake --build build -j",
        "test_command": "ctest --test-dir build --output-on-failure",
        "benchmark_command": "./build/bin/benchmarks",
        "binary_path": "build/bin/sample_app",
        "build_dir": "build",
    },
    "analyzers": {
        "complexity": {"tool": "auto", "complexity_threshold": 15},
        "static_analysis": {"tool": "auto", "checks": []},
        "architecture": {
            "layers": {
                "presentation": ["src/presentation"],
                "application": ["src/application"],
                "domain": ["src/domain"],
                "infrastructure": ["src/infrastructure"],
            }
        },
    },
}


class ConfigError(Exception):
    pass


def load_config(path: Path | None) -> dict[str, Any]:
    import json
    import tomllib

    cfg: dict[str, Any] = json.loads(json.dumps(DEFAULTS))
    if path and path.exists():
        data = path.read_bytes()
        if data.startswith(b"\xef\xbb\xbf"):
            data = data[3:]
        try:
            raw = tomllib.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f"could not parse {path}: {exc}") from exc
        _deep_merge(cfg, raw)
    return cfg


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value