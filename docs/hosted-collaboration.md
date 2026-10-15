# Accounts, sharing and deployment

Kaizen currently runs locally. The Dockerfile and `render.yaml` prepare a future shared deployment;
no Render service has been deployed. GitHub CI tests/builds the app and does not deploy it.

## Accounts and access

Registrations accept `bd.com` by default (`KAIZEN_ALLOWED_DOMAINS` can change the allowed domains).
Signup creates an approved regular profile; pending profiles become approved after valid sign-in.
New users do not become administrators. Revoked accounts stay blocked and their sessions are ended.
Administrators manage roles/revocation through **Manage users**; the last approved administrator is protected.

| Access | Run capabilities |
| --- | --- |
| Owner | Review, approve, import/export, copy and manage action items; rename/share and enable closed testing. |
| Edit | Review, approve, import/export, copy and manage action items. |
| View | Browse comparisons and source previews; no changes, approvals, copies or review exports. |

Owners use **Share and rename** to grant approved profiles View/Edit access or revoke a grant.
Application administrator status does not grant access to private runs. Terminology changes need an
administrator; ground-truth verification/evaluation/exports also need Edit access to that run.

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

## Optional shared password provider

Local salted-scrypt accounts are the default. Supabase can check passwords across installations;
profiles/roles, Kaizen sessions, run grants, documents and reviews remain in each configured workspace.
It does not synchronize them. Registration is still immediate after provider credentials are valid.

This integration has no confirmation/reset-email workflow. Its configured Supabase project must allow
password signup without required confirmation emails. Existing unconfirmed accounts need operator help.
Use the project's publishable key; legacy anon keys are accepted for compatibility. Kaizen rejects secret
and service-role keys. See Supabase's [API-key guide](https://supabase.com/docs/guides/getting-started/api-keys)
and [password-auth guide](https://supabase.com/docs/guides/auth/passwords).

```bash
.venv/bin/kaizen auth supabase "https://YOUR_PROJECT.supabase.co" "YOUR_PUBLISHABLE_KEY"
.venv/bin/kaizen auth show
# Return this workspace to local accounts when appropriate:
.venv/bin/kaizen auth local
```

`KAIZEN_SUPABASE_URL` and `KAIZEN_SUPABASE_KEY` override stored provider configuration; set both or neither.
Restart `kaizen serve` after changing the provider configuration.
Bootstrap the local administrator before enabling the provider and ensure its address exists there too.
Provider accounts are not migrated from local password records. Forgotten provider passwords need an
authorized administrator's supported provider workflow; Kaizen sends no reset email. For local accounts,
`kaizen users reset <email>` clears the password account so it can register again; prior decisions retain identity.

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
