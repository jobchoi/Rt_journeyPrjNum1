"""Back up and upgrade an existing local SQLite ledger, including unversioned MVPs."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from alembic import command
from alembic.config import Config


def upgrade(database: Path, backup_dir: Path):
    database = database.resolve()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    os.environ["DATABASE_URL"] = "sqlite:///" + str(database)
    config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    if not database.exists():
        database.parent.mkdir(parents=True, exist_ok=True)
        command.upgrade(config, "head")
        print("새 데이터베이스 생성 및 migration 완료")
        return
    with sqlite3.connect(database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        stamp = bool(tables) and "alembic_version" not in tables
        if stamp:
            # Never stamp an unknown schema. Verify every initial table and column first.
            with sqlite3.connect(":memory:") as reference:
                reference.executescript((ROOT / "database/migrations/0001_initial_auth_programs.sql").read_text())
                expected = {row[0] for row in reference.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not expected.issubset(tables):
                    raise RuntimeError("초기 스키마와 테이블이 달라 자동 업그레이드를 중단합니다.")
                for table in expected:
                    columns = {row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')}
                    original = {row[1] for row in reference.execute(f'PRAGMA table_info("{table}")')}
                    if columns != original:
                        raise RuntimeError(f"{table} 컬럼이 초기 스키마와 다릅니다. migration 상태를 확인하세요.")
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp_time = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = backup_dir / f"{database.stem}-{stamp_time}.db"
        with sqlite3.connect(backup) as destination:
            connection.backup(destination)
    print(f"DB 백업: {backup}")
    if stamp:
        command.stamp(config, "0001_initial_schema")
    command.upgrade(config, "head")
    print("입출금 원장 migration 완료")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=ROOT / "database/rt.db")
    parser.add_argument("--backup-dir", type=Path, default=ROOT / "storage/backups")
    args = parser.parse_args()
    upgrade(args.database, args.backup_dir)
