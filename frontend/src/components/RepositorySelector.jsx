import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRepositories } from '../context/RepositoryContext';

export default function RepositorySelector({ onSelect }) {
  const { repositories, selectedRepo, setSelectedRepo, loadingRepositories } = useRepositories();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleSelect = (repo) => {
    setSelectedRepo(repo);
    setIsOpen(false);
    if (onSelect) onSelect(repo);
  };

  const currentName = selectedRepo
    ? `${selectedRepo.owner}/${selectedRepo.name}`
    : loadingRepositories
    ? 'Loading repositories...'
    : 'No repository available';

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-space-sm px-space-sm py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high border border-outline-variant/30 transition-colors text-on-surface group"
      >
        {/* GitHub Octocat SVG */}
        <svg
          className="w-4 h-4 fill-on-surface group-hover:fill-primary transition-colors shrink-0"
          viewBox="0 0 24 24"
        >
          <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
        </svg>

        <span className="font-code-sm text-code-sm font-semibold tracking-tight text-on-surface truncate max-w-[200px] sm:max-w-[280px]">
          {currentName}
        </span>

        <span className={`material-symbols-outlined text-[16px] text-outline transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}>
          expand_more
        </span>
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute left-0 mt-1 w-72 rounded-xl bg-surface-container-high border border-outline-variant/40 shadow-2xl p-space-xs z-50 flex flex-col gap-1 max-h-80 overflow-y-auto">
          <div className="px-space-sm py-1 flex items-center justify-between border-b border-surface-container pb-1 mb-1">
            <span className="font-label-sm text-label-sm text-outline uppercase tracking-wider">
              Indexed Repositories
            </span>
            <span className="font-code-sm text-code-sm text-outline">
              {repositories.length} total
            </span>
          </div>

          {repositories.length === 0 ? (
            <div className="p-space-sm text-center">
              <p className="font-body-sm text-body-sm text-outline mb-2">No repositories indexed yet.</p>
              <button
                type="button"
                onClick={() => {
                  setIsOpen(false);
                  navigate('/repositories');
                }}
                className="px-space-sm py-1 bg-primary text-on-primary rounded font-label-sm text-label-sm font-semibold"
              >
                Index a repository
              </button>
            </div>
          ) : (
            repositories.map((repo) => {
              const fullName = `${repo.owner}/${repo.name}`;
              const isSelected = selectedRepo && selectedRepo.github_id === repo.github_id;

              return (
                <button
                  key={repo.github_id}
                  type="button"
                  onClick={() => handleSelect(repo)}
                  className={`flex items-center justify-between w-full px-space-sm py-2 rounded text-left transition-colors ${
                    isSelected
                      ? 'bg-surface-container text-primary font-medium border border-primary/30'
                      : 'hover:bg-surface-container text-on-surface-variant'
                  }`}
                >
                  <div className="flex flex-col truncate pr-2">
                    <span className="font-code-sm text-code-sm text-on-surface font-medium truncate">
                      {fullName}
                    </span>
                    <span className="font-label-sm text-label-sm text-outline">
                      ID #{repo.github_id}
                    </span>
                  </div>
                  {isSelected && (
                    <span className="font-label-sm text-label-sm text-secondary shrink-0 font-medium px-1.5 py-0.5 rounded bg-surface-container-lowest">
                      Active
                    </span>
                  )}
                </button>
              );
            })
          )}

          <div className="pt-1 border-t border-surface-container mt-1">
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                navigate('/repositories');
              }}
              className="flex items-center gap-space-xs w-full px-space-sm py-1.5 text-secondary hover:bg-surface-container rounded font-label-sm text-label-sm transition-colors"
            >
              <span className="material-symbols-outlined text-[14px]">add</span>
              <span>Manage & index more repos</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

