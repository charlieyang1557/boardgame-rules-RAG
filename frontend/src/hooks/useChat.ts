import { useState, useCallback, useRef } from "react";
import type { AskResponse, Language, Message } from "../types";
import { UI_STRINGS } from "../constants";
import { v4 as uuidv4 } from "uuid";

export function useChat(
  gameName: string,
  sessionId: string,
  language: Language = "en"
) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (query: string) => {
      // Cancel any in-flight request so a stale-language answer can't land
      // in the new conversation.
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const userMsg: Message = {
        id: uuidv4(),
        role: "user",
        content: query,
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      const t = UI_STRINGS[language];

      try {
        const res = await fetch("/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            game_name: gameName,
            session_id: sessionId,
            language,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          if (res.status === 503) {
            setError(t.errorUnavailable);
          } else {
            setError(t.errorGeneric);
          }
          return;
        }

        const data: AskResponse = await res.json();

        // If the user switched game/language while the body was streaming,
        // drop this now-stale response instead of appending it.
        if (controller.signal.aborted) return;

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
        // Ignore aborts (the user switched game/language mid-request).
        if (controller.signal.aborted) return;
        setError(t.errorGeneric);
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    },
    [gameName, sessionId, language]
  );

  const clearMessages = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setError(null);
    setIsLoading(false);
  }, []);

  return { messages, sendMessage, isLoading, error, clearMessages };
}
