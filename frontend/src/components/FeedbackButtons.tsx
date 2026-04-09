import { useState } from "react";

interface FeedbackButtonsProps {
  sessionId: string;
  queryId: number;
}

export function FeedbackButtons({ sessionId, queryId }: FeedbackButtonsProps) {
  const [submitted, setSubmitted] = useState<boolean | null>(null);

  async function handleFeedback(helpful: boolean) {
    setSubmitted(helpful);
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          query_id: queryId,
          helpful,
          comment: "",
        }),
      });
    } catch {
      // Feedback is best-effort — don't disrupt UX on failure
    }
  }

  if (submitted !== null) {
    return (
      <span className="text-xs text-parchment-500 dark:text-parchment-400">
        {submitted ? "Thanks!" : "Thanks for the feedback"}
      </span>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-parchment-500 dark:text-parchment-400">Helpful?</span>
      <button
        onClick={() => handleFeedback(true)}
        className="text-sm hover:scale-110 transition-transform"
        aria-label="Helpful"
      >
        👍
      </button>
      <button
        onClick={() => handleFeedback(false)}
        className="text-sm hover:scale-110 transition-transform"
        aria-label="Not helpful"
      >
        👎
      </button>
    </div>
  );
}
