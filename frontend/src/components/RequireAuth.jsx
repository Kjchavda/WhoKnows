import React from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LoadingState from './LoadingState';

export default function RequireAuth() {
  const { user, loadingUser, authError, refreshUser } = useAuth();
  const location = useLocation();

  if (loadingUser) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface-container-lowest">
        <LoadingState message="Checking your session..." />
      </div>
    );
  }

  // Server is unreachable (not a 401 — that just means logged out)
  if (authError) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-surface-container-lowest px-4 text-center">
        <div className="w-14 h-14 rounded-2xl bg-surface-container flex items-center justify-center text-error border border-error/30">
          <span className="material-symbols-outlined text-[32px]">cloud_off</span>
        </div>
        <div className="flex flex-col gap-2 max-w-sm">
          <h1 className="font-headline-md text-headline-md text-on-surface font-semibold">
            Can't reach the server
          </h1>
          <p className="font-body-md text-body-md text-on-surface-variant">
            {authError}
          </p>
        </div>
        <button
          type="button"
          onClick={refreshUser}
          className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-primary text-on-primary font-body-md text-body-md font-semibold hover:bg-primary-fixed-dim transition-colors shadow-md"
        >
          <span className="material-symbols-outlined text-[18px]">refresh</span>
          <span>Retry</span>
        </button>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
