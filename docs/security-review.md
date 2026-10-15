# Security and data handling

This is an implementation guide for the current prototype, not a penetration test or regulatory
validation. See [accounts, sharing and deployment](hosted-collaboration.md) for operator setup.

## Identity and access

- Registration accepts configured email domains (`bd.com` by default) and creates a regular account.
  Administrator approval is not required. Registration does not prove ownership of the email address.
- Local passwords use salted scrypt. The optional external password provider is configured explicitly;
  account roles, sessions, run grants and documents remain in the Kaizen workspace.
- Each run has an owner and explicit View/Edit grants. Application administrators do not automatically
  gain access to private runs. Revocation ends an account's sessions; the last active administrator is
  protected from removal.
- Mutations use the authenticated identity, same-origin checks and run permissions. Review updates use
  revisions to reject stale writes. Changing a decision invalidates its approval; self-approval is
  separately confirmed and recorded.
- Sessions do not expire automatically. Sign out to end a session. A wider deployment needs an approved
  identity-verification and session-lifetime policy.

## Storage and processing

- Documents, rendered previews, accounts and reviews belong in the workspace. Real BD sources,
  credentials, SQLite databases/sidecars and generated outputs are excluded from Git and Docker context.
  The versioned golden documents are synthetic fixtures used for reproducible tests and demonstrations.
- Parsing and deterministic matching run locally by default. Optional external AI suggestions require
  explicit configuration and transmit description strings and SKU/item identity. They do not approve
  pairings or modify review decisions.
- Uploads validate paths and sizes. Hosted mode disables arbitrary server-path imports. Source hashes
  and terminology snapshots identify a run's inputs. Audit history includes reviewer-entered business
  content, so exports and backups require the same handling as source documents.
- Workbook exports store formula-like values as literal text. CSV terminology exports escape such values
  for spreadsheet safety. Imports validate the run identity and values before applying changes.

Both per-SKU Excel variants and portable bundles contain business/review content. Importing decisions
checks the workbook run identity, stable row IDs and stale-write conflicts; changing a decision removes
its approval. Terminology imports and independently verified learning datasets use separate workflows.

## Hosting and operations

Render deployment is pending. The supplied Render configuration enables Secure cookies over HTTPS and uses one process/worker with a persistent
workspace. Local HTTP development uses non-Secure cookies. SQLite access is serialized within the
process; multiple application instances require a shared database and document storage design.

Back up the entire workspace, including the database and source files. Use SQLite's backup API or stop
writes while taking a consistent copy. Define document retention and restoration procedures before a
shared deployment. Never commit bootstrap passwords or workspace databases. CI checks lint, regression
tests and synthetic accuracy; those checks do not establish production security or real-data accuracy.
