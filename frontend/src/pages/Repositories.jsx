import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRepositories } from '../context/RepositoryContext';
import { indexRepository } from '../services/api';
import JobCard from '../components/JobCard';
import ErrorMessage from '../components/ErrorMessage';

export default function Repositories() {
  const {
    repositories,
    loadingRepositories,
    repositoriesError,
    selectedRepo,
    setSelectedRepo,
    jobs,
    addJob,
    refreshRepositories,
  } = useRepositories();

  const [fullName, setFullName] = useState('');
  const [branch, setBranch] = useState('main');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const navigate = useNavigate();

  const handleIndexSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);
    setFeedback(null);

    const trimmed = fullName.trim();
    const parts = trimmed.split('/');
    if (parts.length !== 2 || !parts[0] || !parts[1]) {
      setFormError('Repository must be in OWNER/NAME format (e.g. redis/redis-py or pallets/flask)');
      return;
    }

    setSubmitting(true);
    try {
      const response = await indexRepository(trimmed);
      addJob({
        job_id: response.job_id,
        repository: response.repository || trimmed,
        status: response.status || 'queued',
      });
      setFeedback({
        type: 'success',
        jobId: response.job_id,
        message: `Indexing job queued for ${trimmed}. Worker will start processing.`,
      });
      setFullName('');
    } catch (err) {
      console.error('Index submit error:', err);
      setFormError(err.message || 'Failed to submit indexing job to FastAPI.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSelectAndSearch = (repo) => {
    setSelectedRepo(repo);
    navigate('/');
  };

  const activeJobsCount = jobs.filter(
    (j) => j.status === 'queued' || j.status === 'started' || j.status === 'deferred'
  ).length;

  return (
    <div className="flex flex-col w-full">
      <div className="p-space-lg md:p-space-xl flex flex-col gap-space-xl max-w-7xl mx-auto w-full">
        {/* Header Title & Metric Strip */}
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-space-md">
          <div className="flex flex-col gap-space-xs">
            <div className="flex items-center gap-space-sm text-outline">
              <span className="font-label-sm text-label-sm uppercase tracking-widest text-secondary font-mono">
                Registry v1.4
              </span>
              <span>/</span>
              <span className="font-code-sm text-code-sm text-outline">FastAPI Client Engine</span>
            </div>
            <h1 className="font-headline-lg text-headline-lg text-on-surface font-semibold tracking-tight">
              Repositories & Codebase Indexing
            </h1>
            <p className="font-body-md text-body-md text-on-surface-variant max-w-3xl">
              Manage the GitHub repositories WhoKnows has indexed.
            </p>
          </div>

          {/* Global Metric Strip */}
          <div className="flex items-center flex-wrap gap-space-sm bg-surface-container-low px-space-md py-space-sm rounded-xl border border-outline-variant/20">
            <div className="flex items-center gap-space-xs">
              <span className="font-code-md text-code-md font-semibold text-secondary">
                {repositories.length}
              </span>
              <span className="font-body-sm text-body-sm text-outline">Repositories Indexed</span>
            </div>
            <span className="text-outline-variant font-code-sm">•</span>
            <div className="flex items-center gap-space-xs">
              <span className="relative flex h-2 w-2">
                {activeJobsCount > 0 && (
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary-container opacity-75" />
                )}
                <span className={`relative inline-flex rounded-full h-2 w-2 ${activeJobsCount > 0 ? 'bg-secondary' : 'bg-outline'}`} />
              </span>
              <span className="font-code-md text-code-md font-semibold text-on-surface">
                {activeJobsCount}
              </span>
              <span className="font-body-sm text-body-sm text-outline">
                {activeJobsCount === 1 ? 'Job in Progress' : 'Jobs in Progress'}
              </span>
            </div>
            <span className="text-outline-variant font-code-sm">•</span>
            <div className="flex items-center gap-space-xs">
              <span className="font-code-md text-code-md font-semibold text-tertiary">
                {jobs.length}
              </span>
              <span className="font-body-sm text-body-sm text-outline">Total Jobs Tracked</span>
            </div>
          </div>
        </div>

        {/* Index New Repository Form Card (POST /repositories/index) */}
        <div className="bg-surface-container p-space-lg rounded-xl shadow-md border border-outline-variant/30 flex flex-col gap-space-md">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-xs">
            <div className="flex items-center gap-space-sm">
              <span className="material-symbols-outlined text-primary text-[20px]">hub</span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface font-medium">
                Index New Repository
              </h2>
            </div>
            <div className="flex items-center gap-space-xs font-label-sm text-label-sm text-outline">
              <span className="bg-surface-container-high px-space-xs py-0.5 rounded text-tertiary font-mono">
                POST
              </span>
              <span className="font-code-sm text-code-sm">/repositories/index</span>
            </div>
          </div>

          {formError && <ErrorMessage title="Submission Error" message={formError} />}

          {feedback && (
            <div className="p-space-sm rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-body-sm text-body-sm flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px]">check_circle</span>
                <span>{feedback.message}</span>
                <span className="font-code-sm text-code-sm text-secondary">
                  (ID: #{feedback.jobId.slice(0, 8)})
                </span>
              </div>
              <button
                type="button"
                onClick={() => setFeedback(null)}
                className="text-emerald-400 hover:text-emerald-200"
              >
                <span className="material-symbols-outlined text-[16px]">close</span>
              </button>
            </div>
          )}

          <form onSubmit={handleIndexSubmit} className="flex flex-col gap-space-md">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-space-md items-start">
              {/* GitHub Repo Target */}
              <div className="md:col-span-7 flex flex-col gap-space-xs">
                <label className="font-label-sm text-label-sm text-outline uppercase tracking-wider" htmlFor="repo_full_name">
                  GitHub Full Name <span className="text-error">*</span>
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-space-md text-outline text-[18px]">
                    bookmark
                  </span>
                  <input
                    id="repo_full_name"
                    name="full_name"
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. pallets/flask, encode/httpx, redis/redis-py"
                    required
                    className="w-full bg-surface-container-lowest text-on-surface font-code-md text-code-md pl-10 pr-space-md py-space-sm rounded-lg border border-outline-variant/30 focus:border-primary focus:outline-none transition-colors placeholder:text-outline-variant"
                  />
                </div>
              </div>

              {/* Branch */}
              <div className="md:col-span-3 flex flex-col gap-space-xs">
                <label className="font-label-sm text-label-sm text-outline uppercase tracking-wider" htmlFor="repo_branch">
                  Default Branch <span className="text-outline font-normal">(optional)</span>
                </label>
                <div className="relative flex items-center">
                  <span className="material-symbols-outlined absolute left-space-md text-outline text-[18px]">
                    account_tree
                  </span>
                  <input
                    id="repo_branch"
                    name="branch"
                    type="text"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    placeholder="main"
                    className="w-full bg-surface-container-lowest text-on-surface font-code-md text-code-md pl-10 pr-space-md py-space-sm rounded-lg border border-outline-variant/30 focus:border-primary focus:outline-none transition-colors placeholder:text-outline-variant"
                  />
                </div>
              </div>

              {/* Submit Button */}
              <div className="md:col-span-2 flex flex-col justify-end pt-space-xs md:pt-5">
                <button
                  type="submit"
                  disabled={submitting || !fullName.trim()}
                  className="w-full h-[38px] flex items-center justify-center gap-space-xs bg-primary text-on-primary font-body-sm text-body-sm font-semibold rounded-lg hover:bg-primary-fixed-dim transition-all shadow-sm active:translate-y-0.5 disabled:opacity-50"
                >
                  {submitting ? (
                    <>
                      <span className="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>
                      <span>Queueing...</span>
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[18px]">fork_right</span>
                      <span>Index Repository</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center gap-space-xs text-outline font-body-sm text-body-sm pt-space-xs border-t border-surface-container-high/60">
              <span className="material-symbols-outlined text-secondary text-[16px]">info</span>
              <span>
                Submits an asynchronous indexing job to FastAPI backend (<code>POST /repositories/index</code>). Retrieval and graph compilation begin immediately in background.
              </span>
            </div>
          </form>
        </div>

        {/* Active & Recent Indexing Jobs Grid */}
        <div className="flex flex-col gap-space-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-sm">
              <span className="material-symbols-outlined text-secondary text-[20px]">swap_calls</span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface font-medium">
                Active & Recent Indexing Jobs
              </h2>
              <span className="font-label-sm text-label-sm bg-surface-container-high text-on-surface-variant px-space-xs py-0.5 rounded font-mono">
                {jobs.length} tracked
              </span>
            </div>

            <div className="flex items-center gap-space-xs font-code-sm text-code-sm text-outline">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-secondary" />
              <span>GET /repositories/jobs/{'{job_id}'}</span>
            </div>
          </div>

          {jobs.length === 0 ? (
            <div className="p-space-lg rounded-xl bg-surface-container-low text-center border border-outline-variant/20 text-outline font-body-md text-body-md">
              No indexing jobs queued yet. Submit a repository above to trigger the worker.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-space-md">
              {jobs.map((job) => (
                <JobCard key={job.job_id} job={job} />
              ))}
            </div>
          )}
        </div>

        {/* Connected Repositories Section */}
        <div className="flex flex-col gap-space-md pt-space-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-sm">
              <span className="material-symbols-outlined text-primary text-[20px]">folder</span>
              <h2 className="font-headline-sm text-headline-sm text-on-surface font-medium">
                Connected Repositories ({repositories.length})
              </h2>
            </div>
            <button
              type="button"
              onClick={refreshRepositories}
              className="px-space-sm py-1 rounded-lg bg-surface-container hover:bg-surface-container-high text-outline hover:text-on-surface font-label-sm text-label-sm flex items-center gap-1 transition-colors"
            >
              <span className="material-symbols-outlined text-[14px]">refresh</span>
              <span>Refresh List</span>
            </button>
          </div>

          {repositoriesError && (
            <ErrorMessage title="Repository Fetch Error" message={repositoriesError} onRetry={refreshRepositories} />
          )}

          {loadingRepositories ? (
            <div className="p-space-lg rounded-xl bg-surface-container-low text-center text-outline font-body-sm text-body-sm border border-outline-variant/20">
              Loading repositories from FastAPI database...
            </div>
          ) : repositories.length === 0 ? (
            <div className="p-space-xl rounded-xl bg-surface-container-low text-center border border-outline-variant/20">
              <p className="font-headline-sm text-headline-sm text-on-surface font-semibold mb-1">
                No repositories registered
              </p>
              <p className="font-body-md text-body-md text-outline max-w-md mx-auto mb-4">
                Enter a repository like <code className="font-code-sm text-secondary">redis/redis-py</code> above to begin indexing.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-space-md">
              {repositories.map((repo) => {
                const fullName = `${repo.owner}/${repo.name}`;
                const isSelected = selectedRepo && selectedRepo.github_id === repo.github_id;

                return (
                  <div
                    key={repo.github_id}
                    className={`p-space-md rounded-xl bg-surface-container-low border transition-all flex flex-col justify-between gap-space-md ${
                      isSelected
                        ? 'border-primary/50 shadow-lg bg-surface-container/60'
                        : 'border-outline-variant/20 hover:border-outline-variant/40 hover:bg-surface-container'
                    }`}
                  >
                    <div className="flex flex-col gap-space-xs">
                      <div className="flex items-center justify-between">
                        <span className="font-code-sm text-code-sm text-outline">
                          Repo ID: #{repo.github_id}
                        </span>
                        {isSelected && (
                          <span className="font-label-sm text-label-sm px-1.5 py-0.5 rounded bg-primary text-on-primary font-semibold">
                            Active in Search
                          </span>
                        )}
                      </div>

                      <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold truncate mt-1">
                        {fullName}
                      </h3>
                      <p className="font-body-sm text-body-sm text-outline">
                        Owner: <span className="text-on-surface-variant font-medium">{repo.owner}</span>
                      </p>
                    </div>

                    <div className="flex items-center gap-space-xs pt-space-xs border-t border-surface-container">
                      <button
                        type="button"
                        onClick={() => handleSelectAndSearch(repo)}
                        className="flex-1 py-1.5 px-space-sm rounded-lg bg-primary text-on-primary font-body-sm text-body-sm font-semibold hover:bg-primary-fixed-dim transition-colors flex items-center justify-center gap-1"
                      >
                        <span className="material-symbols-outlined text-[16px]">search</span>
                        <span>Search</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => navigate(`/repositories/${repo.github_id}`)}
                        className="py-1.5 px-space-sm rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface font-body-sm text-body-sm transition-colors border border-outline-variant/20"
                      >
                        Details
                      </button>

                      <a
                        href={`https://github.com/${fullName}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-outline hover:text-on-surface transition-colors border border-outline-variant/20"
                        title="Open on GitHub"
                      >
                        <span className="material-symbols-outlined text-[18px]">open_in_new</span>
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

