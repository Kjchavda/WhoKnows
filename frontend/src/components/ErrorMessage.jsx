import React from 'react';

export default function ErrorMessage({ title = "Error", message, onRetry }) {
  if (!message) return null;

  return (
    <div className="w-full p-space-md rounded-xl bg-error-container/20 border border-error/30 text-on-surface flex items-start gap-space-md shadow-lg my-space-sm">
      <div className="p-2 rounded-lg bg-error/20 text-error shrink-0">
        <span className="material-symbols-outlined text-[20px]">error</span>
      </div>

      <div className="flex-1 flex flex-col gap-1 min-w-0">
        <span className="font-headline-sm text-headline-sm font-semibold text-error">
          {title}
        </span>
        <p className="font-body-md text-body-md text-on-surface-variant break-words">
          {message}
        </p>

        {onRetry && (
          <div className="pt-2">
            <button
              type="button"
              onClick={onRetry}
              className="px-space-md py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-bright text-on-surface font-body-sm text-body-sm font-medium border border-outline-variant/30 transition-colors inline-flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[16px]">refresh</span>
              <span>Try Again</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

