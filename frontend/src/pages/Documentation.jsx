import React from 'react';

export default function Documentation() {
  const endpoints = [
    {
      method: 'GET',
      path: '/',
      summary: 'Check Backend Health',
      description: 'Returns the API status and is used by the workspace health indicator.',
      response: `{
  "message": "WhoKnows API is running"
}`,
    },
    {
      method: 'GET',
      path: '/auth/github',
      summary: 'Start GitHub Sign-In',
      description: 'Redirects the browser to GitHub OAuth. The frontend links to this route from the login page.',
      response: 'Redirects to GitHub authorization.',
    },
    {
      method: 'GET',
      path: '/auth/github/callback',
      summary: 'Complete GitHub Sign-In',
      description: 'Validates the OAuth state, stores the GitHub user, sets the session cookie, and redirects to the configured frontend.',
      response: 'Redirects to the frontend with an authenticated session cookie.',
    },
    {
      method: 'GET',
      path: '/auth/me',
      summary: 'Get Signed-In User',
      description: 'Returns the profile for the current session. The frontend uses this to restore sign-in state.',
      response: `{
  "user": {
    "id": 1,
    "github_id": 1024,
    "username": "octocat",
    "email": null,
    "avatar_url": "https://avatars.githubusercontent.com/u/1024"
  }
}`,
    },
    {
      method: 'POST',
      path: '/auth/logout',
      summary: 'Sign Out',
      description: 'Clears the signed session cookie.',
      response: `{
  "message": "Logged out."
}`,
    },
    {
      method: 'GET',
      path: '/repositories/',
      summary: 'List Indexed Repositories',
      description: 'Returns all GitHub repositories currently indexed in the PostgreSQL database.',
      response: `[
  {
    "github_id": 1,
    "owner": "redis",
    "name": "redis-py"
  }
]`,
    },
    {
      method: 'GET',
      path: '/repositories/{repo_id}',
      summary: 'Get Repository Details',
      description: 'Fetches metadata for a specific repository by its database identifier.',
      response: `{
  "github_id": 1,
  "owner": "redis",
  "name": "redis-py"
}`,
    },
    {
      method: 'POST',
      path: '/repositories/index',
      summary: 'Trigger Repository Indexing Job',
      description: 'Queues an indexing job for the background worker.',
      request: `{
  "full_name": "redis/redis-py"
}`,
      response: `{
  "message": "Repository indexing queued",
  "job_id": "c1f7a1e0-32df-4c22-b5b9-478ac921008f",
  "repository": "redis/redis-py",
  "status": "queued"
}`,
    },
    {
      method: 'GET',
      path: '/repositories/jobs/{job_id}',
      summary: 'Get Indexing Job Status',
      description: 'Polls the status of an active or completed indexing job.',
      response: `{
  "job_id": "c1f7a1e0-32df-4c22-b5b9-478ac921008f",
  "status": "finished",
  "result": {
    "repository_id": 1
  }
}`,
    },
    {
      method: 'POST',
      path: '/search/',
      summary: 'Search Repository & Rank Developers',
      description: 'Executes semantic retrieval across indexed chunks and ranks developers using semantic matches and file history.',
      request: `{
  "repo_id": 1,
  "query": "connection pooling and socket timeouts",
  "limit": 100
}`,
      response: `{
  "repo_id": 1,
  "query": "connection pooling and socket timeouts",
  "results": [
    {
      "developer_id": 1024,
      "developer_login": "andymccurdy",
      "score": 0.88,
      "semantic_relevance": 0.94,
      "semantic_contribution_count": 12,
      "direct_pr_count": 8,
      "historical_related_pr_count": 14,
      "covered_files": 6,
      "total_files": 18,
      "coverage": 0.42,
      "historical_depth": 0.75,
      "signals": {
        "semantic_relevance": 0.94,
        "coverage": 0.42,
        "historical_depth": 0.75,
        "origin": "semantic"
      },
      "evidence": [
        {
          "source": "item_body",
          "item_kind": "pr",
          "item_number": 1204,
          "item_title": "Refactor ConnectionPool to support non-blocking acquire",
          "similarity": 0.91,
          "github_url": "https://github.com/redis/redis-py/pull/1204",
          "text": "ConnectionPool should allow non-blocking acquire while the socket waits for data."
        }
      ]
    }
  ]
}`,
    },
  ];

  return (
    <div className="p-space-lg md:p-space-xl flex flex-col gap-space-xl max-w-7xl mx-auto w-full">
      <div className="flex flex-col gap-space-xs">
        <div className="flex items-center gap-space-sm text-outline">
          <span className="font-label-sm text-label-sm uppercase tracking-widest text-secondary font-mono">
            API Reference
          </span>
          <span>/</span>
          <span className="font-code-sm text-code-sm text-outline">REST Endpoints</span>
        </div>
        <h1 className="font-headline-lg text-headline-lg text-on-surface font-semibold tracking-tight">
          WhoKnows Architecture & API Reference
        </h1>
        <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
          The WhoKnows engine indexes GitHub codebases into searchable chunks and a developer-file graph to suggest people who have worked on a topic.
        </p>
      </div>

      <div className="rounded-xl border border-outline-variant/30 bg-surface-container-low p-space-lg">
        <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold mb-space-sm">How ranking works</h2>
        <p className="font-body-md text-body-md text-on-surface-variant">
          Ranking combines semantic match on issue and PR text with file history from authored and reviewed pull requests. Recent activity is weighted more heavily, results are suggestions rather than verdicts, and the UI keeps the evidence visible for checks.
        </p>
        <p className="font-body-md text-body-md text-on-surface-variant mt-space-sm">
          On the evaluation repository a simple “most recently active maintainers” baseline performed comparably; see the README for the numbers.
        </p>
      </div>

      {/* Endpoints List */}
      <div className="flex flex-col gap-space-lg">
        {endpoints.map((ep, idx) => (
          <div
            key={idx}
            className="p-space-lg rounded-xl bg-surface-container-low border border-outline-variant/30 flex flex-col gap-space-md"
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-xs pb-space-xs border-b border-surface-container">
              <div className="flex items-center gap-space-sm">
                <span
                  className={`px-space-xs py-0.5 rounded font-label-sm text-label-sm font-bold font-mono ${
                    ep.method === 'GET'
                      ? 'bg-secondary/20 text-secondary border border-secondary/30'
                      : 'bg-primary/20 text-primary border border-primary/30'
                  }`}
                >
                  {ep.method}
                </span>
                <span className="font-code-md text-code-md text-on-surface font-semibold">
                  {ep.path}
                </span>
              </div>
              <span className="font-body-sm text-body-sm text-outline">
                {ep.summary}
              </span>
            </div>

            <p className="font-body-md text-body-md text-on-surface-variant">
              {ep.description}
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
              {ep.request && (
                <div className="flex flex-col gap-1">
                  <span className="font-label-sm text-label-sm uppercase text-outline">
                    Request Payload
                  </span>
                  <pre className="p-space-sm rounded-lg bg-surface-container-lowest border border-outline-variant/20 font-code-sm text-code-sm text-secondary-fixed-dim overflow-x-auto">
                    {ep.request}
                  </pre>
                </div>
              )}

              <div className={`flex flex-col gap-1 ${!ep.request ? 'md:col-span-2' : ''}`}>
                <span className="font-label-sm text-label-sm uppercase text-outline">
                  Sample Response
                </span>
                <pre className="p-space-sm rounded-lg bg-surface-container-lowest border border-outline-variant/20 font-code-sm text-code-sm text-on-surface overflow-x-auto max-h-72">
                  {ep.response}
                </pre>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
