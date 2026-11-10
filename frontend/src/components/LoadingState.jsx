import React from 'react';

export default function LoadingState({ message = "Searching knowledge base and ranking developers..." }) {
  return (
    <div className="w-full flex flex-col gap-space-lg py-space-xl items-center justify-center">
      <div className="p-space-lg rounded-2xl bg-surface-container border border-outline-variant/30 shadow-2xl flex flex-col items-center max-w-md w-full text-center">
        {/* Terminal Radar Icon */}
        <div className="relative mb-space-md">
          <div className="w-16 h-16 rounded-2xl bg-surface-container-high border border-primary/30 flex items-center justify-center text-primary shadow-inner">
            <span className="material-symbols-outlined text-[32px] animate-pulse text-primary">
              psychology
            </span>
          </div>
          <span className="absolute -top-1 -right-1 flex h-4 w-4">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-secondary opacity-75"></span>
            <span className="relative inline-flex rounded-full h-4 w-4 bg-secondary"></span>
          </span>
        </div>

        <h3 className="font-headline-sm text-headline-sm text-on-surface font-semibold mb-1">
          Vector & Graph Ranking in Progress
        </h3>
        <p className="font-body-md text-body-md text-on-surface-variant mb-space-md">
          {message}
        </p>

        {/* Animated code stream skeleton */}
        <div className="w-full bg-surface-container-lowest rounded-lg p-space-sm border border-outline-variant/20 flex flex-col gap-2 font-code-sm text-code-sm text-left">
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-secondary animate-pulse" />
            <span className="text-outline">Semantic retrieval via pgvector embeddings...</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-tertiary animate-pulse delay-100" />
            <span className="text-outline">Building bipartite commit & review graph...</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse delay-200" />
            <span className="text-outline">Computing weighted recency & file coverage...</span>
          </div>
        </div>
      </div>
    </div>
  );
}

