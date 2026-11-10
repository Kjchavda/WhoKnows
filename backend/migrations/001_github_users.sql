BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS repositories_github_id_unique
    ON repositories (github_id);

CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    github_id BIGINT NOT NULL UNIQUE,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    avatar_url TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_repositories (
    user_id BIGINT NOT NULL
        REFERENCES users(id) ON DELETE CASCADE,

    repo_id BIGINT NOT NULL
        REFERENCES repositories(github_id) ON DELETE CASCADE,

    access_role VARCHAR(20) NOT NULL DEFAULT 'owner'
        CHECK (access_role IN ('owner', 'collaborator')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (user_id, repo_id)
);

CREATE INDEX idx_user_repositories_repo_id
    ON user_repositories(repo_id);

COMMIT;
