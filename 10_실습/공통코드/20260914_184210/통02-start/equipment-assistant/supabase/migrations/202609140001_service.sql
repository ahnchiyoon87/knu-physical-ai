CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;
CREATE SCHEMA IF NOT EXISTS lab;
CREATE TABLE IF NOT EXISTS lab.imports (
  id text PRIMARY KEY, profile text NOT NULL, source_id text NOT NULL,
  file_hash text NOT NULL, mapping_hash text NOT NULL, provenance text NOT NULL,
  rows bigint NOT NULL DEFAULT 0, created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(profile, source_id, file_hash, mapping_hash)
);
CREATE TABLE IF NOT EXISTS lab.records (
  import_id text REFERENCES lab.imports(id) ON DELETE CASCADE,
  row_no bigint NOT NULL, lot_id text, payload jsonb NOT NULL,
  PRIMARY KEY(import_id, row_no)
);
CREATE INDEX IF NOT EXISTS records_lot ON lab.records(import_id, lot_id, row_no);
REVOKE ALL ON SCHEMA lab FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA lab FROM PUBLIC;
-- A separate read-only login is created by scripts/bootstrap.py, using environment secrets.
-- Supabase's browser roles receive no direct access to this service's tables.;
