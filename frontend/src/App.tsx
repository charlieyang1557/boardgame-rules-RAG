import { useState, useMemo, useCallback, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { useChat } from "./hooks/useChat";
import { GameSelector } from "./components/GameSelector";
import { ChatWindow } from "./components/ChatWindow";
import { InputBar } from "./components/InputBar";
import { GAMES } from "./constants";

function getInitialGame(): string {
  const params = new URLSearchParams(window.location.search);
  const gameParam = params.get("game")?.toLowerCase();
  if (gameParam && GAMES.some((g) => g.apiKey === gameParam)) {
    return gameParam;
  }
  return "splendor";
}

export default function App() {
  const [gameName, setGameName] = useState(getInitialGame);
  const sessionId = useMemo(() => uuidv4(), []);
  const { messages, sendMessage, isLoading, error, clearMessages } = useChat(
    gameName,
    sessionId
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
      window.history.replaceState({}, "", url.toString());
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto
                    border-x border-parchment-200 dark:border-walnut-700">
      <header className="flex items-center justify-between px-4 py-3
                         border-b border-parchment-200 dark:border-walnut-700
                         bg-white dark:bg-walnut-800">
        <h1 className="font-heading text-xl font-bold tracking-tight
                       text-walnut-800 dark:text-parchment-100">
          BoardGameOracle
        </h1>
        <GameSelector selectedGame={gameName} onGameChange={handleGameChange} />
      </header>

      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        error={error}
        sessionId={sessionId}
        gameName={gameName}
        onExampleClick={handleExampleClick}
      />

      <InputBar onSend={sendMessage} isLoading={isLoading} />
    </div>
  );
}
