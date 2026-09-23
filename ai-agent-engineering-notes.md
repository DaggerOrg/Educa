# AI Agent Engineering — Study Notes

Personal reference for moving into AI Engineer / Prompt Engineer / AI-native Product Owner roles.
Focus: systems around LLMs (agents, context, tools, evals) — not ML/model training.

---

## 1. The core building blocks

1. **The model** — the reasoning engine. Everything else compensates for what it can't do alone (no memory, no live data, no actions).
2. **System prompt / instructions** — role, boundaries, output format, what *not* to do. Root cause of most reasoning failures when left vague.
3. **Tools / actions** — functions the agent can call (APIs, DB writes, file edits). Highest-leverage, least-glamorous work — a well-scoped tool with a clear description prevents wrong-tool-selection and bad-argument failures before they happen.
4. **Memory & context management** — short-term (this run's context window) vs long-term (persisted across runs). See deep dive below.
5. **Retrieval (RAG)** — grounds the agent in real, current data instead of frozen training knowledge.
6. **Orchestration / control flow** — the loop logic: single-agent loop vs multi-agent routing/handoff. Use a fixed workflow when the task is well-defined; only reach for a full autonomous agent when you need model-driven flexibility (agents are the expensive, harder-to-debug option, not the default).
7. **Guardrails / validation** — structured output (JSON schema), input sanitization against injection, scoped tool permissions.
8. **Evaluation & observability** — logging/tracing every step, eval suites targeting known failure modes, metrics (hallucination rate, task success rate, fallback rate).
9. **Human-in-the-loop / escalation** — approval gates before irreversible actions, an "ask instead of guess" path for ambiguity.

**One-line version:** *model + tools + memory* = the minimum viable agent ("augmented LLM"). Everything else exists to make that minimum agent safe and reliable enough to ship.

---

## 2. The agent loop, concretely

Strip away any framework (LangChain, CopilotKit, Agno) and every agent is this loop against a raw LLM API:

```
messages = [system_prompt, user_goal]
while not done:
    response = llm.call(messages, tools=tool_schemas)
    if response.type == "tool_call":
        result = execute(response.tool_name, response.arguments)  # your code, real side effects
        messages.append(response)   # the model's tool_call request
        messages.append(result)     # the result, as a new message
    else:
        done = True                 # model returned plain text — finished
```

This is the **ReAct pattern** (Reason → Act → Observe, repeat) under a fancier name.

**Tool calling, mechanically:** each tool is a JSON schema (name, description, typed parameters). The model outputs a structured request; your code executes it. Wrong-tool / hallucinated-argument failures happen when tool descriptions overlap, or a required argument isn't actually available in context and the model guesses.

**Orchestration — who holds the loop:**
- Single-agent: one loop does everything. Simple, but context balloons and one bad step can derail the whole run.
- Multi-agent: an orchestrator routes sub-tasks to specialized agents, each running its own small loop with only the context it needs. Bounds blast radius of a mistake, adds coordination overhead and a handoff-loss failure class.
- Patterns: prompt chaining (fixed sequence), routing (classify → dispatch), parallelization, orchestrator-workers, evaluator-optimizer (one agent generates, another critiques/scores).

---

## 3. Context engineering (not "prompt wording")

Four levers — what the model has access to *at decision time*:

- **System prompt** — the one constant on every call. Even here, "lost in the middle" risk applies once the conversation gets long — recency bias can under-weight rules stated early.
- **Few-shot examples** — 2–3 concrete input→output pairs reduce ambiguity far more reliably than prose description (pattern-matching > spec-following).
- **Structured output constraints** — force the final answer into a schema so downstream code can parse it reliably instead of "usually formatted right."
- **RAG retrieval** — a ranking problem, not binary. Too few chunks → missing info → hallucination to fill the gap. Too many → irrelevant chunks dilute attention and can override the correct instruction.

**Reframe:** a "bad prompt" (wrong wording) is rare with modern models. A **bad context** (stale doc, missing constraint, contradictory instruction buried in history) causes the same symptom (wrong answer) for a different reason — and needs a different fix (fix retrieval/pruning, not wording).

---

## 4. Memory & context management — deep dive

**Two fundamental types:**
- **Short-term / working memory** — the live context window for this run: system prompt, conversation so far, recent tool outputs. Vanishes when the session ends unless explicitly persisted.
- **Long-term / persistent memory** — stored outside the window (DB, vector store, KV store), retrieved back in only when relevant. Survives across sessions.

**Long-term memory sub-types (borrowed loosely from cognitive science):**
- *Semantic* — facts/knowledge ("user prefers metric units," "listing is a studio") — structured records or embeddings.
- *Episodic* — specific past events/interactions, used for personalization/continuity.
- *Procedural* — learned "how to do this task" patterns — usually baked into prompts/few-shot examples rather than retrieved dynamically.

**Practical architectures, cheapest to most engineering-heavy:**
1. **Buffer memory** — keep raw conversation, truncate oldest when full. Simplest, degrades ungracefully (silently drops old constraints).
2. **Summary buffer** — periodically compress older turns into a running summary, keep recent turns raw + summary. Better gist retention, loses exact detail.
3. **Vector-store retrieval memory** — embed every past fact/interaction, retrieve only the top-k relevant ones per turn and inject them. RAG applied to memory instead of documents. Tools: Mem0, Zep, pgvector, Pinecone, or a Postgres table + embeddings.
4. **Structured / knowledge-graph memory** — store facts as nodes/edges (entities + relationships), query the graph instead of similarity-searching chunks. More precise for relational facts ("which listings does this landlord own") but more engineering to build and keep in sync. *Note: this is conceptually what `kg_boards.py` in the Educa project already does — structured knowledge representation, not just vector similarity.*
5. **Hierarchical memory** — hot (in-context, current task) / warm (session summary) / cold (long-term store, fetched on demand). Mirrors CPU cache design: cheap near-term access, everything else fetched only when needed.

**Token budgeting, the practical discipline:**
- Effective budget = context window size − (system prompt + tool schemas + reserved output tokens). Large tool sets with verbose schemas can eat a surprising chunk before a single conversation turn happens.
- Track token usage per component (system prompt / tools / retrieved context / history) so when something breaks, you know *which* part overflowed.

**Failures this causes, and the fix:**
- Context overflow → silently dropped constraints. Fix: summarize before evicting, or move rarely-needed rules out of the system prompt into a tool the agent calls only when relevant (removes the constant token tax).
- Stale memory → agent acts on outdated facts. Fix: timestamp/TTL stored memories, re-verify anything time-sensitive (price, availability) before acting on it.
- Context poisoning → one wrong intermediate result treated as ground truth for the rest of the run. Fix: tag sub-agent/tool results as *claims to verify*, not facts, especially before any irreversible action.

**How to talk about this concretely (interview-ready):** name the architecture for a specific scenario, not memory "in general." E.g. — *"For a WhatsApp lead-qualification agent, I'd use a summary-buffer for the live conversation plus a vector-store lookup keyed by phone number for past interactions, with a TTL so a 6-month-old preference doesn't override what the lead says today."*

---

## 5. Failure modes — full taxonomy

**Input/perception:** garbage-in retrieval, ambiguous instructions, adversarial input / prompt injection.
**Reasoning/planning:** hallucination, faulty task decomposition, sycophancy / premature success claims, retry loops instead of escalation.
**Tool-use:** wrong tool selected, malformed/hallucinated arguments, silent partial failure leaving inconsistent state.
**Memory/context:** overflow, "lost in the middle," context poisoning, stale memory.
**Multi-agent:** misrouting, context loss on handoff, compounding errors, conflicting sub-agent goals.
**Output/verification:** no grounding check before use, non-determinism breaking reproducibility, output format drift.
**Security:** prompt injection → data exfiltration via tool access, excessive tool permissions, jailbreaks.
**Operational:** cost/latency blowups from non-terminating loops, model drift after provider updates, no fallback/circuit breaker.

**The engineer's actual job:** mitigation — structured output + schema validation, human-in-the-loop before high-stakes actions, scoped tool permissions, context pruning/summarization, eval suites targeting each class above, and logging/tracing so failures are debuggable, not invisible.

---

## 6. How this maps to roles applied to

- **Codigo (AI Engineer)** — CopilotKit AI, A2A, AG-UI, LlamaIndex multi-agent SQL project (parsing/validation/optimization split — a real orchestration example), prompt-injection defenses + deterministic validation on the Agno admin-commerce design. Gap: no evidence of formal evals/hallucination-rate tracking — worth building one small eval example.
- **PropertyScout (AI-native Product Owner)** — hard requirement is *links* to shipped AI-built work (Tech Links Asia platform, LlamaIndex project). Weak spot: heavy SQL/large-dataset analysis isn't shown on resume — address directly rather than gloss over.
- **Prompt Engineer (generic JD)** — strong overlap on prompt design + multi-agent orchestration; weaker on RAG/embeddings specifics and voice/SSML/multilingual — no evidence of either on resume.

---

## 7. Study resources

**Core reading (short, free):**
- Anthropic — Building Effective AI Agents: https://www.anthropic.com/engineering/building-effective-agents
- Anthropic — Effective Context Engineering for AI Agents: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Anthropic — Writing Effective Tools for AI Agents: https://www.anthropic.com/engineering/writing-tools-for-agents

**Free structured courses:**
- DeepLearning.AI — Agentic AI (Andrew Ng): via https://www.classcentral.com/subject/llm-agents
- Anthropic Academy — Building with the Claude API (84 lessons, free, incl. "Claude Code in Action")
- Generative AI for Beginners (Microsoft, GitHub, MIT-licensed): via https://www.kdnuggets.com/5-free-courses-to-learn-modern-ai-and-llms

**YouTube:**
- Building AI Agents: Prompt Engineering for Beginners (Part 3, n8n): https://www.youtube.com/watch?v=77Z07QnLlB8
- How We Build Effective Agents — Barry Zhang, Anthropic: https://www.youtube.com/watch?v=D7_ipDqhtwk
- Building Effective AI Agents: Anthropic's Practical Architecture Guide: https://www.youtube.com/watch?v=-tfQf_hwGNQ

**Fastest path to real fluency:** rebuild one small piece of your own LlamaIndex or Agno project and deliberately trigger a failure mode from Section 5 (prompt-inject an input, overflow its context, feed it an ambiguous instruction) — then fix it. That loop teaches more than another course would.
