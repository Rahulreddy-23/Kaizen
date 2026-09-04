# Security and data-handling review (prototype)

Scope: the code under `src/kaizen`, the local API, the workspace database and generated outputs. This is a
self-review of a hackathon prototype, not a formal assessment, and it makes no regulatory-compliance claim.

| Check | Result | Evidence |
|---|---|---|
| No external API calls by default | PASS | The only network client is `AnthropicProvider`, constructed only when `KAIZEN_AI_PROVIDER=anthropic` **and** `ANTHROPIC_API_KEY` are set; otherwise `NullProvider` (`src/kaizen/ai/providers.py`). Run metadata records which provider was active. |
| Documents stay local | PASS | Parsing, matching, storage and the API bind to `127.0.0.1` by default (`kaizen serve`). Uploads are written under the workspace folder. Even when AI is enabled only two description strings and a SKU/item number are sent, never documents. |
| No document contents logged | PASS | No `logging`/`print` of document content in `src/kaizen`; the CLI prints summaries and file paths only. The audit log stores actions, row ids, decisions and relationship ids. |
| No secrets in source or repo | PASS | `grep` for key/secret/password finds only the environment-variable check; no `.env` files; `.gitignore` excludes the workspace, outputs and virtualenv. |
| Temporary files | PASS | No `tempfile`/`/tmp` use; generated files live in the chosen `--out` folder or the workspace. Upload folders are per-run and kept for evidence rendering (delete the workspace to purge). |
| Path handling on upload | PASS | `POST /api/runs/upload` rejects absolute paths and `..` segments before writing. `from-path` only reads folders the local user can already read. |
| Deterministic hashes | PASS | SHA-256 of every input, terminology snapshot hash, and content-derived run ids; verified by tests (`test_run_id_is_deterministic_for_same_inputs`, `test_build_is_deterministic`). |
| Audit content | PASS | Audit rows contain actor, action, ids and short notes. Reviewer comments are stored as entered by reviewers (they are business content, not secrets). |
| Dependencies | INFO | Runtime: pydantic, PyMuPDF, openpyxl, rapidfuzz, typer, rich; API extra: fastapi, uvicorn, python-multipart. No dependency performs network calls at runtime. Optional: `rapidocr-onnxruntime` (offline OCR), `sentence-transformers` (local embeddings), `anthropic` (opt-in). |
| Reviewer identity / blind mode | PARTIAL | Identity, slot and blind mode are a server-side session (`src/kaizen/review/sessions.py`): the token is in an HttpOnly cookie, the `viewer`/`blind` query parameters are ignored when a session exists, and the blind flag is derived from the workspace policy rather than the request. A blind reviewer 2 cannot see reviewer 1's decision, the row state that implies it, an override through `effective_classification`, a final taken without them, the row history, the Excel export, the annotated BOM or the audit log. The policy is changed only from the command line. Remaining gap: this is identification, not authentication — anyone with access to the machine can open a session under any name, and the cookie is not `Secure` because the server is plain HTTP on localhost. |
| Multi-user concurrency | PARTIAL | Writes to the workspace database are serialised with a process lock (verified by a 25-thread test); SQLite in one process is adequate for a local tool, not for a shared server. |

Recommendations before any shared deployment: put the API behind SSO so a session proves *who* the
reviewer is (the slot and blind machinery is already server-side and would carry over), serve it over
HTTPS and mark the session cookie `Secure`, run it on a server with a proper database, and decide the
retention policy for uploaded documents and rendered page images.
