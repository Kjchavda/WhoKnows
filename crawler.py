#!/usr/bin/env python3
"""Sequential GitHub-to-PostgreSQL crawler for WhoKnows (Python 3.11+)."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Callable
from urllib.parse import urlparse

import requests
import psycopg
from psycopg.types.json import Jsonb

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com").rstrip("/")
TOKEN = os.getenv("GITHUB_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
MAX_HTTP_ATTEMPTS = 6
MAX_DB_ATTEMPTS = 5
CLOSING_RE = re.compile(
    r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+#(\d+)",
    re.IGNORECASE,
)

SCHEMA_SQL = r"""
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
"""

def clean(value: Any) -> Any:
    """Remove NULs recursively, including from raw JSON before JSONB insertion."""
    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, dict):
        return {clean(k): clean(v) for k, v in value.items()}
    return value

def txt(value: Any) -> str | None:
    return clean(value) if value is not None else None

def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # GitHub timestamps are ISO-8601 UTC strings, usually ending in Z.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def log(message: str) -> None:
    print(f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {message}", flush=True)

def require_database_url() -> str:
    if not DATABASE_URL:
        raise SystemExit(
            "ERROR: DATABASE_URL is missing. Set it to your Neon PostgreSQL connection string "
            "(including sslmode=require) before running crawler.py."
        )
    return DATABASE_URL

class Database:
    def __init__(self, url: str):
        self.url = url
        self.conn: psycopg.Connection | None = None
        self.connect()

    def connect(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
        # Neon pooled endpoints use PgBouncer; disabling prepared statements avoids incompatibilities.
        self.conn = psycopg.connect(self.url, autocommit=True, prepare_threshold=None)

    def close(self) -> None:
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def run_tx(self, work: Callable[[psycopg.Connection], Any]) -> Any:
        """Retry only the current transaction after reconnect; writes are idempotent upserts."""
        last_error: Exception | None = None
        for attempt in range(MAX_DB_ATTEMPTS):
            try:
                if self.conn is None or self.conn.closed:
                    self.connect()
                assert self.conn is not None
                with self.conn.transaction():
                    return work(self.conn)
            except psycopg.OperationalError as exc:
                last_error = exc
                log(f"Database connection dropped; reconnect attempt {attempt + 1}/{MAX_DB_ATTEMPTS}.")
                if attempt + 1 >= MAX_DB_ATTEMPTS:
                    break
                time.sleep(2 ** attempt)
                self.connect()
        raise RuntimeError(f"Database operation failed after reconnect retries: {last_error}") from last_error

def raw_upsert(cur: psycopg.Cursor, resource: str, github_id: int, payload: Any) -> None:
    cur.execute(
        """INSERT INTO raw_payloads(resource, github_id, payload)
           VALUES (%s, %s, %s)
           ON CONFLICT(resource, github_id) DO UPDATE
           SET payload = EXCLUDED.payload, fetched_at = now()""",
        (resource, github_id, Jsonb(clean(payload))),
    )

def upsert_developer(cur: psycopg.Cursor, user: dict | None) -> int | None:
    if not user or user.get("id") is None:
        return None
    user_id = int(user["id"])
    login = txt(user.get("login")) or f"deleted-{user_id}"
    account_type = txt(user.get("type")) or "User"
    cur.execute(
        """INSERT INTO developers(github_id, login, type) VALUES (%s, %s, %s)
           ON CONFLICT(github_id) DO UPDATE SET login=EXCLUDED.login, type=EXCLUDED.type""",
        (user_id, login, account_type),
    )
    return user_id

def get_state(conn: psycopg.Connection, repo_id: int, resource: str) -> datetime | None:
    row = conn.execute(
        "SELECT since FROM crawl_state WHERE repo_id=%s AND resource=%s", (repo_id, resource)
    ).fetchone()
    return row[0] if row else None

def save_state(cur: psycopg.Cursor, repo_id: int, resource: str, stamp: datetime) -> None:
    cur.execute(
        """INSERT INTO crawl_state(repo_id, resource, since) VALUES (%s, %s, %s)
           ON CONFLICT(repo_id, resource) DO UPDATE
           SET since=GREATEST(crawl_state.since, EXCLUDED.since), updated_at=now()""",
        (repo_id, resource, stamp),
    )

class GitHub:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "WhoKnows-repository-crawler",
        })
        if TOKEN:
            self.session.headers["Authorization"] = f"Bearer {TOKEN}"
        else:
            log("WARNING: GITHUB_TOKEN is unset; unauthenticated GitHub API quota is about 60 requests/hour.")

    def request(self, url: str, params: dict | None = None) -> requests.Response:
        backoff = 1
        for attempt in range(MAX_HTTP_ATTEMPTS):
            try:
                response = self.session.get(url, params=params, timeout=(10, 60))
            except requests.RequestException as exc:
                if attempt + 1 >= MAX_HTTP_ATTEMPTS:
                    raise RuntimeError(f"GitHub network request failed after {MAX_HTTP_ATTEMPTS} attempts: {exc}") from exc
                log(f"Network error; retrying in {backoff}s ({attempt + 1}/{MAX_HTTP_ATTEMPTS}).")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue

            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            status = response.status_code

            if status in (403, 429):
                retry_after = response.headers.get("Retry-After")
                if remaining == "0" and reset:
                    delay = max(0, int(reset) - int(time.time())) + 2
                    log(f"GitHub primary rate limit exhausted; sleeping {delay}s.")
                    time.sleep(delay)
                    continue
                if retry_after:
                    delay = max(1, int(retry_after))
                    log(f"GitHub secondary/burst limit; sleeping {delay}s.")
                    time.sleep(delay)
                    continue
                response.raise_for_status()

            if 500 <= status <= 599:
                if attempt + 1 >= MAX_HTTP_ATTEMPTS:
                    response.raise_for_status()
                log(f"GitHub HTTP {status}; retrying in {backoff}s ({attempt + 1}/{MAX_HTTP_ATTEMPTS}).")
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
                continue

            if status >= 400:
                # A 404/401/422 usually means a real problem; hiding it makes crawls silently incomplete.
                response.raise_for_status()

            if remaining is not None and reset is not None and int(remaining) <= 2:
                delay = max(0, int(reset) - int(time.time())) + 2
                log(f"Only {remaining} GitHub API calls remain; sleeping {delay}s before next request.")
                time.sleep(delay)
            return response
        raise RuntimeError(f"GitHub request failed after {MAX_HTTP_ATTEMPTS} attempts: {url}")

    def get_json(self, url: str, params: dict | None = None) -> tuple[Any, requests.Response]:
        response = self.request(url, params)
        try:
            return clean(response.json()), response
        except ValueError as exc:
            raise RuntimeError(f"GitHub returned invalid JSON for {url}") from exc

    def pages(self, url: str, params: dict | None = None):
        """Yield each response page and follow GitHub's Link header rather than inventing page numbers."""
        next_url = url
        next_params = params
        while next_url:
            data, response = self.get_json(next_url, next_params)
            if not isinstance(data, list):
                raise RuntimeError(f"Expected a JSON list from paginated endpoint: {response.url}")
            yield data, response
            next_link = response.links.get("next", {}).get("url")
            next_url = next_link
            next_params = None  # Link URL already includes its query string.

