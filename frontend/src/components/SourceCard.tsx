import { useState } from "react";
import type { ChunkInfo } from "../types";

interface SourceCardProps {
  chunk: ChunkInfo;
}

function formatChunkLabel(chunkId: string): string {
  // Pattern: "splendor_p4_c14_727c8fdb" → "Splendor — Page 4"
  const match = chunkId.match(/^(\w+?)_p(\d+)/);
  if (!match) return chunkId;
  const game = match[1].charAt(0).toUpperCase() + match[1].slice(1);
  const page = match[2];
  return `${game} — Page ${page}`;
}

export function SourceCard({ chunk }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const isTruncated = chunk.text.length >= 297;

  return (
    <button
      onClick={() => setExpanded(!expanded)}
      className="w-full text-left border border-parchment-300 dark:border-walnut-700
                 rounded-lg p-3 text-sm transition-colors
                 hover:bg-parchment-100 dark:hover:bg-walnut-800
                 bg-parchment-50 dark:bg-walnut-900"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-walnut-700 dark:text-parchment-300 truncate">
          {formatChunkLabel(chunk.chunk_id)}
        </span>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-parchment-500">
            {(chunk.score * 100).toFixed(0)}% match
          </span>
          <span className="text-parchment-400 text-xs">
            {expanded ? "\u25B2" : "\u25BC"}
          </span>
        </div>
      </div>
      {expanded && (
        <p className="mt-2 text-walnut-800 dark:text-parchment-200 leading-relaxed
                      border-t border-parchment-200 dark:border-walnut-700 pt-2
                      font-body whitespace-pre-wrap">
          {chunk.text}
          {isTruncated && (
            <span className="text-parchment-400 italic">{" "}...</span>
          )}
        </p>
      )}
    </button>
  );
}
