# Reviewer walkthrough

Use synthetic documents for demonstrations. Keep existing BD review data in its normal workspace.

```bash
npm --prefix ui ci
npm --prefix ui run build
.venv/bin/kaizen --workspace /tmp/kaizen-demo serve
```

Bootstrap an administrator in the isolated workspace as described in [account setup](hosted-collaboration.md), then open http://127.0.0.1:8765 and sign in. New users require a one-use invitation. If the normal app already uses that
port, stop it first or start the isolated demo with `serve --port 8766` instead. Accounts and data in the
demo workspace are separate from the normal workspace. Follow the displayed counts rather than quoting
fixed comparison totals: results depend on the engine and terminology version.

| Step | Screen | What to verify |
| --- | --- | --- |
| 1 | All runs | Choose **New cross-check → Try a demo** to create a synthetic run owned by the signed-in account. |
| 2 | Overview | Inspect SKU/document counts, coverage issues, original recommendations and current review progress. |
| 3 | Documents | Browse the SKU groups, filter files, open a document and inspect its extracted content and source pages. |
| 4 | Review queue | Filter by SKU, check or discrepancy. Search descriptions and item numbers; use pagination for longer lists. |
| 5 | Evidence | Open a comparison and inspect both sources, page references, explanation and uncertainty. **Potential** is a review request, not an approved match. |
| 6 | Review tools | Record a decision and comment, reload it, and inspect history. Approval is a separate action; self-approval needs explicit confirmation. |
| 7 | Terminology | Reviewers explicitly approve eligible one-to-one identities; others can adopt whole lists or selected entries from the shared library. Administrators manage imports and shared edits. Configuration and assembly membership are not synonyms. Existing runs retain their original snapshots. |
| 8 | Action items | Create an item from an unresolved comparison, assign its owner and status, then verify it against a later corrective run. A disappeared comparison is not proof of resolution. |
| 9 | Overview exports | Use **Download Excel → Summary** for totals/attention rows or **Complete details** for all comparisons/audit sheets. Both have SKU worksheets and importable decisions/comments. Download the certificate or annotated BOM separately. |
| 10 | Manage a run | Use Rename/Delete on Overview or All runs; restore from Deleted runs. Share View/Edit access with an existing approved account, or make an independent private copy. Copies do not inherit approvals or sharing. |
| 11 | Compare runs | Select an earlier run by name and inspect resolved, new and still-open discrepancies. |

For an Excel round trip, edit the SKU decision/comment columns and use **Import from Excel** on the review
queue. Preview first. Use an independent in-app copy if the original must remain unchanged; workbooks
are bound to their run IDs. Changes invalidate approval and do not rewrite engine evidence.

For curated pairing and attribute feedback, follow [closed testing](closed-testing.md). It requires
independent verification and sufficient held-out evidence; accepting a review decision does not train or
release a candidate automatically.

The current website uses a shared decision and explicit approval. Historical two-reviewer records and
legacy CLI commands remain available, but selecting reviewer slots and blind review are not website steps.

If the browser is unavailable, `kaizen demo` produces an evaluated run and workbook. See the command
help with `kaizen --help` and the relevant subcommand for report, diff, terminology and review-import commands.

For the complete user-facing walkthrough, use [How to use Kaizen](user-guide.md) or Tutorial in the website.
