# GitHub OAuth and frontend

Apply [`backend/migrations/001_github_users.sql`](./backend/migrations/001_github_users.sql)
before using sign-in. Configure `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`,
`SESSION_SECRET` (at least 32 characters), and `GITHUB_REDIRECT_URI` in the
backend environment. Register the redirect URI in the GitHub OAuth App.

For local development, set `GITHUB_REDIRECT_URI` to
`http://localhost:5173/auth/github/callback`, set `FRONTEND_URL` to
`http://localhost:5173`, and set `SESSION_COOKIE_SECURE=false` for HTTP. Leave
`VITE_API_BASE_URL` empty so the Vite proxy sends API calls and OAuth through the
frontend origin. In a separate frontend/API deployment, set `FRONTEND_URL` to
the frontend origin and `VITE_API_BASE_URL` to the backend origin; set
`VITE_AUTH_BASE_URL` to the backend origin when `/auth` is not proxied by the
frontend host. If the frontend and backend are on different sites, set
`SESSION_COOKIE_SAMESITE=none` and `SESSION_COOKIE_SECURE=true` so browsers send
the session cookie with credentialed API requests. Keep the default `lax` when
both hosts are same-site.

The login page is available at `/login`. The frontend calls `GET /auth/me` to
restore the session and `POST /auth/logout` to sign out. Repository listing,
repository details, indexing, job status polling, search, and API health are
connected to the existing backend routes.