import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { useRepositories } from '../context/RepositoryContext';
import { searchRepository } from '../services/api';
import DeveloperCard from '../components/DeveloperCard';
import LoadingState from '../components/LoadingState';
import ErrorMessage from '../components/ErrorMessage';

export default function SearchResults() {
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { selectedRepo, repositories, setSelectedRepo } = useRepositories();

  const queryParam = searchParams.get('query') || '';
  const repoIdParam = searchParams.get('repo_id') || (selectedRepo ? selectedRepo.github_id : null);

  const [queryInput, setQueryInput] = useState(queryParam);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [resultsData, setResultsData] = useState(() => {
    // If passed via router state
    if (location.state && location.state.resultsData) {
      return location.state.resultsData;
    }
    return null;
  });

  const [sortBy, setSortBy] = useState('weighted'); // 'weighted' | 'depth' | 'semantic' | 'breadth'
  const [highConfidenceOnly, setHighConfidenceOnly] = useState(false);
  const [corpusFilter, setCorpusFilter] = useState('all'); // 'all' | 'prs' | 'issues' | 'commits'
  const [searchDuration, setSearchDuration] = useState(128);

  // Sync selectedRepo with repoIdParam if needed
  useEffect(() => {
    if (repoIdParam && repositories.length > 0) {
      const match = repositories.find((r) => String(r.github_id) === String(repoIdParam));
      if (match && (!selectedRepo || selectedRepo.github_id !== match.github_id)) {
        setSelectedRepo(match);
      }
    }
  }, [repoIdParam, repositories, selectedRepo, setSelectedRepo]);

  // Execute search when query or repoId changes
  const executeSearch = useCallback(async (repoId, q) => {
    if (!repoId || !q) return;
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const data = await searchRepository(Number(repoId), q, 100);
      setResultsData(data);
      setSearchDuration(Math.round(performance.now() - start));
    } catch (err) {
      console.error('Search error:', err);
      setError(err.message || 'Search execution failed.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // If not already provided via location.state, run search
    if (repoIdParam && queryParam && (!resultsData || resultsData.query !== queryParam)) {
      executeSearch(repoIdParam, queryParam);
    }
  }, [repoIdParam, queryParam, resultsData, executeSearch]);

  const handleRefineSearch = (e) => {
    e.preventDefault();
    const trimmed = queryInput.trim();
    if (!trimmed) return;
    const repoId = selectedRepo ? selectedRepo.github_id : repoIdParam;
    setSearchParams({ repo_id: repoId, query: trimmed });
    executeSearch(repoId, trimmed);
  };

  // Filter and Sort results
  const developers = useMemo(() => {
    if (!resultsData || !Array.isArray(resultsData.results)) return [];
    let list = [...resultsData.results];

    // High confidence filter
    if (highConfidenceOnly) {
      list = list.filter((dev) => (dev.score || 0) >= 0.70 || (dev.semantic_relevance || 0) >= 0.75);
    }

    // Corpus filter (filter evidence inside or filter developers)
    if (corpusFilter !== 'all') {
      list = list.filter((dev) => {
        if (!dev.evidence || dev.evidence.length === 0) return true;
        if (corpusFilter === 'prs') return dev.evidence.some(e => e.item_kind === 'pr' || e.source === 'item_body');
        if (corpusFilter === 'issues') return dev.evidence.some(e => e.item_kind === 'issue' || e.source.includes('comment'));
        return true;
      });
    }

    // Sort order
    list.sort((a, b) => {
      if (sortBy === 'depth') {
        const aPrs = (a.direct_pr_count || 0) + (a.historical_related_pr_count || 0);
        const bPrs = (b.direct_pr_count || 0) + (b.historical_related_pr_count || 0);
        return bPrs - aPrs;
      }
      if (sortBy === 'semantic') {
        return (b.semantic_relevance || 0) - (a.semantic_relevance || 0);
      }
      if (sortBy === 'breadth') {
        return (b.covered_files || 0) - (a.covered_files || 0);
      }
      // default: weighted score
      return (b.score || 0) - (a.score || 0);
    });

    return list;
  }, [resultsData, sortBy, highConfidenceOnly, corpusFilter]);

  const repoDisplay = selectedRepo
    ? `${selectedRepo.owner}/${selectedRepo.name}`
    : `Repo #${repoIdParam || ''}`;

  return (
    <div className="flex flex-col w-full">
      {/* Top Context & Search Parameter Banner */}
      <div className="relative w-full overflow-hidden bg-surface-container-low border-b border-surface-container px-space-md md:px-space-xl py-space-xl">
        <div className="absolute -top-32 -right-32 w-96 h-96 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-20 w-80 h-80 rounded-full bg-secondary-container/10 blur-3xl pointer-events-none" />

        <div className="relative z-10 max-w-7xl mx-auto flex flex-col gap-space-lg">
          {/* Header Row */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md">
            <div className="flex flex-col gap-space-xs">
              <div className="flex items-center gap-space-xs flex-wrap">
                <button
                  type="button"
                  onClick={() => navigate('/repositories')}
                  className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container-high text-secondary font-label-sm text-label-sm hover:bg-surface-container hover:text-primary transition-colors"
                >
                  <span className="material-symbols-outlined text-[13px]">hub</span>
                  {repoDisplay}
                </button>
                <span className="font-label-sm text-label-sm text-outline">•</span>
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container text-tertiary font-label-sm text-label-sm">
                  <span className="material-symbols-outlined text-[13px]">scatter_plot</span>
                  hybrid_semantic_v2
                </span>
                <span className="font-label-sm text-label-sm text-outline">•</span>
                <span className="font-code-sm text-code-sm text-outline">
                  recency-weighted graph
                </span>
              </div>

              <div className="flex items-baseline gap-space-sm mt-1">
                <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline">
                  Target Query:
                </span>
                <h1 className="font-headline-lg text-headline-lg text-on-surface tracking-tight font-semibold">
                  “{queryParam || 'No query specified'}”
                </h1>
              </div>
            </div>

            {/* Results counter stats */}
            <div className="flex items-center gap-space-sm self-start md:self-auto">
              <div className="flex flex-col text-right">
                <span className="font-code-sm text-code-sm text-secondary-fixed-dim font-medium">
                  Found {developers.length} engineers
                </span>
                <span className="font-label-sm text-label-sm text-outline">
                  {developers.reduce((acc, d) => acc + (d.evidence?.length || 0), 0)} hits • {searchDuration}ms
                </span>
              </div>
              <button
                type="button"
                onClick={() => navigate('/')}
                className="flex items-center justify-center p-2 rounded-lg bg-surface-container text-outline hover:text-on-surface hover:bg-surface-container-high transition-colors"
                title="New Query"
              >
                <span className="material-symbols-outlined text-[18px]">search</span>
              </button>
            </div>
          </div>

          {/* Search refinement bar */}
          <form
            onSubmit={handleRefineSearch}
            className="flex flex-col md:flex-row items-center gap-space-sm bg-surface-container p-1.5 rounded-xl shadow-lg border border-outline-variant/30"
          >
            <div className="flex-1 flex items-center gap-space-sm px-space-md py-1.5 bg-surface-container-lowest rounded-lg w-full">
              <span className="material-symbols-outlined text-outline text-[18px]">search</span>
              <input
                type="text"
                value={queryInput}
                onChange={(e) => setQueryInput(e.target.value)}
                placeholder="Refine search query, technical terms, or components..."
                className="w-full bg-transparent text-on-surface font-body-md text-body-md focus:outline-none placeholder:text-outline"
              />
              <span className="px-1.5 py-0.5 rounded bg-surface-container text-outline font-code-sm text-code-sm">
                refine
              </span>
            </div>

            <div className="flex items-center gap-space-xs w-full md:w-auto justify-end overflow-x-auto">
              <div className="flex items-center gap-1 bg-surface-container-lowest px-space-sm py-1.5 rounded-lg shrink-0 border border-outline-variant/20">
                <span className="material-symbols-outlined text-outline text-[16px]">sort</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="bg-transparent text-on-surface font-label-md text-label-md focus:outline-none cursor-pointer pr-2"
                >
                  <option value="weighted" className="bg-surface-container-high text-on-surface">
                    Overall Expertise (Weighted)
                  </option>
                  <option value="depth" className="bg-surface-container-high text-on-surface">
                    Historical Depth (PRs)
                  </option>
                  <option value="semantic" className="bg-surface-container-high text-on-surface">
                    Semantic Relevance
                  </option>
                  <option value="breadth" className="bg-surface-container-high text-on-surface">
                    File Breadth
                  </option>
                </select>
              </div>

              <button
                type="submit"
                disabled={loading || !queryInput.trim()}
                className="px-space-md py-1.5 rounded-lg bg-primary text-on-primary font-body-sm text-body-sm font-semibold hover:bg-primary-fixed-dim transition-all shadow-sm disabled:opacity-50 shrink-0"
              >
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>
          </form>

          {/* Corpus and Filter chips */}
          <div className="flex flex-wrap items-center justify-between gap-space-md pt-space-xs text-on-surface-variant">
            <div className="flex flex-wrap items-center gap-space-xs">
              <span className="font-label-sm text-label-sm text-outline mr-1">CORPUS:</span>
              <button
                type="button"
                onClick={() => setCorpusFilter('all')}
                className={`px-2.5 py-1 rounded font-label-sm text-label-sm transition-colors ${
                  corpusFilter === 'all'
                    ? 'bg-primary text-on-primary font-medium'
                    : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
                }`}
              >
                All Sources
              </button>
              <button
                type="button"
                onClick={() => setCorpusFilter('prs')}
                className={`px-2.5 py-1 rounded font-label-sm text-label-sm transition-colors ${
                  corpusFilter === 'prs'
                    ? 'bg-primary text-on-primary font-medium'
                    : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
                }`}
              >
                Pull Requests
              </button>
              <button
                type="button"
                onClick={() => setCorpusFilter('issues')}
                className={`px-2.5 py-1 rounded font-label-sm text-label-sm transition-colors ${
                  corpusFilter === 'issues'
                    ? 'bg-primary text-on-primary font-medium'
                    : 'bg-surface-container text-on-surface-variant hover:text-on-surface'
                }`}
              >
                Issues & Discussions
              </button>
            </div>

            <div className="flex items-center gap-space-md">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={highConfidenceOnly}
                  onChange={(e) => setHighConfidenceOnly(e.target.checked)}
                  className="accent-primary rounded h-3.5 w-3.5 bg-surface-container-lowest cursor-pointer"
                />
                <span className="font-label-sm text-label-sm text-on-surface">
                  High confidence only (&gt;0.70)
                </span>
              </label>
              <div className="h-3 w-px bg-surface-variant hidden sm:block" />
              <span className="font-code-sm text-code-sm text-outline hidden sm:inline">
                Decay Halflife: 180d
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Results Container */}
      <div className="max-w-7xl w-full mx-auto px-space-md md:px-space-xl py-space-xl flex flex-col gap-space-lg">
        {error && (
          <ErrorMessage
            title="Search Error"
            message={error}
            onRetry={() => executeSearch(repoIdParam, queryParam)}
          />
        )}

        {loading && <LoadingState message={`Retrieving semantic vectors and ranking developers for "${queryParam}"...`} />}

        {!loading && !error && (
          <>
            <div className="flex items-center justify-between pb-space-xs border-b border-surface-container">
              <div className="flex items-center gap-space-sm">
                <span className="font-headline-sm text-headline-sm text-on-surface font-medium">
                  Ranked Domain Specialists
                </span>
                <span className="font-label-sm text-label-sm px-2 py-0.5 rounded-full bg-surface-container-high text-primary font-semibold font-mono">
                  {developers.length} identified
                </span>
              </div>
              <div className="flex items-center gap-space-xs font-code-sm text-code-sm text-outline">
                <span className="inline-block w-2 h-2 rounded-full bg-secondary" />
                <span>Vector + Git Blame Cosine Similarity</span>
              </div>
            </div>

            {developers.length === 0 ? (
              <div className="p-space-xl rounded-2xl bg-surface-container text-center flex flex-col items-center gap-space-sm border border-outline-variant/30 my-space-md">
                <div className="w-12 h-12 rounded-xl bg-surface-container-high flex items-center justify-center text-outline">
                  <span className="material-symbols-outlined text-[28px]">search_off</span>
                </div>
                <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                  No specialists found
                </h3>
                <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
                  No developers scored above the current threshold for this query. Try broader keywords or adjust your filter parameters.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setHighConfidenceOnly(false);
                    setCorpusFilter('all');
                  }}
                  className="mt-2 px-space-md py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-bright text-primary font-body-sm text-body-sm transition-colors"
                >
                  Reset Filters
                </button>
              </div>
            ) : (
              <div className="flex flex-col gap-space-lg">
                {developers.map((dev, idx) => (
                  <DeveloperCard
                    key={dev.developer_id || idx}
                    developer={dev}
                    rank={idx + 1}
                    repoName={repoDisplay}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

