# Reviewer interface design

This is the current design contract, consolidated from the implemented interface. Product workflows,
permissions and the complete route inventory live in [PRODUCT.md](PRODUCT.md).

## Source of truth

- [index.css](../../ui/src/index.css): theme variables, shell, forms, tables and responsive overrides.
- [tailwind.config.js](../../ui/tailwind.config.js): token-backed utilities and typography.
- [Layout](../../ui/src/components/Layout.tsx): navigation, run context and account controls.
- Shared [controls](../../ui/src/components/ui.tsx), [badges](../../ui/src/components/Badges.tsx),
  [ChoiceList](../../ui/src/components/ChoiceList.tsx) and [pagination](../../ui/src/components/Pagination.tsx).

Spacing and colour variables are in `ui/src/index.css`; there is no separate root `tokens.css`.
When reading the stylesheet, include its later overrides rather than using the initial palette alone.
Do not copy historical palette values or add a second component-specific theme.

## Appearance

Use neutral surfaces, restrained status colours, BD blue links and an orange primary action/focus accent.
Colour accompanies a written classification, severity or state. Evidence images retain their source colours.

| Role | Light | Dark |
| --- | --- | --- |
| Canvas | `#F8F9FB` | `#14161B` |
| Surface | `#FFFFFF` | `#1B1E24` |
| Secondary surface | `#F5F6F8` | `#22252C` |
| Main text | `#1E242E` | `#EBEEF4` |
| Secondary text | `#4A5463` | `#C5CBD6` |
| Muted text | `#636E7F` | `#A3ACBB` |
| Sidebar | `#F5F6F8` | `#17191E` |
| Primary action | `#FF6E00` | `#F49F62` |
| Primary action text | `#181B21` | `#181B21` |

CSS variables hold RGB channels; Tailwind reads them. Theme is applied through `data-theme` and stored
under `kaizen.theme`; until explicitly selected it follows the operating system. The boot script sets
it before rendering. Use semantic tokens instead of literal component colours. Target at least 4.5:1
for ordinary text and 3:1 for large text/focus indicators; check actual rendered combinations when changed.
These targets are not a claim that every future combination has been measured.

Source Sans 3 is the interface font, bundled as a variable font with swap loading. Geist Mono is
reserved for identifiers, codes and raw extracted text; document names use the interface font.
Page headings are 28px on desktop and 24px below 768px, with restrained tracking. Body copy is 15px,
tables and controls 14px, labels and supporting text 13px. Narrow-screen inputs use 16px text.
Badges reset heading tracking and keep short labels on one line; long explanatory badges explicitly
allow wrapping. Use tabular numbers for aligned counts. Comparison rows separate item codes,
descriptions and source references. Document category explanations expand on demand within their row.

Cards use 10px corners and subtle borders/shadows. Inputs/buttons use 7px corners. Standard buttons are
36px high, small buttons 32px and large buttons 42px. Spacing uses the shared 8/12/16/24/32/48px scale.

## Shell and responsive behavior

- Desktop sidebar: 240px; top bar: 60px. Main content is capped at 1500px, with 32px desktop side padding,
  20px below 1024px and 16px below 768px.
- Workspace contains **All runs**, **Action items** and **Terminology**. **Runs** lists accessible runs;
  each expands to one flat list: Overview, Review queue, Documents, Closed testing, Suggested matches
  and Compare runs. Business case and the Analysis subsection have been removed.
  **Administration** is visible to administrators. The header has one avatar button: its menu offers Profile, Light/Dark mode and Sign out.
  Profile is also available from the sidebar.
- Sidebar sections are remembered per account. The active run expands to reveal its destination.
  Desktop supports a compact rail; below 1024px navigation becomes a labelled drawer.
- The drawer has a backdrop, locks background scrolling, contains keyboard focus, closes with Escape,
  and restores focus to its trigger. Dialogs follow the same focus/recovery conventions.
- Breadcrumbs identify the current screen. A named run selector appears on run pages. Do not ask users
  to paste raw run IDs where the app can supply accessible run names.
- Overview groups the heading, verdict and run metadata together. Quick view, Review queue, Download
  Excel and Options share a top edge and 40px height; narrow screens reflow the actions into two columns.
  Owners open Options for Rename/Delete; deletion retains the named-run confirmation and restore workflow.
- Keep page overflow within the viewport. Dense tables and source images may scroll in their own
  containers. Wrap long explanations, paths and identifiers; preserve full text in accessible content.
- Overview offers explicit bulk approval under Auto-cleared. The queue’s Bulk review menu separates Accept decisions from approvals. Bulk approval previews run-wide eligible counts and requires a self-approval acknowledgement. Approved filters disable Pending only; enabling Pending only clears the Approved filter. Saving a decision and approving it remain separate states.

## Lists and evidence

