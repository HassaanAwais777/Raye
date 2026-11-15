"""Alembic migrations environment for AudienceLens (Neon PostgreSQL).

Migrations use DIRECT_URL when available (Neon recommends the direct,
non-pooled connection for schema changes), falling back to DATABASE_URL.
Both are read from environment variables — never hardcoded.

Run:
  alembic upgrade head                 # apply migrations (needs DIRECT_URL/DATABASE_URL)
  alembic revision --autogenerate -m "..."   # generate a new migration
  alembic upgrade head --sql           # emit SQL without a connection (for review)
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import the models metadata so autogenerate can see all tables.
from backend.db.models import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Resolve the migration URL: DIRECT_URL (preferred for migrations) > DATABASE_URL.
migration_url = os.getenv("DIRECT_URL") or os.getenv("DATABASE_URL") or ""
if migration_url:
    config.set_main_option("sqlalchemy.url", migration_url)


def run_migrations_offline() -> None:
    """Render SQL to stdout without a DB connection (for review/CI)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
