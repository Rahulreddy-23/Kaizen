import { useState } from "react";
import { api } from "../api";
import type { Invitation } from "../types";
import { fmtDate } from "../lib/format";
import { errorMessage, useAsync } from "../lib/useAsync";
import { ErrorBox, Notice } from "./Feedback";
import { Button, Card, CardHead, Field } from "./ui";

export function AccountInvitations() {
  const list = useAsync(api.invitations, []);
  const [email, setEmail] = useState("");
  const [issued, setIssued] = useState<(Invitation & {code: string}) | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const pending = (list.data ?? []).filter(x => !x.consumed_at && !x.revoked_at && Date.parse(x.expires_at) > Date.now());
  async function invite(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setError(null); setCopied(false); setIssued(null);
    try { setIssued(await api.invite(email.trim().toLowerCase())); setEmail(""); list.reload(); }
    catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  async function revoke(id: string) {
    setBusy(true); setError(null);
    try { await api.revokeInvitation(id); if (issued?.id === id) setIssued(null); list.reload(); }
    catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <Card className="mb-6">
    <CardHead title="Invite a reviewer" />
    <div className="p-5 space-y-4">
      <p className="text-sm text-ink-2 max-w-prose">Check the recipient’s identity, then share their one-use code through a trusted BD channel. No invitation email is sent automatically.</p>
      <form className="flex flex-wrap items-end gap-3" onSubmit={invite}>
        <Field label="BD email address" htmlFor="invite-email" className="min-w-0 flex-1 basis-64"><input id="invite-email" type="email" className="input w-full" required value={email} disabled={busy} onChange={e => setEmail(e.target.value)} placeholder="name@bd.com" /></Field>
        <Button type="submit" variant="primary" loading={busy} disabled={busy || !/^[^@\s]+@bd\.com$/i.test(email.trim())}>Create invitation</Button>
      </form>
      {issued && <Notice><div className="space-y-3">
        <p><strong>Invitation for {issued.email}</strong><br />Shown once. Copy it before leaving this page. Expires {fmtDate(issued.expires_at)}.</p>
        <Field label="Invitation code" htmlFor="issued-invitation"><input id="issued-invitation" className="input w-full mono" readOnly value={issued.code} onFocus={e => e.target.select()} /></Field>
        <div className="flex gap-2"><Button size="sm" onClick={async () => {try {await navigator.clipboard.writeText(issued.code); setCopied(true);} catch {setError("Couldn’t copy automatically. Select the code and copy it manually.");}}}>{copied ? "Copied" : "Copy code"}</Button><Button size="sm" variant="ghost" onClick={() => setIssued(null)}>Hide code</Button></div>
      </div></Notice>}
      {(error || list.error) && <ErrorBox error={error || list.error || ""} />}
      <details>
        <summary className="cursor-pointer text-sm font-medium">Pending invitations{list.data ? ` (${pending.length})` : ""}</summary>
        {list.loading && !list.data && <p className="mt-3 text-sm">Loading invitations…</p>}
        {!list.loading && list.data && pending.length === 0 && <p className="mt-3 text-sm text-ink-3">No pending invitations. Used, expired and revoked codes cannot register an account.</p>}
        <ul className="divide-y divide-line mt-3">{pending.map(x => <li key={x.id} className="flex flex-wrap items-center justify-between gap-3 py-3"><div className="min-w-0"><strong className="break-all">{x.email}</strong><p className="text-xs text-ink-3 break-words">Invited by {x.invited_by} · Expires {fmtDate(x.expires_at)}</p></div><Button size="sm" variant="danger" disabled={busy} onClick={() => void revoke(x.id)} aria-label={`Revoke invitation for ${x.email}`}>Revoke invitation</Button></li>)}</ul>
      </details>
    </div>
  </Card>;
}