def upsert_repository(db: Database, gh: GitHub, full_name: str) -> tuple[int, str, str]:
    parts = full_name.split("/")
    if len(parts) != 2 or not all(parts):
        raise SystemExit("Repository must be OWNER/NAME, for example redis/redis-py.")
    owner, name = parts
    data, _ = gh.get_json(f"{API_URL}/repos/{owner}/{name}")
    repo_id = int(data["id"])
    canonical_owner = txt(data["owner"]["login"])
    canonical_name = txt(data["name"])
    canonical_full = txt(data["full_name"])
    description = txt(data.get("description"))

    def write(conn):
        conn.execute(
            """INSERT INTO repositories(github_id, owner, name, full_name, description)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT(github_id) DO UPDATE SET owner=EXCLUDED.owner, name=EXCLUDED.name,
                 full_name=EXCLUDED.full_name, description=EXCLUDED.description""",
            (repo_id, canonical_owner, canonical_name, canonical_full, description),
        )
    db.run_tx(write)
    log(f"Repository ready: {canonical_full} (GitHub id {repo_id}).")
    return repo_id, canonical_owner, canonical_name

def save_item_page(conn: psycopg.Connection, repo_id: int, items: list[dict], stamp: datetime) -> None:
    with conn.cursor() as cur:
        for item in items:
            author_id = upsert_developer(cur, item.get("user"))
            is_pr = "pull_request" in item
            pr_obj = item.get("pull_request") or {}
            merged_at = parse_dt(pr_obj.get("merged_at")) if is_pr else None
            # Some issue-list payloads omit merged_at; null is valid, but details phase still syncs PRs.
            cur.execute(
                """INSERT INTO items(github_id, repo_id, number, kind, title, body, state, author_id,
                       created_at, updated_at, closed_at, merged_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT(github_id) DO UPDATE SET repo_id=EXCLUDED.repo_id, number=EXCLUDED.number,
                     kind=EXCLUDED.kind, title=EXCLUDED.title, body=EXCLUDED.body, state=EXCLUDED.state,
                     author_id=EXCLUDED.author_id, created_at=EXCLUDED.created_at,
                     updated_at=EXCLUDED.updated_at, closed_at=EXCLUDED.closed_at,
                     merged_at=EXCLUDED.merged_at""",
                (int(item["id"]), repo_id, int(item["number"]), "pr" if is_pr else "issue",
                 txt(item.get("title")) or "(untitled)", txt(item.get("body")),
                 item.get("state") if item.get("state") in ("open", "closed") else "closed",
                 author_id, parse_dt(item["created_at"]), parse_dt(item["updated_at"]),
                 parse_dt(item.get("closed_at")), merged_at),
            )
            item_id = int(item["id"])
            raw_upsert(cur, "item", item_id, item)
            if is_pr:
                cur.execute("DELETE FROM pr_closes_issue WHERE pr_id=%s", (item_id,))
                body = txt(item.get("body")) or ""
                for issue_number in sorted({int(m.group(1)) for m in CLOSING_RE.finditer(body)}):
                    cur.execute(
                        """INSERT INTO pr_closes_issue(pr_id, repo_id, issue_number)
                           VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                        (item_id, repo_id, issue_number),
                    )
        save_state(cur, repo_id, "items", stamp)

def crawl_items(db: Database, gh: GitHub, repo_id: int, owner: str, name: str, max_pages: int | None) -> None:
    state = db.run_tx(lambda conn: get_state(conn, repo_id, "items"))
    if state:
        log(f"Items resuming from {iso_z(state)}.")
    params = {"state": "all", "sort": "updated", "direction": "asc", "per_page": 100}
    # GitHub's since filter is exclusive; overlap slightly to avoid losing equal-timestamp records.
    if state:
        params["since"] = iso_z(state - timedelta(seconds=1))
    url = f"{API_URL}/repos/{owner}/{name}/issues"
    page_count = 0
    total = 0
    for page, response in gh.pages(url, params):
        if not page:
            log(f"Items page {page_count + 1}: empty; remaining API calls {response.headers.get('X-RateLimit-Remaining', '?')}.")
            break
        # sort=updated asc makes the last record a suitable high-water mark.
        stamp = max(parse_dt(x["updated_at"]) for x in page if x.get("updated_at"))
        db.run_tx(lambda conn, p=page, s=stamp: save_item_page(conn, repo_id, p, s))
        page_count += 1
        total += len(page)
        log(f"Items page {page_count}: saved/updated {len(page)} rows (seen {total}); remaining API calls {response.headers.get('X-RateLimit-Remaining', '?')}.")
        if max_pages and page_count >= max_pages:
            log(f"Reached --max-pages {max_pages}; items checkpoint committed.")
            break

def load_item_map(db: Database, repo_id: int) -> dict[int, int]:
    return db.run_tx(lambda conn: {
        int(number): int(github_id)
        for github_id, number in conn.execute(
            "SELECT github_id, number FROM items WHERE repo_id=%s", (repo_id,)
        ).fetchall()
    })

def upsert_file(cur: psycopg.Cursor, repo_id: int, path: str) -> int:
    path = clean(path)
    cur.execute(
        """INSERT INTO files(repo_id, path) VALUES (%s,%s)
           ON CONFLICT(repo_id, path) DO UPDATE SET path=EXCLUDED.path
           RETURNING id""",
        (repo_id, path),
    )
    return int(cur.fetchone()[0])

def crawl_comment_resource(
    db: Database, gh: GitHub, repo_id: int, owner: str, name: str,
    item_map: dict[int, int], kind: str, max_pages: int | None,
) -> None:
    resource = "issue_comments" if kind == "issue_comment" else "review_comments"
    state = db.run_tx(lambda conn: get_state(conn, repo_id, resource))
    if state:
        log(f"{resource} resuming from {iso_z(state)}.")
    params = {"sort": "updated", "direction": "asc", "per_page": 100}
    if state:
        params["since"] = iso_z(state - timedelta(seconds=1))
    endpoint = "issues/comments" if kind == "issue_comment" else "pulls/comments"
    page_count = total = skipped = 0
    for page, response in gh.pages(f"{API_URL}/repos/{owner}/{name}/{endpoint}", params):
        if not page:
            log(f"{resource} page {page_count + 1}: empty; remaining API calls {response.headers.get('X-RateLimit-Remaining', '?')}.")
            break
        stamp = max(parse_dt(x["updated_at"]) for x in page if x.get("updated_at"))

        def write(conn):
            nonlocal skipped
            with conn.cursor() as cur:
                for comment in page:
                    parent_url = comment.get("issue_url") if kind == "issue_comment" else comment.get("pull_request_url")
                    try:
                        parent_number = int(urlparse(parent_url or "").path.rstrip("/").split("/")[-1])
                    except (ValueError, IndexError):
                        skipped += 1
                        continue
                    item_id = item_map.get(parent_number)
                    if item_id is None:
                        skipped += 1
                        continue
                    author_id = upsert_developer(cur, comment.get("user"))
                    file_id = None
                    if kind == "review_comment" and comment.get("path"):
                        file_id = upsert_file(cur, repo_id, txt(comment["path"]))
                    body = txt(comment.get("body")) or ""
                    cur.execute(
                        """INSERT INTO comments(github_id, kind, item_id, author_id, body, file_id, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT(github_id) DO UPDATE SET kind=EXCLUDED.kind, item_id=EXCLUDED.item_id,
                             author_id=EXCLUDED.author_id, body=EXCLUDED.body, file_id=EXCLUDED.file_id,
                             created_at=EXCLUDED.created_at, updated_at=EXCLUDED.updated_at""",
                        (int(comment["id"]), kind, item_id, author_id, body, file_id,
                         parse_dt(comment["created_at"]), parse_dt(comment["updated_at"])),
                    )
                    raw_upsert(cur, kind, int(comment["id"]), comment)
                save_state(cur, repo_id, resource, stamp)
        db.run_tx(write)
        page_count += 1
        total += len(page)
        log(f"{resource} page {page_count}: processed {len(page)} rows (seen {total}, skipped {skipped}); remaining API calls {response.headers.get('X-RateLimit-Remaining', '?')}.")
        if max_pages and page_count >= max_pages:
            log(f"Reached --max-pages {max_pages}; {resource} checkpoint committed.")
            break

def crawl_comments(db: Database, gh: GitHub, repo_id: int, owner: str, name: str, max_pages: int | None) -> None:
    item_map = load_item_map(db, repo_id)
    crawl_comment_resource(db, gh, repo_id, owner, name, item_map, "issue_comment", max_pages)
    crawl_comment_resource(db, gh, repo_id, owner, name, item_map, "review_comment", max_pages)

def crawl_details(db: Database, gh: GitHub, repo_id: int, owner: str, name: str, max_prs: int | None) -> None:
    rows = db.run_tx(lambda conn: conn.execute(
        """SELECT github_id, number, updated_at FROM items
           WHERE repo_id=%s AND kind='pr'
             AND (details_synced_at IS NULL OR details_synced_at < updated_at)
           ORDER BY created_at DESC, number DESC""", (repo_id,)
    ).fetchall())
    if max_prs is not None:
        rows = rows[:max_prs]
    log(f"PR details: {len(rows)} pending PR(s){' (limited by --max-prs)' if max_prs is not None else ''}.")

    for index, (pr_id, number, _updated_at) in enumerate(rows, start=1):
        base = f"{API_URL}/repos/{owner}/{name}/pulls/{number}"
        # The issues-list pull_request object commonly contains links only, not merged_at.
        # Fetch the PR resource here so merged status is accurate without a second pass over every PR.
        pull_data, _pull_response = gh.get_json(base)
        # Fetch outside the DB transaction; the transaction below makes all fetched details atomic.
        reviews: list[dict] = []
        files_list: list[dict] = []
        for page, _resp in gh.pages(f"{base}/reviews", {"per_page": 100}):
            reviews.extend(page)
        for page, _resp in gh.pages(f"{base}/files", {"per_page": 100}):
            files_list.extend(page)

        def write(conn):
            with conn.cursor() as cur:
                for review in reviews:
                    reviewer_id = upsert_developer(cur, review.get("user"))
                    state = (txt(review.get("state")) or "COMMENTED").upper()
                    submitted_at = parse_dt(review.get("submitted_at"))
                    cur.execute(
                        """INSERT INTO reviews(github_id, item_id, reviewer_id, state, body, submitted_at)
                           VALUES (%s,%s,%s,%s,%s,%s)
                           ON CONFLICT(github_id) DO UPDATE SET item_id=EXCLUDED.item_id,
                             reviewer_id=EXCLUDED.reviewer_id, state=EXCLUDED.state,
                             body=EXCLUDED.body, submitted_at=EXCLUDED.submitted_at""",
                        (int(review["id"]), int(pr_id), reviewer_id, state,
                         txt(review.get("body")) or "", submitted_at),
                    )
                    raw_upsert(cur, "review", int(review["id"]), review)

                # Replace the PR's file links as a set because force-pushes can change its diff.
                cur.execute("DELETE FROM pr_files WHERE item_id=%s", (int(pr_id),))
                for changed in files_list:
                    path = txt(changed.get("filename"))
                    if not path:
                        continue
                    file_id = upsert_file(cur, repo_id, path)
                    cur.execute(
                        """INSERT INTO pr_files(item_id, file_id, status, additions, deletions)
                           VALUES (%s,%s,%s,%s,%s) ON CONFLICT(item_id,file_id) DO UPDATE
                           SET status=EXCLUDED.status, additions=EXCLUDED.additions, deletions=EXCLUDED.deletions""",
                        (int(pr_id), file_id, txt(changed.get("status")),
                         int(changed.get("additions") or 0), int(changed.get("deletions") or 0)),
                    )
                # One raw row per PR stores the entire file-list response (file objects have no stable numeric id).
                raw_upsert(cur, "pr_files", int(pr_id), files_list)
                # Keep merged_at correct even when the /issues listing omitted that field.
                cur.execute(
                    "UPDATE items SET merged_at=%s, details_synced_at=now() WHERE github_id=%s",
                    (parse_dt(pull_data.get("merged_at")), int(pr_id)),
                )
        db.run_tx(write)
        if index % 25 == 0 or index == len(rows):
            log(f"PR details: {index}/{len(rows)} synced; remaining API calls shown on most recent API response.")

def run_init_db(db: Database) -> None:
    # Schema is intentionally kept inline so this remains a single-file runnable tool.
    db.run_tx(lambda conn: conn.execute(SCHEMA_SQL))
    log("Database schema initialized (safe to run repeatedly).")

def main() -> int:
    parser = argparse.ArgumentParser(description="Copy GitHub issues, PRs, comments, reviews and changed files to PostgreSQL.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="Create the WhoKnows schema (safe to repeat).")
    crawl = sub.add_parser("crawl", help="Crawl one GitHub repository.")
    crawl.add_argument("repository", help="Repository in OWNER/NAME form, e.g. redis/redis-py")
    crawl.add_argument("--only", choices=("items", "comments", "details"), help="Run one crawl phase only.")
    crawl.add_argument("--max-pages", type=int, help="Stop each selected items/comments resource after N pages (testing).")
    crawl.add_argument("--max-prs", type=int, help="Sync at most N pending PRs in the details phase (testing).")
    args = parser.parse_args()

    try:
        db = Database(require_database_url())
    except psycopg.Error as exc:
        raise SystemExit(f"ERROR: Could not connect to PostgreSQL. Check DATABASE_URL and Neon SSL settings. Details: {exc}") from exc

    gh = GitHub()
    try:
        if args.command == "init-db":
            run_init_db(db)
            return 0

        if args.max_pages is not None and args.max_pages < 1:
            raise SystemExit("--max-pages must be at least 1.")
        if args.max_prs is not None and args.max_prs < 0:
            raise SystemExit("--max-prs cannot be negative.")

        repo_id, owner, name = upsert_repository(db, gh, args.repository)
        phase = args.only
        if phase in (None, "items"):
            crawl_items(db, gh, repo_id, owner, name, args.max_pages)
        if phase in (None, "comments"):
            crawl_comments(db, gh, repo_id, owner, name, args.max_pages)
        if phase in (None, "details"):
            crawl_details(db, gh, repo_id, owner, name, args.max_prs)
        log("Crawl finished.")
        return 0
    except KeyboardInterrupt:
        log("Interrupted by Ctrl+C. Committed page/PR progress is saved; restart the same command to resume.")
        return 130
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
