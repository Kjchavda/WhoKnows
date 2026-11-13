import React, { useEffect } from 'react';
import { Link, useSearchParams, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { user, loadingUser, authError, signInWithGitHub } = useAuth();
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const authorizationError = searchParams.get('error');

  // If already signed in, go back to where the user came from
  useEffect(() => {
    if (!loadingUser && user) {
      const from = location.state?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [user, loadingUser, navigate, location.state]);

  return (
    <main className="min-h-screen flex items-center justify-center bg-surface-container-lowest px-space-md py-space-xl">
      <section className="w-full max-w-md rounded-2xl border border-outline-variant/30 bg-surface-container-low p-space-lg md:p-space-xl shadow-xl">
        <Link to="/" className="mb-space-xl inline-flex items-center gap-space-sm">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-outline-variant/30 bg-surface-container-high text-primary">
            <span className="material-symbols-outlined text-[24px]">psychology</span>
          </span>
          <span className="font-headline-sm text-headline-sm font-semibold text-on-surface">
            WhoKnows
          </span>
        </Link>

        <p className="mb-space-xs font-label-sm uppercase tracking-widest text-secondary">
          Developer Knowledge Engine
        </p>
        <h1 className="font-headline-lg text-headline-lg font-semibold tracking-tight text-on-surface">
          Sign in to WhoKnows
        </h1>
        <p className="mt-space-sm font-body-md text-body-md text-on-surface-variant">
          Connect your GitHub account to continue to your codebase workspace.
        </p>

        {authorizationError === 'github_denied' && (
          <p
            role="alert"
            className="mt-space-md rounded-lg border border-error/30 bg-error/10 p-space-sm font-body-sm text-body-sm text-error"
          >
            GitHub sign-in was cancelled. You can try again whenever you’re ready.
          </p>
        )}

        {authError && (
          <p
            role="alert"
            className="mt-space-md rounded-lg border border-error/30 bg-error/10 p-space-sm font-body-sm text-body-sm text-error"
          >
            {authError}
          </p>
        )}

        <button
          type="button"
          onClick={signInWithGitHub}
          className="mt-space-lg flex w-full items-center justify-center gap-space-sm rounded-lg bg-primary px-space-md py-3 font-body-md text-body-md font-semibold text-on-primary transition-colors hover:bg-primary-fixed-dim"
        >
          <svg
            aria-hidden="true"
            className="h-5 w-5 fill-current"
            viewBox="0 0 24 24"
          >
            <path d="M12 .9a11.1 11.1 0 0 0-3.51 21.63c.55.1.76-.24.76-.53v-2.08c-3.1.67-3.76-1.32-3.76-1.32-.5-1.29-1.24-1.63-1.24-1.63-1.01-.69.08-.68.08-.68 1.12.08 1.7 1.15 1.7 1.15.99 1.69 2.6 1.2 3.23.92.1-.72.39-1.2.7-1.48-2.47-.28-5.06-1.24-5.06-5.5 0-1.22.44-2.22 1.15-3-.12-.28-.5-1.42.11-2.96 0 0 .94-.3 3.05 1.15a10.6 10.6 0 0 1 5.55 0c2.11-1.45 3.05-1.15 3.05-1.15.61 1.54.23 2.68.11 2.96.72.78 1.15 1.78 1.15 3 0 4.27-2.6 5.22-5.08 5.5.4.35.75 1.02.75 2.06V22c0 .29.2.64.77.53A11.1 11.1 0 0 0 12 .9Z" />
          </svg>
          <span>Continue with GitHub</span>
        </button>

        {!loadingUser && user && null}

        <p className="mt-space-lg border-t border-surface-container-high pt-space-md font-label-sm text-label-sm text-outline">
          Sign-in uses GitHub OAuth. WhoKnows requests access to your public
          profile only.
        </p>
      </section>
    </main>
  );
}
