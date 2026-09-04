// Sign-in gate. Reviewers identify themselves before they can see or record decisions, because every
// decision is stored against a name and because blind review only means something if the server, not
// the browser, decides who is blind.
import { useState } from "react";
import { useReviewer } from "../lib/reviewer";

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

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-100 p-4">
      <form onSubmit={submit} className="w-full max-w-md bg-white border border-gray-300 p-5">
        <div className="font-semibold tracking-wider text-sm">KAIZEN CROSS-CHECK</div>
        <p className="text-xs text-gray-600 mt-1 mb-4">
          Every decision is recorded against your name. Choose the slot you are reviewing in: the facilitator prepares the review, the independent
          reviewer checks it.
        </p>

        <label className="block text-xs mb-3">
          <span className="label block mb-1">Your name</span>
          <input className="border border-gray-400 px-2 py-1 w-full text-xs" autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Dharma Reddy" />
        </label>

        <fieldset className="text-xs mb-3">
          <legend className="label mb-1">Reviewer slot</legend>
          {([1, 2] as const).map((n) => (
            <label key={n} className="flex items-start gap-2 py-1 cursor-pointer">
              <input type="radio" name="slot" className="mt-0.5" checked={slot === n} onChange={() => setSlot(n)} />
              <span>
                <b>
                  {n} · {n === 1 ? "BOM facilitator" : "Independent reviewer"}
                </b>
                <span className="block text-gray-600">
                  {n === 1
                    ? "Prepares the review and records the first decision on each row."
                    : required
                      ? "Reviews blind: reviewer 1's decision on a row stays hidden until you record your own."
                      : "Second review. Blind mode is optional in this workspace."}
                </span>
              </span>
            </label>
          ))}
        </fieldset>

        <div className="text-2xs text-gray-600 border-t border-gray-200 pt-2 mb-3">
          Blind review is <b>{required ? "required" : "optional"}</b> in this workspace. The setting is server-side; change it with{" "}
          <code className="mono">kaizen review policy --set …</code>.
        </div>

        {(failed || error) && <div className="text-xs text-red-800 mb-2">{failed ?? error}</div>}
        <button className="btn" disabled={!name.trim() || busy} type="submit">
          {busy ? "Signing in…" : "Start reviewing"}
        </button>
      </form>
    </div>
  );
}
