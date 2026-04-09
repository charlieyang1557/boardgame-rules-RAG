import { useState, useRef, type KeyboardEvent } from "react";

interface InputBarProps {
  onSend: (query: string) => void;
  isLoading: boolean;
}

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <path d="M3 9h12M11 5l4 4-4 4" stroke="currentColor"
            strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function InputBar({ onSend, isLoading }: InputBarProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSend(trimmed);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleInput() {
    const el = textareaRef.current;
    if (el) {
      el.style.height = "auto";
      el.style.height = Math.min(el.scrollHeight, 120) + "px";
    }
  }

  return (
    <div className="relative">
      {/* Top shadow for depth separation */}
      <div className="absolute -top-4 left-0 right-0 h-4
                      bg-gradient-to-t from-parchment-50/80 to-transparent
                      dark:from-walnut-900/80 dark:to-transparent
                      pointer-events-none" />
      <div className="flex items-end gap-3 px-4 py-3.5
                      bg-parchment-50/90 dark:bg-walnut-800/90
                      backdrop-blur-sm
                      border-t border-parchment-200/40 dark:border-walnut-700/40">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => {
            setInput(e.target.value);
            handleInput();
          }}
          onKeyDown={handleKeyDown}
          placeholder="Ask a rules question..."
          rows={1}
          className="flex-1 resize-none rounded-xl
                     border border-parchment-300/60 dark:border-walnut-700
                     bg-white dark:bg-walnut-900
                     px-4 py-2.5 text-sm
                     focus:outline-none focus:ring-2 focus:ring-parchment-400/30
                     dark:focus:ring-parchment-400/20
                     focus:border-parchment-400 dark:focus:border-walnut-700
                     placeholder:text-parchment-400 dark:placeholder:text-parchment-500
                     shadow-sm transition-all"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="shrink-0 rounded-xl
                     bg-walnut-900 dark:bg-parchment-200
                     text-parchment-50 dark:text-walnut-900
                     p-2.5 shadow-md shadow-walnut-900/20
                     hover:bg-walnut-800 dark:hover:bg-parchment-100
                     hover:shadow-lg hover:-translate-y-px
                     active:translate-y-0 active:shadow-md
                     disabled:opacity-30 disabled:cursor-not-allowed
                     disabled:hover:translate-y-0 disabled:hover:shadow-md
                     transition-all duration-150"
          aria-label={isLoading ? "Sending" : "Send"}
        >
          {isLoading ? (
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none"
                 className="animate-spin">
              <circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="2"
                      strokeDasharray="32" strokeDashoffset="8"
                      strokeLinecap="round" />
            </svg>
          ) : (
            <SendIcon />
          )}
        </button>
      </div>
    </div>
  );
}
