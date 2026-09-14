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
CREATE TABLE IF NOT EXISTS lab.documents (
  id text PRIMARY KEY, title text NOT NULL, revision text NOT NULL,
  status text NOT NULL CHECK(status IN ('current','obsolete')),
  source text NOT NULL, file_hash text NOT NULL, provenance text NOT NULL,
  UNIQUE(id, revision)
);
CREATE TABLE IF NOT EXISTS lab.chunks (
  id text PRIMARY KEY, document_id text REFERENCES lab.documents(id) ON DELETE CASCADE,
  section text NOT NULL, body text NOT NULL, embedding extensions.vector(1024),
  search tsvector GENERATED ALWAYS AS (to_tsvector('simple', body)) STORED
);
CREATE INDEX IF NOT EXISTS chunks_text ON lab.chunks USING gin(search);
CREATE INDEX IF NOT EXISTS chunks_vector ON lab.chunks USING hnsw(embedding extensions.vector_cosine_ops);
CREATE TABLE IF NOT EXISTS lab.rules (
  id text PRIMARY KEY, version integer NOT NULL, definition jsonb NOT NULL,
  active boolean NOT NULL DEFAULT true, updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS lab.events (
  id text PRIMARY KEY, profile text NOT NULL, source_id text NOT NULL,
  lot_id text, row_no bigint, kind text NOT NULL, method text NOT NULL,
  payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS events_lookup ON lab.events(profile, source_id, lot_id, row_no);
CREATE TABLE IF NOT EXISTS lab.proposals (
  id text PRIMARY KEY, version integer NOT NULL DEFAULT 1,
  status text NOT NULL CHECK(status IN ('pending_approval','approved','rejected','recorded')),
  payload jsonb NOT NULL, payload_hash text NOT NULL,
  actor text, reason text, created_at timestamptz NOT NULL DEFAULT now(), decided_at timestamptz
);
CREATE TABLE IF NOT EXISTS lab.decisions (
  proposal_id text PRIMARY KEY REFERENCES lab.proposals(id),
  proposal_version integer NOT NULL, payload_hash text NOT NULL,
  actor text NOT NULL, reason text NOT NULL, before_rule jsonb, after_rule jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS lab.graph_outbox (
  id text PRIMARY KEY, payload jsonb NOT NULL, applied_at timestamptz,
  error_type text, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS lab.evaluations (
  id text PRIMARY KEY, request_id text NOT NULL, provider text NOT NULL,
  payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS lab.artifacts (
  id text PRIMARY KEY, kind text NOT NULL, payload jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
REVOKE ALL ON SCHEMA lab FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA lab FROM PUBLIC;
-- A separate read-only login is created by scripts/bootstrap.py, using environment secrets.
-- Supabase's browser roles receive no direct access to this service's tables.;
