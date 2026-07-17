# Handoff: LinkedIn_JobBot — Scraped Job Feed Dashboard

## Overview
A mobile-friendly, responsive UI for a backend LinkedIn job-scraping tool. It shows scraped job listings ranked by a computed "match score," lets the user triage them quickly (open the real listing or delete), and lets them clear out old data by date/period. Editorial/job-board visual tone (serif display + clean sans, warm neutral palette).

## About the Design Files
The bundled file is a **design reference prototype built in HTML**, not production code to copy directly. It was authored in this design tool's internal "Design Component" format (see **Note on file format** below) — treat it as a precise behavioral and visual spec, and **reimplement it in the target codebase's actual framework** (React, Vue, SwiftUI, native, etc.), using that codebase's existing component patterns, state management, and libraries. If no frontend exists yet, choose the framework that best fits the project.

## Fidelity
**High-fidelity.** Colors, type, spacing, and interaction behavior below are final — recreate pixel-close using the target codebase's own styling system (CSS-in-JS, Tailwind, stylesheets, whatever it already uses instead of inline styles).

## Note on file format
`design-reference.dc.html` uses a proprietary templating syntax for streaming/live-editing purposes:
- `{{ path }}` — a data binding (like `{value}` in JSX)
- `<sc-for list="{{ items }}" as="item">` — a loop (like `.map()`)
- `<sc-if value="{{ cond }}">` — a conditional (like `{cond && ...}`)
- The `<script data-dc-script>` class (`DCLogic`) — component state/logic (like a React component's state + handlers)

**Do not copy this syntax into the target codebase.** Read through it for exact markup structure, inline styles, and logic, then reimplement using normal framework idioms (JSX conditionals/`.map`, a real component + hooks/state, etc.).

## Screens / Views
This is a single screen (one continuous feed), no routing.

### Job Feed (only screen)
**Purpose:** Review scraped jobs ranked by match score; open a listing or discard it; clear stale data.

**Layout:**
- Centered single column, `max-width: 640px`, full-height, `1px` solid borders on left/right (visible as a "reading column" on wide viewports; edge-to-edge on mobile).
- Page background: warm off-white. Column background: warm near-white (slightly lighter than page bg), so the column reads as a raised sheet.
- Vertical structure top to bottom: sticky header → scrollable job list (grouped by date) → fixed bottom toast (conditional).

**Header (sticky, `position: sticky; top: 0`):**
- Padding `18px 20px 12px` for the title block, `0 20px 14px` for the controls row. Bottom border `1px solid` (border color, see tokens).
- Row 1 — kicker label: "Job feed", 11px/700, uppercase, `letter-spacing: 0.10em`, colored with the accent color.
- Row 2 — title line: flex row, `justify-content: space-between`, `align-items: baseline`.
  - Left: wordmark "LinkedIn_JobBot", serif (Newsreader) 24px/600, `letter-spacing: -0.01em`, ink color.
  - Right: "{shown} of {total} jobs" counter, 13px/400, muted ink, no-wrap.
- Row 3 — controls, flex row, `gap: 8px`:
  - **Sort toggle pill**: button, pill-shaped (`border-radius: 999px`), `padding: 8px 12px`, 1px border, sort icon (swap-arrows glyph) + text `"Score: High → Low"` / `"Score: Low → High"`. Click flips the direction. Default: High → Low.
  - **Date filter chip**: pill button, calendar icon + current filter label + small chevron. Border/bg/text shift to an "active" tint when a non-"All time" filter is applied (see tokens). Opens a popover below-left on click.

**Date filter popover** (absolute, anchored under the chip, `top: calc(100% + 8px)`, `width: min(250px, calc(100vw - 40px))`, white card, `border-radius: 14px`, soft shadow, `padding: 8px`):
- A full-viewport invisible fixed overlay behind it closes the popover on outside click.
- 5 option rows, each full-width, left-aligned, `border-radius: 8px`, `padding: 9px 10px`: **All time, Today, Yesterday, Last 7 days, Custom range**. The active option is bold with a checkmark icon and a light tinted background.
- Selecting an option closes the popover immediately, **except** "Custom range," which keeps it open and reveals two `<input type="date">` fields (start/end) side by side.
- If the active filter is not "All time" and it matches ≥1 job, a divider + a danger-outline button appears: **"Delete N job(s) from {filter label}"** — bulk-deletes everything currently matching the filter.

**Job list (grouped by date, most recent first):**
- Container padding `14px 16px 100px` (extra bottom padding clears the toast).
- Each date group: `margin-bottom: 18px`.
  - Group header row: flex, `justify-content: space-between`, `padding: 4px 4px 8px`.
    - Left: date label + count, e.g. **"Today · 3"** / **"Yesterday · 3"** / **"Tue, Jul 7 · 3"** — 12px/700, uppercase, `letter-spacing: 0.06em`, muted.
    - Right: **"Clear day"** text button with a small trash icon — bulk-deletes every job in that date group.
  - Jobs in the group, sorted by the active sort direction, each `margin-bottom: 8px`.

**Job row** (the core repeating component):
- Outer wrapper: `position: relative`, `border-radius: 14px`, no visible border/bg (it's a clipping/positioning shell).
  - A full-bleed **red delete backdrop** sits behind the row (`position: absolute; inset: 0`), right-aligned trash icon button, `padding-right: 22px`. Hidden behind the row content at rest; revealed by swipe (see Interactions).
  - The **row content** sits on top: white/near-white card, `1px` border, `border-radius: 14px`, `transition: transform .22s ease, opacity .22s ease` (drives both the swipe reveal and the delete/remove animation).
- Row content — main clickable band, flex row, `gap: 12px`, `padding: 11px 6px 11px 12px`:
  - **Score badge**: 44×44px, `border-radius: 12px`, background = score-tier tint color, centered number in Newsreader serif 18px/700, tabular numerals, color = score-tier text color.
  - **Text block** (`flex: 1; min-width: 0`): job title (15px/600, ink, single line + ellipsis) over company + location joined by " · " (13px/400, muted, single line + ellipsis).
  - **Action group** (`flex-shrink: 0`, 2px gap): a 32×32 trash icon button (`opacity: 0.45` at rest, full opacity + red tint on hover — always present, not hover-only, so it also works on touch) and a 32×32 chevron button that rotates 180° when the row is expanded.
  - Clicking anywhere on this band **except** the two action buttons opens the job (see Interactions).
- **Expanded detail panel** (only when the row is expanded; `padding: 0 14px 14px 68px` — the left inset lines it up under the title text):
  - A wrapped row of small pill/rounded-rect meta chips (light gray bg, `border-radius: 999px` except the last which is `8px` for skills — see tokens): Experience Level (e.g. "Entry/Associate"), Role Category (e.g. "AI Engineer"), "Easy Apply: Yes/No", full date + time (e.g. "Tue, Jul 7 · 6:15 PM").
  - "MATCHED SKILLS" label (11px/700 uppercase) + wrapped skill tags (warm-tinted pills, e.g. "python ×3").
  - Two buttons: primary **"Open job ↗"** (solid accent background, white text) and outline **"Delete"** (danger-tinted).

**Empty states** (shown instead of the list):
- **Queue is empty** (no jobs at all): centered, circle-check icon at 50% opacity, serif headline "Queue is empty", muted subtext "New matches will show up here once the scraper finds them."
- **No jobs in this range** (jobs exist but the active filter matches none): serif headline "No jobs in this range", subtext "Try a wider date filter.", pill button "Reset filter" (sets the filter back to All time).

**Toast / undo snackbar** (fixed, `left: 50%; bottom: 22px; transform: translateX(-50%)`, dark ink background, white text, `border-radius: 12px`, `padding: 12px 16px`, drop shadow, slide-up + fade-in on appear):
- Shows after every delete-type action: `Opened "{title}" and removed it` / `Deleted "{title}"` / `Deleted N jobs from {label}`.
- An **"Undo"** text button (accent color, brightened) restores the removed job(s) to the list.
- Auto-dismisses after 5 seconds; a new action replaces/resets the timer.

## Interactions & Behavior
- **Open a job**: tap/click anywhere on a row's main band (not the trash or chevron button) → `window.open(linkedinUrl, '_blank')`, then (if the "auto-remove on open" setting is on) the row slides out (`translateX(-110%)` + fade to `opacity: 0` over 220ms) and is removed from state; an Undo toast appears.
- **Expand/collapse detail**: tap the chevron button (stops click propagation so it doesn't also open the job) → toggles the expanded panel for that row only (one expanded row at a time via a single `expandedId`).
- **Delete one job**: tap the always-visible trash icon (list row or expanded panel) → same slide-out/fade removal + Undo toast, but does not open the link.
- **Swipe to delete (touch)**: dragging a row left exposes the red backdrop; past a 42px threshold it snaps open to `-84px` (max drag `-110px`); tapping the row again while swiped-open just closes it (does not open the job); tapping the exposed backdrop's trash icon deletes it. Uses `touch-action: pan-y` so vertical scrolling isn't blocked. Live drag feedback is applied directly to the row's transform (not React state) for smoothness; only the final open/closed state is committed to state on touch-end.
- **Sort toggle**: flips global sort between score descending (default) and ascending. Re-sort happens within each date group, not across groups.
- **Date filter**: All time / Today / Yesterday / Last 7 days / Custom range (two native date inputs). Filtering and grouping/labeling ("Today"/"Yesterday"/weekday) are computed relative to the real current date at render time, not hardcoded.
- **Bulk delete by date**: "Clear day" on a group header, or "Delete N job(s) from {filter}" in the date popover when a filter is active — both go through the same remove → toast → undo path as single-item delete.
- **Undo** is universal: every delete path (single tap-delete, swipe-delete, open-and-auto-remove, clear-day, clear-filtered-range) stores the removed job(s) and re-inserts them on Undo.

## State Management
Suggested state shape (was a single component's local state in the prototype; split as needed for the target architecture):
- `jobs: Job[]` — the live list. `Job = { id, title, company, location, easyApply, level, role, score, skills: string[], foundAt: Date, linkedinUrl }`.
- `sortDesc: boolean` — score sort direction.
- `dateFilter: 'all' | 'today' | 'yesterday' | '7d' | 'custom'`, plus `customStart` / `customEnd` (ISO date strings) when `'custom'`.
- `dateFilterOpen: boolean` — popover visibility.
- `expandedId: string | null` — which row (if any) shows its detail panel.
- `swipeOpenId: string | null` — which row (if any) is left-swiped open on touch.
- `removingId: string | null` — which row is mid-removal-animation (used to trigger the transform/opacity transition before the actual splice).
- `toast: { message: string, onUndo: () => void } | null`.
- Derived per render (do not persist): filtered jobs → sorted → grouped by calendar day (key = date, descending) → each group gets a display label (`Today` / `Yesterday` / `"EEE, MMM d"`).
- Score tier is derived from `score`: **high** ≥ 35, **mid** 20–34, **low** < 20.

**Data source note:** the original scraped sheet also has a `Status` column (all rows were `"New"`). This design doesn't render a persistent status — being present in the list *is* the "new/unhandled" state, and opening or deleting a job removes it. If the real backend needs to retain history/status instead of hard-deleting, map "remove from UI" to a status update (e.g. `status: 'opened' | 'dismissed'`) rather than an actual delete, and filter the feed to `status === 'new'`.

## Design Tokens

All colors are authored in OKLCH.

**Core palette**
| Token | Value | Use |
|---|---|---|
| Page background | `oklch(0.975 0.008 75)` | outermost background |
| Surface / column background | `oklch(0.99 0.004 75)` | header + column bg |
| Card / row background | `oklch(0.995 0.004 75)` | job row, popover |
| Border (default) | `oklch(0.88 0.014 70)` | header divider, chip border, inputs |
| Border (subtle) | `oklch(0.9 0.012 70)` | row border, chip dividers |
| Border (active) | `oklch(0.75 0.02 50)` | active date-filter chip |
| Ink (primary text) | `oklch(0.22 0.02 50)` | titles, wordmark |
| Ink (muted text) | `oklch(0.52 0.02 50)` (also 0.55/0.6 variants) | secondary text, icons |
| Accent (tweakable) | default `#B4472E` (rust); alternates `#2F6F5E` (forest), `#9C6B2E` (ochre), `#3A4A6B` (indigo) | kicker label, primary button, Undo text |

**Score tiers**
| Tier | Threshold | Background | Text |
|---|---|---|---|
| High | score ≥ 35 | `oklch(0.93 0.05 150)` | `oklch(0.4 0.12 150)` (green) |
| Mid | 20 ≤ score < 35 | `oklch(0.93 0.06 85)` | `oklch(0.42 0.13 75)` (amber) |
| Low | score < 20 | `oklch(0.93 0.01 55)` | `oklch(0.45 0.02 55)` (neutral gray) |

**Semantic**
| Token | Value | Use |
|---|---|---|
| Danger / delete fill | `oklch(0.55 0.19 25)` | swipe-reveal backdrop |
| Danger text | `oklch(0.5 0.17 25)` | delete button label, bulk-delete button |
| Danger tint bg | `oklch(0.97 0.02 25)` | delete button background |
| Danger border | `oklch(0.85 0.05 25)` | delete button border |
| Skill tag background | `oklch(0.97 0.02 85)` | matched-skill pills |
| Skill tag text | `oklch(0.4 0.06 70)` | matched-skill pills |
| Toast background | `oklch(0.22 0.02 50)` | snackbar |
| Toast text | `oklch(0.98 0.005 75)` | snackbar |

**Typography**
- Display/serif: **Newsreader** (weights 500/600/700, italic 600) — wordmark (24px/600), score badge number (18px/700, tabular numerals), empty-state headlines (18px/600).
- UI/body: **Public Sans** (weights 400/500/600/700) — everything else.
- Kicker label: 11px / 700 / uppercase / `letter-spacing: 0.10em`.
- Job title: 15px / 600.
- Meta line: 13px / 400.
- Buttons, chips, filter options: 13–13.5px / 600–700.
- Group date header: 12px / 700 / uppercase / `letter-spacing: 0.06em`.

**Shape & spacing**
- Card/row radius: 14px. Buttons/icons: 8–10px. Pills/chips: 999px (fully round) except skill tags (8px).
- Row internal padding: `11px 6px 11px 12px`. Expanded panel padding: `0 14px 14px 68px` (68px aligns under the title text: 12 row padding + 44 badge + 12 gap).
- Row-to-row gap: 8px. Group-to-group gap: 18px.
- Icon touch targets: 32×32px (delete/expand), meets the ≥44px combined tap area with padding on mobile.
- Max content column: 640px, centered, 1px side borders.

## Assets
No images or photography. All icons are minimal hand-drawn inline SVGs (16×16 viewBox, `currentColor` strokes, ~1.3–1.6px stroke): chevron (expand), trash (delete), external-link arrow (open job), calendar (date filter), checkmark (active filter option), sort/swap arrows, circle-check (empty state). Recreate as a small icon set (e.g. Lucide/Feather-equivalent glyphs) in the target codebase rather than reusing raw SVG paths verbatim.

## Files
- `design-reference.dc.html` — the full prototype (markup + logic class), in this tool's Design Component format. See **Note on file format** above before reading it as code.
