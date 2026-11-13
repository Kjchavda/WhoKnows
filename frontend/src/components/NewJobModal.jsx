import React, { useState } from 'react';
import { useRepositories } from '../context/RepositoryContext';
import { indexRepository } from '../services/api';
import ErrorMessage from './ErrorMessage';

export default function NewJobModal() {
  const { isNewJobModalOpen, setIsNewJobModalOpen, addJob } = useRepositories();
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  if (!isNewJobModalOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const trimmed = fullName.trim();
    if (!trimmed || !trimmed.includes('/')) {
      setError('Repository must be in OWNER/NAME format (e.g. redis/redis-py)');
      return;
    }

    setLoading(true);
    try {
      const response = await indexRepository(trimmed);
      addJob({
        job_id: response.job_id,
        repository: response.repository || trimmed,
        status: response.status || 'queued',
      });
      setSuccess(`Job #${response.job_id.slice(0, 8)} queued successfully!`);
      setFullName('');
      setTimeout(() => {
        setIsNewJobModalOpen(false);
        setSuccess(null);
      }, 1500);
    } catch (err) {
      setError(err.message || 'Failed to submit indexing job');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-space-md bg-black/70 backdrop-blur-sm animate-fade-in">
      <div
        className="w-full max-w-lg rounded-2xl bg-surface-container border border-outline-variant/40 shadow-2xl p-space-lg flex flex-col gap-space-md"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-space-xs border-b border-surface-container-high">
          <div className="flex items-center gap-space-sm">
            <div className="p-2 rounded-lg bg-surface-container-lowest text-primary">
              <span className="material-symbols-outlined text-[20px]">hub</span>
            </div>
            <div>
              <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                New Repository Indexing Job
              </h3>
              <span className="font-label-sm text-label-sm text-outline font-mono">
                POST /repositories/index
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setIsNewJobModalOpen(false)}
            className="p-1 text-outline hover:text-on-surface rounded-lg hover:bg-surface-container-high transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {error && <ErrorMessage message={error} />}

        {success && (
          <div className="p-space-sm rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-body-sm text-body-sm flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">check_circle</span>
            <span>{success}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-space-md">
          <div className="flex flex-col gap-space-xs">
            <label className="font-label-sm text-label-sm uppercase tracking-wider text-outline" htmlFor="modal-repo-name">
              GitHub Full Name <span className="text-error">*</span>
            </label>
            <div className="relative flex items-center">
              <span className="material-symbols-outlined absolute left-space-md text-outline text-[18px]">
                bookmark
              </span>
              <input
                id="modal-repo-name"
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. pallets/flask, encode/httpx, redis/redis-py"
                required
                className="w-full bg-surface-container-lowest text-on-surface font-code-md text-code-md pl-10 pr-space-md py-space-sm rounded-lg border border-outline-variant/30 focus:border-primary focus:outline-none transition-colors placeholder:text-outline-variant"
              />
            </div>
          </div>

          <div className="flex items-center gap-space-xs text-outline font-body-sm text-body-sm bg-surface-container-lowest/40 p-space-sm rounded-lg border border-outline-variant/15">
            <span className="material-symbols-outlined text-secondary text-[16px] shrink-0">info</span>
            <span>
              You can index public repositories owned by your own GitHub account.
            </span>
          </div>

          <div className="flex items-center gap-space-xs text-outline font-body-sm text-body-sm bg-surface-container-lowest/40 p-space-sm rounded-lg border border-outline-variant/15">
            <span className="material-symbols-outlined text-secondary text-[16px] shrink-0">info</span>
            <span>
              The backend will fetch the repository's issues, pull requests, comments, reviews and changed files, embed the text, and build a developer-file graph.
            </span>
          </div>

          <div className="flex items-center justify-end gap-space-sm pt-space-xs border-t border-surface-container-high">
            <button
              type="button"
              onClick={() => setIsNewJobModalOpen(false)}
              className="px-space-md py-2 rounded-lg bg-surface-container-high hover:bg-surface-bright text-on-surface font-body-sm text-body-sm transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !fullName.trim()}
              className="px-space-lg py-2 rounded-lg bg-primary text-on-primary font-body-sm text-body-sm font-semibold hover:bg-primary-fixed-dim transition-all shadow-sm disabled:opacity-50 flex items-center gap-1.5"
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined text-[16px] animate-spin">progress_activity</span>
                  <span>Queueing Job...</span>
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[16px]">fork_right</span>
                  <span>Queue Indexing Job</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

