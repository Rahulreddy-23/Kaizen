// Sign-in gate, with sign-up beside it. Reviewers identify themselves before they can see or record
// decisions: every decision is stored against a BD email address, and blind review only means something
// if the server decides who is blind. No email is ever sent (BD mail blocks external senders), so a
// forgotten password is handled by an administrator: with local accounts they clear it (`kaizen users
// reset`) and the reviewer signs up again; with Supabase accounts they set a new one in Supabase.
import { Eye, EyeSlash } from "@phosphor-icons/react";
import { Link } from "react-router-dom";
import { useState } from "react";
import { useReviewer } from "../lib/reviewer";
import { ThemeToggle } from "./ThemeToggle";
import { Button, Field } from "./ui";

const BD_DOMAIN = "@bd.com";
const BAD_DOMAIN = "Only BD email addresses can sign in";
const MIN_PASSWORD = 10;

type Mode = "signin" | "signup";

/** A password box with a reveal toggle. Typing a long password blind is where most typos come from. */
function PasswordInput({ id, value, onChange, autoComplete, disabled, error }: { id: string; value: string; onChange: (v: string) => void; autoComplete: string; disabled: boolean; error?: boolean }) {
  const [shown, setShown] = useState(false);
  return (
    <div className="relative">
      <input disabled={disabled} aria-invalid={error || undefined} aria-describedby={error ? `${id}-note` : undefined} id={id} type={shown ? "text" : "password"} className="input w-full pr-10" autoComplete={autoComplete} value={value} onChange={(e) => onChange(e.target.value)} />
      <button
        type="button"
        disabled={disabled}
        onClick={() => setShown((s) => !s)}
        className="absolute inset-y-0 right-0 w-10 grid place-items-center text-ink-3 hover:text-ink rounded-r-md"
        aria-label={shown ? "Hide password" : "Show password"}
        aria-pressed={shown}
        title={shown ? "Hide password" : "Show password"}
      >
        {shown ? <EyeSlash size={17} /> : <Eye size={17} />}
      </button>
    </div>
  );
}

export function SignIn() {
  const { signUp, signIn, error } = useReviewer();
  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [invitation, setInvitation] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const address = email.trim().toLowerCase();
  const looksBd = address.endsWith(BD_DOMAIN) && address.length > BD_DOMAIN.length;
  const wrongDomain = address.length > 0 && !looksBd;
  const tooShort = mode === "signup" && password.length > 0 && password.length < MIN_PASSWORD;
  const mismatch = mode === "signup" && confirm.length > 0 && password !== confirm;
  const ready = mode === "signin" ? looksBd && password.length > 0 : looksBd && password.length >= MIN_PASSWORD && password === confirm && invitation.trim().length > 0;

  function switchTo(next: Mode) {
    setMode(next);
    setPassword("");
    setConfirm("");
    setFailed(null);
    setNotice(null);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy || !ready) return;
    setBusy(true);
    setFailed(null);
    setNotice(null);
    try {
      if (mode === "signup") {
        await signUp(address, password, invitation.trim());
        setInvitation("");
        setMode("signin");
        setPassword("");
        setConfirm("");
        setNotice("Account created. Sign in with your email and password.");
      } else {
        await signIn(address, password);
      }
    } catch (err) {
      setFailed((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center p-6">
      <div className="fixed top-3 right-3">
        <ThemeToggle />
      </div>
      <form onSubmit={submit} className="w-full max-w-[30rem] card shadow-pop p-7 enter-pop">
        <div className="flex items-center gap-3 mb-6">
          <span className="w-11 h-11 rounded-md bg-white grid place-items-center px-1.5 ring-1 ring-black/5" aria-hidden>
            <img src="/bd-logo.png" alt="" className="w-full" />
          </span>
          <div className="leading-tight">
            <div className="text-lg font-semibold tracking-tight">Kaizen Cross-Check</div>
            <div className="text-xs text-ink-3">BOM · label · drawing · PCO review</div>
          </div>
        </div>

        <h1 className="text-2xl mb-1">{mode === "signin" ? "Sign in" : "Accept your invitation"}</h1>
        <p className="text-sm text-ink-3 mb-5">
          {mode === "signin"
            ? "Use your BD account to access Kaizen."
            : `Use the BD address on your invitation and choose a password of at least ${MIN_PASSWORD} characters.`}
        </p>

        <Field label="BD email address" htmlFor="reviewer-email" className="mb-4" error={wrongDomain ? BAD_DOMAIN : undefined}>
          <input
            id="reviewer-email"
            disabled={busy}
            type="email"
            className="input w-full"
            autoFocus
            autoComplete="username"
            spellCheck={false}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="name@bd.com"
          />
        </Field>

        {mode === "signup" && <Field label="Invitation code" htmlFor="invitation-code" className="mb-4" hint="Ask an administrator to send your code privately. Codes expire after 72 hours.">
          <input id="invitation-code" className="input w-full" disabled={busy} value={invitation} onChange={e => setInvitation(e.target.value)} autoComplete="off" spellCheck={false} />
        </Field>}

        <Field label="Password" htmlFor="reviewer-password" className="mb-4" error={tooShort ? `At least ${MIN_PASSWORD} characters` : undefined}>
          <PasswordInput disabled={busy} error={tooShort} id="reviewer-password" value={password} onChange={setPassword} autoComplete={mode === "signin" ? "current-password" : "new-password"} />
        </Field>

        {mode === "signup" && (
          <Field label="Confirm password" htmlFor="reviewer-confirm" className="mb-4" error={mismatch ? "The two passwords do not match" : undefined}>
            <PasswordInput disabled={busy} error={mismatch} id="reviewer-confirm" value={confirm} onChange={setConfirm} autoComplete="new-password" />
          </Field>
        )}

        {notice && (
          <div role="status" className="text-sm text-ok mb-3">
            {notice}
          </div>
        )}
        {(failed || error) && (
          <div role="alert" className="text-sm text-bad mb-3">
            {failed ?? error}
          </div>
        )}

        <Button variant="primary" size="lg" className="w-full" type="submit" loading={busy} disabled={!ready}>
          {mode === "signin" ? "Sign in" : "Create account"}
        </Button>

        <div className="mt-4 text-xs text-ink-3 text-center">
          {mode === "signin" ? (
            <>
              Have an invitation?{" "}
              <button type="button" disabled={busy} className="underline hover:text-ink" onClick={() => switchTo("signup")}>
                Accept invitation
              </button>
            </>
          ) : (
            <>
              Already have an account?{" "}
              <button type="button" disabled={busy} className="underline hover:text-ink" onClick={() => switchTo("signin")}>
                Sign in
              </button>
            </>
          )}
        </div>
        {mode === "signin" && (
          <p className="mt-3 text-2xs text-ink-3 text-center leading-relaxed">
            Access is invite-only. For an invitation or password help, contact your administrator.
          </p>
        )}
        <nav aria-label="Help and privacy" className="mt-5 pt-4 border-t border-line flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs"><Link to="/tutorial">Read the tutorial</Link><Link to="/privacy">Privacy and documents</Link></nav>
      </form>
    </div>
  );
}
