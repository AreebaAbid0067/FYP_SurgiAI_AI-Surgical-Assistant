"use client";

import { FormEvent, useState } from "react";
import { Alert } from "../components/ui";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = Object.fromEntries(new FormData(event.currentTarget));
    const response = await fetch(`/api/auth/${mode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    }).catch(() => null);
    const body = await response?.json().catch(() => ({}));
    if (!response || !response.ok) {
      setError(body?.detail ?? "Could not reach the server.");
      setBusy(false);
      return;
    }
    window.location.href = body.user?.role === "admin" ? "/verification" : "/";
  };

  return (
    <div className="grid min-h-screen md:grid-cols-2">
      <div className="hidden flex-col justify-between bg-teal-950 p-12 text-teal-50 md:flex">
        <p className="text-2xl font-semibold">SurgiAI</p>
        <div>
          <h1 className="text-4xl font-semibold leading-tight">Guideline-grounded support for every stage of surgery.</h1>
          <p className="mt-4 max-w-md text-teal-200">Pre-operative assessment, intra-operative guidance and post-operative planning in one secure workspace.</p>
        </div>
        <p className="text-xs text-teal-400">Decision support only. Final clinical judgement rests with the surgeon.</p>
      </div>
      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
          <h2 className="text-xl font-semibold">{mode === "login" ? "Sign in" : "Create surgeon account"}</h2>
          {mode === "register" && (
            <input className="input" name="full_name" placeholder="Full name" required minLength={2} autoComplete="name" />
          )}
          <input className="input" name="username" placeholder="Username" required minLength={3} autoComplete="username" />
          <input className="input" name="password" type="password" placeholder="Password" required minLength={mode === "register" ? 8 : 1} autoComplete={mode === "login" ? "current-password" : "new-password"} />
          {error && <Alert tone="error">{error}</Alert>}
          <button className="btn btn-primary w-full" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
          <button type="button" className="w-full text-sm text-teal-700 hover:underline" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
            {mode === "login" ? "New surgeon? Create an account" : "Have an account? Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
