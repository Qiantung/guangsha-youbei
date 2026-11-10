"""Export a reproducible SQLite starter and its schema, using synthetic data only."""
import argparse
from pathlib import Path

from .service import ROOT, Service


def main():
    parser = argparse.ArgumentParser(description="广厦有备本地数据库初始化")
    parser.add_argument("--output", type=Path, default=ROOT / "private/demo.sqlite3")
    parser.add_argument("--schema", type=Path)
    args = parser.parse_args()
    service = Service(args.output)
    if args.schema:
        args.schema.parent.mkdir(parents=True, exist_ok=True)
        with service.db() as db:
            statements = [r[0] + ";" for r in db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND sql IS NOT NULL ORDER BY name")]
        args.schema.write_text("-- 广厦有备 SQLite schema; initialize data with backend.database.\n" +
                               "\n\n".join(statements) + "\n", encoding="utf-8")
    print("SQLite initialized. Existing account history has been preserved.")


if __name__ == "__main__":
    main()
