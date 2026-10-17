# How to use Kaizen

A practical guide from your first upload to an approved review.

## Start here

Start with a synthetic demo to learn the workflow before reviewing project documents.

1. **Open a practice run.** Go to All runs, choose New cross-check, then Try a demo. The app creates a separate run using synthetic sample documents.

2. **Check the sources.** Open Documents to inspect the files and extraction, then open Review queue and choose a comparison to see its source evidence.

3. **Save a review.** Choose a decision, add a comment and Save decision. Approval is a separate action. Use the following topics when you are ready to upload your own project.

A run is one saved set of documents, automated comparisons and review history. Engine recommendations still need human judgment.

## Sign in and invitations

Existing users sign in with their BD address and password. New users need an invitation.

1. **Get an invitation.** Ask an application administrator for a code issued to your exact BD email address. Administrators share codes privately through a trusted BD channel.

2. **Accept the invitation.** On the sign-in screen, choose Accept invitation. Enter the invited address and code, then choose and confirm a password of at least ten characters.

3. **Sign in.** After creating the account, use Sign in. Codes normally expire after 72 hours and can be used only once. An expired or revoked code needs a new invitation.

Already approved? Use your existing password; a new invitation is not needed. For password recovery, contact the administrator.

## Upload a project

Keep related BOMs, labels, drawings and PCOs together in a project folder, using SKU subfolders where possible.

1. **Start a cross-check.** In All runs, choose New cross-check. Enter a recognizable run name, such as the product and review date.

2. **Choose the documents.** Choose folder preserves SKU subfolders. Choose files accepts individual documents. To include several top-level folders together, put them under one project folder before choosing it.

3. **Review your selection.** Check the file names, paths, sizes and total. Remove unwanted files or use Clear all. Choosing again replaces the selection; cancelling the picker keeps it.

4. **Start the run.** Choose Start cross-check and wait for the results. A new upload creates a new run, so you can compare later corrections with the original.

Supported files: PDF, XLSX, XLSM and CSV, up to 250 MB per run. Word files are unsupported. For initial testing, use clean source PDFs or readable spreadsheets.

## Check extracted documents

Confirm that the app read the intended files before relying on any finding.

1. **Check coverage.** In the run Overview, inspect SKU and document counts and any coverage warnings. Missing source documents can prevent a comparison from being performed.

2. **Open Documents.** Inspect the SKU groups and shared documents. Open a file to see its extracted content, warnings and source details.

3. **Compare extraction with the source.** For PDFs, select an extracted line to locate it on the retained source page. For spreadsheets, use the recorded sheet and row information. Expand Why this category when a line’s role needs explanation.

Unreadable text, an incorrect SKU association or a missing drawing page can explain a bad comparison. Record unresolved evidence rather than approving a guess.

## Review and approve findings

Open Review queue in a run, narrow the list, then inspect each finding against its evidence.

1. **Find the relevant comparisons.** Filter by SKU, check type, classification or discrepancy; search descriptions or item numbers. Longer lists have pagination.

2. **Inspect Evidence.** Open a comparison. Read the explanation and inspect both source documents, their page references, quantities, units and specifications.

3. **Choose and save a decision.** Accept keeps the engine recommendation. Override changes its classification; to clear a flagged mismatch as a valid match, choose an Exact or Equivalent override. Confirm discrepancy records an observed issue. Needs more information keeps uncertainty visible. Add your reason and Save decision.

4. **Approve the saved decision.** Review the saved values, then choose Approve decision. If you are approving your own work, complete the explicit confirmation and use Confirm self-approval. Changes made later remove the old approval but keep its history.

Potential means review is needed. Unmapped means no counterpart was accepted; it does not prove a physical component is absent. Saving a decision is different from approving it.

## Choose shared terminology

Reuse confirmed one-to-one wordings while controlling the terminology your future uploads use.

1. **Approve an equivalence.** Use an eligible comparison’s Save as relationship tools, or Terminology → Approve relationship. Confirm that both wordings identify the same component and choose the appropriate scope and item anchors.

2. **See who approved it.** The Shared library shows the approving account, approval date and version. Your explicit approval adds that version to your account.

3. **Choose another reviewer’s entries.** Filter Approved by to the reviewer you want. Add entire list adds the active entries in the current filters. For a subset, tick the entries and choose Add selected to my account.

