import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useRepositories } from '../context/RepositoryContext';

export default function Header({ setMobileOpen }) {
  const { selectedRepo, setIsNewJobModalOpen } = useRepositories();
  const navigate = useNavigate();
  const location = useLocation();

  const getPageTitle = () => {
    if (location.pathname === '/' || location.pathname === '/search') {
      return 'Developer Search';
    }
    if (location.pathname.startsWith('/repositories')) {
      return 'Repository Registry';
    }
    if (location.pathname.startsWith('/jobs')) {
      return 'Indexing Jobs';
    }
    if (location.pathname.startsWith('/docs')) {
      return 'Documentation & API';
    }
    return 'Knowledge Engine';
  };

  return (
    <header className="fixed top-0 left-0 md:left-64 right-0 h-14 bg-surface/85 backdrop-blur-xl z-40 px-space-md md:px-space-lg flex items-center justify-between border-b border-surface-container shadow-[0_1px_8px_rgba(0,0,0,0.2)]">
      {/* Left: Mobile hamburger & Repository Breadcrumbs */}
      <div className="flex items-center gap-space-sm min-w-0">
        <button
          type="button"
          onClick={() => setMobileOpen(true)}
          className="md:hidden p-1.5 text-outline hover:text-on-surface rounded-lg bg-surface-container transition-colors"
          aria-label="Open navigation menu"
        >
          <span className="material-symbols-outlined text-[20px]">menu</span>
        </button>

        <div className="flex items-center gap-space-xs font-code-sm text-code-sm truncate">
          {selectedRepo ? (
            <>
              <button
                type="button"
                onClick={() => navigate(`/repositories/${selectedRepo.github_id}`)}
                className="text-outline hover:text-on-surface transition-colors truncate"
              >
                {selectedRepo.owner}
              </button>
              <span className="text-outline">/</span>
              <button
                type="button"
                onClick={() => navigate(`/repositories/${selectedRepo.github_id}`)}
                className="text-on-surface font-medium hover:text-primary transition-colors truncate"
              >
                {selectedRepo.name}
              </button>
            </>
          ) : (
            <span className="text-outline">No repo</span>
          )}
          <span className="font-body-sm text-body-sm text-outline mx-space-xs hidden sm:inline">&gt;</span>
          <span className="font-body-sm text-body-sm text-secondary hidden sm:inline truncate">
            {getPageTitle()}
          </span>
        </div>
      </div>

      {/* Right: Quick Command trigger & Primary Action */}
      <div className="flex items-center gap-space-sm md:gap-space-md">
        {/* Quick Search Trigger / Shortcut */}
        <button
          type="button"
          onClick={() => navigate('/')}
          className="hidden lg:flex items-center gap-space-xs px-space-md py-1.5 bg-surface-container-lowest border border-outline-variant/20 rounded-lg cursor-pointer hover:bg-surface-container-high transition-colors text-left"
        >
          <span className="material-symbols-outlined text-outline text-[16px]">search</span>
          <span className="font-body-sm text-body-sm text-outline">Search repo commits, PRs, docs...</span>
          <kbd className="font-code-sm text-code-sm ml-space-md px-space-xs py-0.5 bg-surface-container text-on-surface-variant rounded border border-outline-variant/20">
            ⌘K
          </kbd>
        </button>

        {/* Sync Status Badge */}
        <div className="hidden sm:flex items-center gap-space-xs px-space-sm py-1 bg-surface-container-lowest border border-outline-variant/20 rounded-lg">
          <span className="material-symbols-outlined text-secondary text-[16px]">sync</span>
          <span className="font-label-sm text-label-sm text-on-surface-variant">
            Synced with GitHub API
          </span>
        </div>

        {/* New Indexing Job Button */}
        <button
          type="button"
          onClick={() => setIsNewJobModalOpen(true)}
          className="flex items-center gap-space-xs px-space-md py-1.5 bg-primary text-on-primary rounded-lg font-body-sm text-body-sm font-semibold hover:bg-primary-fixed-dim transition-all shadow-sm active:scale-95 shrink-0"
        >
          <span className="material-symbols-outlined text-[16px]">add</span>
          <span className="hidden sm:inline">New Indexing Job</span>
          <span className="sm:hidden">Index</span>
        </button>
      </div>
    </header>
  );
}

