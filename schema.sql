-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Schema definition
CREATE SCHEMA IF NOT EXISTS "public";

-- 3. Base Tables
CREATE TABLE "developers" (
	"github_id" bigint PRIMARY KEY,
	"login" varchar(255) NOT NULL,
	"type" varchar(50) NOT NULL
);

CREATE TABLE "repositories" (
	"github_id" bigint PRIMARY KEY,
	"owner" text NOT NULL,
	"name" text NOT NULL,
	"full_name" text NOT NULL CONSTRAINT "repositories_full_name_key" UNIQUE,
	"description" text
);

CREATE TABLE "users" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "users_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"github_id" bigint NOT NULL CONSTRAINT "users_github_id_key" UNIQUE,
	"username" varchar(255) NOT NULL,
	"email" varchar(255),
	"avatar_url" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE "crawl_state" (
	"repo_id" bigint REFERENCES "repositories"("github_id"),
	"resource" text,
	"since" timestamp with time zone NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "crawl_state_pkey" PRIMARY KEY("repo_id","resource")
);

CREATE TABLE "files" (
	"id" bigserial PRIMARY KEY,
	"repo_id" bigint NOT NULL REFERENCES "repositories"("github_id"),
	"path" text NOT NULL,
	CONSTRAINT "uq_files_repo_path" UNIQUE("repo_id","path")
);

CREATE TABLE "items" (
	"github_id" bigint PRIMARY KEY,
	"repo_id" bigint NOT NULL REFERENCES "repositories"("github_id"),
	"number" integer NOT NULL,
	"kind" text NOT NULL,
	"title" text NOT NULL,
	"body" text,
	"state" text NOT NULL,
	"author_id" bigint REFERENCES "developers"("github_id"),
	"created_at" timestamp with time zone NOT NULL,
	"updated_at" timestamp with time zone NOT NULL,
	"closed_at" timestamp with time zone,
	"merged_at" timestamp with time zone,
	"details_synced_at" timestamp with time zone,
	CONSTRAINT "uq_items_repo_number" UNIQUE("repo_id","number"),
	CONSTRAINT "ck_merged_only_for_pr" CHECK (((merged_at IS NULL) OR (kind = 'pr'::text))),
	CONSTRAINT "items_kind_check" CHECK ((kind = ANY (ARRAY['issue'::text, 'pr'::text]))),
	CONSTRAINT "items_state_check" CHECK ((state = ANY (ARRAY['open'::text, 'closed'::text])))
);

CREATE TABLE "chunks" (
	"id" bigserial PRIMARY KEY,
	"item_id" bigint NOT NULL REFERENCES "items"("github_id") ON DELETE CASCADE,
	"source" text NOT NULL,
	"source_id" bigint,
	"author_id" bigint REFERENCES "developers"("github_id"),
	"text" text NOT NULL,
	"embedding" vector(384),
	"embedding_model" text,
	"chunk_index" integer DEFAULT 0 NOT NULL,
	"chunk_hash" varchar(64),
	CONSTRAINT "uq_chunks_source_chunk" UNIQUE("item_id","source","source_id","chunk_index"),
	CONSTRAINT "chunks_source_check" CHECK ((source = ANY (ARRAY['item_body'::text, 'issue_comment'::text, 'review_comment'::text, 'review'::text])))
);

CREATE TABLE "comments" (
	"github_id" bigint PRIMARY KEY,
	"kind" text NOT NULL,
	"item_id" bigint NOT NULL REFERENCES "items"("github_id") ON DELETE CASCADE,
	"author_id" bigint REFERENCES "developers"("github_id"),
	"body" text NOT NULL,
	"file_id" bigint REFERENCES "files"("id"),
	"created_at" timestamp with time zone NOT NULL,
	"updated_at" timestamp with time zone NOT NULL,
	CONSTRAINT "ck_file_only_for_review" CHECK (((file_id IS NULL) OR (kind = 'review_comment'::text))),
	CONSTRAINT "comments_kind_check" CHECK ((kind = ANY (ARRAY['issue_comment'::text, 'review_comment'::text])))
);

CREATE TABLE "pr_closes_issue" (
	"pr_id" bigint REFERENCES "items"("github_id") ON DELETE CASCADE,
	"repo_id" bigint NOT NULL REFERENCES "repositories"("github_id"),
	"issue_number" integer,
	CONSTRAINT "pr_closes_issue_pkey" PRIMARY KEY("pr_id","issue_number")
);

CREATE TABLE "pr_files" (
	"item_id" bigint REFERENCES "items"("github_id") ON DELETE CASCADE,
	"file_id" bigint REFERENCES "files"("id"),
	"status" text,
	"additions" integer DEFAULT 0 NOT NULL,
	"deletions" integer DEFAULT 0 NOT NULL,
	CONSTRAINT "pr_files_pkey" PRIMARY KEY("item_id","file_id")
);

CREATE TABLE "raw_payloads" (
	"resource" text,
	"github_id" bigint,
	"payload" jsonb NOT NULL,
	"fetched_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "raw_payloads_pkey" PRIMARY KEY("resource","github_id")
);

CREATE TABLE "reviews" (
	"github_id" bigint PRIMARY KEY,
	"item_id" bigint NOT NULL REFERENCES "items"("github_id") ON DELETE CASCADE,
	"reviewer_id" bigint REFERENCES "developers"("github_id"),
	"state" text NOT NULL,
	"body" text,
	"submitted_at" timestamp with time zone
);

CREATE TABLE "user_repositories" (
	"user_id" bigint REFERENCES "users"("id") ON DELETE CASCADE,
	"repo_id" bigint REFERENCES "repositories"("github_id") ON DELETE CASCADE,
	"access_role" varchar(20) DEFAULT 'owner' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "user_repositories_pkey" PRIMARY KEY("user_id","repo_id"),
	CONSTRAINT "user_repositories_access_role_check" CHECK (((access_role)::text = ANY ((ARRAY['owner'::character varying, 'collaborator'::character varying])::text[])))
);

-- 4. Indexes
-- Explicitly binding vector_cosine_ops for cosine similarity queries (<=>)
CREATE INDEX "idx_chunks_embedding_hnsw" ON "chunks" USING hnsw ("embedding" vector_cosine_ops);

CREATE INDEX "idx_chunks_author_id" ON "chunks" ("author_id");
CREATE INDEX "idx_chunks_source_id" ON "chunks" ("source_id");
CREATE INDEX "ix_chunks_author" ON "chunks" ("author_id");
CREATE INDEX "ix_chunks_item" ON "chunks" ("item_id");
CREATE INDEX "ix_chunks_source" ON "chunks" ("source","source_id");
CREATE INDEX "ix_comments_author" ON "comments" ("author_id");
CREATE INDEX "ix_comments_file" ON "comments" ("file_id");
CREATE INDEX "ix_comments_item" ON "comments" ("item_id");
CREATE INDEX "ix_items_author" ON "items" ("author_id");
CREATE INDEX "ix_items_updated" ON "items" ("repo_id","updated_at");
CREATE INDEX "ix_pr_files_file" ON "pr_files" ("file_id");
CREATE INDEX "ix_reviews_item" ON "reviews" ("item_id");
CREATE INDEX "ix_reviews_reviewer" ON "reviews" ("reviewer_id");
CREATE INDEX "idx_user_repositories_repo_id" ON "user_repositories" ("repo_id");