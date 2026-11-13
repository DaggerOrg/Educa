"""Live-model evaluations for the AI agents.

Unit and integration tests (tests/) prove the code around the agents works
with the model stubbed out. These evals run the REAL model on fixed cases and
score what it does -- routing, resistance to injected instructions, citation
quality -- so a prompt, model, or agent-structure change can be compared
before and after. They need a Gemini key and cost tokens, so they are run on
demand (`python -m evals`), not in CI. The scoring logic itself is pure and
covered by tests/unit/test_evals.py, which does run in CI.
"""
