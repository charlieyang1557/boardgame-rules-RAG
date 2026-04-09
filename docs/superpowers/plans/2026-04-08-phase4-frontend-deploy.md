# Phase 4: Frontend + Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship BoardGameOracle as a usable product with a React chat UI served from FastAPI, deployed as a single service on Railway.

**Architecture:** Single-service deployment — FastAPI serves both the API endpoints (/ask, /api/feedback, /health) and the React SPA (built static files via StaticFiles mount). No CORS needed. Multi-stage Dockerfile: Node builds frontend, Python runtime serves everything.

**Tech Stack:** React 18 + TypeScript + Tailwind CSS + Vite (frontend), FastAPI + StaticFiles (backend serving), Vitest + @testing-library/react (frontend tests), Docker multi-stage build (deployment).

**Design Direction — "Tabletop Oracle":** Warm, rich aesthetic inspired by game manuals and tabletop culture. NOT the generic blue/white AI chat look. Deep warm neutrals (aged parchment, dark walnut), jewel-tone tier badges (emerald, amber, burnt orange), editorial serif headings (Crimson Pro) paired with clean body text (Source Sans 3). Source cards styled like rule book excerpts. The feel: consulting a knowledgeable game master at the table.

**Spec:** `docs/phase4-frontend-deploy.md`

---

## File Map

### New Files (frontend/)
| File | Responsibility |
|------|---------------|
| `frontend/package.json` | Dependencies: react, react-dom, typescript, tailwindcss, vite, vitest, @testing-library/react, jsdom, uuid |
| `frontend/index.html` | Vite entry HTML, Google Fonts link |
| `frontend/vite.config.ts` | Vite config + dev proxy for /ask, /api, /health → localhost:8000 |
| ~~`frontend/tailwind.config.js`~~ | Not needed — Tailwind v4 uses `@theme` in CSS (see index.css) |
| `frontend/tsconfig.json` | TypeScript strict config |
| `frontend/src/main.tsx` | React root mount |
| `frontend/src/App.tsx` | Root component: GameSelector + ChatWindow + InputBar, URL param handling |
| `frontend/src/types.ts` | TypeScript interfaces matching actual AskResponse, ChunkInfo, FeedbackRequest |
| `frontend/src/constants.ts` | GAMES array (display name → API key), example questions per game |
| `frontend/src/hooks/useChat.ts` | Custom hook: messages, sendMessage, isLoading, error, clearMessages |
| `frontend/src/components/GameSelector.tsx` | Dropdown with display names → API values |
| `frontend/src/components/ChatWindow.tsx` | Scrollable message list, auto-scroll, empty state |
| `frontend/src/components/MessageBubble.tsx` | Message rendering: answer, tier badge, source cards |
| `frontend/src/components/InputBar.tsx` | Text input, Enter to send, Shift+Enter newline |
| `frontend/src/components/FeedbackButtons.tsx` | Thumbs up/down per response |
| `frontend/src/components/SourceCard.tsx` | Expandable chunk text card |
| `frontend/src/__tests__/useChat.test.ts` | Hook tests with mocked fetch |
| `frontend/src/__tests__/App.test.tsx` | Integration test: render, select game, type, send |
| `frontend/src/index.css` | Tailwind directives + custom scrollbar + dark mode base |

### New Files (root)
| File | Responsibility |
|------|---------------|
| `Dockerfile` | Multi-stage: Node frontend build → Python runtime |
| `.dockerignore` | Exclude .env, __pycache__, .venv, node_modules, logs/, .git |

### Modified Files
| File | Change |
|------|--------|
| `api/main.py` | Add StaticFiles mount for frontend/dist after all API routes |
| `.gitignore` | Add frontend/node_modules/, frontend/dist/ |

---

## Task 1: Scaffold Frontend Project

**Files:**
- Create: `frontend/package.json`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/src/main.tsx`, `frontend/src/index.css`
  (No tailwind.config.js needed — Tailwind v4 configures via `@theme` in CSS)

- [ ] **Step 1: Initialize Vite React TypeScript project**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
npm create vite@latest frontend -- --template react-ts
```

- [ ] **Step 2: Install dependencies**

