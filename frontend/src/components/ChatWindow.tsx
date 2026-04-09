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

function LargeOracleIcon() {
  return (
    <svg width="72" height="72" viewBox="0 0 72 72" fill="none"
         className="mx-auto mb-4 animate-fade-in">
      {/* Outer ring */}
      <circle cx="36" cy="32" r="26" stroke="currentColor" strokeWidth="1.5"
              className="text-parchment-300 dark:text-walnut-700" />
      {/* Crystal ball fill */}
      <circle cx="36" cy="32" r="26"
              className="fill-parchment-100/60 dark:fill-walnut-800/60" />
      {/* Inner radial highlight */}
      <circle cx="36" cy="30" r="16"
              className="fill-parchment-200/50 dark:fill-parchment-400/10" />
      {/* Specular highlight */}
      <circle cx="30" cy="24" r="5"
              className="fill-white/50 dark:fill-parchment-200/20" />
      <circle cx="28" cy="22" r="2"
              className="fill-white/70 dark:fill-parchment-100/30" />
      {/* Decorative star points */}
      <path d="M36 4 L37.5 8 L36 6 L34.5 8 Z" fill="currentColor"
            className="text-parchment-400/60 dark:text-parchment-500/40" />
      <path d="M36 56 L37.5 52 L36 54 L34.5 52 Z" fill="currentColor"
            className="text-parchment-400/60 dark:text-parchment-500/40" />
      {/* Base/pedestal */}
      <path d="M22 58 C22 55 27 52 36 52 C45 52 50 55 50 58"
            stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
            className="text-parchment-400 dark:text-parchment-500" />
      <line x1="20" y1="58" x2="52" y2="58" stroke="currentColor" strokeWidth="1.5"
            strokeLinecap="round"
            className="text-parchment-400 dark:text-parchment-500" />
      {/* Small decorative dots on pedestal */}
      <circle cx="28" cy="58" r="1" className="fill-parchment-300 dark:fill-walnut-700" />
      <circle cx="36" cy="58" r="1" className="fill-parchment-300 dark:fill-walnut-700" />
      <circle cx="44" cy="58" r="1" className="fill-parchment-300 dark:fill-walnut-700" />
    </svg>
  );
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
      <div className="flex-1 flex flex-col items-center justify-center p-8
                      chat-scroll overflow-y-auto relative">
        {/* Radial gradient behind heading */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="w-80 h-80 rounded-full
                          bg-gradient-radial from-parchment-200/40 to-transparent
                          dark:from-walnut-700/20 dark:to-transparent
                          blur-2xl" />
        </div>

        <div className="text-center max-w-md space-y-6 relative z-10">
          <div>
            <LargeOracleIcon />
            <h2 className="font-heading text-3xl font-bold text-walnut-800
                           dark:text-parchment-100 mb-2 animate-fade-in"
                style={{ animationDelay: "0.1s" }}>
              Ask the Oracle
            </h2>
            <p className="text-parchment-500 dark:text-parchment-400 text-sm
                          animate-fade-in" style={{ animationDelay: "0.2s" }}>
              Ask any rules question and get answers with citations from the official rule book.
            </p>
          </div>
          {examples.length > 0 && (
            <div className="space-y-2">
              <span className="text-xs font-medium text-parchment-400 uppercase tracking-widest
                               animate-fade-in" style={{ animationDelay: "0.25s" }}>
                Try asking
              </span>
              {examples.map((q, i) => (
                <button
                  key={q}
                  onClick={() => onExampleClick(q)}
                  className={`animate-fade-in stagger-${i + 1}
                             block w-full text-left px-4 py-3 rounded-xl
                             border border-parchment-200/80 dark:border-walnut-700/80
                             hover:bg-parchment-100 dark:hover:bg-walnut-800
                             hover:border-parchment-300 dark:hover:border-walnut-700
                             hover:shadow-sm
                             text-sm text-walnut-700 dark:text-parchment-300
                             transition-all duration-200`}
                >
                  <span className="text-parchment-400 mr-1">&ldquo;</span>
                  {q}
                  <span className="text-parchment-400 ml-1">&rdquo;</span>
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
        <div key={msg.id} className="animate-message-in">
          <MessageBubble message={msg} sessionId={sessionId} />
        </div>
      ))}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="flex justify-start animate-message-in">
          <div className="bg-white dark:bg-walnut-800 rounded-2xl
                          rounded-bl-sm px-4 py-3 shadow-sm border
                          border-parchment-200 dark:border-walnut-700">
            <div className="flex items-center gap-2.5">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-parchment-400 rounded-full"
                      style={{ animation: "pulse-soft 1.2s ease-in-out infinite" }} />
                <span className="w-1.5 h-1.5 bg-parchment-400 rounded-full"
                      style={{ animation: "pulse-soft 1.2s ease-in-out 0.2s infinite" }} />
                <span className="w-1.5 h-1.5 bg-parchment-400 rounded-full"
                      style={{ animation: "pulse-soft 1.2s ease-in-out 0.4s infinite" }} />
              </div>
              <span className="text-sm text-parchment-500 dark:text-parchment-400">
                Consulting the rule book...
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="flex justify-start animate-message-in">
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
