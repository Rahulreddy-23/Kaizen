# Accounts, sharing and deployment

Kaizen supports local use and an invite-only Render pilot in Singapore. The Dockerfile and
`render.yaml` define the hosted configuration. The [pilot plan](testing-launch.md) targets a $27.50
monthly base before tax and extra usage. GitHub CI validates the app and deployment image; Render controls deployment.

## Accounts and access

Registration is invite-only and restricted to `@bd.com`. Local salted-scrypt accounts require no external
identity service. A password never promotes pending or revoked membership. Existing approved accounts remain
approved; administrators should review their existing membership before a shared deployment.

1. Bootstrap the first administrator using `KAIZEN_ADMIN_EMAIL` and a private `KAIZEN_ADMIN_PASSWORD`.
   Remove the bootstrap password after successful setup. Operator bootstrap is the only first-admin path.
2. Open **Manage users → Invite a reviewer**, enter the intended BD address and create an invitation.
3. Check the recipient’s identity and deliver the displayed code privately through a trusted BD channel.
   The app does not send email. Codes appear once, expire after 72 hours, and are bound to that address.
4. The recipient uses **Accept invitation** to choose a password. Registration consumes the code exactly once.
   A failed password validation does not consume it. Only code hashes are stored; codes never enter the audit log.
5. Revoke unused codes under **Pending invitations**. Reissuing invalidates older codes for the same address.
   Codes from a revoked/demoted inviter are invalid. Manage account roles/revocations separately; the last
   approved administrator is protected. Revoking an accepted invitation does not revoke its account.

Invite-only access relies on trusted delivery; it is not automatic email ownership verification or BD SSO.
Hosted/confidential sessions expire after eight hours. Hosting approval, retention and backup policy remain operator work.

| Access | Run capabilities |
| --- | --- |
| Owner | Review, approve, import/export, copy and manage action items; rename/delete/restore, share. Closed-testing collection is automatic. |
| Edit | Review, approve, import/export, copy and manage action items. |
| View | Browse comparisons and source previews; no changes, approvals, copies or review exports. |

Owners use **Share run** under Overview’s run settings to grant approved profiles View/Edit access or revoke a grant.
Application administrator status does not grant access to private runs. Reviewers can explicitly approve new one-to-one terminology; administrators manage shared edits, imports and
revocations. Ground-truth verification/evaluation/exports also need Edit access to that run.

Owners can rename/delete from All runs or Overview. Deleted runs are hidden from active lists and all
shared access. Restore from **All runs → Deleted runs** retains sources, review history and existing
sharing; only the owner can see or restore deleted runs. The owner can also permanently delete a deleted run after typing DELETE: run files, exports, review history and run-specific learning records are erased. Shared files, original local folders, independent copies and approved shared terminology survive. Storage failures leave a durable cleanup job that retries at startup; backups follow operator retention. Independent copies remain separate.

A saved decision records the signed-in actor and revision. Approval is separate; an author or run owner
explicitly confirms self-approval. Edits remove the old approval while retaining history. Independent
verification of ground truth still requires a different administrator.

## Excel downloads and independent work

**Download Excel** on Overview offers **Summary** (totals, current status and attention rows) and
**Complete details** (all comparisons/evidence plus supporting audit sheets). Each uses SKU worksheets
with importable reviewer decisions/comments. On the review queue, use **Import from Excel**, preview,
then apply. Run IDs and row IDs bind the workbook to its originating run; stale decisions are conflicts.
Engine/source columns are not imported and changed decisions invalidate approvals.

**Make a copy** creates a private run with independent sources, working decisions and action items.
Sharing/approvals do not transfer. To preserve the original, make the copy first, download that copy's
workbook, then import into the same copy. **Download independent copy** supplies source files, portable
run JSON, history and an editable workbook; downloading alone does not register a new in-app run.

## Shared terminology and account choices

