"""Add campaign execution tracking and metrics logging tables.

Revision ID: 0012_campaign_pipeline_tracking
Revises: 0011_content_token_columns
Create Date: 2026-06-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_campaign_pipeline_tracking"
down_revision = "0011_content_token_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create campaigns table
    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_space_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("format", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_campaigns_tenant"),
        sa.ForeignKeyConstraint(["brand_space_id"], ["brand_spaces.id"], name="fk_campaigns_brand_space"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_campaigns_user"),
    )
    op.create_index("ix_campaigns_tenant_id", "campaigns", ["tenant_id"])
    op.create_index("ix_campaigns_brand_space_id", "campaigns", ["brand_space_id"])
    op.create_index("ix_campaigns_user_id", "campaigns", ["user_id"])

    # Create pipeline_runs table
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("layer_reached", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column("total_cost_usd", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], name="fk_pipeline_runs_campaign"),
    )
    op.create_index("ix_pipeline_runs_campaign_id", "pipeline_runs", ["campaign_id"])
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])

    # Create layer_outputs table
    op.create_table(
        "layer_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("layer_name", sa.String(), nullable=False),
        sa.Column("output_json", postgresql.JSONB(), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("model_used", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], name="fk_layer_outputs_run"),
    )
    op.create_index("ix_layer_outputs_run_id", "layer_outputs", ["run_id"])
    op.create_index("ix_layer_outputs_layer_name", "layer_outputs", ["layer_name"])

    # Create evaluation_results table
    op.create_table(
        "evaluation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brand_alignment_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("prompt_match_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("originality_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("repair_instructions", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["pipeline_runs.id"], name="fk_evaluation_results_run"),
    )
    op.create_index("ix_evaluation_results_run_id", "evaluation_results", ["run_id"])
    op.create_index("ix_evaluation_results_passed", "evaluation_results", ["passed"])


def downgrade() -> None:
    op.drop_index("ix_evaluation_results_passed", table_name="evaluation_results")
    op.drop_index("ix_evaluation_results_run_id", table_name="evaluation_results")
    op.drop_table("evaluation_results")

    op.drop_index("ix_layer_outputs_layer_name", table_name="layer_outputs")
    op.drop_index("ix_layer_outputs_run_id", table_name="layer_outputs")
    op.drop_table("layer_outputs")

    op.drop_index("ix_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_campaign_id", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")

    op.drop_index("ix_campaigns_user_id", table_name="campaigns")
    op.drop_index("ix_campaigns_brand_space_id", table_name="campaigns")
    op.drop_index("ix_campaigns_tenant_id", table_name="campaigns")
    op.drop_table("campaigns")
