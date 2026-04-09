# Phase 4 — Web Frontend + Deployment

## Goal
Ship BoardGameOracle as a usable product. Build a minimal web frontend,
deploy the full stack as a single service, and get it in front of real
users. No new RAG features — this is pure product shipping.

## Why now
The backend handles 4 games with 3 tiers, multi-hop retrieval, and
citation verification. But it's an API endpoint that only works via
curl. Real user feedback is now more valuable than incremental accuracy
improvements. Ship it, collect feedback, iterate.

## Frontend — React Chat UI

### Tech stack
- React 18 + TypeScript
- Tailwind CSS (fast styling, no custom CSS needed)
- Vite (build tool)
- Single page app — no routing needed for MVP

### Layout
```
┌─────────────────────────────────────┐
│  BoardGameOracle                    │
│  [Game: Splendor ▼]                 │
├─────────────────────────────────────┤
│                                     │
│  User: Can I take 2 gems of the     │
│        same color?                  │
│                                     │
│  Oracle: Yes, but only if there are │
│  at least 4 tokens of that color    │
│  remaining. [Rule Book p.3]         │
│  ─────────────────────              │
│  Tier: 1 | Confidence: High        │
│  Sources: [Splendor - Game Rules]   │
│                                     │
│  User: What about gold tokens?      │
│                                     │
│  Oracle: Gold joker tokens can      │
│  replace any color when purchasing  │
│  development cards. [Rule Book p.3] │
│  ─────────────────────              │
│  Tier: 1 | Confidence: High        │
│  Sources: [Splendor - Game Rules]   │
│                                     │
├─────────────────────────────────────┤
│  [Type your question...]    [Send]  │
│                                     │
│  [👍] [👎] Helpful?                  │
└─────────────────────────────────────┘
```

### Components
1. **GameSelector** — Dropdown with display names → API values:
   - "Splendor" → `splendor`
   - "Catan" → `catan`
   - "Speakeasy" → `speakeasy`
   - "Food Chain Magnate" → `fcm`
   - Supports URL parameter: `?game=splendor` for shareable links
   - Changing game clears conversation and shows new example questions
2. **ChatWindow** — Scrollable message list (user messages + system responses)
   - Auto-scrolls to bottom on new message
3. **MessageBubble** — Renders a single message with:
   - Answer text
   - Citation highlights (chunk references shown as collapsible SourceCards)
   - Tier badge:
     - Tier 1 = green ("Direct Answer")
     - Tier 2 = yellow ("Multi-Step Reasoning")
     - Tier 3 = orange ("Uncertain")
   - For Tier 2: show multi-hop indicator ("Synthesized from multiple rules")
   - For Tier 3: "Suggested interpretation" clearly labeled as non-authoritative
   - When `chunks` is empty (cache hits): hide Sources section entirely
4. **InputBar** — Text input + send button. Enter to send. Shift+Enter for newline.
5. **FeedbackButtons** — Thumbs up/down per response. Calls POST /api/feedback.
6. **SourceCard** — Expandable card showing cited chunk text.
   - Chunk text is truncated to 300 chars by the API. Show full text with
     "..." indicator when truncated. (Full text retrieval deferred.)

### State management — useChat hook
A simple custom hook at `hooks/useChat.ts` (~30 lines) that owns:
- `messages: Message[]` — full conversation array
- `sendMessage(query: string): void` — calls /ask, appends user + system messages
- `isLoading: boolean` — true while awaiting /ask response
- `error: string | null` — latest error message, cleared on next send

This keeps App.tsx clean and gives all 6 components a single source of truth
via props. Not a state management library — just a hook.

### API integration
The frontend calls two endpoints on the SAME origin (no CORS needed):

```
POST /ask
Request:
{
  "query": "Can I take 2 gems of the same color?",
  "game_name": "splendor",
  "session_id": "uuid-generated-on-page-load"
}

Response (actual contract from api/main.py):
{
  "answer": "...",
  "tier": 1,                    // 1, 2, or 3
  "session_id": "...",
  "query_id": 42,               // int, not string
  "chunks": [                   // "chunks", not "citations"
    {
      "chunk_id": "splendor_p3_c5",
      "text": "...",            // truncated to 300 chars by backend
      "score": 0.92             // sigmoid score, no "section" field
    }
  ],
  "cache_hit": false,
  "latency_ms": 3200.5
}

POST /api/feedback
{
  "session_id": "...",
  "query_id": 42,               // int to match /ask response
  "helpful": true,
  "comment": "optional"
}
```

