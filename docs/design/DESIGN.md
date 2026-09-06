# DESIGN.md — Kaizen Cross-Check reviewer interface

Durable visual decisions. Mode: **Operate** (the reviewer is in a task; the tool should disappear into
it). Brief: BD colour system, clear hierarchy, easy keyboard-first review, crafted motion.

## Visual world

**A BD instrument panel.** Clinical white surfaces on a cool, blue-tinted canvas; BD blue as the
structural colour (navigation, links, selection, headings' emphasis); BD orange reserved for the one
action that matters on each screen, the active marker, and focus. Dense but calm: the density of a
laboratory instrument, not a spreadsheet. Colour means something or is not there.

The panel has two compositions, light and dark, built from the same tokens. Dark is the same
instrument with the lights down: a deep blue-black canvas, cards one step lighter, hairlines that are
barely there, off-white ink, and the same orange. It is composed, not inverted (see *Dark theme*).

## Colour

Brand, from BD's identity (Pantone 2755 blue, Pantone 1665 orange):

| Token | Hex | Use |
|---|---|---|
| `brand-700` | `#12305F` | Navigation rail, strongest brand text |
| `brand-600` | `#194890` | BD blue: links, selected states, structural emphasis, INFO |
| `brand-500` | `#1F5AB0` | Hover on blue |
| `brand-100` | `#E8EEF8` | Selected row, soft blue surfaces |
| `accent-600` | `#D9660F` | Orange pressed |
| `accent-500` | `#F07822` | BD orange: primary action, active nav marker, focus ring, caret, selection |
| `accent-100` | `#FDEBDD` | Orange soft surface |

Neutrals, one family, tinted toward the blue:

| Token | Hex | Use |
|---|---|---|
| `canvas` | `#F4F6F9` | Page background |
| `surface` | `#FFFFFF` | Cards, tables, inputs |
| `surface-2` | `#EDF1F6` | Toolbars, side panels, table headers |
| `line` | `#DCE3EC` | Hairline borders |
| `line-2` | `#B8C4D4` | Stronger borders, input borders on hover |
| `ink` | `#0F1F35` | Primary text |
| `ink-2` | `#3D4F66` | Secondary text |
| `ink-3` | `#5C6E86` | Muted text and placeholders: 5.3:1 on white, 4.6:1 on `surface-2` |

Semantic (state), separate from brand:

| Token | Hex | Meaning |
|---|---|---|
| `ok` / `ok-soft` | `#1E7F4F` / `#E3F4EA` | success, cleared |
| `warn` / `warn-soft` | `#B7791F` / `#FBF1DC` | needs attention |
| `bad` / `bad-soft` | `#C13A2B` / `#FBE7E4` | failure, blocker |

Classification (carried by colour and word, always together): EXACT `#1E7F4F`, EQUIVALENT `#0E7C86`,
POTENTIAL `#B7791F`, MISMATCH `#C13A2B`, MISSING `#7E3AA6`. Severity: BLOCKER `#7A1F1F`, MAJOR
`#C13A2B`, MINOR `#B7791F`, INFO `#194890`. Missing is plum, never orange: orange belongs to the brand.
Filled severity badges carry white text only where it reaches 4.5:1 (blocker, major, info); the minor
badge is soft amber with dark amber text.

Contrast floor 4.5:1 for body and placeholder text, 3:1 for large text. Primary buttons are orange
with ink text (5.9:1); white on orange is never used for text. The focus ring is `accent-600` in light
(3.6:1 on white) and `accent-500` in dark.

### Dark theme

Every colour token is a CSS variable (`--c-*`, RGB channels) with a light set on `:root` and a dark set
on `:root[data-theme="dark"]`; Tailwind's colour utilities read them, so no component knows which
theme is on. The choice is remembered per browser under `kaizen.theme`; until a choice is made the
tool follows the operating system, including live changes. A boot script in `index.html` stamps the
theme before first paint so there is no flash. `color-scheme` follows the theme, so native selects,
scrollbars and form controls render in it too.

| Token | Dark | Note |
|---|---|---|
| `canvas` | `#0F1520` | blue-black, not grey |
| `surface` / `surface-2` / `surface-3` | `#161D2B` / `#1D2637` / `#263145` | one step lighter per level |
| `line` / `line-2` | `#27334A` / `#3F4E6E` | hairlines 1.3:1, input borders 2:1 |
| `ink` / `ink-2` / `ink-3` | `#E6ECF5` / `#B3BFD1` / `#8694AB` | 14:1, 9:1, 5.5:1 on `surface` |
| `rail` / `rail-ink` / `rail-muted` | `#0D1A33` / `#EEF3FB` / `#93A8CC` | a deeper BD navy with a hairline edge |
| `brand-600` (links) | `#86A9E6` | BD blue lightened until it reads as text (7.1:1) |
| `brand-100` / `brand-700` | `#1C2C4B` / `#B9CDF2` | soft blue surface and the text on it |
| `brand-fill` | `#2E4F8C` | filled brand chip, white text (8:1) |
| `accent-500` | `#F07822` | unchanged; text on it is always ink |
| `accent-50` / `accent-100` | `#2B1A0E` / `#3D2313` | soft orange surfaces, selection, focus halo |
| `ok` / `ok-soft` / `ok-strong` | `#3DBF7A` / `#0F2A1D` / `#7EDDA8` | strong on soft 9.3:1 |
| `warn` / `warn-soft` / `warn-strong` | `#E4A33B` / `#2C2210` / `#F2C067` | 9.3:1 |
| `bad` / `bad-soft` / `bad-strong` | `#F0705F` / `#331714` / `#F8A094` | 8.2:1 |
| Classification dots and bars | EXACT `#3DBF7A`, EQUIVALENT `#38B6C2`, POTENTIAL `#E4A33B`, MISMATCH `#F0705F`, MISSING `#B685D9` | brightened so they carry on a dark ground |
| Severity fills | BLOCKER `#A32323`, MAJOR `#C13A2B`, INFO `#2B63C7` | white text 5.4:1 or better |
| Scrim | `rgba(0,0,0,.6)` | light uses `rgba(9,26,53,.4)` |
| Shadows | `rgba(0,0,0,.7)` and `.45` | tinted shadows do not read on dark |

Rules that hold in the dark: orange is unchanged and still carries ink text; meaning colours stay
paired with words; page images are evidence and stay white paper inside a dark frame; strong tones
read both on their soft surface and on plain `surface`; text stays at or above 4.5:1 (measured, both
themes, for every pair the interface uses).

## Typography

One family: **Geist** (variable, self-hosted). **Geist Mono** only for data: ids, hashes, item numbers,
quantities and file names. No display face; product UI carries hierarchy with size and weight.

| Role | Size / line | Weight | Tracking |
|---|---|---|---|
| Page title | 22 / 28 | 600 | -0.01em |
| Section title | 16 / 24 | 600 | -0.005em |
| Body | 14 / 20 | 400 | 0 |
| Small | 13 / 18 | 400 | 0 |
| Caption | 12 / 16 | 500 | 0 |
| Big number | 34–40 / 1 | 600 | -0.02em, tabular |

Sentence case everywhere. No all-caps eyebrows above headings. Labels for fields and table headers are
12px, weight 500, `ink-2`, sentence case. Numbers that line up are `tabular-nums`.

## Space, shape, depth

Spacing scale 4 / 8 / 12 / 16 / 24 / 32 / 48. Tight inside a group, generous between groups; more space
above a heading than below it. Cards: radius 12px, 1px `line` border, no shadow (elevation declared
once). Overlays (dialogs, popovers, toasts): radius 12px, tinted shadow
`0 12px 32px -12px rgba(15,31,53,.28), 0 2px 6px rgba(15,31,53,.08)`. Controls: radius 8px, height 36px
(small 30px, large 44px). Badges are pills, 22px tall. Page content is capped at 1440px with 24px padding.

## Layout

App shell: a 232px navigation rail in `brand-700` with two groups, *Workspace* (Runs, Terminology,
Action items) and *This run* (Dashboard, Review queue, Documents, Worklist and mining, Business case,
Compare runs); the active item carries a 3px orange marker. A 56px top bar on `surface`: wordmark, run
switcher, theme toggle (moon or sun, one press), reviewer identity (initials, name, slot pill, BLIND
pill), sign out. Each page opens with a title, one line saying what the page is for, and the page's
actions on the right.

## Motion

Motion conveys state and feedback, never decoration. Easing `cubic-bezier(0.16, 1, 0.3, 1)` for
arrivals, `cubic-bezier(0.77, 0, 0.175, 1)` for on-screen movement; exits faster than entrances.

| Moment | Treatment |
|---|---|
| Press | `transform: scale(.97)` 120ms on any pressable |
| Hover | background or border change 150ms; gated to `(hover: hover) and (pointer: fine)` |
| Panels and rows appearing after a load | rise 6px + fade, 200ms, sibling stagger 40ms capped at 8 items |
| Dialog, help overlay | scale .97 to 1 + fade, 180ms in, 120ms out; centred origin |
| Toast | slide 8px + fade, 200ms in, 120ms out |
| The authored moment | the dashboard's cleared-versus-review split bar fills from empty over 600ms when a run first opens, once |
| Theme switch | every colour cross-fades 200ms (background, border, text); the toggle's icon pops in |
| Keyboard navigation (`j`/`k`, `Enter`) | no animation |
| `prefers-reduced-motion` | no movement; opacity and colour transitions only |

Loading: skeletons shaped like the content, never a spinner in the middle of a page. Empty states say
what to do next.

## Iconography

Phosphor icons, regular weight, 16px inline and 18px in navigation, always with a text label or an
`aria-label`. No emoji, no unicode glyphs as icons.

## Browser surfaces

Selection `accent-100` with `ink`; caret `accent-500`; focus ring 2px `accent-600` (light) or
`accent-500` (dark) with 2px offset; scrollbars thin, thumb `line-2` on `surface-2`; underline offset
3px on links; `color-scheme` set per theme so the browser's own controls match.

## Refuse

Eyebrows and section numbers; nested cards; coloured left borders thicker than 1px; gradient text;
glass or blur as decoration; monospace as a costume; emoji icons; white text on orange; animation on
keyboard-driven actions; any colour whose meaning is not stated in words next to it; a dark theme made
by inverting the light one; hard-coded hex colours in components.
