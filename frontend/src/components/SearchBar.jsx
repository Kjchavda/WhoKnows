import React, { useRef, useEffect } from 'react';

export default function SearchBar({
  query,
  setQuery,
  onSearch,
  loading,
  placeholder = "Ask about a topic, component, or technical concept...",
  compact = false,
}) {
  const inputRef = useRef(null);

  // Global ⌘K keyboard shortcut
  useEffect(() => {
    function handleKeyDown(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSearch) {
      onSearch(query);
    }
  };

  if (compact) {
    return (
      <form onSubmit={handleSubmit} className="flex-1 flex items-center gap-space-sm px-space-md py-1.5 bg-surface-container-lowest border border-outline-variant/30 rounded-lg w-full focus-within:border-primary transition-colors">
        <span className="material-symbols-outlined text-outline text-[18px]">search</span>
        <label htmlFor="search-compact" className="sr-only">Search repository</label>
        <input
          id="search-compact"
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          aria-label="Search repository"
          className="w-full bg-transparent text-on-surface font-body-md text-body-md focus:outline-none placeholder:text-outline"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          aria-label="Submit search"
          className="px-2 py-1 rounded bg-primary text-on-primary font-code-sm text-code-sm font-semibold hover:bg-primary-fixed-dim disabled:opacity-50 transition-all shrink-0"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>
    );
  }

  return (
    <div className="relative bg-surface-container border border-outline-variant/30 rounded-xl shadow-xl p-space-md md:p-space-lg flex flex-col gap-space-md transition-all duration-200 focus-within:ring-2 focus-within:ring-primary/60 focus-within:bg-surface-container-high">
      <form onSubmit={handleSubmit} className="flex flex-col gap-space-md">
        <div className="flex items-start gap-space-md">
          <div className="p-space-xs rounded-lg bg-surface-container-lowest border border-outline-variant/20 text-primary mt-1 shrink-0">
            <span className="material-symbols-outlined text-[24px]">terminal</span>
          </div>

          <div className="flex-1 flex flex-col gap-space-xs min-w-0">
            <div className="flex items-center justify-between">
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-outline font-semibold">
                Semantic Query Parser
              </span>
              <div className="flex items-center gap-space-xs">
                <kbd className="font-code-sm text-code-sm px-space-xs py-0.5 rounded bg-surface-container-lowest text-on-surface-variant border border-outline-variant/20">
                  ⌘K
                </kbd>
                <span className="font-label-sm text-label-sm text-outline">or</span>
                <kbd className="font-code-sm text-code-sm px-space-xs py-0.5 rounded bg-surface-container-lowest text-on-surface-variant border border-outline-variant/20">
                  Enter ↵
                </kbd>
              </div>
            </div>

            <label htmlFor="semantic-query" className="sr-only">Search query</label>
            <input
              id="semantic-query"
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={placeholder}
              aria-label="Search repository for expertise"
              className="w-full bg-transparent text-on-surface font-headline-md text-headline-md placeholder:text-outline focus:outline-none tracking-tight py-1"
            />
          </div>
        </div>

        {/* Parameters & Submit Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-sm pt-space-xs border-t border-surface-container-high/60">
          <div className="flex flex-wrap items-center gap-space-xs" aria-hidden="true">
            <span className="font-label-sm text-label-sm px-space-sm py-1 rounded bg-surface-container-lowest text-on-surface-variant border border-outline-variant/15">
              Search across repository evidence
            </span>
          </div>

          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="flex items-center justify-center gap-space-sm px-space-xl py-2 rounded-lg bg-primary text-on-primary font-headline-sm text-headline-sm font-semibold hover:bg-primary-fixed-dim transition-all active:scale-[0.99] disabled:opacity-50 disabled:cursor-not-allowed shadow-md shrink-0"
          >
            {loading ? (
              <>
                <span className="material-symbols-outlined text-[18px] animate-spin">progress_activity</span>
                <span>Searching Engine...</span>
              </>
            ) : (
              <>
                <span>Search Expertise</span>
                <span className="material-symbols-outlined text-[18px]">keyboard_return</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

