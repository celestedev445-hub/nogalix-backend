"""Exporte la base MySQL locale vers nogalix.sql à la racine du backend."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import pymysql
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def format_value(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, bytes):
        return "X'" + value.hex() + "'"
    text = str(value).replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n").replace("\r", "\\r")
    return f"'{text}'"


def main() -> None:
    database = os.getenv("DB_DATABASE", "nogalix")
    output = ROOT / "nogalix.sql"

    connection = pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USERNAME", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=database,
        charset="utf8mb4",
    )

    try:
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]

        with output.open("w", encoding="utf-8") as handle:
            handle.write("-- Nogalix database dump\n")
            handle.write(f"-- Generated: {datetime.now(timezone.utc).isoformat()}\n")
            handle.write(f"-- Database: {database}\n\n")
            handle.write("SET NAMES utf8mb4;\n")
            handle.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

            for table in tables:
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                create_sql = cursor.fetchone()[1]
                handle.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                handle.write(f"{create_sql};\n\n")

                cursor.execute(f"SELECT * FROM `{table}`")
                rows = cursor.fetchall()
                if not rows:
                    continue

                cursor.execute(f"DESCRIBE `{table}`")
                columns = [row[0] for row in cursor.fetchall()]
                column_list = ", ".join(f"`{column}`" for column in columns)

                for row in rows:
                    values = ", ".join(format_value(value) for value in row)
                    handle.write(f"INSERT INTO `{table}` ({column_list}) VALUES ({values});\n")
                handle.write("\n")

            handle.write("SET FOREIGN_KEY_CHECKS=1;\n")
    finally:
        connection.close()

    print(f"Dump écrit : {output}")
    print(f"Tables : {len(tables)}")
    print(f"Taille : {output.stat().st_size} octets")


if __name__ == "__main__":
    main()
