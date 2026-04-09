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
