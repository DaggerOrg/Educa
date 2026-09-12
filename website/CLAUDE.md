# Marketing site (website)

Design system: [../docs/design-system.md](../docs/design-system.md) — "Marketing site" section.

Quick reference: dark SaaS aesthetic (ref: liveblocks.io) via CSS custom
properties in `src/styles.css` — `--bg`/`--bg-raised`/`--bg-soft` (near-black
layers), one accent hue `--accent` (blue, `#4F6EF7`) with `--accent-line`/
`--accent-bright`/`--accent-soft`, reserved for interactive/secondary
emphasis (links, brand mark, small badges) — not gradients. `.btn-primary`
is flat black/white (`background: var(--ink); color: var(--bg)`), matching
liveblocks.io's high-contrast CTA. These tokens are shared with
`frontend/`'s dark mode. Plus Jakarta Sans throughout (weight carries the
hierarchy, no separate display face). Full-pill buttons
(`border-radius: 999px`), 14–16px card radius, soft shadows are back (the
screenshot/ghost-card/badges float above the dark canvas). Nav labels are
Product / Use Cases / Pricing / Resources with a real mobile hamburger menu
(`.nav-toggle` + `.nav-mobile`) below 760px — links never just disappear.
Accessibility structure to keep on any new page: `.skip-link` before `<nav>`,
content wrapped in `<main id="main-content">`, `scroll-padding-top` on
`html` so the sticky nav doesn't cover a jumped-to heading, visible
`:focus-visible` rings. Icons: original SVGs live in `src/assets/icons/`; source attribution
(currently Lucide, ISC) is tracked in [../docs/NOTICE.md](../docs/NOTICE.md)
— inline the path data in a component rather than `<img src>` so
`currentColor` still works.