4. **Manage your choices.** Open My terminology to see included entries. Select additions and Remove selected from my account when no longer wanted. New versions show an update notice; review them before adding. Lists do not automatically follow future additions.

Publishing terminology makes those terms and notes visible to all approved application users. Publish only what is approved for that audience. Packaged defaults remain included; existing runs keep their snapshots. Assemblies and configuration relationships are not synonyms.

## Download and import Excel

Use Excel for a review handoff or offline decisions, then import changes into the same run.

1. **Choose a download.** On Overview, use Download Excel → Summary for totals and attention rows, or Complete details for every comparison and supporting audit sheets. Both include SKU worksheets and editable decision/comment columns.

2. **Review offline.** Edit the provided decision and comment fields. Keep the workbook’s run and row identifiers intact; source and engine evidence are not editable through decision import.

3. **Preview the import.** Open that run’s Review queue → Import from Excel. Preview the changes and resolve stale-value conflicts before applying. Changed decisions need approval again.

To work independently, first Make a copy in the app, then download and import that copy’s workbook. A workbook belongs to its originating run. Exports contain document and review content; share them through approved channels.

## Share and manage runs

Runs start private to their owner. Owners control who can view or change them.

1. **Share with an approved user.** On Overview, expand Run settings and exports → Share run. Choose an approved account and either Can view or Can edit and approve. Update or remove its grant when needed.

2. **Rename or delete.** Owners can Rename or Delete from Overview or All runs. Read the named confirmation before deleting.

3. **Restore or make a copy.** Deletion moves a run to All runs → Deleted runs. Only its owner can restore it, including its previous sharing. Make a copy creates an independent private run; approvals and sharing do not transfer.

Delete is recoverable: source files and review history remain stored. For permanent removal, contact the application operator. View-only users cannot change decisions, approve results or download review exports.

## Follow up and compare runs

Keep a traceable follow-up when corrected documents arrive.

1. **Record an action item.** Create an action item from an unresolved comparison, assign an owner and track its status on Action items.

2. **Upload corrected sources.** Create a new run with the corrected project files. Keep the original run as evidence of the earlier review.

3. **Compare results.** Open Compare runs under the new run and select the earlier run by name. Inspect new, still-open, changed and resolved findings. Use Verify and close for the relevant action items after checking the supporting evidence.

Gone means the comparison disappeared; it is not proof that an issue was fixed. Compare document coverage and source evidence before closing follow-up work.

## Understand closed testing

Closed testing collects review data automatically and curates independently verified feedback.

1. **Review normally.** Collection is on by default for eligible new runs, copies and existing active owned runs. No Enable step is needed. Editors can annotate correct pairings, attributes, drawing applicability and unresolved evidence.

2. **Get independent verification.** A different administrator verifies an annotation before it enters the verified dataset. Normal self-approval does not create independently verified ground truth.

3. **Inspect the candidate report.** Verified feedback can rebuild and evaluate a local candidate. Training and held-out evaluation identities stay separate; the report does not automatically replace the live matching rules.

For an ordinary document review, use the Review queue. Closed testing is not required to finish a review and is not an automatic release of a new model.

## Profile and appearance

Use the avatar in the top-right corner for account options.

1. **Open Profile.** Choose the avatar → Profile to see your account, role and run links.

2. **Change appearance.** Choose Switch to dark mode or Switch to light mode in the avatar menu, or change the theme on Profile. The browser remembers your preference.

3. **Sign out.** Use the avatar menu or Profile → Sign out, particularly on a shared computer.

## Invite reviewers

Only application administrators can invite new accounts or manage account roles.

For: Administrators.

1. **Issue a code.** Open Manage users → Invite a reviewer and enter the intended BD address. Choose Create invitation.

2. **Deliver it privately.** Copy the one-time code before leaving or hiding it. Verify the recipient and deliver the code privately through a trusted BD channel. The app does not automatically email codes.

3. **Revoke or reissue.** Open Pending invitations to revoke an unused code. Reissuing for the same address invalidates older outstanding codes. To revoke an existing account, use its account controls instead.

An existing account cannot receive a new signup invitation. Removing a run share, revoking an invitation and revoking account access are separate actions.
