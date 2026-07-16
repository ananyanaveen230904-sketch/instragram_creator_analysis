"""
Database Setup Script

Loads the project's CSV outputs into a local SQLite database
(output/analytics.db), one table per CSV, so they can be queried with SQL
by the natural-language Q&A layer (query_engine.py).

Idempotent: running this again drops and recreates each table, so it never
errors out or duplicates data on repeated runs.
"""

import os
import sqlite3
import logging
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
DB_PATH = os.path.join(OUTPUT_DIR, "analytics.db")

# Maps CSV file -> SQLite table name. Table names mirror the CSV filenames
# (minus .csv) so they're intuitive when referenced in generated SQL.
CSV_TABLE_MAP = {
    "posts.csv": "posts",
    "creators.csv": "creators",
    "comparison_results.csv": "comparison_results",
    "creators_with_sentiment_eqs.csv": "creators_with_sentiment_eqs",
}


def load_csv_to_table(conn: sqlite3.Connection, csv_path: str, table_name: str) -> int:
    """
    Load a single CSV into a SQLite table, dropping any existing table with
    the same name first (idempotent refresh, not append).

    Args:
        conn: Open sqlite3 connection
        csv_path: Path to the CSV file
        table_name: Name of the table to create

    Returns:
        int: Number of rows loaded (0 if the CSV was missing/empty)
    """
    if not os.path.isfile(csv_path):
        logger.warning(f"Skipping '{table_name}': file not found at {csv_path}")
        return 0

    df = pd.read_csv(csv_path, encoding='utf-8')

    # Drop and recreate the table each run (idempotent, no duplication)
    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    df.to_sql(table_name, conn, if_exists='replace', index=False)

    return len(df)


def print_table_schema(conn: sqlite3.Connection, table_name: str) -> None:
    """Print table name, columns (with types), and row count for verification."""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()  # (cid, name, type, notnull, dflt_value, pk)

    row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

    print(f"\nTable: {table_name}  ({row_count} rows)")
    print("-" * 50)
    for col in columns:
        print(f"  {col[1]:<30} {col[2]}")


def setup_database(output_dir: str = OUTPUT_DIR, db_path: str = DB_PATH) -> None:
    """
    Load all known CSVs into output/analytics.db, one table per CSV.
    Prints schema + row count for each created table.
    """
    os.makedirs(output_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        print("=" * 60)
        print("DATABASE SETUP: Loading CSVs into SQLite")
        print("=" * 60)

        any_loaded = False
        for csv_filename, table_name in CSV_TABLE_MAP.items():
            csv_path = os.path.join(output_dir, csv_filename)
            row_count = load_csv_to_table(conn, csv_path, table_name)

            if row_count > 0:
                any_loaded = True
                logger.info(f"Loaded '{csv_filename}' -> table '{table_name}' ({row_count} rows)")
                print_table_schema(conn, table_name)
            else:
                logger.warning(f"Table '{table_name}' not created (missing or empty CSV)")

        conn.commit()

        if not any_loaded:
            logger.error("No tables were created. Check that CSVs exist in the output/ folder.")
        else:
            logger.info(f"Database ready at {db_path}")

        print("\n" + "=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    setup_database()
