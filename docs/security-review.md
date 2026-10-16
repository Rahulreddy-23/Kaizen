# Security and data handling

This is an implementation guide for the current prototype, not a penetration test or regulatory
validation. See [accounts, sharing and deployment](hosted-collaboration.md) for operator setup.

## Identity and access

- New registration requires an administrator-issued, email-bound invitation for an `@bd.com` address.
  Invitations are random 256-bit codes, stored as SHA-256 hashes, shown once, expiring within 72 hours
  by default (API range 1–168 hours), revocable and consumed atomically with local account creation.
  Failed signup does not consume a valid code. Reissuing invalidates older codes; losing the inviter’s
  administrator access invalidates their outstanding codes. Invitation metadata never returns hashes.
- Invite-only access depends on an administrator checking identity and delivering the code privately.
  It does not establish automatic email ownership verification or BD SSO. Existing approved accounts
  are retained; a valid password never promotes missing, pending or revoked membership.
- Local passwords use salted scrypt. The optional external password provider is configured explicitly;
  account roles, sessions, run grants and documents remain in the Kaizen workspace.
- Each run has an owner and explicit View/Edit grants. Application administrators do not automatically
  gain access to private runs. Revocation ends an account's sessions; the last active administrator is
  protected from removal.
- Mutations use the authenticated identity, same-origin checks and run permissions. Review updates use
  revisions to reject stale writes. Changing a decision invalidates its approval; self-approval is
  separately confirmed and recorded.
- Confidential/hosted sessions expire after eight hours on both the server and cookie. Sign out to end a session sooner. Legacy local mode retains its existing session behavior.

- Shared terminology publishes the explicitly approved equivalence and attribution to approved users.
  Each account must adopt other reviewers’ additions. Selections are version-pinned and server-scoped to
  the authenticated account. Changes do not silently update other accounts; deactivation/deletion blocks
  future use across accounts. Existing runs retain evidence snapshots. Do not put private document content
  in publicly shared terminology notes unless its application-wide visibility is intended.

## Storage and processing

- Documents, rendered previews, accounts and reviews belong in the workspace. Real BD sources,
  credentials, SQLite databases/sidecars and generated outputs are excluded from Git and Docker context.
  The versioned golden documents are synthetic fixtures used for reproducible tests and demonstrations.
- Hosted/confidential mode enforces local OCR/matching, blocks external AI providers even when configured, and refuses external password providers. In non-confidential local operator mode, optional AI requires explicit configuration and can transmit description/SKU strings.
- Uploads validate paths and sizes. Hosted mode disables arbitrary server-path imports. Source hashes
  and terminology snapshots identify a run's inputs. Audit history includes reviewer-entered business
  content, so exports and backups require the same handling as source documents.
- Workbook exports store formula-like values as literal text. CSV terminology exports escape such values
  for spreadsheet safety. Imports validate the run identity and values before applying changes.

Both per-SKU Excel variants and portable bundles contain business/review content. Importing decisions
checks the workbook run identity, stable row IDs and stale-write conflicts; changing a decision removes
its approval. Terminology imports and independently verified learning datasets use separate workflows.

## Hosting and operations

The Singapore Render pilot has been provisioned; see [the Singapore pilot plan](testing-launch.md). API responses use no-store headers, response hardening blocks framing, and the hosted launcher suppresses query-bearing access logs. Confidential-mode errors log error types and reference IDs without exception text/tracebacks. The supplied Render configuration enables Secure cookies over HTTPS and uses one process/worker with a persistent
workspace. Local HTTP development uses non-Secure cookies. SQLite access is serialized within the
process; multiple application instances require a shared database and document storage design.

Back up the entire workspace, including the database and source files. Use SQLite's backup API or stop
writes while taking a consistent copy. Define document retention and restoration procedures before a
shared deployment. Never commit bootstrap passwords or workspace databases. CI checks lint, regression
tests and synthetic accuracy; those checks do not establish production security or real-data accuracy.
