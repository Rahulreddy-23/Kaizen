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
  previews render at a stable 300 DPI, defaulting to 200% for dense BOM rows and 125% for labels/diagrams.
  Open document reader uses the full window with focus containment and Escape/close recovery.
  Previous/next entry controls navigate the current filtered page. Each pane supports drag-to-pan,
  keyboard scrolling, 25–400% zoom, Fit width and explicit Locate selected recovery. Touch supports one-finger pan and two-finger pinch; trackpad pinch/Ctrl-wheel zooms around the pointer. Only document canvases intercept these gestures. Zoom preserves the source point under the gesture instead of snapping back to evidence. The clicked entry determines its exact page/box, including multiple entries in one column.
  Missing counterparts have no invented box. Spreadsheet sources retain raw text and sheet/row locators.
- Search/status filters and 100-row pagination bound the matrix; its header stays visible inside its
  scroll area. Desktop layouts offer three panes, any document pair, or a focused single source. Drag dividers
  to resize; keyboard arrows, Home/End, Enter and double-click adjust/reset a divider. Reset widths
  rebalances the layout. Focus and Restore split view retain each source’s page and zoom. Narrow
  containers use full-width source tabs rather than shrinking three pages. Selected wording remains
  readable above each page; raw text and locators stay available. Dense table
  overflow stays within the matrix. Back to comparison and Clear selection provide explicit recovery.
- Default to compared entries; All entries includes exempt/unpaired source rows. Keep search controls
  and SKU navigation available while requests load, and hide stale rows until the response arrives.
- Switching SKU, run, mode or filters clears the selection. Refresh picks up current review status.
- The surface is read-only, including for editors; decisions and approvals remain in Evidence.
  Authentication, run sharing, deleted-run protection and private response headers apply unchanged.
- Owners/editors can download this SKU or all SKUs as Excel: one BOM/Label/Diagram comparison sheet per SKU, plus original source text, quantities and page/row locators. Export includes all entries regardless of screen filters; current saved statuses match Quick view. Literal text cannot execute as formulas. It cannot be imported as review decisions. Viewers and blind sessions cannot export.


## Reader design references

The reader combines [Bluebeam independent split views](https://support.bluebeam.com/revu/how-to/split-sync-and-unsplit-views.html),
[Acrobat side-by-side/single-source and previous/next navigation](https://helpx.adobe.com/acrobat/using/compare-documents.html),
and [VS Code resizable/maximized editor groups](https://code.visualstudio.com/docs/configure/custom-layout).
[WAI window-splitter guidance](https://www.w3.org/WAI/ARIA/apg/patterns/windowsplitter/) informs divider roles and keyboard controls.
The application-specific inference is to synchronize by saved evidence selection, with independent page/zoom/pan:
a BOM, label and drawing have different geometry and pagination, so equal page indices or scroll offsets would
not reliably show corresponding content. No external viewer, telemetry or document upload service is introduced.
Gesture handling follows [MDN pointer pinch guidance](https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events/Pinch_zoom_gestures) and [wheel events](https://developer.mozilla.org/en-US/docs/Web/API/Element/wheel_event), scoped to the canvas so ordinary page zoom remains available elsewhere.
