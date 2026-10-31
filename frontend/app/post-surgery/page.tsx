"use client";

import { Suspense, useState } from "react";
import { LuPrinter } from "react-icons/lu";
import { CasePicker, useCases } from "../components/case-picker";
import { Alert, Card, ChipGroup, PageHeader, Report, Spinner } from "../components/ui";
import { ApiError, postJson } from "../lib/api";

type Plan = { mode: "ai" | "protocol_only"; plan: string; notice?: string; sources?: string[]; elapsed_seconds?: number; cached?: boolean };

const STATUS = ["Stable, no concerns", "Fever", "Uncontrolled pain", "Nausea / vomiting", "Wound concern", "Not tolerating diet", "Drain output high"];

function PostSurgery() {
  const { cases, current, error, select } = useCases();
  const [status, setStatus] = useState<string[]>([]);
  const [result, setResult] = useState<Plan | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState("");

  const generate = async () => {
    if (!current) return;
    setBusy(true); setProblem("");
    try {
      setResult(await postJson<Plan>(`cases/${current.case_id}/post-surgery`, { current_status: status.join(", ") }));
    } catch (e) { setProblem((e as ApiError).message); }
    finally { setBusy(false); }
  };

  const intra = current?.data.intraop.summary;

  return (
    <>
      <PageHeader eyebrow="Step 3 of 3" title="Post-surgery plan" description="Medications, wound care, diet, activity and monitoring based on the pre-operative record and operative summary." />
      {!current ? (
        <CasePicker cases={cases} error={error} onSelect={select} emptyHint="No patients yet." />
      ) : (
        <div className="space-y-4">
          <Card title={current.patient_label} subtitle={current.procedure_name}>
            <p className="whitespace-pre-line text-sm text-slate-600">{current.data.history_text}</p>
            {intra ? (
              <p className="mt-3 text-sm text-slate-600"><b>Operative summary:</b> {Object.entries(intra).map(([k, v]) => `${k.replace(/_/g, " ")}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" · ")}</p>
            ) : (
              <div className="mt-3"><Alert tone="warning">No operative summary recorded. The plan will use the pre-operative record only.</Alert></div>
            )}
          </Card>
          <Card title="Current patient status" subtitle="Optional. Select anything that applies.">
            <ChipGroup options={STATUS} value={status} onChange={setStatus} />
            <div className="mt-4 flex items-center gap-3">
              <button className="btn btn-primary" onClick={generate} disabled={busy}>Generate plan</button>
              {busy && <Spinner label="Preparing plan…" />}
            </div>
          </Card>
          {problem && <Alert tone="error">{problem}</Alert>}
          {result && (
            <>
              {result.mode === "protocol_only" && (
                <Alert tone="warning">{result.notice ?? "AI is unavailable. Showing the standard guideline protocol for this procedure."}</Alert>
              )}
              <Card title="Recommended plan" action={<button className="btn btn-ghost no-print" onClick={() => window.print()}><LuPrinter /> Print</button>}>
                <Report>{result.plan}</Report>
                {result.sources && result.sources.length > 0 && (
                  <p className="mt-4 text-xs text-slate-500">Sources: {result.sources.join("; ")}</p>
                )}
              </Card>
              <Alert tone="info">Decision support only. Review every medication and dose against the patient&apos;s record before ordering.</Alert>
            </>
          )}
        </div>
      )}
    </>
  );
}

export default function Page() {
  return <Suspense fallback={<Spinner label="Loading…" />}><PostSurgery /></Suspense>;
}
