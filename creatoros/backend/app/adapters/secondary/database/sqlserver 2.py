"""SQL Server adapter — ingest CreatorOS exports into dbo.prodmauploadvakodata.

Requires pyodbc plus an ODBC driver that matches `db_driver`. The adapter
probes the destination table's columns and maps CreatorOS record fields onto
them; ingest is idempotent (MERGE upsert keyed on the detected username
column) with a graceful INSERT fallback.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.core.ports.database import DatabasePort

_FIELD_CANDIDATES = {
    "user_name": ["user_name", "username", "insta_handle", "handle", "user__name"],
    "full_name": ["full_name", "name", "fullname", "creator_name", "display_name"],
    "email": ["email", "contact_email", "creator_email"],
    "followers_count": ["followers_count", "followers", "follower_count", "follower"],
    "following_count": ["following_count", "following"],
    "account_type": ["account_type", "accounttype", "type"],
    "gender": ["gender", "gender_pred"],
    "age_group": ["age_group", "age", "agegroup"],
    "city": ["city", "creator_city"],
    "country": ["country", "country_code", "creator_country"],
    "platform": ["platform"],
}


class SqlServerAdapter(DatabasePort):
    """Driven adapter: SQL Server (pyodbc) ingest target."""

    def __init__(self, server=None, database=None, user=None, password=None,
                 driver=None, table=None):
        self._server = server or settings.db_server
        self._database = database or settings.db_name
        self._user = user or settings.db_user
        self._password = password or settings.db_password
        self._driver = driver or settings.db_driver
        self._table = table or settings.db_table

    @property
    def name(self) -> str:
        return "sqlserver"

    def _connstr(self) -> str:
        return (
            f"DRIVER={{{self._driver}}};SERVER={self._server};"
            f"DATABASE={self._database};UID={self._user};PWD={self._password};"
            "TrustServerCertificate=yes"
        )

    def _connect(self):
        import pyodbc

        return pyodbc.connect(self._connstr(), timeout=10)

    def available(self) -> bool:
        if not (self._server and self._password):
            return False
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False

    def status(self) -> dict:
        return {
            "available": self.available(),
            "type": "sqlserver",
            "server": self._server,
            "database": self._database,
            "table": self._table,
            "driver": self._driver,
        }

    def _columns(self, conn) -> list[str]:
        rows = conn.execute(f"SELECT TOP 1 * FROM {self._table}").fetchall()
        if not rows:
            return []
        return [column[0] for column in conn.cursor().description]

    def ingest_from_keylist(self, keylist_path, on_event=None, table=None):
        if table:
            self._table = table
        if not (self._server and self._password):
            raise ValueError("SQL Server not configured (db_server / db_password)")
        path = Path(keylist_path)
        if not path.exists():
            raise FileNotFoundError(f"keylist not found: {path}")

        records = _load_records(path)
        if not records:
            raise ValueError("no extractable records in keylist")

        def emit(msg):
            if on_event:
                try:
                    on_event("log", msg)
                except Exception:
                    pass

        import pyodbc

        conn = self._connect()
        try:
            cursor = conn.cursor()
            columns = self._columns(conn)
            if not columns:
                raise RuntimeError(
                    f"could not read schema of {self._table} — verify the table exists"
                )

            mapping = _build_mapping(columns)
            insert_cols = mapping["insert_columns"]
            key_col = mapping["key_column"]
            if not insert_cols:
                raise RuntimeError(
                    f"no matching columns in {self._table} — got {columns}"
                )

            col_list = ", ".join(insert_cols)
            placeholders = ", ".join(f"?" for _ in insert_cols)
            prepared = conn.cursor()

            def sqls(field):
                return f"[{field}]" if " " in field else field

            insert_sql = f"INSERT INTO {self._table} ({col_list}) VALUES ({placeholders})"
            update_sql = (
                f"UPDATE {self._table} SET "
                + ", ".join(f"{sqls(c)} = ?" for c in insert_cols if c != key_col)
                + f" WHERE {sqls(key_col)} = ?"
            )

            inserted = updated = skipped = 0
            for i, record in enumerate(records, start=1):
                row_values = [record.get(f) for f in mapping["fields"]]
                if any(v is None for v in row_values):
                    skipped += 1
                    continue
                try:
                    prepared.execute(insert_sql, row_values)
                    inserted += 1
                except pyodbc.IntegrityError:
                    try:
                        update_values = [
                            record.get(f) for f in mapping["fields"] if f != mapping["key_field"]
                        ]
                        update_values.append(record.get(mapping["key_field"]))
                        prepared.execute(update_sql, update_values)
                        updated += 1
                    except pyodbc.IntegrityError:
                        skipped += 1
                except pyodbc.ProgrammingError:
                    # defaults/TRIGGER conflicts — tolerate
                    skipped += 1
                if i % 50 == 0:
                    conn.commit()
                    emit(f"ingesting... {inserted} inserted, {updated} updated ({i}/{len(records)})")
            conn.commit()
        finally:
            conn.close()

        emit(f"ingest complete — {inserted} inserted, {updated} updated, {skipped} skipped")
        return {
            "total": len(records),
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped,
            "table": self._table,
        }


def _load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    text = path.read_text("utf-8", errors="ignore").strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            return list(json.loads(text))
        except Exception:
            pass
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    if records:
        return records
    # last resort: JSON object with "creators" array (data.json shape) or keylist
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "creators" in obj and isinstance(obj["creators"], list):
            return obj["creators"]
        if isinstance(obj, dict):
            return [obj]
    except Exception:
        pass
    return records


def _build_mapping(columns: list[str]):
    colset = {c.lower(): c for c in columns}
    fields: list[str] = []
    insert_columns: list[str] = []
    for canonical, candidates in _FIELD_CANDIDATES.items():
        for candidate in candidates:
            if candidate.lower() in colset:
                fields.append(canonical)
                insert_columns.append(colset[candidate.lower()])
                break

    key_field = None
    key_column = None
    for candidate in ("user_name", "username", "insta_handle", "handle"):
        if candidate.lower() in colset:
            key_field = candidate
            key_column = colset[candidate.lower()]
            break
    return {
        "fields": fields,
        "insert_columns": insert_columns,
        "key_field": key_field,
        "key_column": key_column or insert_columns[0],
    }