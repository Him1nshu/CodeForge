"""Java-mode analyzer tests: build output, JUnit XML, complexity, arch, deps."""

from __future__ import annotations

import json
from pathlib import Path

from buildpulse.analyzers import architecture, complexity, dependencies
from buildpulse.analyzers import build as build_analyzer
from buildpulse.analyzers import tests as tests_analyzer
from buildpulse.analyzers.base import AnalyzerContext

JAVA_LAYERS = {
    "presentation": ["src/main/java/avlog/presentation"],
    "application": ["src/main/java/avlog/application"],
    "domain": ["src/main/java/avlog/domain"],
    "infrastructure": ["src/main/java/avlog/infrastructure"],
}

JAVA_CONFIG = {
    "project": {"language": "java", "test_format": "junit", "benchmark_command": "", "build_command": "build.bat", "test_command": "run-tests.bat"},
    "analyzers": {"complexity": {"tool": "auto", "complexity_threshold": 15}, "architecture": {"layers": JAVA_LAYERS}},
}


def _write_tree(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _ctx(root: Path, config: dict | None = None) -> AnalyzerContext:
    return AnalyzerContext(
        repo_root=root,
        config=config or JAVA_CONFIG,
        report={
            "build": {
                "status": "UNKNOWN",
                "collector_run_id": "test-java",
                "environment": {"os": "test", "tool_versions": {}},
            },
            "metrics": {},
            "tests": [],
            "benchmarks": [],
            "static_analysis": [],
            "complexity": {},
            "dependencies": [],
            "architecture": {"module_count": 0, "edge_count": 0, "edges": [], "layer_mapping": {}},
        },
    )


def test_build_parses_javac_and_maven_output(tmp_path) -> None:
    _write_tree(
        tmp_path,
        {
            "build.bat": (
                "@echo off\n"
                "echo Main.java:7: error: cannot find symbol\n"
                "echo Main.java:9: error: incompatible types\n"
                "echo Main.java:12: warning: [unchecked] unchecked method invocation\n"
                "echo [ERROR] COMPILATION ERROR\n"
                "exit /b 1\n"
            )
        },
    )
    ctx = _ctx(tmp_path)
    result = build_analyzer.analyze_build(ctx)
    assert result.status == "ok"
    assert ctx.report["build"]["status"] == "FAILURE"
    assert ctx.report["build"]["compiler_warnings"] == 1
    assert ctx.report["build"]["compiler_errors"] == 3


def test_build_auto_detects_jar_binary(tmp_path) -> None:
    _write_tree(tmp_path, {"build.bat": "@echo off\nexit /b 0\n"})
    lib = tmp_path / "lib" / "junit-platform-console-standalone-1.11.4.jar"
    jar = tmp_path / "build" / "analytic-engine.jar"
    lib.parent.mkdir(parents=True, exist_ok=True)
    jar.parent.mkdir(parents=True, exist_ok=True)
    lib.write_bytes(b"x" * 10)
    jar.write_bytes(b"y" * 20)
    ctx = _ctx(tmp_path)
    config = ctx.config
    config["project"]["binary_path"] = ""
    result = build_analyzer.analyze_build(ctx)
    assert result.status == "ok"
    assert ctx.report["metrics"]["artifact_paths"] == ["build/analytic-engine.jar"]
    assert ctx.report["metrics"]["binary_size"] == 20


JUNIT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="avlog.HashStoreTest" tests="4" failures="1" errors="1" skipped="1" time="0.35">
  <testcase name="testPutGet" classname="avlog.HashStoreTest" time="0.01"/>
  <testcase name="testThrashPuts" classname="avlog.HashStoreTest" time="0.02">
    <failure message="expected &lt;true&gt; but was &lt;false&gt;" type="AssertionFailedError">java.lang.AssertionFailedError: expected &lt;true&gt; but was &lt;false&gt; at avlog.HashStoreTest.testThrashPuts</failure>
  </testcase>
  <testcase name="testDuplicateKeys" classname="avlog.HashStoreTest" time="0.03">
    <error message="IndexOutOfBoundsException: index 9" type="java.lang.IndexOutOfBoundsException">java.lang.IndexOutOfBoundsException: index 9</error>
  </testcase>
  <testcase name="testTooBig()" classname="avlog.HashStoreTest" time="0.0">
    <skipped/>
  </testcase>
</testsuite>
"""


def test_junit_xml_failures_spanish_messages_and_skips(tmp_path) -> None:
    _write_tree(tmp_path, {"run-tests.bat": "@echo off\nexit /b 0\n"})
    _write_tree(tmp_path, {"build/test-results/test/TEST-avlog.HashStoreTest.xml": JUNIT_XML})
    ctx = _ctx(tmp_path)
    result = tests_analyzer.analyze_tests(ctx)
    assert result.status == "ok"
    entries = ctx.report["tests"]
    by_name = {e["name"]: e for e in entries}
    assert by_name["avlog.HashStoreTest.testPutGet"]["status"] == "passed"
    # failure message preserved so the dashboard can tell the real cause
    assert "expected <true> but was <false>" in by_name["avlog.HashStoreTest.testThrashPuts"]["error"]
    assert by_name["avlog.HashStoreTest.testDuplicateKeys"]["status"] == "failed"
    assert by_name["avlog.HashStoreTest.testTooBig()"]["status"] == "skipped"
    assert len(entries) == 4


def test_junit_xml_dedupes_repeat_names(tmp_path) -> None:
    dup = JUNIT_XML.replace(
        '<testcase name="testThrashPuts" classname="avlog.HashStoreTest" time="0.02">',
        '<testcase name="testThrashPuts" classname="avlog.HashStoreTest" time="0.02">\n  <testcase name="testThrashPuts" classname="avlog.HashStoreTest" time="0.01"/>',
    )
    _write_tree(tmp_path, {"run-tests.bat": "@echo off\nexit /b 0\n", "build/test-results/test/TEST-avlog.HashStoreTest.xml": dup})
    ctx = _ctx(tmp_path)
    tests_analyzer.analyze_tests(ctx)
    names = [e["name"] for e in ctx.report["tests"]]
    assert len(names) == len(set(names))
    assert "avlog.HashStoreTest.testThrashPuts#2" in names


def test_junit_no_reports_note(tmp_path) -> None:
    _write_tree(tmp_path, {"run-tests.bat": "@echo off\nexit /b 0\n"})
    ctx = _ctx(tmp_path)
    result = tests_analyzer.analyze_tests(ctx)
    assert result.status == "ok"
    assert ctx.report["tests"] == []
    assert "no JUnit XML reports found" in result.request["note"]


JAVA_CODE = {
    "src/main/java/avlog/domain/Model.java": "package avlog.domain;\npublic final class Model { int value; }\n",
    "src/main/java/avlog/application/Svc.java": """
package avlog.application;
import avlog.domain.Model;
public class Svc {
  public int run(int a, int b) {
    int total = 0;
    for (int i = 0; i < b; ++i) { if (a % 2 == 0) total += i; }
    while (total > 100) { total -= 10; }
    return total;
  }
}
""",
    "src/main/java/avlog/presentation/Main.java": """
package avlog.presentation;
import avlog.application.Svc;
public final class Main {
  public static void main(String[] args) {
    Svc svc = new Svc();
    if (args.length == 0) { svc.run(1, 2); }
  }
}
""",
}


def test_java_complexity_counts_methods_not_guards(tmp_path) -> None:
    _write_tree(tmp_path, JAVA_CODE)
    ctx = _ctx(tmp_path)
    result = complexity.analyze_complexity(ctx)
    assert result.status == "ok"
    stats = ctx.report["complexity"]
    assert stats["functions"] >= 2  # main + Svc.run (+ implicit ctors)
    assert stats["max_function_complexity"] >= 3  # run() has for+while+if
    # control guards must not be mis-scored as functions
    names = [fn["function"] for fn in stats["top_complex_functions"]]
    assert "if" not in names and "for" not in names
    assert all(fn["file"] != "?" for fn in stats["top_complex_functions"])


def test_java_architecture_import_edges(tmp_path) -> None:
    _write_tree(tmp_path, JAVA_CODE)
    ctx = _ctx(tmp_path)
    result = architecture.analyze_architecture(ctx)
    assert result.status == "ok"
    edges = {(e["source"], e["target"]) for e in ctx.report["architecture"]["edges"]}
    assert ("presentation", "application") in edges
    assert ("application", "domain") in edges
    assert ("domain", "infrastructure") not in edges


def test_pom_dependencies_parsed_without_plugin_deps(tmp_path) -> None:
    pom = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <dependencies>
    <dependency><groupId>org.slf4j</groupId><artifactId>slf4j-api</artifactId><version>2.0.13</version></dependency>
    <dependency><groupId>com.google.guava</groupId><artifactId>guava</artifactId><version>33.0.0-jre</version></dependency>
  </dependencies>
  <build><plugins><plugin>
    <dependencies><dependency><groupId>org.apache.maven.plugins</groupId><artifactId>maven-compiler-plugin</artifactId></dependency></dependencies>
  </plugin></plugins></build>
</project>
"""
    _write_tree(tmp_path, {"pom.xml": pom})
    ctx = _ctx(tmp_path)
    result = dependencies.analyze_dependencies(ctx)
    assert result.status == "ok"
    by_name = {d["name"]: d for d in ctx.report["dependencies"]}
    assert by_name["org.slf4j:slf4j-api"]["version"] == "2.0.13"
    assert by_name["org.slf4j:slf4j-api"]["type"] == "maven"
    # plugin-scoped deps are build tooling, not app dependencies
    assert "org.apache.maven.plugins:maven-compiler-plugin" not in by_name


def test_gradle_dependencies_parsed(tmp_path) -> None:
    gradle = (
        "dependencies {\n"
        "  implementation \"com.google.guava:guava:33.0.0-jre\"\n"
        "  api 'org.slf4j:slf4j-api:2.0.13'\n"
        "  testImplementation 'org.junit.jupiter:junit-jupiter:5.11.4'\n"
        "}\n"
    )
    _write_tree(tmp_path, {"build.gradle": gradle})
    ctx = _ctx(tmp_path)
    result = dependencies.analyze_dependencies(ctx)
    assert result.status == "ok"
    by_name = {d["name"]: d for d in ctx.report["dependencies"]}
    assert by_name["org.junit.jupiter:junit-jupiter"]["version"] == "5.11.4"
    assert by_name["com.google.guava:guava"]["type"] == "gradle"


def test_java_report_is_uploadable_json(tmp_path) -> None:
    _write_tree(tmp_path, JAVA_CODE)
    ctx = _ctx(tmp_path)
    complexity.analyze_complexity(ctx)
    json.dumps(ctx.report)  # must not raise


def test_detect_format_java_defaults_to_junit(tmp_path) -> None:
    project = {"language": "java", "test_format": "auto", "test_command": "run-tests.bat"}
    assert tests_analyzer._detect_format(project, "run-tests.bat", tmp_path) == "junit"
    project["test_format"] = "ctest"
    assert tests_analyzer._detect_format(project, "run-tests.bat", tmp_path) == "ctest"


def test_detect_format_cpp_defaults_to_ctest_unless_manifest(tmp_path) -> None:
    project = {"language": "cpp", "test_format": "auto", "test_command": "run-tests.bat"}
    assert tests_analyzer._detect_format(project, "run-tests.bat", tmp_path) == "ctest"
    _write_tree(tmp_path, {"pom.xml": "<project/>"})
    assert tests_analyzer._detect_format(project, "run-tests.bat", tmp_path) == "junit"