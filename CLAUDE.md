# Educa

Curriculum-builder prototype. See [docs/README.md](docs/README.md) for
architecture (React/TypeScript + FastAPI + CopilotKit + Agno) and
[docs/ARTIFACTS.md](docs/ARTIFACTS.md) for the spec docs (`ARCH-01`, SRS,
etc).

## Design system

Full design system: [docs/design-system.md](docs/design-system.md).

This repo shares **one brand** — black/white + a single light-blue accent
(ref: liveblocks.io), Plus Jakarta Sans throughout, flat fills (no
gradients) — expressed across **two apps** with different defaults, so
still check which one you're in before writing or editing UI code:

- `frontend/` — **Studio**, the teacher-facing app. Light by default (dark
  mode via `prefers-color-scheme`), 8px/12px corners for a denser working
  UI. Dark-mode tokens are identical to the website's.
- `website/` — the **marketing site**. Dark-only, near-black background,
  full-pill buttons and 14–16px cards, soft shadows on floating panels over
  the dark canvas.

Don't carry Studio's control density (8/12px radius, denser spacing) into
the website's full-pill system or vice versa — but do reuse the shared
color tokens and Plus Jakarta Sans typography. When in doubt, open
`docs/design-system.md` and read the section for the app you're touching.
