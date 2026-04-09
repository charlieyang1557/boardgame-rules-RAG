import { useState } from "react";
import type { ChunkInfo } from "../types";

interface SourceCardProps {
  chunk: ChunkInfo;
}

function formatChunkLabel(chunkId: string): string {
  const match = chunkId.match(/^(\w+?)_p(\d+)/);
  if (!match) return chunkId;
  const game = match[1].charAt(0).toUpperCase() + match[1].slice(1);
  const page = match[2];
  return `${game} — Page ${page}`;
}

function BookIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none"
         className="text-parchment-400 dark:text-parchment-500 shrink-0 mt-px">
      <path d="M2 2.5A1.5 1.5 0 013.5 1H6v12H3.5A1.5 1.5 0 012 11.5v-9z"
            stroke="currentColor" strokeWidth="1" />
      <path d="M6 1h4.5A1.5 1.5 0 0112 2.5v9a1.5 1.5 0 01-1.5 1.5H6V1z"
            stroke="currentColor" strokeWidth="1" />
      <line x1="6" y1="1" x2="6" y2="13" stroke="currentColor" strokeWidth="1" />
    </svg>
  );
}

export function SourceCard({ chunk }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const isTruncated = chunk.text.length >= 297;

  // Score-based accent: higher score = more saturated accent
  const scorePercent = Math.round(chunk.score * 100);

  return (
    <button
      onClick={() => setExpanded(!expanded)}
      className="group w-full text-left rounded-lg text-sm transition-all duration-200
                 border border-parchment-200/80 dark:border-walnut-700/80
                 hover:border-parchment-300 dark:hover:border-walnut-700
                 hover:shadow-sm
                 bg-parchment-50/60 dark:bg-walnut-900/60
                 overflow-hidden"
    >
      {/* Left accent bar */}
      <div className="flex">
        <div className="w-1 shrink-0 rounded-l-lg bg-parchment-300/60
                        group-hover:bg-parchment-400/80
                        dark:bg-walnut-700 dark:group-hover:bg-parchment-500/40
                        transition-colors" />
        <div className="flex-1 p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <BookIcon />
              <span className="font-medium text-walnut-700 dark:text-parchment-300 truncate">
                {formatChunkLabel(chunk.chunk_id)}
              </span>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs text-parchment-500 tabular-nums">
                {scorePercent}%
              </span>
              <span className="text-parchment-400 text-[10px] transition-transform duration-200
                               group-hover:text-parchment-500"
                    style={{ transform: expanded ? "rotate(180deg)" : "rotate(0)" }}>
                &#x25BC;
              </span>
            </div>
          </div>
          {expanded && (
            <div className="source-expand-enter">
              <p className="text-walnut-800 dark:text-parchment-200 leading-relaxed
                            border-t border-parchment-200/60 dark:border-walnut-700/60
                            pt-2 mt-2 font-body whitespace-pre-wrap text-[13px]">
                {chunk.text}
                {isTruncated && (
                  <span className="text-parchment-400 italic">{" "}...</span>
                )}
              </p>
            </div>
          )}
        </div>
      </div>
    </button>
  );
}
