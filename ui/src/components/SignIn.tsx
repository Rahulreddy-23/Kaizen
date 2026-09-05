// Sign-in gate. Reviewers identify themselves before they can see or record decisions: every decision
// is stored against a name, and blind review only means something if the server decides who is blind.
import { EyeSlash, UserCircle, UsersThree } from "@phosphor-icons/react";
import { useState } from "react";
import { useReviewer } from "../lib/reviewer";
import { Button, Field } from "./ui";

export function SignIn() {
  const { signIn, policy, error } = useReviewer();
  const [name, setName] = useState("");
  const [slot, setSlot] = useState<1 | 2>(1);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const required = policy === "required";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFailed(null);
    try {
      await signIn(name.trim(), slot);
    } catch (err) {
      setFailed((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const roles: { n: 1 | 2; title: string; body: string; icon: React.ReactNode }[] = [
    { n: 1, title: "Reviewer 1 · BOM facilitator", body: "Prepares the review and records the first decision on each row.", icon: <UserCircle size={22} /> },
    {
      n: 2,
      title: "Reviewer 2 · independent",
      body: required ? "Reviews blind: reviewer 1's decision on a row stays hidden until you record your own." : "Second review. Blind mode is optional in this workspace.",
      icon: <UsersThree size={22} />,
    },
  ];

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-6">
      <form onSubmit={submit} className="w-full max-w-[30rem] card shadow-pop p-7 enter-pop">
        <div className="flex items-center gap-3 mb-6">
          <span className="w-9 h-9 rounded-md bg-accent-500 grid place-items-center font-semibold text-ink" aria-hidden>
            K
          </span>
          <div className="leading-tight">
            <div className="text-lg font-semibold tracking-tight">Kaizen Cross-Check</div>
            <div className="text-xs text-ink-3">BOM · label · drawing · PCO review</div>
          </div>
        </div>

        <h1 className="text-2xl mb-1">Sign in to review</h1>
        <p className="text-sm text-ink-3 mb-5">Every decision is recorded against your name. Choose the slot you are reviewing in.</p>

        <Field label="Your name" htmlFor="reviewer-name" className="mb-4">
          <input id="reviewer-name" className="input w-full" autoFocus autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Dharma Reddy" />
        </Field>

        <fieldset className="mb-5">
          <legend className="label">Reviewer slot</legend>
          <div className="grid gap-2">
            {roles.map((r) => {
              const on = slot === r.n;
              return (
                <label
                  key={r.n}
                  className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-[border-color,background-color,box-shadow] duration-150 ease-out ${
                    on ? "border-accent-500 bg-accent-50 shadow-[0_0_0_3px_#fdebdd]" : "border-line hover:border-line-2 hover:bg-surface-2/60"
                  }`}
                >
                  <input type="radio" name="slot" className="sr-only" checked={on} onChange={() => setSlot(r.n)} />
                  <span className={`shrink-0 mt-0.5 ${on ? "text-accent-600" : "text-ink-3"}`}>{r.icon}</span>
                  <span>
                    <span className="block text-sm font-medium text-ink">{r.title}</span>
                    <span className="block text-xs text-ink-3 mt-0.5">{r.body}</span>
                  </span>
                </label>
              );
            })}
          </div>
        </fieldset>

        <div className="flex items-start gap-2 text-xs text-ink-3 mb-5">
          <EyeSlash size={16} className="shrink-0 mt-0.5" />
          <span>
            Blind review is <b className="text-ink">{required ? "required" : "optional"}</b> in this workspace. The policy is server-side; change it with <span className="mono">kaizen review policy</span>.
          </span>
        </div>

        {(failed || error) && (
          <div role="alert" className="text-sm text-bad mb-3">
            {failed ?? error}
          </div>
        )}
        <Button variant="primary" size="lg" className="w-full" type="submit" loading={busy} disabled={!name.trim()}>
          Start reviewing
        </Button>
      </form>
    </div>
  );
}
