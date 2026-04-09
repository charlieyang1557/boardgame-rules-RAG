# PostgreSQL Migration Guide

When ready to move to production (persistent logs + feedback),
add Railway PostgreSQL addon and set DATABASE_URL.

## Schema (PostgreSQL equivalent of current SQLite)

```sql
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
```

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
