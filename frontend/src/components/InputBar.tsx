import { useState, useRef, type KeyboardEvent } from "react";

interface InputBarProps {
  onSend: (query: string) => void;
  isLoading: boolean;
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
    <div className="flex items-end gap-3 p-4 border-t border-parchment-200
                    dark:border-walnut-700 bg-white dark:bg-walnut-800">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => {
          setInput(e.target.value);
          handleInput();
        }}
        onKeyDown={handleKeyDown}
        placeholder="Type your question..."
        rows={1}
        className="flex-1 resize-none rounded-xl border border-parchment-300
                   dark:border-walnut-700 bg-parchment-50 dark:bg-walnut-900
                   px-4 py-2.5 text-sm focus:outline-none focus:ring-2
                   focus:ring-walnut-700/30 dark:focus:ring-parchment-400/30
                   placeholder:text-parchment-400 dark:placeholder:text-parchment-500"
      />
      <button
        onClick={handleSend}
        disabled={!input.trim() || isLoading}
        className="shrink-0 rounded-xl bg-walnut-900 dark:bg-parchment-300
                   text-parchment-50 dark:text-walnut-900 px-5 py-2.5 text-sm font-semibold
                   hover:bg-walnut-800 dark:hover:bg-parchment-200
                   ring-1 ring-walnut-900/20 dark:ring-parchment-300/20
                   disabled:opacity-40 disabled:cursor-not-allowed
                   transition-colors"
      >
        {isLoading ? "Sending..." : "Send"}
      </button>
    </div>
  );
}
