import { AccountInvitations } from "../components/AccountInvitations";
import { useState } from "react";
import { api } from "../api";
import { useReviewer } from "../lib/reviewer";
import { useAsync } from "../lib/useAsync";
import { Button, Card, EmptyState, Field, LinkButton, PageHeader } from "../components/ui";
import { ErrorBox } from "../components/Feedback";
import { Pagination } from "../components/Pagination";
import { usePagedList } from "../lib/pagination";
import type { Profile } from "../types";

export default function AdminPage() {
  const { session } = useReviewer();
  const users = useAsync(() => session?.is_admin ? api.users() : Promise.resolve([]), [session?.is_admin]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const visible = (users.data ?? []).filter(profile => (!status || profile.status === status) && profile.email.toLowerCase().includes(search.trim().toLowerCase()));
  const pagination = usePagedList(visible, `${status}:${search}`);
  const approvedAdmins = (users.data ?? []).filter(profile => profile.is_admin && profile.status === "approved").length;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  async function update(p: Profile, change: Partial<Profile>) {
    setBusy(p.email); setError(null);
    try { await api.updateUser(p.email, change); users.reload(); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(null); }
  }
  if (!session?.is_admin) return <div><PageHeader title="Manage users" /><Card className="p-5 space-y-4"><p className="text-sm text-ink-2">Administrator access is required to manage accounts.</p><LinkButton to="/">Back to runs</LinkButton></Card></div>;
  return <div>
    <PageHeader title="Manage users" description="Invite reviewers, manage access and assign administrator roles." />
    <AccountInvitations />
    {(error || users.error) && <ErrorBox error={error || users.error || ""} />}
    <Card>
      <div className="p-5 border-b border-line flex flex-wrap items-end gap-3">
        <Field label="Search accounts" className="flex-1 min-w-0 basis-56"><input type="search" className="input w-full" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search by email" /></Field>
        <Field label="Account status"><select className="input" value={status} onChange={event => setStatus(event.target.value)}><option value="">All statuses</option><option value="approved">Approved</option><option value="pending">Pending</option><option value="rejected">Revoked</option></select></Field>
        <span className="text-xs text-ink-3">{visible.length} account{visible.length === 1 ? "" : "s"}</span>
      </div>
      <div role="list" aria-label="Registered accounts" className="divide-y divide-line">
      {users.loading && <p className="p-5">Loading accounts…</p>}
      {!users.loading && !visible.length && !users.error && <EmptyState title="No accounts match" description="Clear the search or choose another status." action={<Button onClick={() => {setSearch(""); setStatus("");}}>Clear filters</Button>} />}
      {pagination.rows.map(p => <div role="listitem" key={p.email} className="p-5 flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0"><b className="break-all">{p.email}</b><p className="text-sm text-ink-3">{p.status.charAt(0).toUpperCase() + p.status.slice(1)} · {p.is_admin ? "Administrator" : "User"}</p></div>
        <div className="flex flex-wrap gap-2">
          {p.status !== "approved" && <Button loading={busy === p.email} disabled={!!busy} onClick={() => update(p, {status: "approved"})}>Approve account</Button>}
          {p.status === "approved" && <Button disabled={!!busy || (!!p.is_admin && approvedAdmins === 1)} title={p.is_admin && approvedAdmins === 1 ? "At least one administrator must retain access" : undefined} onClick={() => {
            if (window.confirm(`${p.is_admin ? "Remove administrator access from" : "Make an administrator:"} ${p.email}?`)) void update(p, {is_admin: !p.is_admin});
          }}>{p.is_admin ? "Remove admin" : "Make admin"}</Button>}
          {p.status !== "rejected" && <Button variant="danger" disabled={!!busy || (!!p.is_admin && p.status === "approved" && approvedAdmins === 1)} title={p.is_admin && p.status === "approved" && approvedAdmins === 1 ? "At least one administrator must retain access" : undefined} onClick={() => {
            if (window.confirm(`Revoke app access for ${p.email}? Their active sessions will end.`)) void update(p, {status: "rejected"});
          }}>{p.status === "pending" ? "Reject" : "Revoke access"}</Button>}
        </div>
      </div>)}
      </div><Pagination {...pagination} onChange={pagination.setOffset} label="Accounts" />
    </Card>
  </div>;
}
