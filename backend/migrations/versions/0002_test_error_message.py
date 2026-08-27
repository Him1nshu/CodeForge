"""Capture per-test failure messages from JUnit XML.

Revision ID: 0002_test_error_message
Revises: 0001_initial
Create Date: 2026-08-27
"""
import sqlalchemy as sa
from alembic import op

revision = "0002_test_error_message"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_results", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("test_results", "error_message")