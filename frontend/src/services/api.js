/**
 * WhoKnows API Client Service
 * Centralizes all HTTP communications with the FastAPI backend.
 */

// Use configured Vite environment variable or fall back to /api prefix (dev proxy or reverse proxy)
const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/+$/, '');
const AUTH_BASE_URL = (import.meta.env.VITE_AUTH_BASE_URL || '/api').replace(/\/+$/, '');

/**
 * Handle API responses and standardized error messages
 */
async function handleResponse(response) {
  if (!response.ok) {
    // Rate limit: surface a friendly message regardless of server body
    if (response.status === 429) {
      const error = new Error("You're searching too fast. Please wait a moment and try again.");
      error.status = 429;
      throw error;
    }
    let errorMessage = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      if (data && data.detail) {
        errorMessage = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } else if (data && data.message) {
        errorMessage = data.message;
      }
    } catch {
      // Body is not JSON
      const text = await response.text().catch(() => '');
      if (text) errorMessage = text;
    }
    const error = new Error(errorMessage);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

/**
 * List all indexed repositories
 * GET /repositories/
 * @returns {Promise<Array<{github_id: number, owner: string, name: string}>>}
 */
export async function listRepositories() {
  const url = `${BASE_URL}/repositories/`;
  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
    },
  });
  return handleResponse(response);
}

/**
 * Get details for a specific repository
 * GET /repositories/{repo_id}
 * @param {number} repoId 
 * @returns {Promise<{github_id: number, owner: string, name: string}>}
 */
export async function getRepository(repoId) {
  if (!repoId) throw new Error('Repository ID is required');
  const url = `${BASE_URL}/repositories/${repoId}`;
  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
    },
  });
  return handleResponse(response);
}

/**
 * Enqueue a repository for indexing
 * POST /repositories/index
 * @param {string} fullName - e.g. "redis/redis-py"
 * @returns {Promise<{message: string, job_id: string, repository: string, status: string}>}
 */
export async function indexRepository(fullName) {
  const trimmed = (fullName || '').trim();
  if (!trimmed || !trimmed.includes('/')) {
    throw new Error('Repository must be in OWNER/NAME format (e.g. redis/redis-py)');
  }
  const url = `${BASE_URL}/repositories/index`;
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({ full_name: trimmed }),
  });
  return handleResponse(response);
}

/**
 * Check indexing job status
 * GET /repositories/jobs/{job_id}
 * @param {string} jobId 
 * @returns {Promise<{job_id: string, status: string, result?: any, error?: string}>}
 */
export async function getJobStatus(jobId) {
  if (!jobId) throw new Error('Job ID is required');
  const url = `${BASE_URL}/repositories/jobs/${jobId}`;
  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
    },
  });
  return handleResponse(response);
}

/**
 * Perform semantic search for developers across a repository
 * POST /search/
 * @param {number} repoId
 * @param {string} query
 * @param {number} limit
 * @returns {Promise<{repo_id: number, query: string, results: Array}>}
 */
export async function searchRepository(repoId, query, limit = 100) {
  if (!repoId) throw new Error('A repository must be selected before searching');
  const trimmedQuery = (query || '').trim();
  if (!trimmedQuery) throw new Error('Search query cannot be empty');

  const url = `${BASE_URL}/search/`;
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({
      repo_id: Number(repoId),
      query: trimmedQuery,
      limit: Number(limit) || 100,
    }),
  });
  return handleResponse(response);
}

/**
 * Get the currently authenticated user
 * GET /auth/me
 */
export async function getCurrentUser() {
  const response = await fetch(`${AUTH_BASE_URL}/auth/me`, {
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
    },
  });
  return handleResponse(response);
}

/**
 * Sign out and clear the session cookie
 * POST /auth/logout
 */
export async function logout() {
  const response = await fetch(`${AUTH_BASE_URL}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
    },
  });
  return handleResponse(response);
}

/**
 * URL to start the GitHub OAuth authorization flow
 * GET /auth/github
 */
export function getGitHubLoginUrl() {
  return `${AUTH_BASE_URL}/auth/github`;
}

/**
 * Check backend health and measure connection latency
 * GET /
 * @returns {Promise<{healthy: boolean, latencyMs: number}>}
 */
export async function checkBackendHealth() {
  const start = performance.now();
  try {
    const url = `${BASE_URL}/`;
    const response = await fetch(url, {
      method: 'GET',
      credentials: 'include',
      headers: { 'Accept': 'application/json' },
    });
    const latencyMs = Math.round(performance.now() - start);
    return {
      healthy: response.ok,
      latencyMs,
    };
  } catch {
    return {
      healthy: false,
      latencyMs: 0,
    };
  }
}
