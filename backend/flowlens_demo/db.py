"""PostgreSQL access for the demo track: one schema, plain SQL, short transactions."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces (
    id uuid PRIMARY KEY,
    name text NOT NULL CHECK (length(name) BETWEEN 1 AND 80),
    scenario_id text NOT NULL,
    status text NOT NULL CHECK (status IN ('PROCESSING', 'READY', 'FAILED')),
    duration_ms integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    processing_started_at timestamptz NOT NULL DEFAULT now(),
    ready_at timestamptz,
    processing_scale real NOT NULL,
    step_details jsonb NOT NULL,
    analysis jsonb,
    variant text
);
CREATE UNIQUE INDEX IF NOT EXISTS workspaces_name_ci ON workspaces (lower(name));

CREATE TABLE IF NOT EXISTS workspace_files (
    workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    part text NOT NULL,
    role text NOT NULL CHECK (role IN ('audio', 'adsb')),
    original_name text NOT NULL,
    size_bytes bigint NOT NULL,
    sha256 text NOT NULL,
    detected jsonb NOT NULL,
    PRIMARY KEY (workspace_id, part, role)
);

CREATE TABLE IF NOT EXISTS transcript_segments (
    workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    seg_key text NOT NULL,
    start_ms integer NOT NULL,
    end_ms integer NOT NULL,
    text text NOT NULL,
    confidence real,
    words jsonb NOT NULL,
    origin text NOT NULL DEFAULT 'STT_HYPOTHESIS',
    PRIMARY KEY (workspace_id, seg_key)
);

CREATE TABLE IF NOT EXISTS findings (
    workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    finding_key text NOT NULL,
    category text NOT NULL,
    priority text NOT NULL,
    title text NOT NULL,
    statement text NOT NULL,
    pending_ms integer NOT NULL,
    available_ms integer NOT NULL,
    body jsonb NOT NULL,
    PRIMARY KEY (workspace_id, finding_key)
);

CREATE TABLE IF NOT EXISTS playback_state (
    workspace_id uuid PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
    cursor_ms integer NOT NULL CHECK (cursor_ms >= 0),
    updated_at timestamptz NOT NULL DEFAULT now()
);
"""


# Upgrades a database created before sessions could hold several recordings (88.wav only).
UPGRADE = """
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS variant text;
UPDATE workspaces SET variant = '88:adsb,88:audio' WHERE variant IS NULL;
ALTER TABLE workspace_files ADD COLUMN IF NOT EXISTS part text NOT NULL DEFAULT '88';
ALTER TABLE workspace_files ALTER COLUMN part DROP DEFAULT;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.key_column_usage
        WHERE table_name = 'workspace_files' AND constraint_name = 'workspace_files_pkey'
          AND column_name = 'part'
    ) THEN
        ALTER TABLE workspace_files DROP CONSTRAINT workspace_files_pkey;
        ALTER TABLE workspace_files ADD PRIMARY KEY (workspace_id, part, role);
    END IF;
END $$;
"""


class Database:
    def __init__(self, url: str):
        self.url = url

    @contextmanager
    def tx(self) -> Iterator[psycopg.Cursor[dict[str, object]]]:
        with (
            psycopg.connect(self.url, row_factory=dict_row) as conn,
            conn.transaction(),
            conn.cursor() as cur,
        ):
            yield cur

    def migrate(self) -> None:
        with self.tx() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(884201)")
            cur.execute(SCHEMA)
            cur.execute(UPGRADE)

    def ping(self) -> bool:
        try:
            with self.tx() as cur:
                cur.execute("SELECT 1")
            return True
        except psycopg.Error:
            return False
