# WhoKnows — Deployment guide

## Architecture

```
Browser  ──→  Reverse proxy (Caddy / nginx)
                ├─ /api/*  ──→  FastAPI  (port 8000)
                └─ /*      ──→  frontend/dist (static)
                                └─ SPA fallback: index.html
```

The dev server (`npm run dev`) does the same thing locally: Vite proxies
`/api/*` to `http://127.0.0.1:8000` and strips the prefix.

---

## nginx equivalent (5 lines)

```nginx
location /api/ {
    proxy_pass http://localhost:8000/;   # trailing slash strips /api
}
location / {
    try_files $uri $uri/ /index.html;   # SPA fallback — do not remove
}
```

**Important:** the SPA fallback (`try_files … /index.html`) is mandatory.
Without it, refreshing `/repositories` or `/search?repo_id=…` returns a
404 instead of loading the app.

---

## Required environment variables (single-origin deploy)

Set these on the server running FastAPI (not in `frontend/.env`):

| Variable | Value |
|---|---|
| `FRONTEND_URL` | `https://<your-domain>` |
| `GITHUB_REDIRECT_URI` | `https://<your-domain>/api/auth/github/callback` — also set the same URL in your GitHub OAuth app's "Authorization callback URL" |
| `SESSION_SECRET` | A long random string (e.g. `openssl rand -hex 32`) |
| `SESSION_COOKIE_SECURE` | `true` |
| `SESSION_COOKIE_SAMESITE` | `lax` |
| `ADMIN_GITHUB_IDS` | Your GitHub numeric user ID (find it at `https://api.github.com/users/<username>`) |
| `GITHUB_TOKEN` | A personal access token — raises the GitHub API rate limit for the crawler |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |

Frontend build-time variable (optional — only needed for a cross-domain deploy
where the API lives on a different origin than the SPA):

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://api.<your-domain>` (omit for same-origin) |

---

## Warnings (not verified in CI)

> **RAM:** The API loads a sentence-transformers model at startup.
> This requires roughly 1–2 GB of RAM. Tiny free-tier instances (512 MB)
> may run out of memory and OOM-kill the process.

> **docker-compose scope:** `docker-compose.yml` currently runs only Redis
> and the background worker. The FastAPI process and the frontend static
> files need their own process or container (e.g. `uvicorn backend.main:app`
> and a web server pointing at `frontend/dist`).

---

## Smoke-test checklist

Run these manually after deploying; record pass/fail next to each line.

- [ ] Signed out: opening `/`, `/search?…` and `/repositories` redirects to `/login`; no 401 error text appears.
- [ ] Sign in with GitHub; land back on the page that was originally requested.
- [ ] Refresh on `/repositories`, `/repositories/<id>` and `/search?repo_id=…&query=…`: each reloads the app page, not JSON.
- [ ] Search on redis-py: results show cards with a "Match score", evidence, and no role label or synthesis paragraph.
- [ ] A brand-new user with no repositories sees the onboarding panel; indexing an org repo shows a clear 403 message.
- [ ] Trigger the rate limit (31 searches in a minute): friendly message appears.
- [ ] Mobile (375 px): sidebar opens and closes; cards do not overflow horizontally.
- [ ] Sign out clears the session; reloading returns to `/login`.
