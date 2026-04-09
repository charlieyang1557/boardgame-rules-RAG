import { renderHook, act } from "@testing-library/react";
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
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    }));

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
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(
      new Promise((resolve) => { resolveFetch = resolve; })
    ));

    const { result } = renderHook(() => useChat("splendor", "session-1"));

    act(() => { result.current.sendMessage("test"); });

    expect(result.current.isLoading).toBe(true);

    await act(async () => {
      resolveFetch!({ ok: true, json: () => Promise.resolve(mockResponse) });
    });

    expect(result.current.isLoading).toBe(false);
  });

  it("sets error on fetch failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));

    const { result } = renderHook(() => useChat("splendor", "session-1"));

    await act(async () => {
      await result.current.sendMessage("test");
    });

    expect(result.current.error).toBe("Something went wrong. Please try again.");
    expect(result.current.messages).toHaveLength(1);
    expect(result.current.messages[0].role).toBe("user");
  });

  it("shows game-specific error on 503", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 503 }));

    const { result } = renderHook(() => useChat("fcm", "session-1"));

    await act(async () => {
      await result.current.sendMessage("test");
    });

    expect(result.current.error).toBe("This game isn't available right now. Try a different game.");
  });

  it("clears messages when clearMessages is called", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    }));

    const { result } = renderHook(() => useChat("splendor", "session-1"));

    await act(async () => {
      await result.current.sendMessage("test");
    });

    expect(result.current.messages).toHaveLength(2);

    act(() => { result.current.clearMessages(); });

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