```bash
cd /Users/yutianyang/boardgame-rules-RAG/frontend
npm install uuid
npm install -D tailwindcss @tailwindcss/vite @types/uuid vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

- [ ] **Step 3: Replace `vite.config.ts` with dev proxy**

```typescript
// frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/ask": "http://localhost:8000",
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/test-setup.ts",
  },
});
```

- [ ] **Step 4: Create test setup file**

```typescript
// frontend/src/test-setup.ts
import "@testing-library/jest-dom";
```

- [ ] **Step 5: Replace `src/index.css` with Tailwind directives + custom styles**

```css
/* frontend/src/index.css */
@import "tailwindcss";

@theme {
  /* Parchment & Walnut palette */
  --color-parchment-50: #faf8f4;
  --color-parchment-100: #f3efe6;
  --color-parchment-200: #e8e0d0;
  --color-parchment-300: #d4c9b0;
  --color-parchment-400: #bfad90;
  --color-parchment-500: #a99470;
  --color-walnut-700: #4a3728;
  --color-walnut-800: #362818;
  --color-walnut-900: #231a10;

  /* Tier jewel tones */
  --color-tier1: #2d7a4f;
  --color-tier2: #b8860b;
  --color-tier3: #c4561a;

  /* Fonts */
  --font-heading: "Crimson Pro", serif;
  --font-body: "Source Sans 3", sans-serif;
}

/* Custom scrollbar */
.chat-scroll::-webkit-scrollbar {
  width: 6px;
}
.chat-scroll::-webkit-scrollbar-thumb {
  background: var(--color-parchment-400);
  border-radius: 3px;
}

/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
  :root {
    color-scheme: dark;
  }
}
```

- [ ] **Step 6: Replace `index.html` with Google Fonts**

```html
<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>BoardGameOracle</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Crimson+Pro:wght@400;600;700&family=Source+Sans+3:wght@400;500;600&display=swap"
      rel="stylesheet"
    />
  </head>
  <body class="bg-parchment-50 text-walnut-900 font-body dark:bg-walnut-900 dark:text-parchment-100">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Replace `src/main.tsx`**

```tsx
// frontend/src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

- [ ] **Step 8: Create minimal `src/App.tsx` placeholder**

```tsx
// frontend/src/App.tsx
export default function App() {
  return <div className="font-heading text-2xl p-8">BoardGameOracle</div>;
}
```

- [ ] **Step 9: Verify dev server starts**

Run: `cd /Users/yutianyang/boardgame-rules-RAG/frontend && npm run dev`
Expected: Vite dev server at http://localhost:5173, renders "BoardGameOracle"

- [ ] **Step 10: Commit scaffold**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add frontend/
git commit -m "feat: scaffold React frontend with Vite + Tailwind + Vitest"
```

---

## Task 2: TypeScript Types + Constants

**Files:**
- Create: `frontend/src/types.ts`, `frontend/src/constants.ts`

- [ ] **Step 1: Create TypeScript interfaces matching actual API**

```typescript
// frontend/src/types.ts

export interface ChunkInfo {
  chunk_id: string;
  text: string;
  score: number;
}

export interface AskResponse {
  answer: string;
  tier: 1 | 2 | 3;
  session_id: string;
  query_id: number;
  chunks: ChunkInfo[];
  cache_hit: boolean;
  latency_ms: number;
}

export interface AskRequest {
  query: string;
  game_name: string;
  session_id: string;
}

export interface FeedbackRequest {
  session_id: string;
  query_id: number;
  helpful: boolean;
  comment: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  tier?: 1 | 2 | 3;
  chunks?: ChunkInfo[];
  queryId?: number;
  cacheHit?: boolean;
  latencyMs?: number;
}

export interface Game {
  displayName: string;
  apiKey: string;
}
```

- [ ] **Step 2: Create constants with game config and example questions**

```typescript
// frontend/src/constants.ts
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
```

- [ ] **Step 3: Commit types + constants**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add frontend/src/types.ts frontend/src/constants.ts
git commit -m "feat: add TypeScript types and game constants"
```

---

## Task 3: useChat Hook (TDD)

**Files:**
- Create: `frontend/src/hooks/useChat.ts`, `frontend/src/__tests__/useChat.test.ts`

- [ ] **Step 1: Write failing tests for useChat**

```typescript
// frontend/src/__tests__/useChat.test.ts
import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useChat } from "../hooks/useChat";

const mockResponse = {
  answer: "Yes, but only if 4 tokens remain.",
  tier: 1 as const,
  session_id: "test-session",
  query_id: 42,
  chunks: [{ chunk_id: "c1", text: "Rule text here", score: 0.95 }],
  cache_hit: false,
  latency_ms: 1200,
};

