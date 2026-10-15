# Reviewer walkthrough

Use synthetic documents for demonstrations. Keep existing BD review data in its normal workspace.

```bash
.venv/bin/kaizen --workspace /tmp/kaizen-demo demo
cd ui && npm ci && npm run build && cd ..
.venv/bin/kaizen --workspace /tmp/kaizen-demo serve
```

Open http://127.0.0.1:8765 and register or sign in with a BD account. If the normal app already uses that
port, stop it first or start the isolated demo with `serve --port 8766` instead. Accounts and data in the
demo workspace are separate from the normal workspace. Follow the displayed counts rather than quoting
fixed comparison totals: results depend on the engine and terminology version.

| Step | Screen | What to verify |
| --- | --- | --- |
| 1 | All runs | Open the synthetic run, or use **Load demo dataset** if it is not listed. |
| 2 | Overview | Inspect SKU/document counts, coverage issues, original recommendations and current review progress. |
| 3 | Documents | Browse the SKU groups, filter files, open a document and inspect its extracted content and source pages. |
| 4 | Review queue | Filter by SKU, check or discrepancy. Search descriptions and item numbers; use pagination for longer lists. |
| 5 | Evidence | Open a comparison and inspect both sources, page references, explanation and uncertainty. **Potential** is a review request, not an approved match. |
| 6 | Review tools | Record a decision and comment, reload it, and inspect history. Approval is a separate action; self-approval needs explicit confirmation. |
| 7 | Terminology | An administrator can review eligible one-to-one identities and import approved relationships. Configuration and assembly membership are not synonyms. Existing runs retain their original snapshots. |
| 8 | Action items | Create an item from an unresolved comparison, assign its owner and status, then verify it against a later corrective run. A disappeared comparison is not proof of resolution. |
| 9 | Overview exports | Download the workbook and certificate; open an annotated BOM from Documents. Check source hashes and reviewer history in the outputs. |
| 10 | Share and rename | Rename the run, share View/Edit access with an existing approved account, or make an independent private copy. Copies do not inherit approvals or sharing. |
| 11 | Compare runs | Select an earlier run by name and inspect resolved, new and still-open discrepancies. |
| 12 | Business case | Distinguish measured review effort from the projection after approved terminology. Keep assumptions visible. |

For curated pairing and attribute feedback, follow [closed testing](closed-testing.md). It requires
independent verification and sufficient held-out evidence; accepting a review decision does not train or
release a candidate automatically.

The current website uses a shared decision and explicit approval. Historical two-reviewer records and
legacy CLI commands remain available, but selecting reviewer slots and blind review are not website steps.

If the browser is unavailable, `kaizen demo` produces an evaluated run and workbook. See the command
reference in [README](../README.md) for report, diff, terminology and review-import commands.
