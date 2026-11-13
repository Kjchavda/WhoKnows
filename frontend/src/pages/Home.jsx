import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRepositories } from '../context/RepositoryContext';
import RepositorySelector from '../components/RepositorySelector';
import SearchBar from '../components/SearchBar';
import DeveloperCard from '../components/DeveloperCard';
import LoadingState from '../components/LoadingState';
import ErrorMessage from '../components/ErrorMessage';
import { searchRepository } from '../services/api';

export default function Home() {
  const { selectedRepo, repositories, loadingRepositories, backendHealth, setIsNewJobModalOpen } = useRepositories();
  const [query, setQuery] = useState('Who understands connection pooling and socket timeout exceptions?');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchResults, setSearchResults] = useState(null);
  const navigate = useNavigate();

  const suggestedQueries = [
    'Who understands connection pooling?',
    'Who has worked on authentication & token refresh?',
    'Who knows the Redis replication implementation?',
    'Who has experience with memory management & buffer leaks?',
    'Who authored async cluster failover logic?',
  ];

  const handleSearch = async (searchQuery) => {
    const q = (searchQuery || query).trim();
    if (!q) {
      setError('Please enter a search query');
      return;
    }
    if (!selectedRepo) {
      setError('Please select a repository first');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await searchRepository(selectedRepo.github_id, q, 100);
      setSearchResults(response);
      // Navigate to dedicated search results page to give full workbench experience
      navigate(`/search?repo_id=${selectedRepo.github_id}&query=${encodeURIComponent(q)}`, {
        state: { resultsData: response },
      });
    } catch (err) {
      console.error('Search error:', err);
      setError(err.message || 'Search failed. Please verify your query and repository.');
    } finally {
      setLoading(false);
    }
  };

  const handlePromptClick = (prompt) => {
    setQuery(prompt);
    handleSearch(prompt);
  };

  const repoFullName = selectedRepo ? `${selectedRepo.owner}/${selectedRepo.name}` : '';

  return (
    <div className="relative w-full max-w-7xl mx-auto px-margin md:px-margin-desktop py-space-xl flex flex-col gap-space-2xl">
      {/* Ambient background glow */}
      <div className="absolute top-12 left-1/2 -translate-x-1/2 w-[720px] h-[340px] bg-primary/5 blur-[120px] rounded-full pointer-events-none -z-10" />

      {/* 1. Hero & Strategic Narrative */}
      <header className="flex flex-col items-start gap-space-md pt-space-md">
        <div className="inline-flex items-center gap-space-xs px-space-sm py-1 rounded bg-surface-container text-tertiary border border-outline-variant/20">
          <span className="material-symbols-outlined text-[14px]">psychology</span>
          <span className="font-label-sm text-label-sm uppercase tracking-wider font-semibold">
            Developer knowledge search
          </span>
        </div>

        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-space-lg w-full">
          <div className="max-w-3xl space-y-space-xs">
            <h1 className="font-headline-xl text-headline-xl text-on-surface font-semibold tracking-tight">
              Find the people who know your codebase.
            </h1>
            <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl">
              Search a repository's issues, pull requests, comments and reviews to find who has worked on a topic.
            </p>
          </div>
        </div>
      </header>

      {/* 2. Central Search Experience */}
      <section className="flex flex-col gap-space-sm w-full">
        {/* Active Repository Bar */}
        <div className="flex flex-wrap items-center justify-between gap-space-sm bg-surface-container-low p-space-xs px-space-md rounded-xl border border-outline-variant/20">
          <div className="flex items-center gap-space-md flex-wrap">
            <RepositorySelector onSelect={() => setError(null)} />

            <span className="font-code-sm text-code-sm text-outline hidden sm:inline">
              {selectedRepo ? (
                <>Repository selected: <span className="text-secondary font-medium">{selectedRepo.owner}/{selectedRepo.name}</span></>
              ) : (
                <span className="text-amber-400">Please select an indexed repository</span>
              )}
            </span>
          </div>

          <div className="flex items-center gap-1.5 px-space-sm py-0.5 rounded bg-surface-container text-outline font-label-sm text-label-sm border border-outline-variant/15">
            <span className="material-symbols-outlined text-[14px]">tune</span>
            <span className="text-on-surface-variant">Limit: 100</span>
          </div>
        </div>

        {repositories.length === 0 && !loadingRepositories && (
          <div className="rounded-2xl border border-dashed border-outline-variant/50 bg-surface-container-low p-space-lg text-center flex flex-col items-center gap-space-sm">
            <div className="w-12 h-12 rounded-xl bg-surface-container-high flex items-center justify-center text-primary">
              <span className="material-symbols-outlined text-[26px]">folder_open</span>
            </div>
            <h2 className="font-headline-sm text-headline-sm text-on-surface font-semibold">
              No repositories yet.
            </h2>
            <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
              Index a public repository that you own to start searching.
            </p>
            <button
              type="button"
              onClick={() => setIsNewJobModalOpen(true)}
              className="px-space-md py-2 rounded-lg bg-primary text-on-primary font-body-sm text-body-sm font-semibold shadow-sm"
            >
              Add repository
            </button>
            <p className="font-label-sm text-label-sm text-outline">
              Organization repositories can only be indexed by an administrator.
            </p>
          </div>
        )}

        {error && <ErrorMessage title="Search Validation" message={error} />}

        {!loadingRepositories && repositories.length > 0 && (
          <SearchBar
            query={query}
            setQuery={setQuery}
            onSearch={handleSearch}
            loading={loading}
          />
        )}

        {/* Suggested Queries Prompt Matrix */}
        <div className="flex flex-col gap-space-xs pt-space-xs">
          <div className="flex items-center gap-space-xs text-outline">
            <span className="material-symbols-outlined text-[15px]">tips_and_updates</span>
            <span className="font-label-sm text-label-sm uppercase tracking-wider font-semibold">
              Suggested Knowledge Probes
            </span>
          </div>

          <div className="flex flex-wrap gap-space-xs">
            {suggestedQueries.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handlePromptClick(prompt)}
                className="px-space-sm py-1 rounded-lg bg-surface-container-low hover:bg-surface-container hover:text-on-surface text-on-surface-variant font-code-sm text-code-sm border border-outline-variant/20 transition-all flex items-center gap-space-xs group"
              >
                <span className="text-tertiary">#</span>
                <span>{prompt}</span>
                <span className="material-symbols-outlined text-[14px] opacity-0 group-hover:opacity-100 transition-opacity text-outline">
                  north_east
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Loading state indicator */}
      {loading && <LoadingState message={`Retrieving semantic vectors and ranking authors for ${repoFullName}...`} />}

      {/* Quick live preview if available */}
      {searchResults && searchResults.results && searchResults.results.length > 0 && !loading && (
        <section className="flex flex-col gap-space-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-space-sm">
              <span className="h-2 w-2 rounded-full bg-secondary-container" />
              <span className="font-headline-sm text-headline-sm text-on-surface font-semibold">
                Ranked Subject Matter Experts for this Query
              </span>
              <span className="font-code-sm text-code-sm px-space-xs py-0.5 rounded bg-surface-container text-outline">
                {searchResults.results.length} engineers identified
              </span>
            </div>

            <button
              type="button"
              onClick={() => navigate(`/search?repo_id=${selectedRepo.github_id}&query=${encodeURIComponent(query)}`)}
              className="font-label-sm text-label-sm text-secondary hover:underline flex items-center gap-1"
            >
              <span>Full Workbench View</span>
              <span className="material-symbols-outlined text-[14px]">arrow_forward</span>
            </button>
          </div>

          <div className="flex flex-col gap-space-md">
            {searchResults.results.slice(0, 3).map((dev, idx) => (
              <DeveloperCard
                key={dev.developer_id || idx}
                developer={dev}
                rank={idx + 1}
                repoName={repoFullName}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

