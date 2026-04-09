import { useState, useCallback } from "react";
import type { AskResponse, Message } from "../types";
import { v4 as uuidv4 } from "uuid";

export function useChat(gameName: string, sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (query: string) => {
      const userMsg: Message = {
        id: uuidv4(),
        role: "user",
        content: query,
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch("/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            game_name: gameName,
            session_id: sessionId,
          }),
        });

        if (!res.ok) {
          if (res.status === 503) {
            setError("This game isn't available right now. Try a different game.");
          } else {
            setError("Something went wrong. Please try again.");
          }
          return;
        }

        const data: AskResponse = await res.json();

        // Strip internal chunk references like [splendor_p4_c14_727c8fdb]
        const cleanAnswer = data.answer.replace(/\s*\[[\w]+(?:_[\w]+)*\]/g, "").trim();

        const assistantMsg: Message = {
          id: uuidv4(),
          role: "assistant",
          content: cleanAnswer,
          tier: data.tier,
          chunks: data.chunks,
          queryId: data.query_id,
          cacheHit: data.cache_hit,
          latencyMs: data.latency_ms,
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } catch {
        setError("Something went wrong. Please try again.");
      } finally {
        setIsLoading(false);
      }
    },
    [gameName, sessionId]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, sendMessage, isLoading, error, clearMessages };
}
