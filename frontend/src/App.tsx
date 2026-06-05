import { useState, useMemo, useCallback, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { useChat } from "./hooks/useChat";
import { GameSelector } from "./components/GameSelector";
import { LanguageSelector } from "./components/LanguageSelector";
import { ChatWindow } from "./components/ChatWindow";
import { InputBar } from "./components/InputBar";
import { GAMES, LANGUAGES } from "./constants";
import type { Language } from "./types";

function getInitialGame(): string {
  const params = new URLSearchParams(window.location.search);
  const gameParam = params.get("game")?.toLowerCase();
  if (gameParam && GAMES.some((g) => g.apiKey === gameParam)) {
    return gameParam;
  }
  return "splendor";
}

function getInitialLanguage(): Language {
  const params = new URLSearchParams(window.location.search);
  const langParam = params.get("lang")?.toLowerCase();
  if (langParam && LANGUAGES.some((l) => l.code === langParam)) {
    return langParam as Language;
  }
  return "en";
}

function OracleIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" className="shrink-0">
      {/* Crystal ball */}
      <circle cx="14" cy="12" r="9" stroke="currentColor" strokeWidth="1.5"
              className="text-parchment-400 dark:text-parchment-500" />
      <circle cx="14" cy="12" r="9" fill="currentColor"
              className="text-parchment-200/40 dark:text-walnut-700/40" />
      {/* Inner glow */}
      <circle cx="14" cy="11" r="5" fill="currentColor"
              className="text-parchment-300/50 dark:text-parchment-400/20" />
      <circle cx="12" cy="9" r="1.5" fill="currentColor"
              className="text-white/60 dark:text-parchment-200/40" />
      {/* Base */}
      <path d="M8 21 C8 19 10 18 14 18 C18 18 20 19 20 21"
            stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"
            className="text-parchment-400 dark:text-parchment-500" />
      <line x1="7" y1="21" x2="21" y2="21" stroke="currentColor" strokeWidth="1.5"
            strokeLinecap="round" className="text-parchment-400 dark:text-parchment-500" />
    </svg>
  );
}

export default function App() {
  const [gameName, setGameName] = useState(getInitialGame);
  const [language, setLanguage] = useState<Language>(getInitialLanguage);
  const sessionId = useMemo(() => uuidv4(), []);
  const { messages, sendMessage, isLoading, error, clearMessages } = useChat(
    gameName,
    sessionId,
    language
  );

  const handleGameChange = useCallback(
    (newGame: string) => {
      setGameName(newGame);
      clearMessages();
      const url = new URL(window.location.href);
      url.searchParams.set("game", newGame);
      window.history.replaceState({}, "", url.toString());
    },
    [clearMessages]
  );

  const handleLanguageChange = useCallback(
    (newLanguage: Language) => {
      setLanguage(newLanguage);
      clearMessages();
      const url = new URL(window.location.href);
      url.searchParams.set("lang", newLanguage);
      window.history.replaceState({}, "", url.toString());
    },
    [clearMessages]
  );

  const handleExampleClick = useCallback(
    (question: string) => {
      sendMessage(question);
    },
    [sendMessage]
  );

  useEffect(() => {
    const url = new URL(window.location.href);
    if (url.searchParams.get("game") !== gameName) {
      url.searchParams.set("game", gameName);
    }
    if (url.searchParams.get("lang") !== language) {
      url.searchParams.set("lang", language);
    }
    window.history.replaceState({}, "", url.toString());
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto
                    border-x border-parchment-200/60 dark:border-walnut-700/60">
      {/* Header with gradient + accent */}
      <header className="relative px-5 py-3.5
                         bg-gradient-to-r from-parchment-50 via-white to-parchment-50
                         dark:from-walnut-900 dark:via-walnut-800 dark:to-walnut-900">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <OracleIcon />
            <h1 className="font-heading text-xl font-bold tracking-tight
                           text-walnut-800 dark:text-parchment-100">
              BoardGameOracle
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <LanguageSelector
              selectedLanguage={language}
              onLanguageChange={handleLanguageChange}
            />
            <GameSelector selectedGame={gameName} onGameChange={handleGameChange} />
          </div>
        </div>
        {/* Accent line */}
        <div className="absolute bottom-0 left-0 right-0 h-px
                        bg-gradient-to-r from-transparent via-parchment-400/50 to-transparent
                        dark:via-parchment-500/30" />
      </header>

      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        error={error}
        sessionId={sessionId}
        gameName={gameName}
        language={language}
        onExampleClick={handleExampleClick}
      />

      <InputBar onSend={sendMessage} isLoading={isLoading} language={language} />
    </div>
  );
}
