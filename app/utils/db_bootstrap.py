from sqlalchemy import inspect, text

from app.extensions import db


def run_schema_upgrades():
    inspector = inspect(db.engine)

    if "social_accounts" in inspector.get_table_names():
        _ensure_columns(
            "social_accounts",
            {
                "username": "ALTER TABLE social_accounts ADD COLUMN username VARCHAR(120)",
                "page_id": "ALTER TABLE social_accounts ADD COLUMN page_id VARCHAR(120)",
                "meta_scopes": "ALTER TABLE social_accounts ADD COLUMN meta_scopes TEXT",
                "raw_metadata_json": "ALTER TABLE social_accounts ADD COLUMN raw_metadata_json TEXT",
                "last_error": "ALTER TABLE social_accounts ADD COLUMN last_error TEXT",
            },
        )

    if "users" in inspector.get_table_names():
        _ensure_columns(
            "users",
            {
                "is_premium": "ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT 0",
                "premium_activated_at": "ALTER TABLE users ADD COLUMN premium_activated_at DATETIME",
                "premium_source": "ALTER TABLE users ADD COLUMN premium_source VARCHAR(50)",
            },
        )
        db.session.execute(
            text(
                "UPDATE users SET plan = 'free' WHERE plan IS NULL OR plan = ''"
            )
        )
        db.session.execute(
            text(
                "UPDATE users SET is_premium = 1, premium_source = COALESCE(premium_source, 'legacy') "
                "WHERE plan = 'lifetime' AND (is_premium IS NULL OR is_premium = 0)"
            )
        )
        db.session.commit()

    if "generated_videos" in inspector.get_table_names():
        _ensure_columns(
            "generated_videos",
            {
                "file_url": "ALTER TABLE generated_videos ADD COLUMN file_url VARCHAR(500)",
                "thumbnail_url": "ALTER TABLE generated_videos ADD COLUMN thumbnail_url VARCHAR(500)",
                "storage_provider": "ALTER TABLE generated_videos ADD COLUMN storage_provider VARCHAR(30) DEFAULT 'local'",
                "processing_started_at": "ALTER TABLE generated_videos ADD COLUMN processing_started_at DATETIME",
                "completed_at": "ALTER TABLE generated_videos ADD COLUMN completed_at DATETIME",
            },
        )
        db.session.commit()


def _ensure_columns(table_name, ddl_by_column):
    inspector = inspect(db.engine)
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    for column_name, ddl in ddl_by_column.items():
        if column_name not in existing_columns:
            db.session.execute(text(ddl))
    db.session.commit()
