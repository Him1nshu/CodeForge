"""BuildPulse initial schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-27
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_name", sa.String(length=200), nullable=False),
        sa.Column("repository_url", sa.String(length=500), nullable=True),
        sa.Column("branch", sa.String(length=200), nullable=False, server_default="main"),
        sa.Column("build_command", sa.String(length=500), nullable=True),
        sa.Column("test_command", sa.String(length=500), nullable=True),
        sa.Column("benchmark_command", sa.String(length=500), nullable=True),
        sa.Column("binary_path", sa.String(length=500), nullable=True),
        sa.Column("analysis_tools", JSON, nullable=False),
        sa.Column("health_config", JSON, nullable=False),
        sa.Column("api_key_hash", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_name"),
    )
    op.create_index("ix_projects_project_name", "projects", ["project_name"])

    op.create_table(
        "builds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("build_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("commit_hash", sa.String(length=64), nullable=True),
        sa.Column("branch", sa.String(length=200), nullable=True),
        sa.Column("commit_message", sa.Text(), nullable=True),
        sa.Column("commit_author", sa.String(length=200), nullable=True),
        sa.Column("commit_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_files", sa.Integer(), nullable=True),
        sa.Column("lines_added", sa.Integer(), nullable=True),
        sa.Column("lines_removed", sa.Integer(), nullable=True),
        sa.Column("compiler_warnings", sa.Integer(), nullable=False),
        sa.Column("compiler_errors", sa.Integer(), nullable=False),
        sa.Column("build_retries", sa.Integer(), nullable=False),
        sa.Column("collector_run_id", sa.String(length=100), nullable=True),
        sa.Column("environment", JSON, nullable=False),
        sa.Column("raw_report", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_builds_project_number", "builds", ["project_id", "build_number"])
    op.create_index("ix_builds_project_commit", "builds", ["project_id", "commit_hash"])
    op.create_index("ix_builds_project_created", "builds", ["project_id", "created_at"])
    op.create_index("ix_builds_project_collector_run", "builds", ["project_id", "collector_run_id"])

    op.create_table(
        "build_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("binary_size", sa.BigInteger(), nullable=True),
        sa.Column("binary_size_change", sa.BigInteger(), nullable=True),
        sa.Column("pct_binary_growth", sa.Float(), nullable=True),
        sa.Column("artifact_count", sa.Integer(), nullable=True),
        sa.Column("artifact_paths", JSON, nullable=False),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("build_id"),
    )

    op.create_table(
        "code_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("lines_of_code", sa.Integer(), nullable=True),
        sa.Column("functions", sa.Integer(), nullable=True),
        sa.Column("cyclomatic_complexity_total", sa.Integer(), nullable=True),
        sa.Column("avg_function_complexity", sa.Float(), nullable=True),
        sa.Column("max_function_complexity", sa.Integer(), nullable=True),
        sa.Column("functions_above_threshold", sa.Integer(), nullable=True),
        sa.Column("complexity_threshold", sa.Integer(), nullable=False),
        sa.Column("maintainability_index", sa.Float(), nullable=True),
        sa.Column("avg_function_length", sa.Float(), nullable=True),
        sa.Column("top_complex_functions", JSON, nullable=False),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("build_id"),
    )

    op.create_table(
        "static_analysis_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("tool", sa.String(length=100), nullable=False),
        sa.Column("file", sa.Text(), nullable=False),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("rule", sa.String(length=200), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("build_id", "tool", "file", "line", "rule", name="uq_issue_dedupe"),
    )
    op.create_index("ix_static_analysis_issues_build_id", "static_analysis_issues", ["build_id"])

    op.create_table(
        "test_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("suite", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("build_id", "suite", "name", name="uq_test_dedupe"),
    )
    op.create_index("ix_test_results_build_id", "test_results", ["build_id"])

    op.create_table(
        "benchmarks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("mean_ms", sa.Float(), nullable=True),
        sa.Column("median_ms", sa.Float(), nullable=True),
        sa.Column("stddev_ms", sa.Float(), nullable=True),
        sa.Column("cpu_ms", sa.Float(), nullable=True),
        sa.Column("throughput", sa.Float(), nullable=True),
        sa.Column("iterations", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("build_id", "name", name="uq_benchmark_dedupe"),
    )
    op.create_index("ix_benchmarks_build_id", "benchmarks", ["build_id"])

    op.create_table(
        "dependencies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("change", sa.String(length=20), nullable=False),
        sa.Column("previous_version", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("build_id", "name", name="uq_dependency_dedupe"),
    )
    op.create_index("ix_dependencies_build_id", "dependencies", ["build_id"])

    op.create_table(
        "architecture_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("drift_score", sa.Float(), nullable=False),
        sa.Column("layer_violations", sa.Integer(), nullable=False),
        sa.Column("cyclic_dependencies", sa.Integer(), nullable=False),
        sa.Column("unexpected_coupling", sa.Integer(), nullable=False),
        sa.Column("direction_violations", sa.Integer(), nullable=False),
        sa.Column("module_count", sa.Integer(), nullable=False),
        sa.Column("edge_count", sa.Integer(), nullable=False),
        sa.Column("dependency_graph", JSON, nullable=False),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("build_id"),
    )

    op.create_table(
        "architecture_violations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("violation_type", sa.String(length=40), nullable=False),
        sa.Column("source_module", sa.String(length=200), nullable=False),
        sa.Column("target_module", sa.String(length=200), nullable=False),
        sa.Column("source_layer", sa.String(length=100), nullable=True),
        sa.Column("target_layer", sa.String(length=100), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("approval", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_architecture_violations_build_id", "architecture_violations", ["build_id"])

    op.create_table(
        "health_scores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("build_health", sa.Float(), nullable=False),
        sa.Column("code_quality", sa.Float(), nullable=False),
        sa.Column("testing", sa.Float(), nullable=False),
        sa.Column("performance", sa.Float(), nullable=False),
        sa.Column("maintainability", sa.Float(), nullable=False),
        sa.Column("architecture", sa.Float(), nullable=False),
        sa.Column("grade", sa.String(length=20), nullable=False),
        sa.Column("formula_version", sa.String(length=10), nullable=False),
        sa.Column("weights", JSON, nullable=False),
        sa.Column("evidence", JSON, nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("build_id", name="uq_health_score_build"),
        sa.UniqueConstraint("project_id", "build_id", name="uq_health_project_build"),
    )
    op.create_index("ix_health_scores_project_id", "health_scores", ["project_id"])

    op.create_table(
        "engineering_insights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("build_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("evidence", JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["build_id"], ["builds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_engineering_insights_project_id", "engineering_insights", ["project_id"])


def downgrade() -> None:
    op.drop_table("engineering_insights")
    op.drop_table("health_scores")
    op.drop_table("architecture_violations")
    op.drop_table("architecture_metrics")
    op.drop_table("dependencies")
    op.drop_table("benchmarks")
    op.drop_table("test_results")
    op.drop_table("static_analysis_issues")
    op.drop_table("code_metrics")
    op.drop_table("build_metrics")
    op.drop_table("builds")
    op.drop_table("projects")