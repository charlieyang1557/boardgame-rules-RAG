import ReactMarkdown from "react-markdown";
import type { Message } from "../types";
import { TIER_CONFIG } from "../constants";
import { SourceCard } from "./SourceCard";
import { FeedbackButtons } from "./FeedbackButtons";

interface MessageBubbleProps {
  message: Message;
  sessionId: string;
}

function TierBadge({ tier }: { tier: 1 | 2 | 3 }) {
  const config = TIER_CONFIG[tier];
  // Gradient-style badges with subtle glow
  const styles = {
    1: "bg-gradient-to-r from-tier1 to-emerald-600 shadow-tier1/20",
    2: "bg-gradient-to-r from-tier2 to-amber-500 shadow-tier2/20",
    3: "bg-gradient-to-r from-tier3 to-orange-500 shadow-tier3/20",
  } as const;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full
                      text-xs font-semibold text-white shadow-sm
                      ${styles[tier]}`}>
      {config.label}
    </span>
  );
}

export function MessageBubble({ message, sessionId }: MessageBubbleProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-walnut-700 text-parchment-50
                        rounded-2xl rounded-br-sm px-4 py-3
                        shadow-md shadow-walnut-900/10">
          <p className="leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  const tier = message.tier;
  const hasChunks = message.chunks && message.chunks.length > 0;

  return (
    <div className="flex justify-start">
      <div className="max-w-prose space-y-2.5">
        {/* Answer bubble */}
        <div className="bg-white dark:bg-walnut-800 rounded-2xl rounded-bl-sm
                        px-5 py-4 shadow-md shadow-parchment-300/20
                        dark:shadow-black/20
                        border border-parchment-200/60 dark:border-walnut-700/60">
          <div className="oracle-prose leading-relaxed prose prose-sm dark:prose-invert
                          prose-p:my-1 prose-ul:my-1.5 prose-ol:my-1.5
                          prose-li:my-0.5 prose-headings:my-2
                          prose-strong:text-walnut-800 dark:prose-strong:text-parchment-100
                          max-w-none">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        </div>

        {/* Metadata bar: tier badge + feedback */}
        <div className="flex items-center justify-between gap-3 px-1">
          <div className="flex items-center gap-2 flex-wrap">
            {tier && <TierBadge tier={tier} />}
            {tier === 2 && (
              <span className="text-xs text-parchment-500 dark:text-parchment-400 italic">
                Synthesized from multiple rules
              </span>
            )}
            {tier === 3 && (
              <span className="text-xs text-tier3 dark:text-orange-400 italic">
                Suggested interpretation — not authoritative
              </span>
            )}
          </div>

          {message.queryId != null && (
            <FeedbackButtons sessionId={sessionId} queryId={message.queryId} />
          )}
        </div>

        {/* Source cards */}
        {hasChunks && (
          <div className="space-y-1.5 px-1">
            <div className="flex items-center gap-1.5">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none"
                   className="text-parchment-400 dark:text-parchment-500">
                <path d="M1 2.5C1 1.67 1.67 1 2.5 1H5l1 1h3.5c.83 0 1.5.67 1.5 1.5v6c0 .83-.67 1.5-1.5 1.5h-7A1.5 1.5 0 011 9.5v-7z"
                      stroke="currentColor" strokeWidth="1" />
              </svg>
              <span className="text-xs font-medium text-parchment-500 dark:text-parchment-400
                               uppercase tracking-widest">
                Sources
              </span>
            </div>
            {message.chunks!.map((chunk) => (
              <SourceCard key={chunk.chunk_id} chunk={chunk} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
