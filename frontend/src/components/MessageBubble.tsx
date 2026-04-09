import type { Message } from "../types";
import { TIER_CONFIG } from "../constants";
import { SourceCard } from "./SourceCard";
import { FeedbackButtons } from "./FeedbackButtons";

interface MessageBubbleProps {
  message: Message;
  sessionId: string;
}

export function MessageBubble({ message, sessionId }: MessageBubbleProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-walnut-700 text-parchment-50
                        rounded-2xl rounded-br-sm px-4 py-3 shadow-sm">
          <p className="leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  const tier = message.tier;
  const tierInfo = tier ? TIER_CONFIG[tier] : null;
  const hasChunks = message.chunks && message.chunks.length > 0;

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-3">
        {/* Answer bubble */}
        <div className="bg-white dark:bg-walnut-800 rounded-2xl rounded-bl-sm
                        px-4 py-3 shadow-sm border border-parchment-200
                        dark:border-walnut-700">
          <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Metadata bar: tier badge + feedback */}
        <div className="flex items-center justify-between gap-3 px-1">
          <div className="flex items-center gap-2">
            {tierInfo && (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full
                               text-xs font-medium ${tierInfo.color} ${tierInfo.textColor}`}>
                {tierInfo.label}
              </span>
            )}
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
            <span className="text-xs font-medium text-parchment-500 dark:text-parchment-400 uppercase tracking-wide">
              Sources
            </span>
            {message.chunks!.map((chunk) => (
              <SourceCard key={chunk.chunk_id} chunk={chunk} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
