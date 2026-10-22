"""WhoKnows crawler v1.

Sequential, resumable GitHub -> Postgres crawler.

    python crawler.py init-db
    python crawler.py crawl redis/redis-py
    python crawler.py crawl redis/redis-py --only items --max-pages 2     # small test run

Design in one paragraph: every page of results is saved in ONE database transaction
together with its checkpoint, so a crash can never leave "data saved but checkpoint
not" (or the reverse). All writes are upserts keyed on GitHub's numeric ids, so
re-running any page is harmless. Raw JSON is stored too, so a schema change means
re-parsing, not re-crawling.
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import timezone

import psycopg
import requests
from psycopg.types.json import Jsonb

API = "https://api.github.com"
DEFAULT_DB = "postgresql://postgres:postgres@localhost:5432/whoknows"
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

# "Fixes #123", "closes: #45", "Resolved #7". Cross-repo refs (owner/repo#1) are ignored on purpose.
CLOSES_RE = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+#(\d+)", re.I)


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


# --------------------------------------------------------------------------- GitHub client
class GitHub:
    """Thin wrapper over requests: auth, rate-limit handling, retries, pagination."""

    def __init__(self, token, api=API):
        self.api = api
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "whoknows-crawler",
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.remaining = None

    def _sleep_until_reset(self, resp):
        # X-RateLimit-Reset is a Unix timestamp (seconds) for when the quota refills.
        reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
        delay = max(reset - time.time(), 0) + 2
        log(f"rate limit reached, sleeping {delay / 60:.1f} min until reset")
        time.sleep(delay)

    def get(self, url, params=None):
        if not url.startswith("http"):
            url = self.api + url
        for attempt in range(6):
            try:
                resp = self.session.get(url, params=params, timeout=30)
            except requests.RequestException as exc:
                wait = 2 ** attempt
                log(f"network error ({exc.__class__.__name__}), retrying in {wait}s")
                time.sleep(wait)
                continue

            left = resp.headers.get("X-RateLimit-Remaining")
            self.remaining = int(left) if left is not None else self.remaining

            if resp.status_code == 200:
                if self.remaining is not None and self.remaining <= 2:
                    self._sleep_until_reset(resp)       # pause BEFORE the next call fails
                return resp
            if resp.status_code in (403, 429):
                if "Retry-After" in resp.headers:        # secondary (burst) rate limit
                    time.sleep(int(resp.headers["Retry-After"]) + 1)
                    continue
                if left == "0":                          # primary quota exhausted
                    self._sleep_until_reset(resp)
                    continue
            if resp.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()                      # 404, real 403, etc: let it fail loudly
        raise RuntimeError(f"giving up on {url} after repeated failures")

    def pages(self, path, params=None):
        """Yield one list of results per page, following the Link: rel="next" header."""
        resp = self.get(path, params)
        while True:
            yield resp.json()
            nxt = resp.links.get("next", {}).get("url")
            if not nxt:
                return
            resp = self.get(nxt)                         # the next-URL already carries its params


# --------------------------------------------------------------------------- small helpers
def clean(text):
    """Postgres text/JSONB reject the NUL character; GitHub bodies occasionally contain one."""
    return text.replace("\x00", "") if isinstance(text, str) else text


def jb(obj):
    return Jsonb(json.loads(json.dumps(obj).replace("\\u0000", "")))


def dev_row(user):
    if not user or user.get("id") is None:
        return None                                      # deleted account: author stays NULL
    return (user["id"], user["login"], user.get("type", "User"))


def upsert_developers(cur, users):
    rows = {}
    for u in users:
        row = dev_row(u)
        if row:
            rows[row[0]] = row
    if rows:
        cur.executemany(
            """INSERT INTO developers (github_id, login, type) VALUES (%s, %s, %s)
               ON CONFLICT (github_id) DO UPDATE SET login = EXCLUDED.login, type = EXCLUDED.type""",
            list(rows.values()),
        )


def author_id(user):
    return user["id"] if user and user.get("id") is not None else None


def to_github_ts(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_checkpoint(conn, repo_id, resource):
    row = conn.execute(
        "SELECT since FROM crawl_state WHERE repo_id = %s AND resource = %s", (repo_id, resource)
    ).fetchone()
    return row[0] if row else None


def set_checkpoint(cur, repo_id, resource, since):
    cur.execute(
        """INSERT INTO crawl_state (repo_id, resource, since) VALUES (%s, %s, %s)
           ON CONFLICT (repo_id, resource) DO UPDATE SET since = EXCLUDED.since, updated_at = now()""",
        (repo_id, resource, since),
    )


def last_segment(url):
    return int(url.rstrip("/").rsplit("/", 1)[1])


# --------------------------------------------------------------------------- phases
def crawl_repo(gh, conn, full_name):
    data = gh.get(f"/repos/{full_name}").json()
    conn.execute(
        """INSERT INTO repositories (github_id, owner, name, full_name, description)
           VALUES (%s, %s, %s, %s, %s)
           ON CONFLICT (github_id) DO UPDATE SET full_name = EXCLUDED.full_name,
                                                 description = EXCLUDED.description""",
        (data["id"], data["owner"]["login"], data["name"], data["full_name"], clean(data.get("description"))),
    )
    return data["id"], data["full_name"]


def crawl_items(gh, conn, repo_id, full_name, max_pages):
    """/issues returns issues AND pull requests (a PR is an issue to GitHub)."""
    since = get_checkpoint(conn, repo_id, "items")
    params = {"state": "all", "sort": "updated", "direction": "asc", "per_page": 100}
    if since:
        params["since"] = to_github_ts(since)
        log(f"items: resuming from {params['since']}")
    total = 0
    for n, page in enumerate(gh.pages(f"/repos/{full_name}/issues", params), start=1):
        if page:
            with conn.transaction():                     # data + checkpoint commit together
                cur = conn.cursor()
                upsert_developers(cur, [it.get("user") for it in page])
                cur.executemany(
                    """INSERT INTO items (github_id, repo_id, number, kind, title, body, state, author_id,
                                          created_at, updated_at, closed_at, merged_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (github_id) DO UPDATE SET
                           title = EXCLUDED.title, body = EXCLUDED.body, state = EXCLUDED.state,
                           author_id = EXCLUDED.author_id, updated_at = EXCLUDED.updated_at,
                           closed_at = EXCLUDED.closed_at, merged_at = EXCLUDED.merged_at""",
                    [(it["id"], repo_id, it["number"], "pr" if "pull_request" in it else "issue",
                      clean(it["title"]), clean(it.get("body")), it["state"], author_id(it.get("user")),
                      it["created_at"], it["updated_at"], it.get("closed_at"),
                      (it.get("pull_request") or {}).get("merged_at")) for it in page],
                )
                cur.executemany(
                    """INSERT INTO raw_payloads (resource, github_id, payload) VALUES ('item', %s, %s)
                       ON CONFLICT (resource, github_id) DO UPDATE SET payload = EXCLUDED.payload, fetched_at = now()""",
                    [(it["id"], jb(it)) for it in page],
                )
                prs = [it for it in page if "pull_request" in it]
                cur.executemany("DELETE FROM pr_closes_issue WHERE pr_id = %s", [(it["id"],) for it in prs])
                closes = {(it["id"], repo_id, int(m)) for it in prs
                          for m in CLOSES_RE.findall(it.get("body") or "")}
                if closes:
                    cur.executemany(
                        "INSERT INTO pr_closes_issue (pr_id, repo_id, issue_number) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                        list(closes),
                    )
                set_checkpoint(cur, repo_id, "items", page[-1]["updated_at"])   # sorted ascending
        total += len(page)
        log(f"items: page {n}, {total} saved, {gh.remaining} API calls left")
        if max_pages and n >= max_pages:
            log("items: stopping early (--max-pages)")
            break


def file_id_for(cur, repo_id, path, cache):
    key = (repo_id, path)
    if key not in cache:
        # the no-op UPDATE makes RETURNING work whether the row is new or already existed
        cur.execute(
            """INSERT INTO files (repo_id, path) VALUES (%s, %s)
               ON CONFLICT (repo_id, path) DO UPDATE SET path = EXCLUDED.path RETURNING id""",
            (repo_id, clean(path)),
        )
        cache[key] = cur.fetchone()[0]
    return cache[key]


def crawl_comments(gh, conn, repo_id, full_name, kind, max_pages, file_cache):
    """One repo-wide listing per comment kind: ~100 comments per call instead of 1 call per PR."""
    if kind == "issue_comment":
        path, parent_field, resource = f"/repos/{full_name}/issues/comments", "issue_url", "issue_comments"
    else:
        path, parent_field, resource = f"/repos/{full_name}/pulls/comments", "pull_request_url", "review_comments"

    item_ids = dict(conn.execute("SELECT number, github_id FROM items WHERE repo_id = %s", (repo_id,)).fetchall())
    since = get_checkpoint(conn, repo_id, resource)
    params = {"sort": "updated", "direction": "asc", "per_page": 100}
    if since:
        params["since"] = to_github_ts(since)
        log(f"{resource}: resuming from {params['since']}")
    total = skipped = 0
    for n, page in enumerate(gh.pages(path, params), start=1):
        if page:
            with conn.transaction():
                cur = conn.cursor()
                upsert_developers(cur, [c.get("user") for c in page])
                rows = []
                for c in page:
                    parent = item_ids.get(last_segment(c[parent_field]))
                    if parent is None:                   # item newer than our items crawl; next run catches it
                        skipped += 1
                        continue
                    fid = file_id_for(cur, repo_id, c["path"], file_cache) if kind == "review_comment" else None
                    rows.append((c["id"], kind, parent, author_id(c.get("user")), clean(c.get("body") or ""),
                                 fid, c["created_at"], c["updated_at"]))
                cur.executemany(
                    """INSERT INTO comments (github_id, kind, item_id, author_id, body, file_id, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (github_id) DO UPDATE SET body = EXCLUDED.body, updated_at = EXCLUDED.updated_at""",
                    rows,
                )
                cur.executemany(
                    """INSERT INTO raw_payloads (resource, github_id, payload) VALUES (%s, %s, %s)
                       ON CONFLICT (resource, github_id) DO UPDATE SET payload = EXCLUDED.payload, fetched_at = now()""",
                    [(kind, c["id"], jb(c)) for c in page],
                )
                set_checkpoint(cur, repo_id, resource, page[-1]["updated_at"])
        total += len(page)
        log(f"{resource}: page {n}, {total} seen ({skipped} skipped), {gh.remaining} API calls left")
        if max_pages and n >= max_pages:
            log(f"{resource}: stopping early (--max-pages)")
            break


def crawl_pr_details(gh, conn, repo_id, full_name, max_prs, file_cache):
    """Reviews and changed files exist only per PR (2 calls each). The 'checkpoint' here is
    items.details_synced_at: a PR is pending if never synced or updated since the last sync."""
    pending = conn.execute(
        """SELECT github_id, number FROM items
           WHERE repo_id = %s AND kind = 'pr'
             AND (details_synced_at IS NULL OR details_synced_at < updated_at)
           ORDER BY updated_at DESC""",                  # newest first: most useful data arrives earliest
        (repo_id,),
    ).fetchall()
    if max_prs:
        pending = pending[:max_prs]
    log(f"details: {len(pending)} PRs to sync")
    for i, (item_id, number) in enumerate(pending, start=1):
        reviews = [r for page in gh.pages(f"/repos/{full_name}/pulls/{number}/reviews", {"per_page": 100}) for r in page]
        files = [f for page in gh.pages(f"/repos/{full_name}/pulls/{number}/files", {"per_page": 100}) for f in page]
        with conn.transaction():
            cur = conn.cursor()
            upsert_developers(cur, [r.get("user") for r in reviews])
            cur.executemany(
                """INSERT INTO reviews (github_id, item_id, reviewer_id, state, body, submitted_at)
                   VALUES (%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (github_id) DO UPDATE SET state = EXCLUDED.state, body = EXCLUDED.body""",
                [(r["id"], item_id, author_id(r.get("user")), r["state"], clean(r.get("body")), r.get("submitted_at"))
                 for r in reviews],
            )
            cur.executemany(
                """INSERT INTO raw_payloads (resource, github_id, payload) VALUES ('review', %s, %s)
                   ON CONFLICT (resource, github_id) DO UPDATE SET payload = EXCLUDED.payload, fetched_at = now()""",
                [(r["id"], jb(r)) for r in reviews],
            )
            cur.execute("DELETE FROM pr_files WHERE item_id = %s", (item_id,))   # file list can change after a force-push
            cur.executemany(
                """INSERT INTO pr_files (item_id, file_id, status, additions, deletions) VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (item_id, file_id) DO NOTHING""",
                [(item_id, file_id_for(cur, repo_id, f["filename"], file_cache), f.get("status"),
                  f.get("additions", 0), f.get("deletions", 0)) for f in files],
            )
            cur.execute(
                """INSERT INTO raw_payloads (resource, github_id, payload) VALUES ('pr_files', %s, %s)
                   ON CONFLICT (resource, github_id) DO UPDATE SET payload = EXCLUDED.payload, fetched_at = now()""",
                (item_id, jb({"files": files})),
            )
            cur.execute("UPDATE items SET details_synced_at = now() WHERE github_id = %s", (item_id,))
        if i % 25 == 0 or i == len(pending):
            log(f"details: {i}/{len(pending)} PRs, {gh.remaining} API calls left")


# --------------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="create all tables from schema.sql")
    c = sub.add_parser("crawl", help="crawl one repository")
    c.add_argument("repo", help="owner/name, e.g. redis/redis-py")
    c.add_argument("--only", choices=["items", "comments", "details"], help="run just one phase")
    c.add_argument("--max-pages", type=int, default=0, help="stop items/comments after N pages (for testing)")
    c.add_argument("--max-prs", type=int, default=0, help="sync details for at most N PRs (for testing)")
    args = ap.parse_args()

    conn = psycopg.connect(os.environ.get("DATABASE_URL", DEFAULT_DB), autocommit=True)

    if args.cmd == "init-db":
        with open(SCHEMA_PATH) as f:
            conn.execute(f.read())
        log("schema ready")
        return

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        log("WARNING: no GITHUB_TOKEN set; unauthenticated limit is only 60 requests/hour")
    gh = GitHub(token, os.environ.get("GITHUB_API_URL", API))

    repo_id, full_name = crawl_repo(gh, conn, args.repo)
    file_cache = {}
    if args.only in (None, "items"):
        crawl_items(gh, conn, repo_id, full_name, args.max_pages)
    if args.only in (None, "comments"):
        crawl_comments(gh, conn, repo_id, full_name, "issue_comment", args.max_pages, file_cache)
        crawl_comments(gh, conn, repo_id, full_name, "review_comment", args.max_pages, file_cache)
    if args.only in (None, "details"):
        crawl_pr_details(gh, conn, repo_id, full_name, args.max_prs, file_cache)
    log("done")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\ninterrupted: progress up to the last committed page is saved, just rerun")