GET /health returns:
```json
{"status": "ok", "games_loaded": ["splendor", "catan", "speakeasy", "fcm"]}
```

Session ID is generated client-side (uuid v4) on page load. Persists
across the conversation. New session on page refresh.

### UX details
- Loading state: show a skeleton/pulse animation in a chat bubble with
  "Thinking..." while waiting for /ask response. Typical latency 3-5s.
- Error state: if /ask returns 4xx/5xx, show "Something went wrong.
  Please try again." Don't expose error details.
- Per-game error: if a specific game returns 503 (BM25 not loaded),
  show "This game isn't available right now" and suggest another game.
- Empty state: show a welcome message with example questions for the
  selected game. Change examples when game selector changes.
- Mobile responsive: single column layout works on both desktop and mobile.
- No auth for MVP — anyone with the URL can use it.
- Dark mode: use Tailwind `dark:` classes. Respect system preference
  via `prefers-color-scheme`. No toggle needed for MVP.

### Example questions per game (shown in empty state)
```
Splendor:
- "Can I take 2 gems of the same color?"
- "How do nobles work?"
- "When does the game end?"

Catan:
- "What happens when I roll a 7?"
- "How does the Longest Road work?"
- "Can I trade with other players on their turn?"

Speakeasy:
- "What does the Contractor do?"
- "How do I protect my buildings?"
- "When is a building considered Operating?"

Food Chain Magnate:
- "How does the Dinnertime phase work?"
- "What does the 'First billboard placed' milestone do?"
- "Can I train an employee I just hired?"
```

## Backend changes (minimal)

### Single-service architecture
Instead of deploying frontend and backend as separate services, FastAPI
serves the React build output directly. This eliminates CORS configuration,
environment variable coordination, and halves deployment complexity.

Add to api/main.py after all route registrations:
```python
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Serve React build (must come AFTER API routes)
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(frontend_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="static-assets")

    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        """Serve React SPA — all non-API routes return index.html."""
        file_path = os.path.join(frontend_dir, path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dir, "index.html"))
```

No CORS middleware needed. Frontend and backend share the same origin.

### Response format verification
The /ask endpoint already returns structured JSON matching the contract above.
Verify these fields exist in AskResponse:
- answer (string)
- tier (int — 1, 2, or 3)
- chunks (list of {chunk_id, text, score})
- session_id (string)
- query_id (int)
- cache_hit (bool)
- latency_ms (float)

All fields confirmed present in current api/main.py. No changes needed.

### /health endpoint
Already exists. Frontend can call this on load to verify backend is ready
and which games are available. Shape: `{status: string, games_loaded: string[]}`.

## Deployment — Single Service

### Platform choice
Railway Hobby plan ($5/month) for simplicity. One service, git-push deploys.

Alternative: Fly.io (persistent volumes would solve SQLite ephemeral issue).
Decision: start with Railway for familiarity. Accept ephemeral SQLite for MVP.
If feedback collection matters long-term, add Railway PostgreSQL addon or
migrate to Fly.io.

### Why single service
- No CORS configuration
- No inter-service networking
- No environment variable coordination (VITE_API_URL)
- One Dockerfile, one deploy, one URL
- FastAPI serves React build + API on the same origin

### Architecture on Railway
```
┌──────────────────────────────────┐
│  Single Railway Service          │
│  ┌────────────────────────────┐  │
│  │  FastAPI                   │  │
│  │  /ask, /api/feedback,      │  │
│  │  /health                   │  │
│  │  /* → React SPA            │  │
│  └────────────────────────────┘  │
│          │                       │
│  ┌───────┼───────┐               │
│  ▼       ▼       ▼               │
│ Pinecone Anthropic OpenAI        │
└──────────────────────────────────┘
```