**Terminology → Shared library** lists approved entries with the approving account, timestamp, scope,
item anchors and version. Reviewers can explicitly approve an eligible evidence pair or a new relationship.
This publishes the equivalence to the application’s approved users and adds it to the approver’s account.
Ordinary review decisions do not automatically publish synonyms. Ambiguous matches, assemblies,
configuration changes and held-out examples retain their existing eligibility restrictions.

Use **Approved by** to browse a person’s list. **Add entire list** adds the active entries in the current
search/scope/reviewer filters. Alternatively select any subset, then **Add selected to my account**.
Selections are saved per account, apply on any device using the same workspace, and never follow future
additions automatically. **My terminology** shows included rules; selected additions can be removed anytime.
Packaged defaults remain included. On migration, authors retain their own existing active terms once.

Uploads use that uploader’s selected versions plus packaged defaults. Copies retain their source run’s
snapshot. Shared runs keep the uploader’s snapshot; a collaborator’s preferences never rewrite that run.
Edits show an update notice, preserving selected versions until the user reviews and adds the new version.
Administrator deactivation/deletion immediately excludes the rule from future runs for all accounts;
existing evidence snapshots remain intact. Removing an adopted override of a packaged default returns
to its packaged version. Shared usage counts only include runs accessible to the requesting account.

Administrators retain import/edit/deactivate/delete controls. A completed import also adopts those active
entries for its importer; other accounts choose whether to use them. Approval attribution is server-derived
from version history, never from an uploaded author field or a client-supplied account name.

## Legacy external password provider

Local accounts are sufficient for this app; no new Supabase credentials are needed. The existing optional
provider adapter remains compatible for installations already using it. It checks passwords only: workspace
membership, invitations, roles, files and account terminology remain local to that installation. A provider
account alone cannot sign in to a new workspace. Return to local accounts with `kaizen auth local` only after
ensuring the local administrator can sign in; remove any `KAIZEN_SUPABASE_URL` / `KAIZEN_SUPABASE_KEY`
environment overrides and restart. Password records are not migrated between providers automatically.

For a forgotten local password, the operator runs `kaizen users reset <email>`, then an administrator issues
a new invitation. Prior decisions retain their recorded identity. Provider password recovery remains an
operator task. No reset or confirmation email is sent by Kaizen.

## Future Render setup

1. Create a Render Blueprint from this repository using `render.yaml`.
2. Confirm `KAIZEN_ADMIN_EMAIL` and set `KAIZEN_ADMIN_PASSWORD` as a secret for initial bootstrap.
3. Deploy the single Docker web service with its persistent disk. The initial setup creates the local
   administrator; later starts retain the workspace. Remove the bootstrap password after successful setup.
4. Validate the HTTPS URL, sign-in, upload/OCR, source previews, permissions, Excel round trips and backups
   before inviting testers. Deployment does not establish accuracy on new document layouts.

The manifest prepares one instance/worker, `/var/data/kaizen` storage, hosted mode and Secure cookies.
Hosted mode disables arbitrary server-path imports. Local HTTP development should not enable Secure
cookies. Keep the persistent disk attached; see [Render disks](https://render.com/docs/disks) and
[Docker services](https://render.com/docs/docker). The manifest does not create or purchase hosting by itself.

Back up the entire workspace, including database, source files and learning artifacts. Stop writes or
use SQLite's backup API for a consistent database snapshot. Multiple instances require a shared database
and object-storage design. Retention, restoration and production identity/session policies remain operator work.

## Existing workspaces

Additive schema initialization preserves legacy records. Operator bootstrap uses `KAIZEN_ADMIN_EMAIL`
and `KAIZEN_ADMIN_PASSWORD`; historical runs without an owner are assigned to that administrator because
the uploader was not previously stored. Historical two-reviewer CLI data remains readable; current web
work uses one shared decision and explicit approval. Keep real source/review data out of Git and Docker context.
