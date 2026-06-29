"""Add materialized token usage columns.

Revision ID: 0011_content_token_columns
Revises: 0010_merge_0009_heads
Create Date: 2026-06-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_content_token_columns"
down_revision = "0010_merge_0009_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE content_history ADD COLUMN IF NOT EXISTS token_input_tokens BIGINT NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE content_history ADD COLUMN IF NOT EXISTS token_output_tokens BIGINT NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE content_history ADD COLUMN IF NOT EXISTS token_total_tokens BIGINT NOT NULL DEFAULT 0")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_content_history_tenant_brand_created_at"
        " ON content_history (tenant_id, brand_space_id, created_at)"
    )

    op.execute(
        """
        UPDATE content_history
        SET
            token_input_tokens = CASE
                WHEN explainability_metadata->'token_usage'->>'input_tokens' ~ '^[0-9]+$'
                    THEN (explainability_metadata->'token_usage'->>'input_tokens')::bigint
                WHEN explainability_metadata->'token_usage'->>'prompt_tokens' ~ '^[0-9]+$'
                    THEN (explainability_metadata->'token_usage'->>'prompt_tokens')::bigint
                ELSE 0
            END,
            token_output_tokens = CASE
                WHEN explainability_metadata->'token_usage'->>'output_tokens' ~ '^[0-9]+$'
                    THEN (explainability_metadata->'token_usage'->>'output_tokens')::bigint
                WHEN explainability_metadata->'token_usage'->>'completion_tokens' ~ '^[0-9]+$'
                    THEN (explainability_metadata->'token_usage'->>'completion_tokens')::bigint
                ELSE 0
            END,
            token_total_tokens = CASE
                WHEN explainability_metadata->'token_usage'->>'total_tokens' ~ '^[0-9]+$'
                    THEN (explainability_metadata->'token_usage'->>'total_tokens')::bigint
                ELSE
                    (
                        CASE
                            WHEN explainability_metadata->'token_usage'->>'input_tokens' ~ '^[0-9]+$'
                                THEN (explainability_metadata->'token_usage'->>'input_tokens')::bigint
                            WHEN explainability_metadata->'token_usage'->>'prompt_tokens' ~ '^[0-9]+$'
                                THEN (explainability_metadata->'token_usage'->>'prompt_tokens')::bigint
                            ELSE 0
                        END
                        +
                        CASE
                            WHEN explainability_metadata->'token_usage'->>'output_tokens' ~ '^[0-9]+$'
                                THEN (explainability_metadata->'token_usage'->>'output_tokens')::bigint
                            WHEN explainability_metadata->'token_usage'->>'completion_tokens' ~ '^[0-9]+$'
                                THEN (explainability_metadata->'token_usage'->>'completion_tokens')::bigint
                            ELSE 0
                        END
                    )
            END
        WHERE explainability_metadata ? 'token_usage'
        """
    )


def downgrade() -> None:
    op.drop_index("ix_content_history_tenant_brand_created_at", table_name="content_history")
    op.drop_column("content_history", "token_total_tokens")
    op.drop_column("content_history", "token_output_tokens")
    op.drop_column("content_history", "token_input_tokens")
