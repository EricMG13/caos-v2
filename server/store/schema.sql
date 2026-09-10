-- The declared schema. Applied in full at startup (docs/REBUILD_PLAN.md Phase 1).
--
-- A table arrives here in the phase that first writes it; the tables of phases
-- not yet reached are not here (SYSTEM_SPEC.md section 2). Phase 1 writes a case
-- and the run that belongs to it.
--
-- Every statement in this file is applied once, as one transaction, against a
-- database no schema has been applied to. There is no `IF NOT EXISTS` here on
-- purpose: re-applying is not how this schema changes, and a statement that
-- silently does nothing is how a missing column reaches production. The digest
-- of this text is what server/store/__init__.py records and re-checks.

CREATE TABLE cases (
    case_id    uuid PRIMARY KEY,
    title      text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE runs (
    run_id     uuid PRIMARY KEY,
    case_id    uuid NOT NULL REFERENCES cases (case_id),
    status     text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    -- The set is closed in the database as well as in RunStatus: a status the
    -- host does not know is a status no reader can act on.
    CONSTRAINT runs_status_is_known CHECK (status IN ('RUNNING', 'COMPLETE', 'FAILED'))
);

CREATE INDEX runs_by_case ON runs (case_id);
