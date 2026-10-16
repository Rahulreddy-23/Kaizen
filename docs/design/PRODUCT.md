# Product context

Kaizen Cross-Check helps BD engineering and quality reviewers compare JDE BOMs, labels, drawings,
PCOs and label revisions. Recommendations retain source evidence; people decide and approve.
See [the design system](DESIGN.md) for interface rules and [architecture](../final-architecture.md)
for implementation boundaries.

## Current workflow

1. Accept an administrator-issued invitation for your BD address, choose a password and sign in. Invitation delivery requires a trusted BD channel; it is not automatic email verification.
2. Open **All runs → New cross-check**. Upload a project folder or individual PDF/XLSX/XLSM/CSV files,
   review the selected-file list and remove unwanted files, or choose **Try a demo**. Choosing again
   replaces the selection; cancelling the picker keeps it. Word files are unsupported.
3. Inspect **Overview** and **Documents**. Documents use actual SKU associations; shared sources appear
   once, with extraction warnings and source details available.
4. Filter **Review queue**, open **Evidence**, inspect both source pages and save a decision.
   Approval is separate; changing a decision clears its previous approval.
5. Use **Download Excel** on Overview: **Summary** shows totals and rows needing attention;
   **Complete details** includes all comparisons, evidence and supporting audit sheets. Both provide
   SKU worksheets and importable decision/comment columns. PDFs and independent-copy ZIPs remain available.
6. Track action items and compare corrective runs. Use **Closed testing** for separately verified
   ground truth and candidate evaluation, not as an automatic approval or live-model update.

Owners can rename or delete from All runs or Overview. Deletion moves a run to **All runs → Deleted runs**,
where only its owner can restore it. Documents, decisions and existing sharing are retained; deleted runs
are inaccessible to everyone until restored. Independent copies are unaffected.

The website uses one shared decision and explicit approval. Reviewer-slot selection and blind-review
steps belong to the legacy CLI workflow; they are not the current website interaction.

## Roles and access

| Role | Capabilities |
| --- | --- |
| Run owner | Review/edit/export/copy; rename/delete/restore and manage View/Edit sharing; enable closed testing. |
| Editor | Review, approve, import/export, copy and manage action items on the shared run. |
| Viewer | Browse results and source previews; no changes, approvals, copies or review exports. |
| Application administrator | Invite/manage users; import/edit/deactivate shared terminology. Approved reviewers can publish new equivalences and choose personal entries. Learning verification/evaluation/exports also require Edit access to the run. Administrator status does not reveal private runs. |

An author or run owner explicitly confirms self-approval of a normal review decision. Ground-truth
verification requires a different administrator from its author; self-approval cannot create training truth.

## Screen inventory

Routes below follow the `#` in the browser URL. All run destinations require access to that run.

| Route | Screen and job |
| --- | --- |
| `/` | All runs: search, ownership filters, pagination and new cross-checks. |
| `/runs/:runId` | Overview: current review progress, original engine totals, exports and run management. |
| `/runs/:runId/review` | Review queue: filters, current findings and comparison selection. |
| `/runs/:runId/rows/:rowId` | Evidence: explanations, source previews, decisions/history and enabled ground-truth forms. |
| `/runs/:runId/documents` | Documents: grouped source list, filters and extraction warnings. |
| `/runs/:runId/documents/:docId` | Document: extracted items, source pages and deep links. |
| `/runs/:runId/learning` | Closed testing: enrollment, drawing applicability, annotations and candidate reports. |
| `/runs/:runId/mining` | Suggested matches: terminology worklist and approval eligibility. |
| `/runs/:runId/diff` | Compare runs: new, resolved, still-open and missing comparisons. |
| `/terminology` | Terminology: reviewer attribution, reviewer filters, whole-list or partial account adoption, version updates; administrators manage/import shared entries. |
| `/action-items` | Action items: named run selection, status and follow-up work. |
| `/admin` | Manage users: administrator-only invitations, search, roles and revocations. |
| `/tutorial` | Public, topic-based walkthrough with a downloadable guide. |
| `/privacy` | Public privacy and document-handling notice, including retention and operator access. |
| `/profile` | Profile: account identity/role, run counts, theme and sign out. |

The retired `/runs/:runId/business` address redirects to that run’s Overview.

Sign-in, missing-page, inaccessible-run, loading, empty and error states are part of the product.
The primary task is desktop document review; narrow screens must preserve access and usable controls.
Fonts and icons are bundled. Hosted/confidential mode blocks external authentication and AI, uses eight-hour sessions, and keeps API responses out of browser caches. Local operator workflows can explicitly configure external providers outside confidential mode.

## Terminology adoption

Explicitly approving a one-to-one relationship publishes the session-derived approver and time, and
adopts that version for its author. Other users choose whole filtered lists or selected entries; choices
are saved per account. Packaged defaults remain included. Future uploads use the uploader’s choices;
shared/copy/existing runs retain their recorded snapshots. No automatic following of reviewers or edits.
New versions require review and adoption; administrator deactivation/deletion blocks future use globally.
A normal comparison decision never automatically publishes a shared synonym.

## Product invariants

- Keep original engine evidence/classification distinct from the current decision, approval and finding.
- Display `MISSING` as **Unmapped**. No accepted counterpart does not establish a physical defect.
- Component candidates, assemblies, pack/pair bases, explicit alternatives and uncertain drawing
  applicability remain review questions until the relevant source evidence is confirmed.
- Terminology represents approved one-to-one identity. Configuration, assembly membership, ambiguity
  and conflicting specifications cannot be saved as synonyms.
- Counts come from the run and current review snapshot. Estimates identify their assumptions.
- Preserve filters during review navigation; source links open the correct retained document/page.
- Keep training and evaluation identities separate. Verified candidate rules do not replace live results.

## Delivery status and voice

The app currently runs locally. Docker/Render files prepare a later deployment; no Render service is
established by pushing this repository. Real documents, reviews and learning artifacts stay out of Git.

Use short, specific, sentence-case labels: **Record decision**, **Download Excel**, **Try a demo**.
Errors explain recovery. Avoid claiming a physical absence, proven accuracy or release readiness from
matching scores, synthetic tests or an unresolved review queue.
