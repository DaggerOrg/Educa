import anthropic

from ai_lab.config import CLAUDE_MODEL

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def ask_claude(prompt: str, system: str | None = None, max_tokens: int = 1024) -> str:
    """Send one user turn to Claude and return the text of the reply."""
    response = get_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
