# WhoKnows

WhoKnows finds developers likely to know about a topic by searching GitHub issues, pull requests, comments, and reviews, then ranks people to help assign tickets. It is for repository owners who want evidence-backed suggestions based on their repository's history.

## How it works

```text
GitHub API -> crawler/ -> PostgreSQL + pgvector (chunks, HNSW index)
                                      |
                                      v
Frontend -> backend API -> semantic retrieval
                             -> developer-PR-file graph
                                + seeds and candidate expansion
                             -> ranked developers with evidence
```

`crawler/` fetches public GitHub repository issues, pull requests, comments, reviews, and changed-file details, and stores them in PostgreSQL. `schema.sql` defines the tables used by the crawler and indexer.

`embeddings/` extracts contribution text, splits it into chunks, embeds it, and stores vectors in the existing `chunks` table. Retrieval uses pgvector's HNSW index to find semantically relevant contributions.

`graph/` builds the developer-PR-file graph from authorship, reviews, and changed files. Ranking can expand issue seeds through closing pull requests and add developers with related file history as candidates; returned results include contribution evidence and ranking signals.

`backend/` serves the API, GitHub OAuth, search, and repository management. Repository indexing is queued through Redis and processed by the worker.

`frontend/` is the React/Vite application for signing in, indexing repositories, searching, and reviewing developer recommendations.

## Results

Test-split results from [docs/EVAL_RESULTS.md](docs/EVAL_RESULTS.md), using the 60 newest issues:

| Preset | Test MRR (95% CI) | Hit@3 | Candidate recall |
|---|---:|---:|---:|
| semantic | 0.4653 [0.369, 0.570] | 0.5333 | 0.8500 |
| popularity-recent | 0.9502 [0.900, 0.992] | 0.9667 | 0.9833 |
| legacy-graph | 0.7667 [0.675, 0.850] | 0.8500 | 0.8500 |
| v2-seeds-cand | 0.9139 [0.853, 0.967] | 0.9667 | 0.9667 |
| v2-pagerank | 0.8417 [0.750, 0.925] | 0.8500 | 0.8500 |

`popularity-recent` scored higher than the graph presets shown; `v2-seeds-cand` was the closest graph preset, and its paired MRR-difference interval versus recent popularity was [-0.072, -0.009]. Candidate expansion improved test candidate recall over semantic and legacy graph ranking, but did not beat the recent-activity baseline on MRR. The newest test issues scored substantially better than the oldest training issues, consistent with more accumulated repository history for newer issues and more cold-start cases among older issues. The selected default is `v2-seeds-cand` because it has the highest test MRR among non-popularity presets whose paired interval versus `legacy-graph` is entirely above zero; popularity baselines are never eligible under that rule.

Evaluation is time-travel: retrieval and graph history are limited to data created before each issue, and the issue and its fixing pull requests are excluded. Ground truth is the fixing pull request's non-bot author plus its non-bot reviewers, not the issue's assignees.

## Running it

Use Python 3.11 or newer, PostgreSQL with pgvector, Docker Compose, and Node.js/npm. Create a root `.env` file and set the variables you need:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string; Neon connections should include `sslmode=require`. |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_REDIRECT_URI` | GitHub OAuth app settings for login. |
| `SESSION_SECRET` | Secret used to sign application sessions. |
| `ADMIN_GITHUB_IDS` | Comma-separated GitHub numeric IDs allowed to index repositories beyond their own. |
| `REDIS_URL` | Redis connection URL; defaults to `redis://localhost:6379/0`. |
| `FRONTEND_URL` | Frontend origin for redirects and CORS; defaults to `http://localhost:5173`. |
| `SESSION_COOKIE_SAMESITE`, `SESSION_COOKIE_SECURE` | Session-cookie settings; defaults are `lax` and `true`. |
| `DATABASE_BATCH_SIZE`, `SEARCH_RATE_LIMIT_PER_MINUTE` | Database batch size (100) and search rate limit (30). |
| `MAX_ITEMS_PER_INDEX`, `MAX_ACTIVE_INDEX_JOBS_PER_USER` | Per-user indexing limits; defaults are 8000 items and one active job. |
| `LOG_LEVEL` | Log verbosity; defaults to `INFO`. |
| `GITHUB_TOKEN` | Optional crawler API token; without it, GitHub applies its lower unauthenticated API quota. |
| `GITHUB_API_URL` | Optional GitHub API base URL; defaults to `https://api.github.com`. |
| `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `CHUNK_SIZE`, `CHUNK_OVERLAP` | Embedding and chunk settings; defaults are `sentence-transformers/all-MiniLM-L6-v2`, 384, 500, and 75. |
| `EXTRACTION_BATCH_SIZE`, `EMBEDDING_BATCH_SIZE` | Embedding pipeline batch sizes; defaults are 100 and 32. |

1. Install the Python dependencies with `pip install -r requirements.txt`.
2. Initialize the database from the repository root; this command applies [schema.sql](schema.sql):

   ```sh
   python -m crawler.crawler init-db
   ```

3. Start Redis and the indexing worker:

   ```sh
   docker compose up --build redis worker
   ```

4. In another terminal, start the API:

   ```sh
   uvicorn backend.main:app --reload
   ```

5. In another terminal, install and start the frontend:

   ```sh
   cd frontend
   npm install
   npm run dev
   ```

   [frontend/.env.example](frontend/.env.example) lists the optional `VITE_API_BASE_URL` and `VITE_AUTH_BASE_URL` settings. The Vite development server proxies API routes to the local backend by default.

   For local HTTP development, set `SESSION_COOKIE_SECURE=false` in the root `.env`; its production-oriented default is `true`.

6. Sign in with GitHub in the frontend, open repository management, and submit an `OWNER/REPO` name. The API queues crawling and embedding for the worker. Indexing is limited to public repositories owned by the signed-in user; IDs in `ADMIN_GITHUB_IDS` can index other public repositories.
7. Run the evaluation harness from a clean Git tree:

   ```sh
   python -m scripts.evaluate_rankers --repo-id 363150 --presets all
   ```

   The harness refreshes `docs/EVAL_RESULTS.md` and writes per-run artifacts under the ignored `eval_results/` directory. For an intentional local dirty-tree run, add `--allow-dirty`.
8. Run the unit tests:

   ```sh
   python -m unittest discover -s tests -t .
   ```

## Design decisions

- Issues and pull requests share one `items` table, with a `kind` distinguishing them.
- Embeddings are stored per text chunk; aggregation keeps the best chunk per author and contribution.
- Evaluation uses chronological time-travel filtering to avoid using future history.
- Seed expansion follows issue-closing pull requests, while candidate expansion adds developers with related file history.
- `RANKING_PRESET` selects a registered ranking preset without changing the frontend API.
- Repository indexing is restricted to public repositories and their owner, with platform administrators explicitly allowed.

## Limitations

- Evaluation covers one repository (redis-py) and about 200 issues.
- The 60-issue test set is small, so confidence intervals remain wide.
- Ground truth is the fixing pull request's author and reviewers, not issue assignees.
- `pr_files` reflects each pull request's final file set, not the file state at issue creation time.
- Users can index only their own public repositories; organization repositories are admin-only.
- There is no per-request graph cache, so the graph is rebuilt for each search.

## Possible v2

- Explore feature-based or learned ranking and weight tuning.
- Evaluate a second repository before generalizing the ranking results.
- Add assignee and merger labels from `raw_payloads` to the evaluation ground truth.
- Cache the graph per repository between searches.
- Check whether the recent-popularity baseline's lead holds across additional repositories.