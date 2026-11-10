import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useRepositories } from '../context/RepositoryContext';

export default function Sidebar({ mobileOpen, setMobileOpen }) {
  const { selectedRepo, backendHealth } = useRepositories();
  const location = useLocation();

  const navItems = [
    {
      to: '/',
      label: 'Search',
      icon: 'search',
      shortcut: '⌘K',
      exact: true,
    },
    {
      to: '/repositories',
      label: 'Repositories',
      icon: 'folder',
    },
    {
      to: '/jobs',
      label: 'Indexing Jobs',
      icon: 'terminal',
    },
    {
      to: '/docs',
      label: 'Documentation & API',
      icon: 'menu_book',
    },
  ];

  return (
    <>
      {/* Mobile backdrop overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm transition-opacity"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={`fixed left-0 top-0 h-screen w-64 bg-surface-container-low border-r border-outline-variant/20 z-50 flex flex-col justify-between select-none transition-transform duration-200 ease-in-out md:translate-x-0 ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="flex flex-col">
          {/* Logo & Brand Header */}
          <div className="h-14 px-space-md flex items-center justify-between border-b border-surface-container">
            <NavLink
              to="/"
              className="flex items-center gap-space-sm group"
              onClick={() => setMobileOpen(false)}
            >
              <div className="w-8 h-8 rounded-lg bg-surface-container-high border border-outline-variant/30 flex items-center justify-center text-primary group-hover:border-primary/50 transition-colors shadow-sm">
                <span className="material-symbols-outlined text-[20px] text-primary">psychology</span>
              </div>
              <span className="font-headline-sm text-headline-sm text-on-surface font-semibold tracking-tight">
                WhoKnows
              </span>
            </NavLink>
            <span className="font-label-sm text-label-sm px-space-xs py-0.5 bg-surface-container-high text-secondary rounded font-mono">
              ENGINE v1.0
            </span>
          </div>

          {/* Active Repository Widget in Sidebar */}
          <div className="px-space-md py-space-sm">
            <NavLink
              to="/repositories"
              onClick={() => setMobileOpen(false)}
              className="p-space-sm bg-surface-container-lowest border border-outline-variant/20 hover:border-outline-variant/40 rounded-xl flex items-center justify-between group transition-all"
              title="Click to view or switch repositories"
            >
              <div className="flex items-center gap-space-sm overflow-hidden">
                <span className="h-2 w-2 rounded-full bg-secondary-container animate-pulse shrink-0"></span>
                <div className="flex flex-col truncate">
                  <span className="font-code-sm text-code-sm text-on-surface font-medium truncate group-hover:text-primary transition-colors">
                    {selectedRepo ? `${selectedRepo.owner}/${selectedRepo.name}` : 'No repo selected'}
                  </span>
                  <span className="font-label-sm text-label-sm text-outline truncate">
                    {selectedRepo ? `ID: #${selectedRepo.github_id} • Active` : 'Select a repository'}
                  </span>
                </div>
              </div>
              <span className="material-symbols-outlined text-[18px] text-outline group-hover:text-on-surface transition-colors">
                unfold_more
              </span>
            </NavLink>
          </div>

          {/* Primary Navigation Menu */}
          <nav className="flex flex-col gap-space-xs px-space-md py-space-sm">
            {navItems.map((item) => {
              const isActive = item.exact
                ? location.pathname === '/' || location.pathname === '/search'
                : location.pathname.startsWith(item.to);

              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center justify-between px-space-md py-space-sm rounded-lg transition-colors text-body-md ${
                    isActive
                      ? 'bg-surface-container-high text-primary font-medium shadow-sm'
                      : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                  }`}
                >
                  <div className="flex items-center gap-space-md">
                    <span className={`material-symbols-outlined text-[18px] ${isActive ? 'text-primary' : 'text-outline'}`}>
                      {item.icon}
                    </span>
                    <span className="font-body-md">{item.label}</span>
                  </div>
                  {item.shortcut && (
                    <kbd className="font-code-sm text-code-sm px-space-xs py-0.5 bg-surface-container-lowest text-outline rounded border border-outline-variant/20">
                      {item.shortcut}
                    </kbd>
                  )}
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Bottom Telemetry & Status Strip */}
        <div className="flex flex-col gap-space-sm p-space-md bg-surface-container-low border-t border-surface-container">
          {/* Backend Health telemetry */}
          <div className="flex items-center justify-between px-space-sm py-space-xs bg-surface-container-lowest rounded-lg border border-outline-variant/20">
            <div className="flex items-center gap-space-sm">
              <span
                className={`h-1.5 w-1.5 rounded-full shrink-0 ${
                  backendHealth.healthy ? 'bg-secondary animate-pulse' : 'bg-error'
                }`}
              ></span>
              <span className="font-label-sm text-label-sm text-outline">FastAPI Backend</span>
            </div>
            <span
              className={`font-code-sm text-code-sm ${
                backendHealth.healthy ? 'text-secondary-fixed-dim' : 'text-error'
              }`}
            >
              {backendHealth.healthy ? `${backendHealth.latencyMs}ms` : 'Offline'}
            </span>
          </div>

          {/* User Profile info */}
          <div className="flex items-center justify-between p-space-sm bg-surface-container rounded-xl border border-outline-variant/20">
            <div className="flex items-center gap-space-sm min-w-0">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-primary/30 to-secondary/30 border border-primary/40 flex items-center justify-center text-primary font-bold text-xs shrink-0">
                WK
              </div>
              <div className="flex flex-col min-w-0">
                <span className="font-body-sm text-body-sm text-on-surface font-medium truncate">
                  developer
                </span>
                <span className="font-label-sm text-label-sm text-outline truncate">
                  Engineering Team
                </span>
              </div>
            </div>
            <NavLink
              to="/docs"
              className="text-outline hover:text-on-surface p-space-xs transition-colors shrink-0"
              title="System Settings & API Docs"
            >
              <span className="material-symbols-outlined text-[18px]">settings</span>
            </NavLink>
          </div>
        </div>
      </aside>
    </>
  );
}

