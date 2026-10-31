"""Local persistence: SQLite (standard library) plus image files on disk.

Layout (under ``data_dir``):
  analyses.db            one row per analysis
  uploads/<id>.<ext>     the uploaded MRI (validated PNG/JPEG)
  heatmaps/<id>.png      the Grad-CAM overlay (optional)

A new connection is opened per operation, which is safe for FastAPI's
threadpool. Search strings are bound as parameters (no SQL injection).

Writes: files are written to ``*.tmp`` and renamed into place, then the row is
inserted; if the insert fails the files are removed again. A crash between the
rename and the insert can still leave an orphan file, which
``cleanup_orphans`` removes at startup.

Schema versions (``PRAGMA user_version``): 1 = original columns,
2 = adds the safety columns and ``comparison``. Older databases are upgraded in
place with ``ALTER TABLE`` and old rows are back-filled from their stored
probabilities.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import config
from .safety import safety_fields

SCHEMA_VERSION = 2

# New ids: secrets.token_urlsafe(16) -> 22 URL-safe characters.
# Legacy ids (8 hex characters) are still readable after an upgrade.
_ID_RE = re.compile(r"^(?:[A-Za-z0-9_-]{22}|[0-9a-f]{8})$")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    filename TEXT NOT NULL,
    predicted_class TEXT NOT NULL,
    confidence REAL NOT NULL,
    probabilities TEXT NOT NULL,
    model_version TEXT NOT NULL,
    image_file TEXT NOT NULL,
    heatmap_file TEXT
);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses (created_at DESC);
"""

# Columns added in schema version 2 (name -> SQL type).
_V2_COLUMNS = {
    "low_confidence": "INTEGER",
    "confidence_threshold": "REAL",
    "top2": "TEXT",
    "entropy": "REAL",
    "model_id": "TEXT",
    "comparison": "TEXT",
}


def is_valid_id(analysis_id: str) -> bool:
    return bool(_ID_RE.match(analysis_id))


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


