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
    const input = screen.getByPlaceholderText("Ask a rules question...");
    await userEvent.type(input, "How do nobles work?");

    const sendBtn = screen.getByRole("button", { name: /send/i });
    await userEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText("Yes, if 4 tokens remain.")).toBeInTheDocument();
    });

    expect(screen.getByText("Direct Answer")).toBeInTheDocument();
    expect(screen.getByText(/Sources/)).toBeInTheDocument();
  });

  it("hides source cards by default and reveals them when the Sources header is clicked", async () => {
    render(<App />);
    const input = screen.getByPlaceholderText("Ask a rules question...");
    await userEvent.type(input, "test");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText("Yes, if 4 tokens remain.")).toBeInTheDocument();
    });

    // Collapsed by default: the source card (chunk_id "c1") is not rendered.
    expect(screen.queryByText("c1")).not.toBeInTheDocument();
    // The header shows the count and toggles the list open.
    await userEvent.click(screen.getByText(/Sources \(1\)/));
    expect(screen.getByText("c1")).toBeInTheDocument();
  });

  it("changes games and clears conversation", async () => {
    render(<App />);

    const input = screen.getByPlaceholderText("Ask a rules question...");
    await userEvent.type(input, "test");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    await waitFor(() => {
      expect(screen.getByText("Yes, if 4 tokens remain.")).toBeInTheDocument();
    });

    const select = screen.getByLabelText(/game/i);
    await userEvent.selectOptions(select, "catan");

    expect(screen.getByText("Ask the Oracle")).toBeInTheDocument();
    expect(screen.getByText(/What happens when I roll a 7/)).toBeInTheDocument();
  });

  it("switches UI chrome and example questions to Chinese", async () => {
    // Reset URL so this test starts from the default game (jsdom shares
    // window.location across tests in a file).
    window.history.replaceState({}, "", "/");
    render(<App />);

    // Default English chrome.
    expect(screen.getByText("Ask the Oracle")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Language"), "zh");

    // Empty-state heading, placeholder, and examples are now localized.
    expect(screen.getByText("询问神谕")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("输入规则问题……")).toBeInTheDocument();
    expect(screen.getByText(/我可以拿两个同色的宝石吗/)).toBeInTheDocument();
  });
});
