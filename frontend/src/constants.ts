import type { Game } from "./types";

export const GAMES: Game[] = [
  { displayName: "Splendor", apiKey: "splendor" },
  { displayName: "Catan", apiKey: "catan" },
  { displayName: "Speakeasy", apiKey: "speakeasy" },
  { displayName: "Food Chain Magnate", apiKey: "fcm" },
];

export const EXAMPLE_QUESTIONS: Record<string, string[]> = {
  splendor: [
    "Can I take 2 gems of the same color?",
    "How do nobles work?",
    "When does the game end?",
  ],
  catan: [
    "What happens when I roll a 7?",
    "How does the Longest Road work?",
    "Can I trade with other players on their turn?",
  ],
  speakeasy: [
    "What does the Contractor do?",
    "How do I protect my buildings?",
    "When is a building considered Operating?",
  ],
  fcm: [
    "How does the Dinnertime phase work?",
    "What does the 'First billboard placed' milestone do?",
    "Can I train an employee I just hired?",
  ],
};

export const TIER_CONFIG = {
  1: { label: "Direct Answer", color: "bg-tier1", textColor: "text-white" },
  2: { label: "Multi-Step Reasoning", color: "bg-tier2", textColor: "text-white" },
  3: { label: "Uncertain", color: "bg-tier3", textColor: "text-white" },
} as const;