describe("useChat", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("starts with empty messages and not loading", () => {
    const { result } = renderHook(() => useChat("splendor", "session-1"));
    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("sends message and appends user + assistant messages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })
    );

    const { result } = renderHook(() => useChat("splendor", "session-1"));

    await act(async () => {
      await result.current.sendMessage("Can I take 2 gems?");
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0].role).toBe("user");
    expect(result.current.messages[0].content).toBe("Can I take 2 gems?");
    expect(result.current.messages[1].role).toBe("assistant");
    expect(result.current.messages[1].content).toBe(mockResponse.answer);
    expect(result.current.messages[1].tier).toBe(1);
    expect(result.current.messages[1].chunks).toEqual(mockResponse.chunks);
    expect(result.current.messages[1].queryId).toBe(42);
  });

  it("sets isLoading during request", async () => {
    let resolveFetch: (value: unknown) => void;
    vi.stubGlobal(
      "fetch",
      vi.fn().mockReturnValue(
        new Promise((resolve) => {
          resolveFetch = resolve;
        })
      )
    );

    const { result } = renderHook(() => useChat("splendor", "session-1"));

    act(() => {
      result.current.sendMessage("test");
    });

    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      resolveFetch!({ ok: true, json: () => Promise.resolve(mockResponse) });
    });

    expect(result.current.isLoading).toBe(false);
  });

  it("sets error on fetch failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500 })
    );

    const { result } = renderHook(() => useChat("splendor", "session-1"));

    await act(async () => {
      await result.current.sendMessage("test");
    });

    expect(result.current.error).toBe("Something went wrong. Please try again.");
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe("user");
  });

  it("shows game-specific error on 503", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 503 })
    );

    const { result } = renderHook(() => useChat("fcm", "session-1"));

    await act(async () => {
      await result.current.sendMessage("test");
    });

    expect(result.current.error).toBe(
      "This game isn't available right now. Try a different game."
    );
  });

  it("clears messages when clearMessages is called", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })
    );

    const { result } = renderHook(() => useChat("splendor", "session-1"));

    await act(async () => {
      await result.current.sendMessage("test");
    });

    expect(result.current.messages).toHaveLength(2);

    act(() => {
      result.current.clearMessages();
    });

    expect(result.current.messages).toEqual([]);
  });

  it("sends correct request body", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });
    vi.stubGlobal("fetch", fetchMock);

    const { result } = renderHook(() => useChat("splendor", "session-1"));

    await act(async () => {
      await result.current.sendMessage("How do nobles work?");
    });

    expect(fetchMock).toHaveBeenCalledWith("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "How do nobles work?",
        game_name: "splendor",
        session_id: "session-1",
      }),
    });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/yutianyang/boardgame-rules-RAG/frontend && npx vitest run src/__tests__/useChat.test.ts`
Expected: FAIL — module `../hooks/useChat` not found

- [ ] **Step 3: Implement useChat hook**

```typescript
// frontend/src/hooks/useChat.ts
import { useState, useCallback } from "react";
import type { AskResponse, Message } from "../types";
import { v4 as uuidv4 } from "uuid";

export function useChat(gameName: string, sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (query: string) => {
      const userMsg: Message = {
        id: uuidv4(),
        role: "user",
        content: query,
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch("/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            game_name: gameName,
            session_id: sessionId,
          }),
        });

        if (!res.ok) {
          if (res.status === 503) {
            setError("This game isn't available right now. Try a different game.");
          } else {
            setError("Something went wrong. Please try again.");
          }
          return;
        }

        const data: AskResponse = await res.json();

        const assistantMsg: Message = {
          id: uuidv4(),
          role: "assistant",
          content: data.answer,
          tier: data.tier,
          chunks: data.chunks,
          queryId: data.query_id,
          cacheHit: data.cache_hit,
          latencyMs: data.latency_ms,
        };

        setMessages((prev) => [...prev, assistantMsg]);
      } catch {
        setError("Something went wrong. Please try again.");
      } finally {
        setIsLoading(false);
      }
    },
    [gameName, sessionId]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, sendMessage, isLoading, error, clearMessages };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/yutianyang/boardgame-rules-RAG/frontend && npx vitest run src/__tests__/useChat.test.ts`
Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add frontend/src/hooks/useChat.ts frontend/src/__tests__/useChat.test.ts
git commit -m "feat: add useChat hook with tests"
```

---

## Task 4: SourceCard Component

**Files:**
- Create: `frontend/src/components/SourceCard.tsx`

