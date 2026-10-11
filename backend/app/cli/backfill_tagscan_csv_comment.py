# Fills TagScan's "CSV Comment" (csv_comment_cell) for files, lines and tags
# that were scanned before that field existed, by re-reading the archived
# CSVs in "Read Tags" — see app/modules/module_1/csv_comment_backfill.py.
#
# Run it once per environment after the migration, from the "backend" folder:
#   python -m app.cli.backfill_tagscan_csv_comment
# On the server:
#   docker compose -f docker-compose.prod.yml exec -T backend python -m app.cli.backfill_tagscan_csv_comment
#
# Safe to run more than once.

from app.core.database import SessionLocal
from app.modules.module_1.csv_comment_backfill import backfill_csv_comment_cells


def main() -> None:
    """Run the backfill in one transaction and print what it did."""
    with SessionLocal() as db:
        result = backfill_csv_comment_cells(db)
        db.commit()

    print(f"Files re-read: {result.files_read}")
    print(f"Lines filled:  {result.lines_filled}")
    print(f"Tags filled:   {result.tags_filled}")
    # Files whose archived CSV is gone keep an empty "CSV Comment".
    if result.missing_files:
        print(f"Archived CSV not found ({len(result.missing_files)}):")
        for filename in result.missing_files:
            print(f"  {filename}")


if __name__ == "__main__":
    main()
