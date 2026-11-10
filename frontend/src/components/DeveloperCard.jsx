import React, { useState } from 'react';
import EvidenceList from './EvidenceList';

export default function DeveloperCard({ developer, rank = 1, repoName = '' }) {
  const [showEvidence, setShowEvidence] = useState(true);

  if (!developer) return null;

  const login = developer.developer_login || `dev_${developer.developer_id || 'unknown'}`;
  const githubProfileUrl = developer.developer_login
    ? `https://github.com/${developer.developer_login}`
    : null;
  const avatarUrl = developer.developer_login
    ? `https://github.com/${developer.developer_login}.png?size=96`
    : null;

  // Formatting metrics from backend
  const score = typeof developer.score === 'number' ? developer.score : 0;
  const scorePercent = Math.min(100, Math.max(0, Math.round(score * 100)));
  const semanticRelevance = typeof developer.semantic_relevance === 'number'
    ? Math.round(developer.semantic_relevance * 100)
    : 0;
  const directPrs = developer.direct_pr_count || 0;
  const historicalPrs = developer.historical_related_pr_count || 0;
  const coveredFiles = developer.covered_files || 0;
  const totalFiles = developer.total_files || 0;
  const coveragePercent = typeof developer.coverage === 'number'
    ? Math.round(developer.coverage * 100)
    : 0;
  const evidence = Array.isArray(developer.evidence) ? developer.evidence : [];

  // Generate deterministic role label
  const getRoleLabel = () => {
    if (rank === 1) return 'Primary Subsystem Author';
    if (rank === 2) return 'Core Contributor';
    if (coveragePercent > 50) return 'Architectural Specialist';
    return 'Domain Contributor';
  };

  return (
    <article className="relative flex flex-col rounded-xl bg-surface-container-low border border-outline-variant/30 p-space-md md:p-space-lg shadow-md hover:bg-surface-container/70 transition-all duration-200">
      {/* Top Header Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-md pb-space-md border-b border-surface-container">
        {/* Left: Avatar, Rank, Login, Role */}
        <div className="flex items-start gap-space-md min-w-0">
          <div className="relative shrink-0">
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt={login}
                onError={(e) => {
                  e.target.onerror = null;
                  e.target.style.display = 'none';
                }}
                className={`w-12 h-12 rounded-full object-cover ring-2 ${
                  rank === 1
                    ? 'ring-primary/60'
                    : rank === 2
                    ? 'ring-secondary/50'
                    : 'ring-outline-variant/40'
                }`}
              />
            ) : (
              <div className="w-12 h-12 rounded-full bg-surface-container-high border border-outline-variant/30 flex items-center justify-center font-bold text-on-surface text-sm">
                {login.slice(0, 2).toUpperCase()}
              </div>
            )}
            <span
              className={`absolute -bottom-1 -right-1 px-1.5 py-0.2 rounded font-label-sm text-label-sm font-bold shadow-sm ${
                rank === 1
                  ? 'bg-primary text-on-primary'
                  : rank === 2
                  ? 'bg-secondary text-on-secondary'
                  : 'bg-surface-container-highest text-on-surface'
              }`}
            >
              #{rank}
            </span>
          </div>

          <div className="flex flex-col min-w-0">
            <div className="flex items-center gap-space-xs flex-wrap">
              <span className="font-headline-md text-headline-md text-on-surface font-semibold truncate">
                {login}
              </span>
              {githubProfileUrl && (
                <a
                  href={githubProfileUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-code-sm text-code-sm text-secondary hover:underline flex items-center gap-0.5"
                  title="View GitHub profile"
                >
                  <span>@{login}</span>
                  <span className="material-symbols-outlined text-[13px]">open_in_new</span>
                </a>
              )}
              <span className="px-2 py-0.5 rounded bg-surface-container text-outline font-label-sm text-label-sm">
                {getRoleLabel()}
              </span>
            </div>

            <div className="flex items-center gap-space-sm mt-0.5 flex-wrap text-outline font-label-sm text-label-sm">
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-[13px] text-tertiary">commit</span>
                {directPrs + historicalPrs} related PRs
              </span>
              <span>•</span>
              <span>{developer.semantic_contribution_count || evidence.length} matched evidence nodes</span>
              {repoName && (
                <>
                  <span>•</span>
                  <span className="text-secondary-fixed-dim">{repoName}</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Right: Expertise Score Gauge */}
        <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-center bg-surface-container-lowest sm:bg-transparent px-space-md sm:px-0 py-space-xs sm:py-0 rounded-lg shrink-0 border border-outline-variant/15 sm:border-0">
          <div className="flex items-baseline gap-1">
            <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider">Expertise</span>
            <span className="font-headline-lg text-headline-lg text-primary font-bold">
              {score.toFixed(2)}
            </span>
            <span className="font-code-sm text-code-sm text-outline">/ 1.0</span>
          </div>
          <div className="w-32 h-1.5 bg-surface-container-high rounded-full overflow-hidden mt-1">
            <div
              className="h-full bg-gradient-to-r from-tertiary via-primary to-secondary rounded-full transition-all duration-500"
              style={{ width: `${scorePercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* Metrics Grid (4 tiles matching Stitch design) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-space-xs my-space-sm">
        {/* Semantic Relevance */}
        <div className="flex flex-col p-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/15">
          <span className="font-label-sm text-label-sm text-outline">Semantic Relevance</span>
          <span className="font-headline-sm text-headline-sm text-secondary font-semibold mt-0.5">
            {semanticRelevance}%
          </span>
          <span className="font-code-sm text-code-sm text-outline-variant truncate">
            raw: {developer.semantic_relevance ? developer.semantic_relevance.toFixed(3) : '0.000'}
          </span>
        </div>

        {/* Subsystem Depth */}
        <div className="flex flex-col p-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/15">
          <span className="font-label-sm text-label-sm text-outline">Subsystem Depth</span>
          <span className="font-headline-sm text-headline-sm text-on-surface font-semibold mt-0.5">
            {directPrs} direct PRs
          </span>
          <span className="font-code-sm text-code-sm text-outline-variant truncate">
            {historicalPrs} historical PRs
          </span>
        </div>

        {/* Code Breadth */}
        <div className="flex flex-col p-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/15">
          <span className="font-label-sm text-label-sm text-outline">Code Breadth</span>
          <span className="font-headline-sm text-headline-sm text-on-surface font-semibold mt-0.5">
            {coveredFiles} files
          </span>
          <span className="font-code-sm text-code-sm text-outline-variant truncate">
            {coveragePercent}% graph coverage
          </span>
        </div>

        {/* Historical Score */}
        <div className="flex flex-col p-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/15">
          <span className="font-label-sm text-label-sm text-outline">Historical Depth</span>
          <span className="font-headline-sm text-headline-sm text-tertiary-fixed-dim font-semibold mt-0.5">
            {typeof developer.historical_depth === 'number'
              ? (developer.historical_depth * 100).toFixed(0) + '%'
              : 'Indexed'}
          </span>
          <span className="font-code-sm text-code-sm text-outline-variant truncate">
            {totalFiles} total touched files
          </span>
        </div>
      </div>

      {/* Synthesis Attribution Strip */}
      <div className="p-space-md rounded-lg bg-surface-container border border-outline-variant/20 mb-space-sm">
        <div className="flex items-center gap-space-xs mb-1">
          <span className="material-symbols-outlined text-[16px] text-primary">auto_awesome</span>
          <span className="font-label-sm text-label-sm text-primary uppercase font-semibold">
            Synthesis & Causal Attribution
          </span>
        </div>
        <p className="font-body-md text-body-md text-on-surface leading-relaxed">
          Identified as a ranked contributor with {directPrs} directly matching pull requests and touch points across{' '}
          {coveredFiles} relevant codebase files. Demonstrates strong semantic correlation ({semanticRelevance}%) with historical involvement in the queried domain.
        </p>
      </div>

      {/* Evidence Section */}
      {evidence.length > 0 && (
        <div className="flex flex-col gap-space-xs pt-space-xs">
          <div className="flex items-center justify-between pb-1">
            <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider">
              Top Traceable Evidence ({evidence.length} records)
            </span>
            <button
              type="button"
              onClick={() => setShowEvidence(!showEvidence)}
              className="font-label-sm text-label-sm text-secondary hover:underline flex items-center gap-1"
            >
              <span>{showEvidence ? 'Collapse Evidence' : 'Expand Evidence'}</span>
              <span className={`material-symbols-outlined text-[14px] transition-transform ${showEvidence ? 'rotate-180' : ''}`}>
                expand_more
              </span>
            </button>
          </div>

          {showEvidence && <EvidenceList evidence={evidence} />}
        </div>
      )}
    </article>
  );
}