class Storage:
    def __init__(self, data_dir: Path | None = None) -> None:
        base = Path(data_dir) if data_dir else config.DATA_DIR
        self.data_dir = base
        self.db_path = base / "analyses.db"
        self.upload_dir = base / "uploads"
        self.heatmap_dir = base / "heatmaps"
        self.init()

    # -- setup ----------------------------------------------------------
    def init(self) -> None:
        """Create folders, create/upgrade the schema (idempotent)."""
        for folder in (self.data_dir, self.upload_dir, self.heatmap_dir):
            folder.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn:
            with conn:
                conn.executescript(_SCHEMA)
                existing = {row[1] for row in conn.execute("PRAGMA table_info(analyses)")}
                for name, sql_type in _V2_COLUMNS.items():
                    if name not in existing:
                        conn.execute(f"ALTER TABLE analyses ADD COLUMN {name} {sql_type}")
                self._backfill(conn)
                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    @staticmethod
    def _backfill(conn: sqlite3.Connection) -> None:
        """Fill the v2 columns of rows written by an older version of the app."""
        rows = conn.execute(
            "SELECT id, probabilities, model_version FROM analyses WHERE entropy IS NULL"
        ).fetchall()
        for row in rows:
            probs = json.loads(row["probabilities"])
            fields = safety_fields(probs)
            conn.execute(
                "UPDATE analyses SET low_confidence = ?, confidence_threshold = ?, top2 = ?,"
                " entropy = ?, model_id = COALESCE(model_id, ?) WHERE id = ?",
                (int(fields["low_confidence"]), fields["confidence_threshold"],
                 json.dumps(fields["top2"]), fields["entropy"],
                 str(row["model_version"]).split("-")[0], row["id"]),
            )

    def schema_version(self) -> int:
        with closing(self._connect()) as conn:
            return int(conn.execute("PRAGMA user_version").fetchone()[0])

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    # -- writes ---------------------------------------------------------
    def create(
        self,
        *,
        filename: str,
        predicted_class: str,
        confidence: float,
        probabilities: dict[str, float],
        model_version: str,
        model_id: str,
        image_bytes: bytes,
        image_ext: str,
        heatmap_png: bytes | None,
        comparison: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist files and the DB row; returns the stored record."""
        analysis_id = secrets.token_urlsafe(16)
        image_file = f"{analysis_id}{image_ext}"
        heatmap_file = f"{analysis_id}.png" if heatmap_png else None
        created_at = _stamp(datetime.now(timezone.utc))
        fields = safety_fields(probabilities)
        written: list[Path] = []
        try:
            written.append(self._atomic_write(self.upload_dir / image_file, image_bytes))
            if heatmap_png and heatmap_file:
                written.append(self._atomic_write(self.heatmap_dir / heatmap_file, heatmap_png))
            with closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT INTO analyses (id, created_at, filename, predicted_class, confidence,"
                    " probabilities, model_version, image_file, heatmap_file, low_confidence,"
                    " confidence_threshold, top2, entropy, model_id, comparison)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (analysis_id, created_at, filename, predicted_class, confidence,
                     json.dumps(probabilities), model_version, image_file, heatmap_file,
                     int(fields["low_confidence"]), fields["confidence_threshold"],
                     json.dumps(fields["top2"]), fields["entropy"], model_id,
                     json.dumps(comparison) if comparison is not None else None),
                )
        except Exception:
            for path in written:  # do not leave orphans
                path.unlink(missing_ok=True)
            raise
        record = self.get(analysis_id)
        assert record is not None
        return record

    @staticmethod
    def _atomic_write(target: Path, data: bytes) -> Path:
        """Write ``data`` to a temp file next to ``target`` and rename it into place."""
        tmp = target.with_name(target.name + ".tmp")
        try:
            with open(tmp, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, target)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        return target

    def delete(self, analysis_id: str) -> bool:
        """Delete the row and its files. Returns False if the id does not exist."""
        record = self.get(analysis_id)
        if record is None:
            return False
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
        self._remove_files(record["image_file"], record["heatmap_file"])
        return True

    def purge_all(self) -> int:
        """Delete every record and file. Returns the number of records removed."""
        return self._purge("SELECT id, image_file, heatmap_file FROM analyses", ())

    def purge_older_than(self, days: int) -> int:
        """Delete records older than ``days`` days (0 or less = nothing)."""
        if days <= 0:
            return 0
        cutoff = _stamp(datetime.now(timezone.utc) - timedelta(days=days))
        return self._purge(
            "SELECT id, image_file, heatmap_file FROM analyses WHERE created_at < ?", (cutoff,)
        )

    def _purge(self, select_sql: str, params: tuple[Any, ...]) -> int:
        with closing(self._connect()) as conn:
            rows = conn.execute(select_sql, params).fetchall()
        if not rows:
            return 0
        with closing(self._connect()) as conn, conn:
            conn.executemany("DELETE FROM analyses WHERE id = ?", [(r["id"],) for r in rows])
        for row in rows:
            self._remove_files(row["image_file"], row["heatmap_file"])
        return len(rows)

    def cleanup_orphans(self, min_age_seconds: float = 60.0) -> int:
        """Remove ``*.tmp`` files and files no row refers to (older than ``min_age_seconds``).

        Rows whose image file is missing are removed too. Meant to run at startup,
        before requests arrive. Returns the number of items removed.
        """
        removed = 0
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT id, image_file, heatmap_file FROM analyses").fetchall()
        known_images = {r["image_file"] for r in rows}
        known_heatmaps = {r["heatmap_file"] for r in rows if r["heatmap_file"]}
        now = time.time()
        for folder, known in ((self.upload_dir, known_images), (self.heatmap_dir, known_heatmaps)):
            for path in folder.iterdir():
                if not path.is_file():
                    continue
                if path.suffix != ".tmp" and path.name in known:
                    continue
                if now - path.stat().st_mtime >= min_age_seconds:
                    path.unlink(missing_ok=True)
                    removed += 1
        broken = [r["id"] for r in rows if not (self.upload_dir / r["image_file"]).is_file()]
        if broken:
            with closing(self._connect()) as conn, conn:
                conn.executemany("DELETE FROM analyses WHERE id = ?", [(i,) for i in broken])
            removed += len(broken)
        return removed

    def _remove_files(self, image_file: str | None, heatmap_file: str | None) -> None:
        for folder, name in ((self.upload_dir, image_file), (self.heatmap_dir, heatmap_file)):
            if name:
                (folder / name).unlink(missing_ok=True)

    # -- reads ----------------------------------------------------------
    def get(self, analysis_id: str) -> dict[str, Any] | None:
        if not is_valid_id(analysis_id):
            return None
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def list_analyses(
        self, *, search: str | None, label: str | None, page: int, page_size: int
    ) -> tuple[list[dict[str, Any]], int]:
        """Newest first. ``search`` matches id, filename or class name (case-insensitive)."""
        where: list[str] = []
        params: list[Any] = []
        if label:
            where.append("predicted_class = ?")
            params.append(label)
        if search and search.strip():
            like = f"%{_escape_like(search.strip())}%"
            where.append(
                "(id LIKE ? ESCAPE '\\' OR filename LIKE ? ESCAPE '\\'"
                " OR predicted_class LIKE ? ESCAPE '\\')"
            )
            params.extend([like, like, like])
        clause = f" WHERE {' AND '.join(where)}" if where else ""
        with closing(self._connect()) as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM analyses{clause}", params).fetchone()[0]
            rows = conn.execute(
                f"SELECT * FROM analyses{clause} ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?",
                [*params, page_size, (page - 1) * page_size],
            ).fetchall()
        return [self._row_to_dict(r) for r in rows], total

    def stats(self) -> dict[str, Any]:
        week_ago = _stamp(datetime.now(timezone.utc) - timedelta(days=7))
        with closing(self._connect()) as conn:
            total, avg = conn.execute("SELECT COUNT(*), AVG(confidence) FROM analyses").fetchone()
            recent = conn.execute(
                "SELECT COUNT(*) FROM analyses WHERE created_at >= ?", (week_ago,)
            ).fetchone()[0]
            counts = dict(conn.execute(
                "SELECT predicted_class, COUNT(*) FROM analyses GROUP BY predicted_class"
            ).fetchall())
        by_class = {c: int(counts.get(c, 0)) for c in config.CLASSES}
        return {
            "total_scans": int(total),
            "last_7_days": int(recent),
            "by_class": by_class,
            "average_confidence": round(float(avg), 4) if avg is not None else 0.0,
        }

    # -- file access ----------------------------------------------------
    def image_path(self, record: dict[str, Any]) -> Path:
        return self.upload_dir / record["image_file"]

    def heatmap_path(self, record: dict[str, Any]) -> Path | None:
        name = record.get("heatmap_file")
        if not name:
            return None
        path = self.heatmap_dir / name
        return path if path.is_file() else None

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        data = dict(row)
        data["probabilities"] = json.loads(data["probabilities"])
        data["top2"] = json.loads(data["top2"]) if data.get("top2") else []
        data["comparison"] = json.loads(data["comparison"]) if data.get("comparison") else None
        data["low_confidence"] = bool(data.get("low_confidence"))
        return data
