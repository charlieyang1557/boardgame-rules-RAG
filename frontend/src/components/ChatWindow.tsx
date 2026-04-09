import { useEffect, useRef } from "react";
import type { Message } from "../types";
import { EXAMPLE_QUESTIONS } from "../constants";
import { MessageBubble } from "./MessageBubble";

interface ChatWindowProps {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  sessionId: string;
  gameName: string;
  onExampleClick: (question: string) => void;
}

export function ChatWindow({
  messages,
  isLoading,
  error,
  sessionId,
  gameName,
  onExampleClick,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const examples = EXAMPLE_QUESTIONS[gameName] ?? [];

  // Empty state
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 chat-scroll overflow-y-auto">
        <div className="text-center max-w-md space-y-6">
          <div>
            <h2 className="font-heading text-3xl font-bold text-walnut-800
                           dark:text-parchment-100 mb-2">
              Ask the Oracle
            </h2>
            <p className="text-parchment-500 dark:text-parchment-400 text-sm">
              Ask any rules question and get answers with citations from the official rule book.
            </p>
          </div>
          {examples.length > 0 && (
            <div className="space-y-2">
              <span className="text-xs font-medium text-parchment-400 uppercase tracking-wide">
                Try asking
              </span>
              {examples.map((q) => (
                <button
                  key={q}
                  onClick={() => onExampleClick(q)}
                  className="block w-full text-left px-4 py-3 rounded-xl
                             border border-parchment-200 dark:border-walnut-700
                             hover:bg-parchment-100 dark:hover:bg-walnut-800
                             text-sm text-walnut-700 dark:text-parchment-300
                             transition-colors"
                >
                  &ldquo;{q}&rdquo;
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto chat-scroll p-4 space-y-4">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} sessionId={sessionId} />
      ))}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="flex justify-start">
          <div className="max-w-[60%] bg-white dark:bg-walnut-800 rounded-2xl
                          rounded-bl-sm px-4 py-3 shadow-sm border
                          border-parchment-200 dark:border-walnut-700">
            <div className="flex items-center gap-2">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-parchment-400 rounded-full animate-bounce
                               [animation-delay:0ms]" />
                <span className="w-2 h-2 bg-parchment-400 rounded-full animate-bounce
                               [animation-delay:150ms]" />
                <span className="w-2 h-2 bg-parchment-400 rounded-full animate-bounce
                               [animation-delay:300ms]" />
              </div>
              <span className="text-sm text-parchment-500 dark:text-parchment-400">
                Thinking...
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="flex justify-start">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200
                          dark:border-red-800 rounded-2xl rounded-bl-sm px-4 py-3
                          text-sm text-red-700 dark:text-red-300">
            {error}
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
