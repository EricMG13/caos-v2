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

-- One row per node per try. Append-only (SYSTEM_SPEC.md section 2), which is why
-- acceptance is not a column here: an accepted attempt is one that has an
-- artifacts row, so recovery reads acceptance rather than a flag someone had to
-- remember to set.
CREATE TABLE run_attempts (
    attempt_id    uuid PRIMARY KEY,
    run_id        uuid NOT NULL REFERENCES runs (run_id),
    route_node_id text NOT NULL,
    started_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX run_attempts_by_run ON run_attempts (run_id);

-- The accepted output of one attempt. `attempt_id` is the key rather than the
-- digest: it is what makes a replayed completion land on the row it already
-- wrote instead of a second one.
CREATE TABLE artifacts (
    attempt_id      uuid PRIMARY KEY REFERENCES run_attempts (attempt_id),
    artifact_sha256 text NOT NULL,
    run_id          uuid NOT NULL REFERENCES runs (run_id),
    case_id         uuid NOT NULL REFERENCES cases (case_id),
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX artifacts_by_run ON artifacts (run_id);

-- Append-only, per-run monotonic `seq`, allocated under the run row lock. The
-- primary key is the second half of that guarantee: were the lock ever dropped,
-- two events claiming one position would fail rather than both be stored.
CREATE TABLE run_events (
    run_id uuid NOT NULL REFERENCES runs (run_id),
    seq    bigint NOT NULL,
    name   text NOT NULL,
    at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, seq),
    CONSTRAINT run_events_seq_is_positive CHECK (seq > 0),
    CONSTRAINT run_events_name_is_known CHECK (
        name IN ('ATTEMPT_STARTED', 'RUN_COMPLETE', 'RUN_FAILED')
    )
);

-- What a run was charged. `amount` is numeric and reaches Python as Decimal:
-- invariant 7 is that no money path is ever a float. One charge per attempt,
-- enforced here rather than argued from the caller.
CREATE TABLE budget_ledger (
    attempt_id uuid PRIMARY KEY REFERENCES run_attempts (attempt_id),
    run_id     uuid NOT NULL REFERENCES runs (run_id),
    amount     numeric NOT NULL,
    charged_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX budget_ledger_by_run ON budget_ledger (run_id);