- [ ] **Step 1: Implement SourceCard**

```tsx
// frontend/src/components/SourceCard.tsx
import { useState } from "react";
import type { ChunkInfo } from "../types";

interface SourceCardProps {
  chunk: ChunkInfo;
}

export function SourceCard({ chunk }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const isTruncated = chunk.text.length >= 297; // backend truncates at 300

  return (
    <button
      onClick={() => setExpanded(!expanded)}
      className="w-full text-left border border-parchment-300 dark:border-walnut-700
                 rounded-lg p-3 text-sm transition-colors
                 hover:bg-parchment-100 dark:hover:bg-walnut-800
                 bg-parchment-50 dark:bg-walnut-900"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-walnut-700 dark:text-parchment-300 truncate">
          {chunk.chunk_id}
        </span>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs text-parchment-500">
            {(chunk.score * 100).toFixed(0)}% match
          </span>
          <span className="text-parchment-400 text-xs">
            {expanded ? "\u25B2" : "\u25BC"}
          </span>
        </div>
      </div>
      {expanded && (
        <p className="mt-2 text-walnut-800 dark:text-parchment-200 leading-relaxed
                      border-t border-parchment-200 dark:border-walnut-700 pt-2
                      font-body whitespace-pre-wrap">
          {chunk.text}
          {isTruncated && (
            <span className="text-parchment-400 italic">{" "}...</span>
          )}
        </p>
      )}
    </button>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add frontend/src/components/SourceCard.tsx
git commit -m "feat: add SourceCard component"
```

---

## Task 5: FeedbackButtons Component

**Files:**
- Create: `frontend/src/components/FeedbackButtons.tsx`

- [ ] **Step 1: Implement FeedbackButtons**

```tsx
// frontend/src/components/FeedbackButtons.tsx
import { useState } from "react";

interface FeedbackButtonsProps {
  sessionId: string;
  queryId: number;
}

export function FeedbackButtons({ sessionId, queryId }: FeedbackButtonsProps) {
  const [submitted, setSubmitted] = useState<boolean | null>(null);

  async function handleFeedback(helpful: boolean) {
    setSubmitted(helpful);
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          query_id: queryId,
          helpful,
          comment: "",
        }),
      });
    } catch {
      // Feedback is best-effort — don't disrupt UX on failure
    }
  }

  if (submitted !== null) {
    return (
      <span className="text-xs text-parchment-500 dark:text-parchment-400">
        {submitted ? "Thanks!" : "Thanks for the feedback"}
      </span>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-parchment-500 dark:text-parchment-400">Helpful?</span>
      <button
        onClick={() => handleFeedback(true)}
        className="text-sm hover:scale-110 transition-transform"
        aria-label="Helpful"
      >
        👍
      </button>
      <button
        onClick={() => handleFeedback(false)}
        className="text-sm hover:scale-110 transition-transform"
        aria-label="Not helpful"
      >
        👎
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add frontend/src/components/FeedbackButtons.tsx
git commit -m "feat: add FeedbackButtons component"
```

---

## Task 6: MessageBubble Component

**Files:**
- Create: `frontend/src/components/MessageBubble.tsx`

- [ ] **Step 1: Implement MessageBubble with tier badges and source cards**