| Surface | Implemented behavior |
| --- | --- |
| All runs | Totals, ownership filters, Deleted runs and search; 25 entries per client-side page. Owners open Options for Rename/Delete; deleted runs offer Restore and Delete permanently. Permanent deletion names the run, explains storage/history removal and retained copies, requires typing DELETE, locks the dialog during submission and reports cleanup failures. |
| Review queue | 100 comparisons per page; basic filters plus More filters; current review state and engine evidence stay distinct. |
| Terminology | Shared library/My terminology, named approval/time/version, reviewer/scope/search filters, explicit checkbox subsets or Add entire list. Current account usage and available version updates stay visible. Packaged defaults are included; shared management remains administrator-only. 25 entries per page. |
| Action items, users | Search/filter controls where relevant; 25 entries per client-side page. Manage users includes invitation creation, a one-time code field and pending invitation revocation. |
| Documents | Actual SKU membership; shared/unassigned sources represented once; six columns, source details and warning disclosures. |
| Quick view | Per-SKU BOM/Label/Diagram matrix, green/orange text with written status, 100-row pagination, search, retained-text mode, and three source previews. See [surface contract](quick-view.md). |
| Upload | Explicit folder/file buttons; selected document sets and folder paths in a visible bounded list with per-set removal and Clear all. Cancelling a picker retains the selection. Skipped unsupported files are reported; pending controls prevent duplicate submission. A compact 0–100% stage progress indicator sits beside the start action and reaches 100% only after saving succeeds. The dialog body scrolls while its actions stay visible. |
| Evidence | Review tools beside source evidence from 1280px; layouts stack when space is limited. Ground truth occupies full width below the workspace. |
| Ground truth | Source lists side by side from 768px and stacked below; searchable checkbox choices, removable selected chips, counts and Clear selection. |

ChoiceList selections survive searching, including no-result searches. Display human-readable labels
and preserve original source IDs/discrepancy codes in saved payloads. Clear selection means no verified
issue; it must not silently change the verdict or source pairing. Keep options in a bounded scroll area.

Previous/next evidence navigation crosses queue pages and respects filters. Direct links locate their
row within the filtered queue; a row outside it does not invent neighbours. Run/row-specific forms reset
on navigation. Source-page inputs clamp to valid pages. Invalid numeric fields show an actionable error.

## Excel downloads and review state

Overview exposes **Download Excel** alongside its main actions. Its popover offers **Summary** and
**Complete details**, states that each SKU gets a worksheet, and explains importable decisions/comments.
It focuses the first option when opened, closes on outside interaction, and restores the trigger on Escape.
Keep the popover within the narrow viewport. Viewers cannot use review exports or mutation controls.

Use **Exact**, **Equivalent**, **Potential**, **Mismatch** and **Unmapped** in the interface. Never relabel
Potential or Unmapped as a confirmed defect. Saved decisions, pending approvals, approved findings and
needs-more-information states must remain distinguishable.

## Interaction, copy and recovery

- Prefer native links, buttons, disclosures, labels, fieldsets and checkboxes with accessible names.
  Icon-only controls need an action label. Hints/errors must be associated with the relevant field.
- Review shortcuts (`j/k`, brackets, Enter, `a/c/o/n`, Escape, `?`) yield to inputs, links, buttons,
  disclosures and dialogs. Do not consume native control keys or browser modifier shortcuts.
- Explain an empty result and how to recover. Loading reflects the content shape; pending actions expose
  busy/disabled states. Screen errors retain recovery/navigation instead of blanking the entire app.
- Use concise sentence-case copy and readable issue names. Avoid decorative slogans, invented metrics,
  heavy nested panels, colour-only meaning, emoji icons or white text on the resting orange action.
- Phosphor icons and fonts ship with the app. Decorative page/bar arrival animations are disabled;
  keep small feedback transitions and respect reduced-motion preferences. Keyboard navigation stays immediate.

## Validation when changing the interface

Run `npm test` and `npm run build` in `ui/`. Check the affected route at desktop and narrow widths, in
both themes and with keyboard focus. Cover loading, empty, error, long text, read-only access and the
relevant list page boundaries. Verify source links and saved form state with synthetic fixtures.

The last UI pass used the in-app browser and an emulated narrow viewport. It does not certify physical
mobile devices, Safari/Firefox, every dataset or public-release readiness. Keep validation artifacts
local under `out/`; do not commit real BD screenshots, source documents or review databases.

## Invitations

The signed-out form offers Sign in and Accept invitation. Registration requires the invited BD address,
code and matching passwords. Administrator invitation creation explains trusted private delivery and
expiry; the one-time read-only code supports copy/manual selection and hiding. No email-sent success
message is shown. Revoking a pending code does not change an already created account’s access.

## Help and privacy

Tutorial and Privacy are accessible from the sidebar footer and sign-in screen. The tutorial uses topic navigation on desktop, a topic selector on narrow screens, ordered task instructions, previous/next links and an all-topics view. Privacy shows the complete notice. Both offer Markdown downloads and use the same bundled typography and theme as the app. No customer screenshots or source documents are included.

## Document text coverage

Label/drawing detail offers **Comparison entries** and **All recognized text** as explicit choices.
The latter includes headers, notes and unparsed text; these lines do not enter component matching.
Both views retain search, source-page filters, confidence and clickable page highlights. Lists paginate
at 100 rows. Structured header values expand as readable details. Older-run empty states explain that a
new cross-check is needed; existing review evidence is never rewritten.
