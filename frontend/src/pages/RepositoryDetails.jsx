import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useRepositories } from '../context/RepositoryContext';
import { getRepository, getRepositoryStats, indexRepository } from '../services/api';
import ErrorMessage from '../components/ErrorMessage';
import LoadingState from '../components/LoadingState';

export default function RepositoryDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { setSelectedRepo, addJob } = useRepositories();

  const [repo, setRepo] = useState(null);
  const [repoStats, setRepoStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reindexing, setReindexing] = useState(false);
  const [reindexAlert, setReindexAlert] = useState(null);
  const [quickQuery, setQuickQuery] = useState('');

  const fetchRepo = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getRepository(Number(id));
      setRepo(data);
    } catch (err) {
      console.error('Fetch repo error:', err);
      setError(err.message || `Repository #${id} not found.`);
    } finally {
      setLoading(false);
    }
  }, [id]);

  const fetchStats = useCallback(async () => {
    if (!id) return;
    setStatsLoading(true);
    try {
      const data = await getRepositoryStats(Number(id));
      setRepoStats(data);
    } catch (err) {
      console.warn('Repository stats unavailable:', err);
      setRepoStats(null);
    } finally {
      setStatsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchRepo();
    fetchStats();
  }, [fetchRepo, fetchStats]);

  const handleSearchCodebase = () => {
    if (repo) {
      setSelectedRepo(repo);
      if (quickQuery.trim()) {
        navigate(`/search?repo_id=${repo.github_id}&query=${encodeURIComponent(quickQuery.trim())}`);
      } else {
        navigate('/');
      }
    }
  };

  const handleReindex = async () => {
    if (!repo) return;
    setReindexing(true);
    setReindexAlert(null);
    const fullName = `${repo.owner}/${repo.name}`;
    try {
      const response = await indexRepository(fullName);
      addJob({
        job_id: response.job_id,
        repository: fullName,
        status: response.status || 'queued',
      });
      setReindexAlert({
        jobId: response.job_id,
        message: `Job #${response.job_id.slice(0, 8)} queued. Repository graph and vector representations are refreshing.`,
      });
    } catch (err) {
      setError(err.message || 'Failed to trigger re-index');
    } finally {
      setReindexing(false);
    }
  };

  if (loading) {
    return (
      <div className="p-space-xl max-w-7xl mx-auto w-full">
        <LoadingState message={`Fetching repository #${id} metadata from database...`} />
      </div>
    );
  }

  if (error || !repo) {
    return (
      <div className="p-space-xl max-w-7xl mx-auto w-full">
        <ErrorMessage
          title="Repository Details"
          message={error || 'Repository details unavailable'}
          onRetry={fetchRepo}
        />
        <button
          type="button"
          onClick={() => navigate('/repositories')}
          className="mt-4 px-space-md py-2 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface font-body-sm text-body-sm flex items-center gap-1"
        >
          <span className="material-symbols-outlined text-[16px]">arrow_back</span>
          <span>Back to Repositories</span>
        </button>
      </div>
    );
  }

  const fullName = `${repo.owner}/${repo.name}`;
  const githubUrl = `https://github.com/${fullName}`;
  const statCards = repoStats
    ? [
        { label: 'Issues', value: repoStats.issues ?? 0 },
        { label: 'Pull requests', value: repoStats.pull_requests ?? 0 },
        { label: 'Developers', value: repoStats.developers ?? 0 },
        { label: 'Chunks', value: repoStats.chunks ?? 0 },
        {
          label: 'Latest activity indexed',
          value: repoStats.last_indexed_at
            ? new Date(repoStats.last_indexed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
            : 'n/a',
        },
      ]
    : [];

  return (
    <div className="p-space-lg md:p-space-xl flex flex-col gap-space-xl max-w-7xl mx-auto w-full">
      <div className="flex flex-wrap items-center justify-between gap-space-md">
        <div className="flex items-center gap-space-xs font-label-sm text-label-sm text-outline">
          <button
            type="button"
            onClick={() => navigate('/repositories')}
            className="hover:text-primary transition-colors flex items-center gap-1"
          >
            <span className="material-symbols-outlined text-[14px]">arrow_back</span>
            <span>Repositories</span>
          </button>
          <span className="text-surface-variant">/</span>
          <span className="text-outline">{repo.owner}</span>
          <span className="text-surface-variant">/</span>
          <span className="text-secondary font-code-sm text-code-sm font-medium">{repo.name}</span>
        </div>

        <div className="flex items-center gap-space-xs text-outline font-label-sm text-label-sm">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-secondary-container" />
          <span>
            Repo ID: <span className="text-on-surface font-code-sm text-code-sm">{repo.github_id}</span>
          </span>
        </div>
      </div>

      <div className="bg-surface-container-low rounded-xl p-space-lg shadow-sm border border-outline-variant/20 flex flex-col lg:flex-row lg:items-center justify-between gap-space-lg">
        <div className="flex items-start gap-space-md min-w-0">
          <div className="w-12 h-12 rounded-xl bg-surface-container border border-outline-variant/30 flex items-center justify-center text-primary shrink-0 shadow-sm">
            <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
          </div>

          <div className="flex flex-col gap-space-xs min-w-0">
            <div className="flex items-center gap-space-sm flex-wrap">
              <h1 className="font-headline-lg text-headline-lg text-on-surface font-semibold tracking-tight">
                {fullName}
              </h1>
              <a
                href={githubUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-outline hover:text-on-surface transition-colors p-0.5 inline-flex items-center"
                title="Open in GitHub"
              >
                <span className="material-symbols-outlined text-[18px]">open_in_new</span>
              </a>
            </div>

            <div className="flex flex-wrap items-center gap-space-sm">
              <span className="inline-flex items-center gap-1.5 px-space-sm py-0.5 rounded bg-surface-container text-on-surface font-label-sm text-label-sm border border-outline-variant/15">
                <span className="w-2 h-2 rounded-full bg-secondary" />
                Repository
              </span>
              <span className="inline-flex items-center gap-1 px-space-sm py-0.5 rounded bg-surface-container font-label-sm text-label-sm text-outline border border-outline-variant/15">
                <span className="material-symbols-outlined text-[13px]">lock_open</span>
                Public repository
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-space-sm shrink-0 flex-wrap">
          <button
            type="button"
            onClick={handleSearchCodebase}
            className="flex items-center gap-space-xs px-space-lg py-2 bg-primary text-on-primary rounded-lg font-headline-sm text-headline-sm font-semibold hover:bg-primary-fixed-dim transition-all shadow-sm active:scale-95"
          >
            <span className="material-symbols-outlined text-[18px]">search</span>
            <span>Search This Codebase</span>
            <kbd className="ml-space-xs px-1.5 py-0.5 bg-on-primary/15 text-on-primary rounded font-code-sm text-code-sm">
              ↵
            </kbd>
          </button>

          <button
            type="button"
            onClick={handleReindex}
            disabled={reindexing}
            className="flex items-center gap-space-xs px-space-md py-2 bg-surface-container text-on-surface rounded-lg font-body-md text-body-md hover:bg-surface-container-high transition-colors active:scale-95 border border-outline-variant/20 disabled:opacity-50"
          >
            <span className={`material-symbols-outlined text-[18px] text-secondary ${reindexing ? 'animate-spin' : ''}`}>
              refresh
            </span>
            <span>{reindexing ? 'Triggering...' : 'Trigger Re-Index'}</span>
          </button>
        </div>
      </div>

      {reindexAlert && (
        <div className="bg-surface-container-high p-space-md rounded-xl border border-secondary/30 flex items-center justify-between shadow-sm animate-fade-in">
          <div className="flex items-center gap-space-sm">
            <span className="material-symbols-outlined text-secondary text-[20px] animate-spin">
              progress_activity
            </span>
            <div className="flex flex-col">
              <span className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                POST /repositories/index requested
              </span>
              <span className="font-body-sm text-body-sm text-outline">
                {reindexAlert.message}
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setReindexAlert(null)}
            className="text-outline hover:text-on-surface p-1"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      )}

      <div className="bg-surface-container p-space-lg rounded-xl border border-outline-variant/30 flex flex-col gap-space-md shadow-md">
        <div className="flex items-center gap-space-xs">
          <span className="material-symbols-outlined text-primary text-[20px]">terminal</span>
          <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
            Search Expertise in {fullName}
          </h2>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-space-sm">
          <div className="flex-1 flex items-center gap-space-sm px-space-md py-2 bg-surface-container-lowest rounded-lg border border-outline-variant/30 w-full">
            <span className="material-symbols-outlined text-outline text-[18px]">search</span>
            <input
              aria-label="Query to search within this repository"
              type="text"
              value={quickQuery}
              onChange={(e) => setQuickQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearchCodebase()}
              placeholder="e.g. connection pooling, memory leaks, cluster failover..."
              className="w-full bg-transparent text-on-surface font-body-md text-body-md focus:outline-none placeholder:text-outline"
            />
          </div>

          <button
            type="button"
            onClick={handleSearchCodebase}
            disabled={!quickQuery.trim()}
            className="w-full sm:w-auto px-space-xl py-2 rounded-lg bg-primary text-on-primary font-headline-sm text-headline-sm font-semibold hover:bg-primary-fixed-dim transition-all shadow-sm disabled:opacity-50"
          >
            Execute Search
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-space-lg">
        {statsLoading && (
          <div className="md:col-span-2 lg:col-span-3">
            <LoadingState message="Loading repository metrics..." />
          </div>
        )}

        {!statsLoading && statCards.map((stat) => (
          <div key={stat.label} className="bg-surface-container-low rounded-xl p-space-lg flex flex-col justify-between gap-space-sm shadow-sm border border-outline-variant/20">
            <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">{stat.label}</span>
            <span className="font-headline-lg text-headline-lg text-on-surface font-semibold break-words">{stat.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

