CREATE SCHEMA "public";
CREATE ROLE "cloud_admin" WITH SUPERUSER CREATEDB CREATEROLE LOGIN REPLICATION BYPASSRLS;
CREATE ROLE "neon_service" WITH CREATEDB CREATEROLE LOGIN REPLICATION BYPASSRLS;
CREATE ROLE "neon_superuser" WITH CREATEDB CREATEROLE REPLICATION BYPASSRLS;
CREATE ROLE "neondb_owner" WITH CREATEDB CREATEROLE LOGIN REPLICATION BYPASSRLS;
CREATE ROLE "pg_checkpoint";
CREATE ROLE "pg_create_subscription";
CREATE ROLE "pg_database_owner";
CREATE ROLE "pg_execute_server_program";
CREATE ROLE "pg_maintain";
CREATE ROLE "pg_monitor";
CREATE ROLE "pg_read_all_data";
CREATE ROLE "pg_read_all_settings";
CREATE ROLE "pg_read_all_stats";
CREATE ROLE "pg_read_server_files";
CREATE ROLE "pg_signal_autovacuum_worker";
CREATE ROLE "pg_signal_backend";
CREATE ROLE "pg_stat_scan_tables";
CREATE ROLE "pg_use_reserved_connections";
CREATE ROLE "pg_write_all_data";
CREATE ROLE "pg_write_server_files";
CREATE ROLE "token_roles";
GRANT INSERT ON "chunks" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "chunks" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "chunks" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "chunks" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "chunks" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "chunks" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "chunks" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "comments" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "comments" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "comments" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "comments" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "comments" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "comments" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "comments" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "crawl_state" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "crawl_state" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "crawl_state" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "crawl_state" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "crawl_state" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "crawl_state" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "crawl_state" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "developers" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "developers" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "developers" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "developers" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "developers" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "developers" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "developers" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "files" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "files" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "files" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "files" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "files" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "files" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "files" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "items" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "items" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "items" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "items" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "items" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "items" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "items" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "pr_closes_issue" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "pr_closes_issue" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "pr_closes_issue" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "pr_closes_issue" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "pr_closes_issue" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "pr_closes_issue" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "pr_closes_issue" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "pr_files" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "pr_files" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "pr_files" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "pr_files" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "pr_files" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "pr_files" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "pr_files" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "raw_payloads" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "raw_payloads" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "raw_payloads" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "raw_payloads" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "raw_payloads" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "raw_payloads" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "raw_payloads" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "reviews" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "reviews" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "reviews" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "reviews" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "reviews" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "reviews" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "reviews" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "user_repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "user_repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "user_repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "user_repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "user_repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "user_repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "user_repositories" TO "neondb_owner" WITH GRANT OPTION;
GRANT INSERT ON "users" TO "neondb_owner" WITH GRANT OPTION;
GRANT SELECT ON "users" TO "neondb_owner" WITH GRANT OPTION;
GRANT UPDATE ON "users" TO "neondb_owner" WITH GRANT OPTION;
GRANT DELETE ON "users" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRUNCATE ON "users" TO "neondb_owner" WITH GRANT OPTION;
GRANT REFERENCES ON "users" TO "neondb_owner" WITH GRANT OPTION;
GRANT TRIGGER ON "users" TO "neondb_owner" WITH GRANT OPTION;
CREATE TABLE "chunks" (
	"id" bigserial PRIMARY KEY,
	"item_id" bigint NOT NULL,
	"source" text NOT NULL,
	"source_id" bigint,
	"author_id" bigint,
	"text" text NOT NULL,
	"embedding" vector(384),
	"embedding_model" text,
	"chunk_index" integer DEFAULT 0 NOT NULL,
	"chunk_hash" varchar(64),
	CONSTRAINT "uq_chunks_item_source_index" UNIQUE("item_id","source","chunk_index"),
	CONSTRAINT "uq_chunks_source_hash" UNIQUE("source_id","chunk_hash"),
	CONSTRAINT "chunks_source_check" CHECK ((source = ANY (ARRAY['item_body'::text, 'issue_comment'::text, 'review_comment'::text, 'review'::text])))
);
CREATE TABLE "comments" (
	"github_id" bigint PRIMARY KEY,
	"kind" text NOT NULL,
	"item_id" bigint NOT NULL,
	"author_id" bigint,
	"body" text NOT NULL,
	"file_id" bigint,
	"created_at" timestamp with time zone NOT NULL,
	"updated_at" timestamp with time zone NOT NULL,
	CONSTRAINT "ck_file_only_for_review" CHECK (((file_id IS NULL) OR (kind = 'review_comment'::text))),
	CONSTRAINT "comments_kind_check" CHECK ((kind = ANY (ARRAY['issue_comment'::text, 'review_comment'::text])))
);
CREATE TABLE "crawl_state" (
	"repo_id" bigint,
	"resource" text,
	"since" timestamp with time zone NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "crawl_state_pkey" PRIMARY KEY("repo_id","resource")
);
CREATE TABLE "developers" (
	"github_id" bigint PRIMARY KEY,
	"login" varchar(255) NOT NULL,
	"type" varchar(50) NOT NULL
);
CREATE TABLE "files" (
	"id" bigserial PRIMARY KEY,
	"repo_id" bigint NOT NULL,
	"path" text NOT NULL,
	CONSTRAINT "uq_files_repo_path" UNIQUE("repo_id","path")
);
CREATE TABLE "items" (
	"github_id" bigint PRIMARY KEY,
	"repo_id" bigint NOT NULL,
	"number" integer NOT NULL,
	"kind" text NOT NULL,
	"title" text NOT NULL,
	"body" text,
	"state" text NOT NULL,
	"author_id" bigint,
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
CREATE TABLE "pr_closes_issue" (
	"pr_id" bigint,
	"repo_id" bigint NOT NULL,
	"issue_number" integer,
	CONSTRAINT "pr_closes_issue_pkey" PRIMARY KEY("pr_id","issue_number")
);
CREATE TABLE "pr_files" (
	"item_id" bigint,
	"file_id" bigint,
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
CREATE TABLE "repositories" (
	"github_id" bigint PRIMARY KEY,
	"owner" text NOT NULL,
	"name" text NOT NULL,
	"full_name" text NOT NULL CONSTRAINT "repositories_full_name_key" UNIQUE,
	"description" text
);
CREATE TABLE "reviews" (
	"github_id" bigint PRIMARY KEY,
	"item_id" bigint NOT NULL,
	"reviewer_id" bigint,
	"state" text NOT NULL,
	"body" text,
	"submitted_at" timestamp with time zone
);
CREATE TABLE "user_repositories" (
	"user_id" bigint,
	"repo_id" bigint,
	"access_role" varchar(20) DEFAULT 'owner' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "user_repositories_pkey" PRIMARY KEY("user_id","repo_id"),
	CONSTRAINT "user_repositories_access_role_check" CHECK (((access_role)::text = ANY ((ARRAY['owner'::character varying, 'collaborator'::character varying])::text[])))
);
CREATE TABLE "users" (
	"id" bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "users_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 9223372036854775807 START WITH 1 CACHE 1),
	"github_id" bigint NOT NULL CONSTRAINT "users_github_id_key" UNIQUE,
	"username" varchar(255) NOT NULL,
	"email" varchar(255),
	"avatar_url" text,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
CREATE UNIQUE INDEX "chunks_pkey" ON "chunks" ("id");
CREATE INDEX "idx_chunks_author_id" ON "chunks" ("author_id");
CREATE INDEX "idx_chunks_embedding_hnsw" ON "chunks" USING hnsw ("embedding");
CREATE UNIQUE INDEX "idx_chunks_item_body_hash" ON "chunks" ("item_id","chunk_hash");
CREATE INDEX "idx_chunks_source_id" ON "chunks" ("source_id");
CREATE INDEX "ix_chunks_author" ON "chunks" ("author_id");
CREATE INDEX "ix_chunks_item" ON "chunks" ("item_id");
CREATE INDEX "ix_chunks_source" ON "chunks" ("source","source_id");
CREATE UNIQUE INDEX "unique_source_chunk" ON "chunks" ("item_id","source","source_id","chunk_index");
CREATE UNIQUE INDEX "uq_chunks_item_source_index" ON "chunks" ("item_id","source","chunk_index");
CREATE UNIQUE INDEX "uq_chunks_source_hash" ON "chunks" ("source_id","chunk_hash");
CREATE UNIQUE INDEX "comments_pkey" ON "comments" ("github_id");
CREATE INDEX "ix_comments_author" ON "comments" ("author_id");
CREATE INDEX "ix_comments_file" ON "comments" ("file_id");
CREATE INDEX "ix_comments_item" ON "comments" ("item_id");
CREATE UNIQUE INDEX "crawl_state_pkey" ON "crawl_state" ("repo_id","resource");
CREATE UNIQUE INDEX "developers_pkey" ON "developers" ("github_id");
CREATE UNIQUE INDEX "files_pkey" ON "files" ("id");
CREATE UNIQUE INDEX "uq_files_repo_path" ON "files" ("repo_id","path");
CREATE UNIQUE INDEX "items_pkey" ON "items" ("github_id");
CREATE INDEX "ix_items_author" ON "items" ("author_id");
CREATE INDEX "ix_items_updated" ON "items" ("repo_id","updated_at");
CREATE UNIQUE INDEX "uq_items_repo_number" ON "items" ("repo_id","number");
CREATE UNIQUE INDEX "pr_closes_issue_pkey" ON "pr_closes_issue" ("pr_id","issue_number");
CREATE INDEX "ix_pr_files_file" ON "pr_files" ("file_id");
CREATE UNIQUE INDEX "pr_files_pkey" ON "pr_files" ("item_id","file_id");
CREATE UNIQUE INDEX "raw_payloads_pkey" ON "raw_payloads" ("resource","github_id");
CREATE UNIQUE INDEX "repositories_full_name_key" ON "repositories" ("full_name");
CREATE UNIQUE INDEX "repositories_pkey" ON "repositories" ("github_id");
CREATE INDEX "ix_reviews_item" ON "reviews" ("item_id");
CREATE INDEX "ix_reviews_reviewer" ON "reviews" ("reviewer_id");
CREATE UNIQUE INDEX "reviews_pkey" ON "reviews" ("github_id");
CREATE INDEX "idx_user_repositories_repo_id" ON "user_repositories" ("repo_id");
CREATE UNIQUE INDEX "user_repositories_pkey" ON "user_repositories" ("user_id","repo_id");
CREATE UNIQUE INDEX "users_github_id_key" ON "users" ("github_id");
CREATE UNIQUE INDEX "users_pkey" ON "users" ("id");
ALTER TABLE "chunks" ADD CONSTRAINT "chunks_author_id_fkey" FOREIGN KEY ("author_id") REFERENCES "developers"("github_id");
ALTER TABLE "chunks" ADD CONSTRAINT "chunks_item_id_fkey" FOREIGN KEY ("item_id") REFERENCES "items"("github_id") ON DELETE CASCADE;
ALTER TABLE "comments" ADD CONSTRAINT "comments_author_id_fkey" FOREIGN KEY ("author_id") REFERENCES "developers"("github_id");
ALTER TABLE "comments" ADD CONSTRAINT "comments_file_id_fkey" FOREIGN KEY ("file_id") REFERENCES "files"("id");
ALTER TABLE "comments" ADD CONSTRAINT "comments_item_id_fkey" FOREIGN KEY ("item_id") REFERENCES "items"("github_id") ON DELETE CASCADE;
ALTER TABLE "crawl_state" ADD CONSTRAINT "crawl_state_repo_id_fkey" FOREIGN KEY ("repo_id") REFERENCES "repositories"("github_id");
ALTER TABLE "files" ADD CONSTRAINT "files_repo_id_fkey" FOREIGN KEY ("repo_id") REFERENCES "repositories"("github_id");
ALTER TABLE "items" ADD CONSTRAINT "items_author_id_fkey" FOREIGN KEY ("author_id") REFERENCES "developers"("github_id");
ALTER TABLE "items" ADD CONSTRAINT "items_repo_id_fkey" FOREIGN KEY ("repo_id") REFERENCES "repositories"("github_id");
ALTER TABLE "pr_closes_issue" ADD CONSTRAINT "pr_closes_issue_pr_id_fkey" FOREIGN KEY ("pr_id") REFERENCES "items"("github_id") ON DELETE CASCADE;
ALTER TABLE "pr_closes_issue" ADD CONSTRAINT "pr_closes_issue_repo_id_fkey" FOREIGN KEY ("repo_id") REFERENCES "repositories"("github_id");
ALTER TABLE "pr_files" ADD CONSTRAINT "pr_files_file_id_fkey" FOREIGN KEY ("file_id") REFERENCES "files"("id");
ALTER TABLE "pr_files" ADD CONSTRAINT "pr_files_item_id_fkey" FOREIGN KEY ("item_id") REFERENCES "items"("github_id") ON DELETE CASCADE;
ALTER TABLE "reviews" ADD CONSTRAINT "reviews_item_id_fkey" FOREIGN KEY ("item_id") REFERENCES "items"("github_id") ON DELETE CASCADE;
ALTER TABLE "reviews" ADD CONSTRAINT "reviews_reviewer_id_fkey" FOREIGN KEY ("reviewer_id") REFERENCES "developers"("github_id");
ALTER TABLE "user_repositories" ADD CONSTRAINT "user_repositories_repo_id_fkey" FOREIGN KEY ("repo_id") REFERENCES "repositories"("github_id") ON DELETE CASCADE;
ALTER TABLE "user_repositories" ADD CONSTRAINT "user_repositories_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE;