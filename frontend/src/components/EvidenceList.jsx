import React, { useState } from 'react';

export default function EvidenceList({ evidence = [] }) {
  const [expandedIndex, setExpandedIndex] = useState(null);

  if (!evidence || evidence.length === 0) {
    return (
      <div className="p-space-sm bg-surface-container-lowest rounded-lg text-outline font-body-sm text-body-sm">
        No specific evidence records attached for this developer.
      </div>
    );
  }

  const toggleExpand = (index) => {
    setExpandedIndex(expandedIndex === index ? null : index);
  };

  const getSourceBadge = (item) => {
    const kind = (item.item_kind || '').toUpperCase();
    const num = item.item_number ? `#${item.item_number}` : '';
    const source = item.source || '';

    if (item.item_kind === 'pr') {
      return {
        label: `PR ${num}`,
        classes: 'bg-surface-container text-tertiary border-tertiary/20',
      };
    }
    if (item.item_kind === 'issue') {
      return {
        label: `ISSUE ${num}`,
        classes: 'bg-surface-container text-secondary border-secondary/20',
      };
    }
    if (source.includes('comment')) {
      return {
        label: `COMMENT ${num}`,
        classes: 'bg-surface-container text-primary border-primary/20',
      };
    }
    if (source.includes('review')) {
      return {
        label: `REVIEW ${num}`,
        classes: 'bg-surface-container text-secondary-fixed border-secondary/20',
      };
    }
    return {
      label: source.toUpperCase() || 'NODE',
      classes: 'bg-surface-container text-outline border-outline/20',
    };
  };

  return (
    <div className="flex flex-col gap-space-xs">
      {evidence.map((item, idx) => {
        const badge = getSourceBadge(item);
        const similarityPct = typeof item.similarity === 'number'
          ? Math.round(item.similarity * 100)
          : null;
        const isExpanded = expandedIndex === idx;

        return (
          <div
            key={idx}
            className="flex flex-col rounded-lg bg-surface-container-lowest border border-outline-variant/15 overflow-hidden transition-colors"
          >
            {/* Header row */}
            <div
              onClick={() => toggleExpand(idx)}
              className="flex flex-col sm:flex-row sm:items-center justify-between p-space-sm gap-space-xs hover:bg-surface-container-high/60 transition-colors cursor-pointer select-none"
            >
              <div className="flex items-center gap-space-sm min-w-0">
                <span
                  className={`inline-flex items-center px-1.5 py-0.5 rounded font-code-sm text-code-sm shrink-0 border ${badge.classes}`}
                >
                  {badge.label}
                </span>

                <span className="font-body-sm text-body-sm text-on-surface truncate font-medium">
                  {item.item_title || (item.text ? item.text.slice(0, 80) : 'Contribution')}
                </span>
              </div>

              <div className="flex items-center gap-space-sm text-outline font-label-sm text-label-sm shrink-0 self-end sm:self-auto">
                {similarityPct !== null && (
                  <span className="font-code-sm text-secondary bg-surface-container px-1.5 py-0.5 rounded border border-secondary/20">
                    {similarityPct}% match
                  </span>
                )}

                {item.github_url && (
                  <a
                    href={item.github_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="text-secondary hover:underline flex items-center gap-0.5 p-1"
                    title="View on GitHub"
                  >
                    <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                  </a>
                )}

                <span className="material-symbols-outlined text-[16px] text-outline">
                  {isExpanded ? 'expand_less' : 'expand_more'}
                </span>
              </div>
            </div>

            {/* Expandable Evidence Details & Text Chunk */}
            {isExpanded && item.text && (
              <div className="p-space-sm bg-surface-container/60 border-t border-outline-variant/15 font-code-sm text-code-sm text-on-surface-variant flex flex-col gap-space-xs">
                <div className="flex items-center justify-between text-outline font-label-sm text-label-sm pb-1 border-b border-surface-container-highest">
                  <span>Context Text Chunk</span>
                  {item.github_url && (
                    <a
                      href={item.github_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-secondary hover:underline flex items-center gap-1"
                    >
                      <span>Open thread on GitHub</span>
                      <span className="material-symbols-outlined text-[12px]">north_east</span>
                    </a>
                  )}
                </div>
                <pre className="whitespace-pre-wrap font-code-sm text-code-sm leading-relaxed text-on-surface bg-surface-container-lowest p-space-sm rounded border border-outline-variant/20 max-h-60 overflow-y-auto">
                  {item.text}
                </pre>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

