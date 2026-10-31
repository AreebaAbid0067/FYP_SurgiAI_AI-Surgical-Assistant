"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Alert, Spinner } from "./ui";
import { api, ApiError, CaseDetail, CaseSummary } from "../lib/api";

// Loads the surgeon's own cases and the one selected via ?case=ID.
export function useCases() {
  const router = useRouter();
  const caseId = useSearchParams().get("case");
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [current, setCurrent] = useState<CaseDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<CaseSummary[]>("cases").then(setCases).catch((e: ApiError) => setError(e.message));
  }, []);

  const reload = async () => {
    if (!caseId) return setCurrent(null);
    try { setCurrent(await api<CaseDetail>(`cases/${caseId}`)); setError(""); }
    catch (e) { setCurrent(null); setError((e as ApiError).message); }
  };
  useEffect(() => { reload(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [caseId]);

  return { cases, current, error, reload, select: (id: string) => router.push(`?case=${id}`) };
}

export function CasePicker({ cases, error, onSelect, emptyHint }: {
  cases: CaseSummary[] | null; error: string; onSelect: (id: string) => void; emptyHint: string;
}) {
  if (error) return <Alert tone="error">{error}</Alert>;
  if (!cases) return <Spinner label="Loading your patients…" />;
  if (!cases.length)
    return (
      <Alert tone="info">
        {emptyHint} <Link href="/pre-surgery" className="font-semibold underline">Start a pre-surgery assessment</Link>.
      </Alert>
    );
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {cases.map((c) => (
        <button key={c.case_id} onClick={() => onSelect(c.case_id)} className="card text-left transition hover:border-teal-600">
          <p className="font-semibold text-slate-900">{c.patient_label}</p>
          <p className="text-sm text-slate-500">{c.procedure_name}</p>
          <p className="mt-2 text-xs uppercase tracking-wide text-teal-700">Stage: {c.stage === "pre" ? "Pre-op" : c.stage === "intra" ? "Intra-op" : "Post-op"}</p>
        </button>
      ))}
    </div>
  );
}
