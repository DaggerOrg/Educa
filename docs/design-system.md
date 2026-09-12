# Educa design system

Derived from the current `frontend/` and `website/` code (last synced
2026-09-10 after a brand-wide pass toward a Liveblocks-style black/white +
light-blue identity), not written from a spec. One shared brand vocabulary
— near-black or white, one blue accent, Plus Jakarta Sans throughout, flat
fills (no gradients) — expressed contextually across **two apps**:

| | `frontend/` — Studio (the teacher-facing app) | `website/` — marketing site |
|---|---|---|
| Feel | clean working tool, light by default | dark, confident, product-forward |
| Background | white/off-white, dark mode via `prefers-color-scheme` | near-black, dark-only by design |
| Color | ink (black/white) + one blue accent | ink (black/white) + one blue accent |
| Corners | 8px controls / 12px cards | pill (999px) buttons/badges, 14–16px cards |
| Display type | `'Plus Jakarta Sans'`, weight 800 | `'Plus Jakarta Sans'`, weight 800 |

Studio's dark-mode tokens and the website's tokens are now the **same
values** (see below) — put Studio in dark mode and it sits in the same
visual family as the marketing site. The two apps still differ in default
background (Studio defaults to light — it's a working tool for scanning
dense, editable content in daylight; the marketing site is always dark)
and in radius scale (Studio stays tighter/denser for a dense editing UI;
the website goes full pill for a more marketing-forward feel), but they no
longer use different hues, different display faces, or fundamentally
different visual philosophies the way earlier passes did.

**History** — both apps have been restyled more than once; if you find a
stray reference to Fraunces, Public Sans as a *display* face, amber/teal/
violet accents, Bricolage Grotesque, or a gradient button/badge anywhere,
it's a leftover from an earlier pass, not the current system:
- Studio: warm "paper and ink" editorial (amber/teal/violet accents,
  Fraunces serif headings) → **current**: black/white + one blue accent,
  Plus Jakarta Sans, tokens unified with the website's.
- Website: 0point1.ventures-style black/white editorial → social.plus-style
  light SaaS → social.plus-style dark/blue SaaS → **current**: the same
  dark/blue palette, flattened (gradients removed from the primary button,
  brand mark, and badges) and referenced more directly against
  liveblocks.io — flat black/white for the primary CTA and brand mark,
  blue reserved for interactive/secondary emphasis (links, focus rings,
  small badges).

Both: plain CSS with custom properties (no Tailwind/CSS-in-JS), fonts
loaded via a Google Fonts `<link>` in `index.html`.

---

## Studio (`frontend/`)

The product itself — a working tool, not a pitch. Optimized for scanning
dense, editable content (syllabi, lesson drafts) during a live agent
conversation.

### Color tokens (`frontend/src/styles.css`)

Defined as CSS custom properties on `:root`, with a `prefers-color-scheme:
dark` override block — **do not hardcode hex values in components**, always
reference the variable. The dark-mode values below are identical to the
website's tokens (same near-black/ink/blue), so Studio in dark mode and the
marketing site read as one brand.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--paper` | `#FAFAFA` | `#0A0A0F` | page background |
| `--paper-raised` | `#FFFFFF` | `#131319` | cards, rows, buttons |
| `--paper-sunken` | `#F1F2F4` | `#17171F` | recessed fills (e.g. draft status pill) |
| `--ink` | `#0A0A0F` | `#F5F5F7` | primary text |
| `--ink-soft` | `#55595E` | `#A3A3B2` | secondary text |
| `--ink-faint` | `#8A8F98` | `#6E6E7D` | tertiary/meta text, labels |
| `--rule` | `#E3E5E9` | `#2A2A35` | borders, dividers |
| `--accent` (blue) | `#4F6EF7` | `#7C93FF` | primary actions, selection, focus, wordmark accent |
| `--accent-soft` / `--accent-soft-ink` | `rgba(79,110,247,.10)` / `#3450D6` | `rgba(124,147,255,.16)` / `#B7C4FF` | "approved" pill/dot, active state, error banner, correct-quiz-answer |
| `--done` / `--done-ink` | `var(--ink)` / `var(--paper)` | (flips automatically) | "published" pill/dot — a solid ink fill, not a new hue |
| `--shadow` | `0 1px 2px rgba(10,10,15,.05), 0 6px 20px rgba(10,10,15,.06)` | darker equivalent | raised surfaces |

One accent, not three: **draft** is neutral (`--paper-sunken`/`--ink-soft`,
no color), **approved** is the blue accent (soft tint — "in progress, needs
a look"), **published** is a solid `--done` fill (`--ink`'s value — black in
light mode, white in dark mode; a "stamped/shipped" moment, not a new hue).
Blue also carries selection (`.lesson-row.is-selected`) and focus rings.
Don't reintroduce a second/third accent hue for a new state — express it as
neutral / soft-blue / solid-ink, or fall back to ink/rule grayscale.

### Typography

