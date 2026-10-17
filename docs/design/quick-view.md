# Quick view

Mode: Operate. Extend the existing reviewer design system. Reviewers choose a SKU in a run, inspect
saved comparisons in BOM / Label / Diagram columns, then select an entry to inspect three source previews.

- Route: `/runs/:runId/quick-view`. Entry points: run navigation, Overview and Documents.
- SKU buttons show sequential labels plus actual SKU codes; membership comes from the saved run groups.
- Comparison rows follow recorded pairings. No text similarity, transitive equivalence or new matching
  rule is introduced. Original source rows remain visible, including unpaired and exempt entries.
- Green text/highlights: a recorded pair with current Exact/Equivalent classification, no pending
  review and no unresolved finding. Orange: unmapped, conflicting or pending evidence. Neutral: not compared.
  A clean pair does not clear a conflicting third comparison. Written status labels accompany colour.
- All extracted text uses independent source order, not matched row alignment. Notes/headers remain
  neutral; component context may colour the text within its source box. Where full text was not saved,
  show original parsed-row evidence and explain the limitation.
- Selecting an entry navigates to the previews. Each source has its own document/page controls and zoom;
  previews render at 180 DPI with a default 125% reading zoom. Expand documents uses the full window
  with focus containment, Escape/close recovery and previous/next entry controls. Each pane scrolls
  independently and offers 50–200% zoom or Fit width. The clicked entry determines its exact page/box, including multiple entries in one column.
  Missing counterparts have no invented box. Spreadsheet sources retain raw text and sheet/row locators.
- Search/status filters and 100-row pagination bound the matrix; its header stays visible inside its
  scroll area. Three previews sit side by side on desktop and stack on narrow screens. Dense table
  overflow stays within the matrix. Back to comparison and Clear selection provide explicit recovery.
- Default to compared entries; All entries includes exempt/unpaired source rows. Keep search controls
  and SKU navigation available while requests load, and hide stale rows until the response arrives.
- Switching SKU, run, mode or filters clears the selection. Refresh picks up current review status.
- The surface is read-only, including for editors; decisions and approvals remain in Evidence.
  Authentication, run sharing, deleted-run protection and private response headers apply unchanged.
