import { GAMES } from "../constants";

interface GameSelectorProps {
  selectedGame: string;
  onGameChange: (apiKey: string) => void;
}

export function GameSelector({ selectedGame, onGameChange }: GameSelectorProps) {
  return (
    <select
      id="game-select"
      aria-label="Game"
      value={selectedGame}
      onChange={(e) => onGameChange(e.target.value)}
      className="rounded-lg border border-parchment-300/60 dark:border-walnut-700
                 bg-parchment-50/80 dark:bg-walnut-900/80 px-3 py-1.5 text-sm
                 font-medium text-walnut-800 dark:text-parchment-200
                 focus:outline-none focus:ring-2 focus:ring-parchment-400/40
                 dark:focus:ring-parchment-400/20 cursor-pointer
                 backdrop-blur-sm transition-colors"
    >
      {GAMES.map((game) => (
        <option key={game.apiKey} value={game.apiKey}>
          {game.displayName}
        </option>
      ))}
    </select>
  );
}
