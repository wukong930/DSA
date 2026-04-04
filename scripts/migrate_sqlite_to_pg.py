#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite → PostgreSQL one-shot migration script.

Usage:
    python scripts/migrate_sqlite_to_pg.py \
        --sqlite ./data/stock_analysis.db \
        --pg postgresql://dsa_user:password@localhost:5432/dsa

This reads all rows from the SQLite database via the existing ORM models
and bulk-inserts them into PostgreSQL. Safe to re-run: it skips tables
that already contain data in the target database.
"""

import argparse
import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.storage import Base  # noqa: E402 — imports all ORM models

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def migrate(sqlite_url: str, pg_url: str, *, force: bool = False) -> None:
    src_engine = create_engine(sqlite_url)
    dst_engine = create_engine(pg_url, pool_size=5, max_overflow=5)

    # Create all tables in PostgreSQL
    Base.metadata.create_all(dst_engine)
    logger.info("PostgreSQL schema created / verified.")

    SrcSession = sessionmaker(bind=src_engine)
    DstSession = sessionmaker(bind=dst_engine)

    src_inspector = inspect(src_engine)
    src_tables = set(src_inspector.get_table_names())

    for table in Base.metadata.sorted_tables:
        table_name = table.name
        if table_name not in src_tables:
            logger.info("  [skip] %s — not in SQLite", table_name)
            continue

        with DstSession() as dst_session:
            if not force:
                existing = dst_session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                ).scalar()
                if existing > 0:
                    logger.info("  [skip] %s — already has %d rows in PostgreSQL", table_name, existing)
                    continue

        # Read all rows from SQLite as dicts
        with SrcSession() as src_session:
            rows = src_session.execute(table.select()).fetchall()
            if not rows:
                logger.info("  [skip] %s — empty in SQLite", table_name)
                continue

        columns = [c.name for c in table.columns]

        # Bulk insert into PostgreSQL in batches
        batch_size = 500
        with DstSession() as dst_session:
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                dst_session.execute(
                    table.insert(),
                    [dict(zip(columns, row)) for row in batch],
                )
            dst_session.commit()

        logger.info("  [done] %s — migrated %d rows", table_name, len(rows))

    # Reset PostgreSQL sequences for auto-increment columns
    with dst_engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            for col in table.columns:
                if col.autoincrement and col.primary_key:
                    seq_name = f"{table.name}_{col.name}_seq"
                    try:
                        conn.execute(text(
                            f"SELECT setval('{seq_name}', COALESCE((SELECT MAX({col.name}) FROM {table.name}), 0) + 1, false)"
                        ))
                    except Exception:
                        pass  # sequence may not exist for this table
        conn.commit()

    logger.info("Migration complete.")


def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite to PostgreSQL")
    parser.add_argument("--sqlite", required=True, help="SQLite file path, e.g. ./data/stock_analysis.db")
    parser.add_argument("--pg", required=True, help="PostgreSQL URL, e.g. postgresql://user:pass@localhost:5432/dsa")
    parser.add_argument("--force", action="store_true", help="Overwrite existing data in target tables")
    args = parser.parse_args()

    sqlite_url = f"sqlite:///{Path(args.sqlite).absolute()}"
    migrate(sqlite_url, args.pg, force=args.force)


if __name__ == "__main__":
    main()
