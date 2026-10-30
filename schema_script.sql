-- WhoKnows schema (v1). Safe to re-run: every statement is IF NOT EXISTS.
-- Order matters: referenced tables come before the tables that point at them.

-- Step 3 (embeddings) will add:  CREATE EXTENSION IF NOT EXISTS vector;
-- (Neon supports pgvector; nothing to install.)

-- One row per crawled GitHub repository.
CREATE TABLE IF NOT EXISTS repositories (
    github_id   BIGINT PRIMARY KEY,
    owner       TEXT NOT NULL,
    name        TEXT NOT NULL,
    full_name   TEXT NOT NULL UNIQUE,
    description TEXT
);

-- One row per GitHub account (human or bot). Keyed on the numeric id because
-- login can be renamed; login is just an attribute we keep up to date.
CREATE TABLE IF NOT EXISTS developers (
    github_id BIGINT PRIMARY KEY,
    login     TEXT NOT NULL,
    type      TEXT NOT NULL
);

-- Issues and pull requests share one table (GitHub's own model: a PR is an issue).
CREATE TABLE IF NOT EXISTS items (
    github_id         BIGINT PRIMARY KEY,
    repo_id           BIGINT NOT NULL REFERENCES repositories(github_id),
    number            INTEGER NOT NULL,
    kind              TEXT NOT NULL CHECK (kind IN ('issue', 'pr')),
    title             TEXT NOT NULL,
    body              TEXT,
    state             TEXT NOT NULL CHECK (state IN ('open', 'closed')),
    author_id         BIGINT REFERENCES developers(github_id),
    created_at        TIMESTAMPTZ NOT NULL,
    updated_at        TIMESTAMPTZ NOT NULL,
    closed_at         TIMESTAMPTZ,
    merged_at         TIMESTAMPTZ,
    details_synced_at TIMESTAMPTZ,
    CONSTRAINT uq_items_repo_number UNIQUE (repo_id, number),
    CONSTRAINT ck_merged_only_for_pr CHECK (merged_at IS NULL OR kind = 'pr')
);
CREATE INDEX IF NOT EXISTS ix_items_author  ON items (author_id);
CREATE INDEX IF NOT EXISTS ix_items_updated ON items (repo_id, updated_at);

-- One row per file path in a repo.
CREATE TABLE IF NOT EXISTS files (
    id      BIGSERIAL PRIMARY KEY,
    repo_id BIGINT NOT NULL REFERENCES repositories(github_id),
    path    TEXT NOT NULL,
    CONSTRAINT uq_files_repo_path UNIQUE (repo_id, path)
);

-- Which PR changed which file (many-to-many, so it needs its own table).
CREATE TABLE IF NOT EXISTS pr_files (
    item_id   BIGINT NOT NULL REFERENCES items(github_id) ON DELETE CASCADE,
    file_id   BIGINT NOT NULL REFERENCES files(id),
    status    TEXT,
    additions INTEGER NOT NULL DEFAULT 0,
    deletions INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (item_id, file_id)
);
CREATE INDEX IF NOT EXISTS ix_pr_files_file ON pr_files (file_id);

-- "PR closes issue #N", parsed from text like "Fixes #123".
CREATE TABLE IF NOT EXISTS pr_closes_issue (
    pr_id        BIGINT NOT NULL REFERENCES items(github_id) ON DELETE CASCADE,
    repo_id      BIGINT NOT NULL REFERENCES repositories(github_id),
    issue_number INTEGER NOT NULL,
    PRIMARY KEY (pr_id, issue_number)
);

-- A review is its own table because it carries data (state, text, time).
CREATE TABLE IF NOT EXISTS reviews (
    github_id    BIGINT PRIMARY KEY,
    item_id      BIGINT NOT NULL REFERENCES items(github_id) ON DELETE CASCADE,
    reviewer_id  BIGINT REFERENCES developers(github_id),
    state        TEXT NOT NULL,
    body         TEXT,
    submitted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_reviews_item     ON reviews (item_id);
CREATE INDEX IF NOT EXISTS ix_reviews_reviewer ON reviews (reviewer_id);

-- Both kinds of comment in one table.
CREATE TABLE IF NOT EXISTS comments (
    github_id  BIGINT PRIMARY KEY,
    kind       TEXT NOT NULL CHECK (kind IN ('issue_comment', 'review_comment')),
    item_id    BIGINT NOT NULL REFERENCES items(github_id) ON DELETE CASCADE,
    author_id  BIGINT REFERENCES developers(github_id),
    body       TEXT NOT NULL,
    file_id    BIGINT REFERENCES files(id),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_file_only_for_review CHECK (file_id IS NULL OR kind = 'review_comment')
);
CREATE INDEX IF NOT EXISTS ix_comments_item   ON comments (item_id);
CREATE INDEX IF NOT EXISTS ix_comments_author ON comments (author_id);
CREATE INDEX IF NOT EXISTS ix_comments_file   ON comments (file_id);

-- Raw GitHub JSON, kept so we can re-parse after a schema change without re-crawling.
CREATE TABLE IF NOT EXISTS raw_payloads (
    resource   TEXT NOT NULL,
    github_id  BIGINT NOT NULL,
    payload    JSONB NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (resource, github_id)
);

-- Crawl checkpoints: how far each resource got, per repo.
CREATE TABLE IF NOT EXISTS crawl_state (
    repo_id    BIGINT NOT NULL REFERENCES repositories(github_id),
    resource   TEXT NOT NULL,
    since      TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (repo_id, resource)
);

-- Text chunks used for semantic search.

CREATE EXTENSION IF NOT EXISTS vector;
-- Embeddings will be populated in Step 3 after enabling pgvector.

CREATE TABLE IF NOT EXISTS chunks (
    id BIGSERIAL PRIMARY KEY,

    item_id BIGINT NOT NULL
        REFERENCES items(github_id) ON DELETE CASCADE,

    source TEXT NOT NULL
        CHECK (source IN (
            'item_body',
            'issue_comment',
            'review_comment',
            'review'
        )),

    source_id BIGINT,

    author_id BIGINT
        REFERENCES developers(github_id),

    text TEXT NOT NULL,

    embedding VECTOR,

    embedding_model TEXT
);

CREATE INDEX IF NOT EXISTS ix_chunks_item
    ON chunks (item_id);

CREATE INDEX IF NOT EXISTS ix_chunks_author
    ON chunks (author_id);

CREATE INDEX IF NOT EXISTS ix_chunks_source
    ON chunks (source, source_id);