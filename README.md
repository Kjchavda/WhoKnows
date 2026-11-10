# GitHub OAuth

Apply [`backend/migrations/001_github_users.sql`](./backend/migrations/001_github_users.sql)
to the PostgreSQL database before using the authentication routes. The migration
expects `repositories.github_id` to contain unique GitHub repository IDs.

Configure these environment variables:

- `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` from your GitHub OAuth App.
- `GITHUB_REDIRECT_URI`, registered as the app's authorization callback, for
  example `http://localhost:8000/auth/github/callback` during local development.
- `SESSION_SECRET`, a random secret with at least 32 characters.
- `SESSION_COOKIE_SECURE`, set to `false` only for local HTTP development; it
  defaults to `true`.

The login flow starts at `GET /auth/github`. The callback saves or updates the
user and returns their profile with a signed, HTTP-only session cookie.
`GET /auth/me` returns the authenticated profile, and `POST /auth/logout` clears
the session. OAuth requests ask for `read:user`; private repository access is
not requested.
