from __future__ import annotations

from dataclasses import dataclass

import tiktoken

_ENCODER = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_ENCODER.encode(text))


@dataclass
class Turn:
    query: str
    answer: str


class SessionManager:
    def __init__(self, max_turns: int = 3, max_tokens: int = 2000) -> None:
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.sessions: dict[str, list[Turn]] = {}

    def add_turn(self, session_id: str, query: str, answer: str) -> None:
        turns = self.sessions.setdefault(session_id, [])
        turns.append(Turn(query=query, answer=answer))
        if len(turns) > self.max_turns:
            self.sessions[session_id] = turns[-self.max_turns :]

    def get_history(self, session_id: str) -> list[Turn]:
        return self.sessions.get(session_id, [])

    def get_history_text(self, session_id: str) -> str:
        selected_parts: list[str] = []
        token_total = 0

        for turn in reversed(self.get_history(session_id)):
            part = f"User: {turn.query}\nAssistant: {turn.answer}"
            part_tokens = _count_tokens(part)
            separator_tokens = _count_tokens("\n\n") if selected_parts else 0

            if token_total + separator_tokens + part_tokens > self.max_tokens:
                break

            selected_parts.append(part)
            token_total += separator_tokens + part_tokens

        selected_parts.reverse()  # Restore chronological order (oldest first)
        return "\n\n".join(selected_parts)

    def clear_session(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)
