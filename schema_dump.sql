CREATE TABLE IF NOT EXISTS public.repositories (
github_id BIGINT NOT NULL,
owner TEXT NOT NULL,
name TEXT NOT NULL,
full_name TEXT NOT NULL,
description TEXT
);

CREATE TABLE IF NOT EXISTS public.items (
github_id BIGINT NOT NULL,
repo_id BIGINT NOT NULL,
number INTEGER NOT NULL,
kind TEXT NOT NULL,
title TEXT NOT NULL,
body TEXT,
state TEXT NOT NULL,
author_id BIGINT,
created_at TIMESTAMP WITH TIME ZONE NOT NULL,
updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
closed_at TIMESTAMP WITH TIME ZONE,
merged_at TIMESTAMP WITH TIME ZONE,
details_synced_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS public.developers (
github_id BIGINT NOT NULL,
login CHARACTER VARYING(255) NOT NULL,
type CHARACTER VARYING(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS public.files (
id BIGINT NOT NULL DEFAULT nextval('files_id_seq'::regclass),
repo_id BIGINT NOT NULL,
path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS public.reviews (
github_id BIGINT NOT NULL,
item_id BIGINT NOT NULL,
reviewer_id BIGINT,
state TEXT NOT NULL,
body TEXT,
submitted_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS public.pr_files (
item_id BIGINT NOT NULL,
file_id BIGINT NOT NULL,
status TEXT,
additions INTEGER NOT NULL DEFAULT 0,
deletions INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS public.pr_closes_issue (
pr_id BIGINT NOT NULL,
repo_id BIGINT NOT NULL,
issue_number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS public.comments (
github_id BIGINT NOT NULL,
kind TEXT NOT NULL,
item_id BIGINT NOT NULL,
author_id BIGINT,
body TEXT NOT NULL,
file_id BIGINT,
created_at TIMESTAMP WITH TIME ZONE NOT NULL,
updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS public.raw_payloads (
resource TEXT NOT NULL,
github_id BIGINT NOT NULL,
payload JSONB NOT NULL,
fetched_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.crawl_state (
repo_id BIGINT NOT NULL,
resource TEXT NOT NULL,
since TIMESTAMP WITH TIME ZONE NOT NULL,
updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.chunks (
id BIGINT NOT NULL DEFAULT nextval('chunks_id_seq'::regclass),
item_id BIGINT NOT NULL,
source TEXT NOT NULL,
source_id BIGINT,
author_id BIGINT,
text TEXT NOT NULL,
embedding USER-DEFINED,
embedding_model TEXT,
chunk_index INTEGER NOT NULL DEFAULT 0
);