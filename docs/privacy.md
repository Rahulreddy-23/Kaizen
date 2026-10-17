# Privacy and document handling

How this limited-testing application handles accounts, documents and review data.

## Scope and purpose

Kaizen compares documents and records human review decisions for invited testers.

This notice describes the application’s implemented behavior and the Render pilot. It is not evidence that BD has approved a particular hosting contract, data classification or processing region. Confirm those requirements with the application operator before uploading confidential material.

The pilot uses a single service in Singapore, with a private persistent workspace. Hosting status and the final service address are confirmed separately; a local preview does not upload documents to Render.

## What is stored

The workspace stores the data needed to perform and retain a review.

This includes uploaded documents, extracted text and images, document hashes, run metadata, review comments and decisions, approvals, action items, learning annotations and exported reports.

Accounts store email addresses, roles, salted password hashes and server-side sessions. Invitations store recipient and inviter metadata and a hash of the code. Invitation codes are displayed once rather than retained as readable codes.

## Who can access it

A run is private to its owner unless the owner grants access.

Approved accounts can access only runs they own or that have been explicitly shared with them. View access permits browsing sources and results. Edit access permits review changes, approvals and exports. Application administrator status alone does not open another person’s private run.

Application administrators can inspect application-wide audit records, which may include run names, reviewer comments and terminology notes. Restrict this role to trusted operators.

The application operator and people with privileged hosting, disk or backup access may access stored data. This server-side processing architecture does not provide end-to-end encryption that excludes the operator or hosting provider. Do not interpret a private run as a guarantee that no authorized infrastructure personnel can ever access it.

People who receive a document or workbook export can keep copies outside Kaizen. Removing a share cannot recall copies already downloaded.

## OCR, matching and AI

Confidential mode blocks external AI adjudication and external password providers.

OCR, extraction and deterministic matching run in the application process. Confidential mode prevents configuration from enabling external AI adjudication or an external password provider. Documents and extracted descriptions are not sent to AI model APIs by these workflows.

Closed testing collects review activity automatically for owned runs, including existing active runs after an application update. Verified learning requires independently verified feedback. It can create local candidate rules and evaluation datasets within the workspace. Ordinary review approval does not automatically train or release a new model.

This notice makes no claim about a hosting provider’s contractual use of customer data. The operator must assess the provider’s agreement and subprocessors against BD requirements.

## Shared terminology

Approving a shared term intentionally publishes it to the invited reviewer group.

The shared library includes canonical terms, aliases, scope, anchors, notes and approving-account attribution. These are visible to approved users across the application, even when the source run itself is private.

Approve only terminology and notes that may be shared with that audience. Other accounts choose whether to adopt the terms. Their selections apply to future runs; existing snapshots remain recorded.

## Hosting and security controls

The Render pilot uses HTTPS and a persistent disk encrypted at rest by the provider.

The hosted configuration uses Secure, HttpOnly cookies, same-origin mutation checks and invitation-only registration. Confidential mode restricts an authentication session to eight hours, prevents browser caching of API responses and suppresses detailed exceptions and query-bearing access logs from application hosting logs.

Rendered source pages may be reused in a bounded, process-local memory cache (up to 64 MiB). Page requests always recheck account/run access and source availability. The cache is not persisted or sent to an external service; entries expire through eviction or a server restart. A visible browser tab checks an opaque change token every five seconds to update saved review data without repeatedly downloading unchanged results.

Source documents and workspace databases are excluded from the Git repository and Docker build context. Packaged synthetic demonstration documents may be included; they are separate from BD source documents.

Render and its infrastructure subprocessors process hosting data. Provider-managed encryption is not customer-exclusive encryption, and this notice does not promise zero unauthorized access or zero security incidents. Keep hosting access restricted and use MFA on operator accounts.

## Retention, deletion and backups

Recoverable deletion does not erase the underlying documents.

Delete run moves a run to Deleted runs. Its sources, decisions, history and previous sharing remain stored so the owner can restore it. The operator must handle permanent removal requests and any required retention schedule; automatic permanent purging is not currently provided.

Backups and provider disk snapshots may retain earlier data. Access revocation and application deletion do not immediately remove all backup copies. The operator must define a backup expiry and restoration process appropriate to the documents.

To request permanent deletion or report unintended access, contact the application administrator or the person who supplied your testing invitation. No unverified privacy-contact address is published here.

## Your controls

Use the smallest audience and data set needed for the review.

1. **Before uploading.** Confirm that the environment and region are approved for the documents. Start with synthetic or approved non-sensitive files for a new pilot.

2. **During review.** Share only with intended approved users, avoid confidential details in shared terminology notes and use approved channels for exported files.

3. **After review.** Remove unnecessary grants, sign out and ask the operator to apply the agreed retention policy. Report any suspected exposure promptly.
