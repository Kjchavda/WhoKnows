import React from 'react';

export default function JobCard({ job }) {
  if (!job) return null;

  const status = (job.status || 'queued').toLowerCase();

  const getStatusConfig = () => {
    switch (status) {
      case 'started':
        return {
          label: 'Started',
          pillClass: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
          dotClass: 'bg-amber-400 animate-ping',
          icon: 'refresh',
          iconClass: 'text-amber-400 animate-spin',
          description: 'Parsing commits, pull requests, and blame graphs...',
        };
      case 'finished':
        return {
          label: 'Finished',
          pillClass: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
          dotClass: 'bg-emerald-400',
          icon: 'check_circle',
          iconClass: 'text-emerald-400',
          description: 'Indexed into vector embeddings and implementation graph.',
        };
      case 'failed':
        return {
          label: 'Failed',
          pillClass: 'bg-rose-500/15 text-rose-300 border-rose-500/30',
          dotClass: 'bg-rose-400',
          icon: 'error',
          iconClass: 'text-rose-400',
          description: job.error || 'Indexing failed or timed out.',
        };
      case 'queued':
      default:
        return {
          label: 'Queued',
          pillClass: 'bg-surface-container-high text-on-surface-variant border-outline-variant/30',
          dotClass: 'bg-secondary animate-pulse',
          icon: 'hourglass_top',
          iconClass: 'text-outline',
          description: 'Waiting for Redis worker allocation...',
        };
    }
  };

  const config = getStatusConfig();
  const formatTime = (isoString) => {
    if (!isoString) return 'Just now';
    try {
      const diffSecs = Math.floor((new Date() - new Date(isoString)) / 1000);
      if (diffSecs < 60) return `${diffSecs}s ago`;
      if (diffSecs < 3600) return `${Math.floor(diffSecs / 60)}m ago`;
      return `${Math.floor(diffSecs / 3600)}h ago`;
    } catch {
      return 'Recently';
    }
  };

  return (
    <div className="bg-surface-container-low border border-outline-variant/20 p-space-md rounded-xl flex flex-col justify-between gap-space-md transition-all hover:bg-surface-container hover:border-outline-variant/40">
      <div className="flex flex-col gap-space-sm">
        <div className="flex items-center justify-between">
          <span className="font-code-sm text-code-sm text-secondary font-medium truncate max-w-[150px]">
            #{job.job_id ? job.job_id.slice(0, 8) : 'job'}
          </span>

          <span
            className={`flex items-center gap-1.5 font-label-sm text-label-sm px-space-xs py-0.5 rounded font-medium border ${config.pillClass}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${config.dotClass}`} />
            {config.label}
          </span>
        </div>

        <div>
          <span className="font-code-md text-code-md text-on-surface font-semibold break-all">
            {job.repository || 'Unknown repository'}
          </span>
          <p className="font-body-sm text-body-sm text-on-surface-variant mt-1 line-clamp-2">
            {config.description}
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between font-label-sm text-label-sm text-outline pt-space-xs bg-surface-container-lowest/50 px-space-xs py-1 rounded border border-outline-variant/10">
        <span>{formatTime(job.createdAt)}</span>
        <span className={`material-symbols-outlined text-[14px] ${config.iconClass}`}>
          {config.icon}
        </span>
      </div>
    </div>
  );
}

