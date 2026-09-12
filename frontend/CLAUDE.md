# Studio (frontend)

Design system: [../docs/design-system.md](../docs/design-system.md) — "Studio" section.

Quick reference: black/white palette + one blue accent (`#4F6EF7` light /
`#7C93FF` dark) via CSS custom properties in `src/styles.css` (`--paper`,
`--ink`, `--accent` + `-soft`/`-soft-ink` pairs, plus `--done`/`--done-ink`
for the "published" state; light + dark via `prefers-color-scheme`). No
amber/teal/violet — draft is neutral, approved is the blue accent,
published is a solid `--done` (ink) fill. Dark-mode tokens are identical to
`website/`'s, so Studio in dark mode and the marketing site share one
brand. `'Plus Jakarta Sans'` for headings and body (weight 800 for
headings), IBM Plex Mono uppercase for labels/status pills, 8px radius on
controls / 12px on cards, hairline `--rule` borders, soft `--shadow` for
elevation only. Always reference existing tokens — never hardcode a hex
value in a component.
