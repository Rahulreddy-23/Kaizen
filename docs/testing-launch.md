# Limited-testing launch — 19 October 2026

Target: a small invited reviewer group, one operator, one Render service in Singapore.
Keep the existing local workspace separate; deploy an empty hosted workspace and use synthetic documents
for the first smoke test. Confirm the environment is approved for confidential BD documents before adding them.

## Budget

Checked against [Render pricing](https://render.com/pricing) on 16 October 2026:

| Item | Monthly base |
| --- | ---: |
| Hobby workspace | $0 |
| Web service, `1c-2g` (1 CPU / 2 GB RAM) | $25 |
| Persistent disk, 10 GB | $2.50 |
| Total before taxes and usage overages | **$27.50** |

Target: under $30 base; spending ceiling supplied by the owner: $40/month, with a preference for less than $30.
Do not add a Pro workspace, paid database, worker, paid domain or paid email service without revisiting the budget.
Tax, currency conversion and excess bandwidth/build usage can raise the actual invoice. This is not a hard billing cap.
The Hobby workspace includes 5 GB outbound bandwidth; review billed usage during the pilot.
Use Render’s supplied HTTPS domain and manual private invitation delivery for the initial group.

## Pilot configuration

- `render.yaml`: Singapore, `1c-2g`, one 10 GB disk, health check and deploys after CI passes.
- `Dockerfile`: bundled UI, Tesseract and RapidOCR; local documents, workspaces, databases and secrets excluded.
- `/var/data/kaizen`: durable documents, account database, decisions, selections and audit history.
- One worker/instance. A disk-backed deployment has brief downtime on restart/redeploy and no horizontal scaling.
- Hosted/confidential mode blocks external AI adjudication and external password providers, even if accidentally configured.
- Secure HttpOnly cookies; eight-hour server-side sessions; API no-store headers; reduced cloud logging.
- Public tutorial and factual privacy/document-handling notice. Run contents still require account and run permission.

## Create the Render service

1. Sign in to [Render](https://dashboard.render.com/) and choose a Hobby workspace. Enable MFA for the operator account.
2. Make the reviewed app changes available on the GitHub `main` branch and confirm GitHub CI passes.
3. Choose **New → Blueprint**, select the Kaizen repository and `main`, then review `render.yaml`.
4. Confirm Singapore, `1c-2g`, 10 GB disk and the estimated monthly price before creating paid resources.
5. Set `KAIZEN_ADMIN_PASSWORD` privately in Render for the initial administrator. Never put it in Git or send it by email.
   `KAIZEN_ADMIN_EMAIL` is the owner’s configured BD address. No local accounts or documents are migrated automatically.
6. Deploy and save the HTTPS service address. After initial sign-in, remove the bootstrap-password environment value;
   the administrator account remains in the persistent database.
7. Keep `KAIZEN_HOSTED=1`, `KAIZEN_CONFIDENTIAL=1`, `KAIZEN_AI_PROVIDER=null` and `KAIZEN_SECURE_COOKIES=1`.
   Do not add AI-provider or Supabase credentials.

A connected Outlook mailbox can send a manually requested test email from this chat. It does not configure the
hosted app to send invitations. Administrators currently copy one-use codes and deliver them privately.

## Hosted acceptance checks

Use disposable synthetic accounts and documents first. Record the exact deployed commit and results.

- Anonymous visitors can read Tutorial/Privacy but cannot list runs, retrieve document pages or download exports.
- Invitation: right address succeeds once; wrong address, expired/revoked/used code and anonymous invitation creation fail.
- A valid password alone cannot approve a pending/revoked account. Revocation ends existing access.
- Upload a synthetic project, inspect extraction and rendered source pages, save and approve a decision.
- A second user cannot open the private run until explicitly shared. View-only users cannot change or export it.
- Test selected and whole-list terminology adoption, attribution and older-version update notices across two users.
- Export Summary/Complete details and preview/import an edited decision workbook into its originating run.
- Restart the service and confirm accounts, sources, decisions, sharing and terminology selections persist.
- Exercise two simultaneous uploads and measure memory/time. The app processes one cross-check at a time and returns a retryable busy response to simultaneous requests;
  if the service cannot handle the test workload in 2 GB, reduce the pilot scope or revisit the budget before launch.
- Verify no external AI/password-provider calls, no source contents in application logs, no secrets/real files in the image.
- Test a consistent backup and restoration on a disposable workspace. Define backup expiry and permanent-deletion handling.

## Privacy boundary

Render provides [disk encryption](https://render.com/docs/disks); it is provider-managed encryption.
The operator and authorized infrastructure personnel may have access. The app processes plaintext server-side
for OCR and comparison; it is not end-to-end encrypted against the host. A privacy notice is not a technical
zero-access guarantee or BD approval. Review [Render security](https://render.com/security), its
[shared responsibility model](https://render.com/docs/shared-responsibility-model) and
[data processing addendum](https://render.com/dpa) with the appropriate BD owner.

The app’s Delete action is recoverable and retains sources/history. Permanent removal and backup retention
remain operator tasks. Publishing terminology intentionally exposes its terms/notes to the invited reviewer group.

## Delivery sequence

- **Friday 16 October:** finish tutorial, privacy controls, image verification and reviewable deployment configuration.
- **Saturday 17 October:** provision the approved service and run hosted synthetic acceptance checks.
- **Sunday 18 October:** complete approved-document checks with a small named group; verify backups and access boundaries.
- **Monday 19 October:** invite the limited testing group only after the hosted checks pass; share the tutorial and support contact.

Infrastructure was provisioned on 16 October 2026. This checklist does not establish that every acceptance check or BD approval is complete; it is not a scheduled automation.