- **Display** (`h1`–`h4`): `'Plus Jakarta Sans', sans-serif`, weight 800,
  `letter-spacing: -0.01em` — same face as body, distinguished by weight
  (matches the website's approach; no separate serif face).
- **Body**: `'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont,
  sans-serif`, 15px base, 1.55 line-height (tighter/denser than the
  website's 16px/1.6 — Studio is a working tool, not a reading page).
- **Labels/meta**: `'IBM Plex Mono', monospace`, small (0.62–0.72rem),
  `letter-spacing: 0.05em`, `text-transform: uppercase` — used for week
  headers, field labels, and status pills. This mono-uppercase treatment is
  the signature "system label" pattern; reuse it for any new
  metadata/eyebrow text rather than inventing a new label style.

### Spacing, radius, borders

- Border radius: 8px (buttons, controls, status pill) / 12px (cards, rows) —
  bumped up from the original 6/8px pass to read closer to the website's
  softer corners, short of its full-pill buttons (Studio's controls are
  denser/more workaday than a marketing CTA).
- Borders: `1px solid var(--rule)` as the default separator — no shadows on
  static content, only `var(--shadow)` for genuinely elevated/floating UI.
- Spacing is ad hoc rem values (0.2rem–1.5rem), not a strict scale — stay in
  that range and prefer values already used nearby over inventing new ones.

### Components

- **Buttons** (`.btn`): 1px `--rule` border, `--paper-raised` background,
  8px radius, 600 weight, 0.85rem. `.btn-primary` fills solid with
  `--accent` (blue) and white text — this is Studio's in-app action button,
  intentionally distinct from the website's black/white hero CTA.
  `:disabled` → `opacity: 0.55`.
- **Status pill** (`.status-pill`): mono-uppercase label pattern above, 6px
  radius (matches the website's `.card .tag` chip), tinted per state —
  `draft` = paper-sunken/ink-soft, `approved` = accent-soft/accent-soft-ink,
  `published` = solid `--done`/`--done-ink`.
- **Card/row** (`.lesson-row`, `.slide-card`): `--paper-raised` fill, 1px
  `--rule` border, 12px radius. Selected state = `border-color:
  var(--accent)` + `box-shadow: 0 0 0 1px var(--accent)` (not a background
  change).
  **Editable text lives inline**: title/objective are `<input>`s styled
  borderless-transparent until focus (`outline: 1px dashed var(--rule)`),
  not separate "edit mode" — keep this pattern for any new inline-editable
  field rather than adding a pencil icon + modal.
- **Layout**: two-column `.grid` (360px chat rail + fluid main), collapses to
  single column under 860px.

---

## Marketing site (`website/`)

Dark SaaS aesthetic, referenced directly against liveblocks.io: near-black
throughout, flat (no-gradient) black/white contrast for the primary CTA and
brand mark, one blue accent reserved for interactive/secondary emphasis
(links, small badges, focus rings), subtle glowing radial highlights behind
the hero and final CTA, pill-shaped buttons, bordered dark cards. The one
deliberate exception is the hero product screenshot, which stays **light**
— it's meant to read as a real capture of Studio's light-themed UI, and a
bright "window" popping against black is what draws the eye to it (contrast
as hierarchy).

This is the site's fourth visual pass — its previous (third) pass already
landed on this dark/blue palette; this pass flattened the gradients that
were on the primary button, brand mark, and small badges, and referenced
liveblocks.io directly for the primary CTA (solid white/black, not a blue
gradient). If old text anywhere mentions Bricolage Grotesque, strict
black/white with no blue, teal, a light background, or a gradient button,
it's a leftover from an earlier pass — this section is current.

### Color tokens (`website/src/styles.css`)

No light-mode block — this site is dark-only by design (not
`prefers-color-scheme`-driven). These are the same values Studio's dark
mode uses (see above), so the two apps share one token vocabulary.

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0A0A0F` | base page background |
| `--bg-raised` | `#131319` | showcase visuals, CTA band, feature cards |
| `--bg-soft` | `#17171F` | alternating "soft" sections, doc/gate rows |
| `--line` | `#2A2A35` | hairline borders throughout |
| `--ink` | `#F5F5F7` | primary text — also doubles as the primary button's fill (near-white on `--bg`) |
| `--ink-soft` | `#A3A3B2` | secondary text |
| `--ink-faint` | `#6E6E7D` | tertiary/meta text |
| `--accent` | `#4F6EF7` | the one accent hue — brand mark, links, small badges, icons |
| `--accent-line` | `#3D5AE0` | hover partner for `--accent` |
| `--accent-bright` | `#7C93FF` | headline highlights, big stat numbers |
| `--accent-soft` / `--accent-soft-ink` | `rgba(79,110,247,.14)` / `#9DB0FF` | eyebrow pills, card tag chips |

No amber/teal/green — the color choice was deliberate: green reads as an
edtech cliché, and blue was the explicit reference direction. Don't add a
second hue; emphasis comes from the accent plus the `--bg`/`--bg-raised`/
`--bg-soft` layering and the flat black/white primary button, not new
colors or gradients.

### Typography

- **Display** (`h1`–`h4`): `'Plus Jakarta Sans', sans-serif` — same family
  as body, distinguished by weight (800 for headings) rather than a
  separate display face. `letter-spacing: -0.015em`, `text-wrap: balance`.
  Hero uses `clamp(2.4rem, 5.2vw, 3.8rem)`.
- **Body**: `'Plus Jakarta Sans'`, 16px base, 1.6 line-height.
- **Eyebrows**: two variants — `.eyebrow-pill` (rounded, tinted background,
  used once in the hero) and `.eyebrow-label` (plain tracked-uppercase text,
  used above every section heading). Don't invent a third eyebrow style.

### Spacing, radius, borders

- Border radius: 14–16px for cards/screenshots, 999px (full pill) for every
  button and badge — no sharp corners anywhere on this pass.
- Shadows are back (`--shadow-sm`, `--shadow-md`) — used on the screenshot,
  the floating ghost-card, and badges, since they're meant to look like
  panels floating above the dark canvas.
- Sections (`.section`, `.section.soft`) use 6rem vertical padding; content
  maxes out at `.wrap`'s 1180px.

### Components

- **Buttons** (`.btn`): full pill (`border-radius: 999px`). `.btn-primary`
  is **flat**, not a gradient — `background: var(--ink); color: var(--bg)`
  (near-white fill, near-black text on this dark-only site), hovering to
  pure `#fff`. This is the liveblocks.io-style high-contrast primary CTA;
  `.btn-outline` (transparent, `--line` border) is the secondary action. A
  new CTA is a new `.btn` variant, not a one-off class — and stays flat, no
  gradients. All interactive elements get a visible `:focus-visible` ring
  (`outline: 2px solid --accent-bright`) — don't suppress it.
- **Nav**: sticky, translucent black (`rgba(10,10,15,.85)`) with
  `backdrop-filter: blur(10px)`. Links: **Product / Use Cases / Pricing /
  Resources** (matches the social.plus reference's top-level labels, mapped
  onto Educa's actual sections rather than fabricated ones) + a primary CTA
  pill. Below 760px the inline links hide behind a real `.nav-toggle`
  hamburger that opens `.nav-mobile` — the mobile links are not just hidden
  with no replacement; keep that pattern for any future nav item.
- **Brand mark** (`.brand-mark`): flat `--accent` (blue) fill, not a
  gradient — the one place blue appears as a filled shape rather than text/
  link color.
- **Hero canvas** (`.hero-canvas`): a dotted background (`radial-gradient`
  dot pattern) with a radial vignette fading to `--bg` at the edges — a
  nod to Educa's own canvas-layout feature, meant to read as an "infinite
  workspace" the product screenshot sits on, not a hard-edged box.
- **Hero glow / CTA glow** (`.hero-glow`, `.cta-band::before`): decorative
  radial-gradient blooms in the accent color, kept subtle (~0.2 peak
  opacity — toned down from the previous pass to stay closer to
  liveblocks.io's flatter minimalism), `pointer-events: none` and
  `aria-hidden`, positioned so they never sit under real text. The hero and
  final CTA are the *only* two glow moments — don't add a third; the effect
  reads as intentional because it bookends the page, not because it's
  everywhere.
- **Floating companions** (`.ghost-card`, `.floating-badge`): a second,
  rotated card and a pill badge overlapping the hero screenshot for depth.
  `.floating-badge` is a flat `--accent` fill (not a gradient).
  `.ghost-card` has a `prefers-reduced-motion: no-preference`-gated float
  animation — animate only when motion is welcomed, never unconditionally.
  Both are hidden below 640px (`display: none`) rather than left to overlap
  content on narrow screens.
- **Pricing / Resources** (`PricingResources.jsx`): Educa is pre-launch, so
  these are two honest `.card`s ("free during early access", "no blog yet")
  rather than fabricated pricing tiers or a resource library that doesn't
  exist. If real pricing or docs exist later, replace the copy — keep the
  nav labels and anchor ids (`#pricing`, `#resources`) stable.
- **Accessibility structure**: a `.skip-link` (visually hidden until
  focused) precedes `<nav>`, page content is wrapped in `<main
  id="main-content">`, and `html { scroll-padding-top: 84px }` keeps the
  sticky nav from covering a heading you've just jumped to via an anchor
  link. Keep all three on any future page in this app.

---

## Applying this

- Before styling a new component, identify which app you're in
  (`frontend/` vs `website/`) and follow that section only — the two apps
  share tokens and philosophy now, but not layout density or radius scale:
  don't drop Studio's 8/12px controls into the website's full-pill system,
  or vice versa.
- Prefer existing tokens/classes over new ones. If a genuinely new pattern
  is needed, add it to the relevant app's `styles.css` following the
  existing naming convention (kebab-case, state as a modifier class like
  `.is-selected`/`.is-correct`), and update this doc.
- Stay within the black/white + one blue accent vocabulary. Don't
  reintroduce amber/teal/violet/green, and don't reach for gradients — flat
  fills are the current pass's whole point.
- This doc reflects the code as of 2026-09-10. If it and the code disagree,
  the code wins — update this file to match rather than "fixing" the code
  to match stale docs.