### Dockerfile (required — do not rely on nixpacks)
```dockerfile
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
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install Python deps
COPY pyproject.toml ./
RUN pip install .

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

# Create logs dir (don't COPY — logs/ is gitignored)
RUN mkdir -p logs

# Copy BM25 pickles (required at runtime)
COPY ingestion/cache/ ingestion/cache/

# Copy frontend build output
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Download cross-encoder model at build time (not runtime)
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

ENV PORT=8000
EXPOSE 8000
CMD uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

### Resource requirements
- **RAM**: Minimum 1GB, recommend 2GB (cross-encoder + 4 BM25 indexes)
- **Startup time**: ~30-60s (model loading + Pinecone init).
  Configure Railway health check grace period to 90s.
- **Disk**: ~2GB Docker image (torch-cpu + sentence-transformers + app)

### Environment variables (Railway dashboard)
```
PINECONE_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
LLAMA_CLOUD_API_KEY=
PORT=8000
```

### Future: PostgreSQL for production logging
See `docs/postgresql-migration.md` for the migration guide when ready
to persist query logs and feedback across deploys. For MVP, SQLite is
sufficient — accept ephemeral logs during the feedback collection window.

### Deployment steps
1. Create Railway project with 1 service
2. Connect GitHub repo
3. Set environment variables
4. Railway detects Dockerfile, builds and deploys
5. Wait for health check to pass (~60s)
6. Access via Railway's default subdomain

### Ephemeral filesystem caveat
SQLite (query_log.db) resets on every deploy. Accepted for MVP.
Feedback data will persist between deploys ONLY if no new deploy happens.
For the 1-week feedback collection window: avoid deploying during that week,
or accept potential data loss.

Long-term fix: Railway PostgreSQL addon ($5/month) or migrate to Fly.io
with persistent volumes.

### Pre-deployment checklist
- [ ] /ask response format matches TypeScript types exactly
- [ ] /health returns 200 with games_loaded
- [ ] Frontend builds without errors (`cd frontend && npm run build`)
- [ ] Dockerfile builds successfully locally (`docker build -t bgo .`)
- [ ] No hardcoded localhost URLs in frontend code
- [ ] .env NOT committed to git (.gitignore)
- [ ] BM25 pickles for all 4 games exist in ingestion/cache/
- [ ] Cross-encoder model downloads during Docker build (not runtime)

## Project structure addition
```
boardgame-oracle/
├── frontend/                  # NEW
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── GameSelector.tsx
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   ├── InputBar.tsx
│   │   │   ├── FeedbackButtons.tsx
│   │   │   └── SourceCard.tsx
│   │   ├── hooks/
│   │   │   └── useChat.ts      # {messages, sendMessage, isLoading, error}
│   │   ├── types.ts            # TypeScript interfaces matching actual API
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   └── vite.config.ts          # Includes dev proxy: /ask, /api, /health → localhost:8000
├── Dockerfile                  # NEW: multi-stage build
├── .dockerignore               # NEW
├── api/                        # Existing (+ StaticFiles mount)
├── ingestion/                  # Existing
├── ...
```

## What NOT to do
- No user authentication (MVP — open access)
- No database migration to PostgreSQL (SQLite ephemeral accepted)
- No SSR or Next.js (static React is sufficient)
- No WebSocket streaming (regular HTTP POST is fine for 3-5s latency)
- No analytics dashboard (SQLite logs + feedback endpoint is enough)
- No custom domain (use Railway's default subdomain)
- No rate limiting beyond Railway's built-in limits
- No redesign of the RAG pipeline — frontend only
- No separate frontend service (single-service architecture)
- No CORS middleware (same-origin serving)
- No state management library (useChat hook + props is sufficient)

## Success criteria
- Frontend loads and shows game selector + example questions
- User can type a question and receive a formatted answer with citations
- Game selector switches context correctly (different games, different answers)
- URL parameter `?game=splendor` pre-selects the game
- All 3 tier badges display correctly (green/yellow/orange)
- Tier 2 shows "Multi-Step Reasoning" indicator
- Tier 3 shows uncertainty label, no authoritative claims
- Source cards expand to show cited chunk text
- Cache hits render correctly (no empty sources section)
- Feedback buttons work (thumbs up/down stored in SQLite)
- Deployed as single service, accessible via public URL
- Mobile-responsive layout
- Dark mode respects system preference
- Latency < 8 seconds end-to-end (including network)
- Health check passes within 90s of deploy

## After deployment
1. Share URL with 5-10 board game friends
2. Ask them to try 10+ queries each across different games
3. Collect feedback via:
   - Thumbs up/down data from /api/feedback (caveat: ephemeral)
   - Direct conversation ("what questions did you ask? what went wrong?")
4. IMPORTANT: Avoid deploying during the feedback collection week
   to preserve SQLite data
5. After 1 week, pull query logs (if still available) and analyze:
   - Most common query patterns
   - Tier distribution (are users hitting Tier 3 often?)
   - Which games get the most questions?
   - Feedback sentiment (thumbs up vs down ratio)
6. Prioritize fixes based on real data, not golden dataset gaps
