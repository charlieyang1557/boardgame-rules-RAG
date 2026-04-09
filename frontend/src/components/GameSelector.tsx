import { GAMES } from "../constants";

interface GameSelectorProps {
  selectedGame: string;
  onGameChange: (apiKey: string) => void;
}

export function GameSelector({ selectedGame, onGameChange }: GameSelectorProps) {
  return (
    <div className="flex items-center gap-3">
      <label htmlFor="game-select" className="text-sm font-medium text-parchment-500
                                               dark:text-parchment-400">
        Game
      </label>
      <select
        id="game-select"
        value={selectedGame}
        onChange={(e) => onGameChange(e.target.value)}
        className="rounded-lg border border-parchment-300 dark:border-walnut-700
                   bg-white dark:bg-walnut-800 px-3 py-1.5 text-sm
                   focus:outline-none focus:ring-2 focus:ring-walnut-700/30
                   dark:focus:ring-parchment-400/30 cursor-pointer"
      >
        {GAMES.map((game) => (
          <option key={game.apiKey} value={game.apiKey}>
            {game.displayName}
          </option>
        ))}
      </select>
    </div>
  );
}