```tsx
// frontend/src/components/MessageBubble.tsx
import type { Message } from "../types";
import { TIER_CONFIG } from "../constants";
import { SourceCard } from "./SourceCard";
import { FeedbackButtons } from "./FeedbackButtons";

interface MessageBubbleProps {
  message: Message;
  sessionId: string;
}

export function MessageBubble({ message, sessionId }: MessageBubbleProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-walnut-700 text-parchment-50
                        rounded-2xl rounded-br-sm px-4 py-3 shadow-sm">
          <p className="leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  const tier = message.tier;
  const tierInfo = tier ? TIER_CONFIG[tier] : null;
  const hasChunks = message.chunks && message.chunks.length > 0;

  return (
    <div className="flex justify-start">
      <div className="max-w-[85%] space-y-3">
        {/* Answer bubble */}
        <div className="bg-white dark:bg-walnut-800 rounded-2xl rounded-bl-sm
                        px-4 py-3 shadow-sm border border-parchment-200
                        dark:border-walnut-700">
          <p className="leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* Metadata bar: tier badge + feedback */}
        <div className="flex items-center justify-between gap-3 px-1">
          <div className="flex items-center gap-2">
            {tierInfo && (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full
                               text-xs font-medium ${tierInfo.color} ${tierInfo.textColor}`}>
                {tierInfo.label}
              </span>
            )}
            {tier === 2 && (
              <span className="text-xs text-parchment-500 dark:text-parchment-400 italic">
                Synthesized from multiple rules
              </span>
            )}
            {tier === 3 && (
              <span className="text-xs text-tier3 dark:text-orange-400 italic">
                Suggested interpretation — not authoritative
              </span>
            )}
          </div>

          {message.queryId != null && (
            <FeedbackButtons sessionId={sessionId} queryId={message.queryId} />
          )}
        </div>

        {/* Source cards */}
        {hasChunks && (
          <div className="space-y-1.5 px-1">
            <span className="text-xs font-medium text-parchment-500 dark:text-parchment-400 uppercase tracking-wide">
              Sources
            </span>
            {message.chunks!.map((chunk) => (
              <SourceCard key={chunk.chunk_id} chunk={chunk} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add frontend/src/components/MessageBubble.tsx
git commit -m "feat: add MessageBubble with tier badges and source cards"
```

---

## Task 7: InputBar Component

**Files:**
- Create: `frontend/src/components/InputBar.tsx`

- [ ] **Step 1: Implement InputBar with Enter/Shift+Enter handling**

```tsx
// frontend/src/components/InputBar.tsx
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
    // Reset textarea height
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
        className="shrink-0 rounded-xl bg-walnut-700 dark:bg-parchment-300
                   text-white dark:text-walnut-900 px-5 py-2.5 text-sm font-medium
                   hover:bg-walnut-800 dark:hover:bg-parchment-200
                   disabled:opacity-40 disabled:cursor-not-allowed
                   transition-colors"
      >
        {isLoading ? "Sending..." : "Send"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add frontend/src/components/InputBar.tsx
git commit -m "feat: add InputBar with Enter/Shift+Enter handling"
```

---

## Task 8: GameSelector Component

**Files:**
- Create: `frontend/src/components/GameSelector.tsx`

- [ ] **Step 1: Implement GameSelector dropdown**

```tsx
// frontend/src/components/GameSelector.tsx
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
```

- [ ] **Step 2: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add frontend/src/components/GameSelector.tsx
git commit -m "feat: add GameSelector dropdown"
```

---

## Task 9: ChatWindow + Empty State

**Files:**
- Create: `frontend/src/components/ChatWindow.tsx`

- [ ] **Step 1: Implement ChatWindow with auto-scroll, loading skeleton, empty state**

```tsx
// frontend/src/components/ChatWindow.tsx
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
```

- [ ] **Step 2: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add frontend/src/components/ChatWindow.tsx
git commit -m "feat: add ChatWindow with empty state, loading skeleton, error display"
```

---

## Task 10: Wire App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Implement full App.tsx with URL params and game switching**

```tsx
// frontend/src/App.tsx
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
      // Update URL param without reload
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

  // Sync URL param on initial load
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
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3
                         border-b border-parchment-200 dark:border-walnut-700
                         bg-white dark:bg-walnut-800">
        <h1 className="font-heading text-xl font-bold tracking-tight
                       text-walnut-800 dark:text-parchment-100">
          BoardGameOracle
        </h1>
        <GameSelector selectedGame={gameName} onGameChange={handleGameChange} />
      </header>

      {/* Chat area */}
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        error={error}
        sessionId={sessionId}
        gameName={gameName}
        onExampleClick={handleExampleClick}
      />

      {/* Input */}
      <InputBar onSend={sendMessage} isLoading={isLoading} />
    </div>
  );
}
```

- [ ] **Step 2: Verify frontend builds cleanly**

Run: `cd /Users/yutianyang/boardgame-rules-RAG/frontend && npm run build`
Expected: Build succeeds, output in `frontend/dist/`

- [ ] **Step 3: Verify dev server renders correctly**

Run: `cd /Users/yutianyang/boardgame-rules-RAG/frontend && npm run dev`
Expected: Opens at localhost:5173, shows "BoardGameOracle" header, game selector, empty state with example questions for Splendor

- [ ] **Step 4: Run all frontend tests**

Run: `cd /Users/yutianyang/boardgame-rules-RAG/frontend && npx vitest run`
Expected: All useChat tests pass

- [ ] **Step 5: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add frontend/src/App.tsx
git commit -m "feat: wire App.tsx with game selector, chat window, URL params"
```

---

## Task 11: Integration Test

**Files:**
- Create: `frontend/src/__tests__/App.test.tsx`

- [ ] **Step 1: Write integration test for the full chat flow**

```tsx
// frontend/src/__tests__/App.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../App";

const mockResponse = {
  answer: "Yes, if 4 tokens remain.",
  tier: 1,
  session_id: "test",
  query_id: 1,
  chunks: [{ chunk_id: "c1", text: "Some rule text", score: 0.9 }],
  cache_hit: false,
  latency_ms: 1000,
};

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      })
    );
  });

  it("renders header, game selector, and empty state", () => {
    render(<App />);
    expect(screen.getByText("BoardGameOracle")).toBeInTheDocument();
    expect(screen.getByText("Ask the Oracle")).toBeInTheDocument();
    expect(screen.getByLabelText(/game/i)).toBeInTheDocument();
  });

  it("shows example questions that can be clicked", async () => {
    render(<App />);
    const example = screen.getByText(/Can I take 2 gems/);
    await userEvent.click(example);

    await waitFor(() => {
      expect(screen.getByText("Yes, if 4 tokens remain.")).toBeInTheDocument();
    });
  });

  it("sends typed question and displays response", async () => {
    render(<App />);
    const input = screen.getByPlaceholderText("Type your question...");
    await userEvent.type(input, "How do nobles work?");

    const sendBtn = screen.getByRole("button", { name: /send/i });
    await userEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText("Yes, if 4 tokens remain.")).toBeInTheDocument();
    });

    // Tier badge
    expect(screen.getByText("Direct Answer")).toBeInTheDocument();
    // Sources section
    expect(screen.getByText("Sources")).toBeInTheDocument();
  });

  it("changes games and clears conversation", async () => {
    render(<App />);

    // Send a message first
    const input = screen.getByPlaceholderText("Type your question...");
    await userEvent.type(input, "test");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText("Yes, if 4 tokens remain.")).toBeInTheDocument();
    });

    // Switch game
    const select = screen.getByLabelText(/game/i);
    await userEvent.selectOptions(select, "catan");

    // Should show empty state again with Catan examples
    expect(screen.getByText("Ask the Oracle")).toBeInTheDocument();
    expect(screen.getByText(/What happens when I roll a 7/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run integration tests**

Run: `cd /Users/yutianyang/boardgame-rules-RAG/frontend && npx vitest run`
Expected: All tests pass (useChat + App integration)

- [ ] **Step 3: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add frontend/src/__tests__/App.test.tsx
git commit -m "test: add App integration tests for chat flow"
```

---

## Task 12: Backend — StaticFiles Mount

**Files:**
- Modify: `api/main.py` (lines 361-366, after feedback router include)

- [ ] **Step 1: Add StaticFiles serving to api/main.py**

Append after the feedback router include (after line 365 in `api/main.py`):

```python
# ── Serve React frontend (must come AFTER all API routes) ───────────────────

_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.isdir(_frontend_dir):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    _assets_dir = os.path.join(_frontend_dir, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="static-assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str) -> FileResponse:
        """Serve React SPA — all non-API routes return index.html."""
        file_path = os.path.join(_frontend_dir, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_frontend_dir, "index.html"))
```

- [ ] **Step 2: Verify /health still works**

Run: `cd /Users/yutianyang/boardgame-rules-RAG && python -c "from api.main import app; print('ok')"`
Expected: "ok" — no import errors

- [ ] **Step 3: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add api/main.py
git commit -m "feat: serve React frontend via FastAPI StaticFiles"
```

---

## Task 12.5: Document PostgreSQL Migration Path (No Code Change)

**Files:**
- Create: `docs/postgresql-migration.md`

Rationale: Railway's filesystem is ephemeral — SQLite logs are lost on
deploy. For MVP, keep SQLite (simpler, no addon cost). Document the
PostgreSQL migration so it's ready when we move to production.
**No runtime code changes in this task.**

- [ ] **Step 1: Write PostgreSQL migration guide**

```markdown
<!-- docs/postgresql-migration.md -->
# PostgreSQL Migration Guide

When ready to move to production (persistent logs + feedback),
add Railway PostgreSQL addon and set DATABASE_URL.

## Schema (PostgreSQL equivalent of current SQLite)

\```sql
CREATE TABLE IF NOT EXISTS query_logs (
    id SERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    raw_query TEXT NOT NULL,
    rewritten_query TEXT NOT NULL,
    game_name TEXT NOT NULL,
    tier_decision INTEGER NOT NULL,
    top_chunks TEXT NOT NULL,
    final_answer TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    cache_hit INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    timestamp TEXT NOT NULL,
    session_id TEXT NOT NULL,
    query_id INTEGER NOT NULL,
    helpful INTEGER NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    FOREIGN KEY (query_id) REFERENCES query_logs(id)
);
\```

## Code changes needed

In `query_logging/query_logger.py`:
1. Add `psycopg2-binary>=2.9.0` to pyproject.toml
2. Read `DATABASE_URL = os.environ.get("DATABASE_URL")`
3. If set: use `psycopg2.connect(DATABASE_URL)` instead of `sqlite3.connect()`
4. Key differences from SQLite:
   - Placeholder: `%s` instead of `?`
   - Auto-increment: `SERIAL` instead of `AUTOINCREMENT`
   - Last insert ID: `RETURNING id` instead of `cursor.lastrowid`
   - Row factory: `psycopg2.extras.RealDictCursor` instead of `sqlite3.Row`
   - No `PRAGMA foreign_keys` needed (enforced by default)
5. If not set: fall back to SQLite (current behavior, zero changes)

## Railway setup
1. Add PostgreSQL addon in Railway dashboard ($5/month)
2. Railway auto-injects `DATABASE_URL` into the service env
3. Redeploy — QueryLogger picks up the new connection automatically
```

- [ ] **Step 2: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add docs/postgresql-migration.md
git commit -m "docs: add PostgreSQL migration guide for production logging"
```

---

## Task 13: Dockerfile + .dockerignore

**Files:**
- Create: `Dockerfile`, `.dockerignore`
- Modify: `.gitignore`

- [ ] **Step 1: Create .dockerignore**

```
# .dockerignore
.env
.env.*
__pycache__/
*.pyc
.venv/
.git/
.ruff_cache/
logs/
frontend/node_modules/
*.egg-info/
.pytest_cache/
```

- [ ] **Step 2: Create multi-stage Dockerfile**

```dockerfile
# Dockerfile

# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + frontend static files
FROM python:3.11-slim AS runtime
WORKDIR /app

# Install torch CPU-only first (saves ~1.5GB vs full torch)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install Python deps
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# Copy backend code
COPY api/ api/
COPY cache/ cache/
COPY conversation/ conversation/
COPY evaluation/ evaluation/
COPY generation/ generation/
COPY ingestion/ ingestion/
COPY query_logging/ query_logging/
COPY retrieval/ retrieval/
COPY routing/ routing/
COPY verification/ verification/

# Create logs dir
RUN mkdir -p logs

# Copy BM25 pickles (required at runtime)
COPY ingestion/cache/ ingestion/cache/

# Copy frontend build output from stage 1
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Download cross-encoder model at build time (not at startup)
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

ENV PORT=8000
EXPOSE 8000
CMD uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 3: Update .gitignore for frontend artifacts**

Append to `.gitignore`:

```
# Frontend
frontend/node_modules/
frontend/dist/
```

- [ ] **Step 4: Verify Docker build locally (optional — skip if no Docker)**

Run: `cd /Users/yutianyang/boardgame-rules-RAG && docker build -t bgo-test .`
Expected: Build completes. If Docker not installed, skip this step.

- [ ] **Step 5: Commit**

```bash
cd /Users/yutianyang/boardgame-rules-RAG
git add Dockerfile .dockerignore .gitignore
git commit -m "feat: add multi-stage Dockerfile for single-service deploy"
```

---

## Task 14: End-to-End Local Verification

**Files:** None (verification only)

- [ ] **Step 1: Build the frontend**

Run: `cd /Users/yutianyang/boardgame-rules-RAG/frontend && npm run build`
Expected: `frontend/dist/` created with index.html and assets/

- [ ] **Step 2: Start the backend serving frontend**

Run: `cd /Users/yutianyang/boardgame-rules-RAG && uvicorn api.main:app --port 8000`
Expected: Server starts, loads BM25 indexes

- [ ] **Step 3: Verify health endpoint**

Run: `curl http://localhost:8000/health`
Expected: `{"status":"ok","games_loaded":["splendor","catan","speakeasy","fcm"]}`

- [ ] **Step 4: Verify frontend is served**

Open: `http://localhost:8000` in browser
Expected: React app loads, shows "BoardGameOracle" header, game selector, empty state

- [ ] **Step 5: Test a query end-to-end**

In the browser UI:
1. Select "Splendor" game
2. Type "Can I take 2 gems of the same color?"
3. Click Send
Expected: Answer appears with Tier 1 badge, source cards, feedback buttons

- [ ] **Step 6: Test game switching**

1. Switch to "Catan"
2. Verify conversation clears, Catan examples shown
3. Ask "What happens when I roll a 7?"
Expected: Catan-specific answer appears

- [ ] **Step 7: Test feedback**

Click thumbs up on a response.
Expected: Button changes to "Thanks!"
Verify: `sqlite3 logs/query_log.db "SELECT * FROM feedback ORDER BY id DESC LIMIT 1;"`

- [ ] **Step 8: Test URL parameter**

Open: `http://localhost:8000/?game=fcm`
Expected: FCM selected in dropdown, FCM example questions shown

- [ ] **Step 9: Test mobile responsiveness**

Open browser dev tools, toggle device toolbar (mobile view).
Expected: Single column layout, no horizontal overflow

- [ ] **Step 10: Test dark mode**

Set system preference to dark mode (or use dev tools media override).
Expected: Dark background, light text, components adapt

- [ ] **Step 11: Run all frontend tests one final time**

Run: `cd /Users/yutianyang/boardgame-rules-RAG/frontend && npx vitest run`
Expected: All tests pass

- [ ] **Step 12: Commit any final fixes**

If any fixes were needed during verification, commit them:
```bash
git add -A
git commit -m "fix: address issues found during e2e verification"
```

---

## Task 15: Pre-Deployment Checklist + Railway Deploy

**Files:** None (deployment only)

- [ ] **Step 1: Run through pre-deployment checklist**

Verify each item:
- [ ] /ask response format matches TypeScript types exactly
- [ ] /health returns 200 with games_loaded
- [ ] Frontend builds without errors (`cd frontend && npm run build`)
- [ ] No hardcoded localhost URLs in frontend code (`grep -r "localhost" frontend/src/`)
- [ ] .env NOT committed to git (`git status | grep -v .env`)
- [ ] BM25 pickles exist for all 4 games (`ls ingestion/cache/*_bm25.pkl`)
- [ ] `.gitignore` includes frontend/node_modules/ and frontend/dist/

- [ ] **Step 2: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 3: Create Railway project**

1. Go to railway.app, create new project
2. Connect GitHub repo (boardgame-rules-RAG)
3. Railway will detect the Dockerfile

- [ ] **Step 4: Set environment variables on Railway**

In Railway dashboard, set:
- `PINECONE_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `LLAMA_CLOUD_API_KEY`
- `PORT=8000`

- [ ] **Step 5: Configure health check**

Set health check path to `/health` with 90s startup grace period.

- [ ] **Step 6: Deploy and verify**

Railway auto-deploys from GitHub. Wait for build + deploy (~5-10 min).
Open the Railway-generated URL.
Expected: App loads, can ask questions, all 4 games work.

- [ ] **Step 7: Test from mobile device**

Open Railway URL on phone.
Expected: Responsive layout, can type and send questions.

---

## Summary

| Task | What | Estimated Steps |
|------|------|----------------|
| 1 | Scaffold frontend (Vite + React + TS + Tailwind) | 10 |
| 2 | TypeScript types + constants | 3 |
| 3 | useChat hook (TDD) | 5 |
| 4 | SourceCard component | 2 |
| 5 | FeedbackButtons component | 2 |
| 6 | MessageBubble component | 2 |
| 7 | InputBar component | 2 |
| 8 | GameSelector component | 2 |
| 9 | ChatWindow + empty state | 2 |
| 10 | Wire App.tsx | 5 |
| 11 | Integration test | 3 |
| 12 | Backend StaticFiles mount | 3 |
| 12.5 | PostgreSQL migration guide (doc only) | 2 |
| 13 | Dockerfile + .dockerignore | 5 |
| 14 | E2E local verification | 12 |
| 15 | Pre-deployment + Railway | 7 |
| **Total** | | **67 steps** |

Dependencies:
- **Wave 0** (sequential): Tasks 1 → 2 (scaffold, then types)
- **Wave 1** (parallel): Tasks 3, 4, 5, 7, 8 (hook + independent components)
- **Wave 2** (parallel): Tasks 6, 9 (MessageBubble needs SourceCard+FeedbackButtons; ChatWindow needs MessageBubble)
- **Wave 3** (sequential): 10 → 11 → 12 → 12.5 → 13 → 14 → 15
