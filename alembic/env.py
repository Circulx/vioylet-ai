from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.core.config import get_settings
from app.db.base import Base
from app.models import *  # noqa: F403


config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.alembic_database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _repair_legacy_alembic_version_rows(connection) -> bool:
    if connection.dialect.name != "postgresql":
        return False
    exists = connection.execute(
        text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
    ).scalar()
    if not exists:
        return False
    rows = {
        str(row[0])
        for row in connection.execute(text("SELECT version_num FROM alembic_version")).fetchall()
    }
    if "0008" in rows and "0009_optional_pgvector_retrieval" in rows:
        connection.execute(text("DELETE FROM alembic_version WHERE version_num = '0008'"))
        return True
    if "0008" in rows:
        connection.execute(
            text(
                "UPDATE alembic_version "
                "SET version_num = '0008_brand_legal_cta_tables' "
                "WHERE version_num = '0008'"
            )
        )
        return True
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=settings.alembic_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        if _repair_legacy_alembic_version_rows(connection):
            connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
