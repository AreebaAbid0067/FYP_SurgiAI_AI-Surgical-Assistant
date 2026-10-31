"use client";

import { useEffect, useState } from "react";
import { LuCircleCheck, LuCircleX, LuMinus, LuPlay, LuTriangleAlert } from "react-icons/lu";
import { Alert, Card, PageHeader, Spinner } from "../../components/ui";
import { api, ApiError, postJson } from "../../lib/api";

type Report = {
  items: { category: string; requirement: string; implementation: string[]; code?: string[]; met: boolean }[];
  latency: Record<string, number | string | null>;
  health: Record<string, unknown>;
};
type Check = { category: string; name: string; status: "passed" | "failed" | "skipped"; detail: string };
type SelfCheck = { checks: Check[] } & Record<string, unknown>;

const icon = {
  passed: <LuCircleCheck className="text-xl text-emerald-600" />,
  failed: <LuCircleX className="text-xl text-red-600" />,
  skipped: <LuMinus className="text-xl text-slate-400" />,
};

export default function CompliancePage() {
  const [report, setReport] = useState<Report | null>(null);
  const [checks, setChecks] = useState<Check[] | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { api<Report>("admin/nfr").then(setReport).catch((e: ApiError) => setError(e.message)); }, []);

  const run = async () => {
    setRunning(true); setError("");
    try { setChecks((await postJson<SelfCheck>("admin/nfr/self-check", {})).checks); }
    catch (e) { setError((e as ApiError).message); }
    finally { setRunning(false); }
  };
  const count = (s: Check["status"]) => checks?.filter((c) => c.status === s).length ?? 0;

  return (
    <>
      <PageHeader eyebrow="Administration" title="Non-functional requirements" description="Run real tests against the live system, and see exactly which code implements each requirement." />
      {error && <Alert tone="error">{error}</Alert>}
      <Card title="Live verification" subtitle="Executes real tests now: password hashing, token forgery, rate limiting, encryption, surgeon isolation, speed and more."
        action={<button className="btn btn-primary" onClick={run} disabled={running}><LuPlay /> Run live checks</button>}>
        {running && <Spinner label="Running checks…" />}
        {checks && (
          <>
            <p className="mb-3 text-sm font-semibold text-slate-700">{count("passed")} passed · {count("failed")} failed · {count("skipped")} skipped</p>
            <ul className="divide-y divide-slate-200">
              {checks.map((c) => (
                <li key={c.name} className="flex gap-3 py-2">
                  {icon[c.status]}
                  <div>
                    <p className="text-sm font-medium text-slate-800">{c.name} <span className="text-xs font-normal text-slate-500">({c.category})</span></p>
                    {c.detail && <p className="text-xs text-slate-500">{c.detail}</p>}
                  </div>
                </li>
              ))}
            </ul>
          </>
        )}
        {!checks && !running && <p className="text-sm text-slate-500">Press “Run live checks” to test the system.</p>}
      </Card>

      {!report && !error && <Spinner label="Loading…" />}
      {report && (
        <div className="mt-4 space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Card title="System health"><pre className="whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(report.health, null, 2)}</pre></Card>
            <Card title="Response latency"><pre className="whitespace-pre-wrap text-xs text-slate-600">{JSON.stringify(report.latency, null, 2)}</pre></Card>
          </div>
          {report.items.map((item) => (
            <Card key={item.category} title={item.category} subtitle={item.requirement}
              action={item.met ? <LuCircleCheck className="text-xl text-emerald-600" /> : <LuTriangleAlert className="text-xl text-amber-600" />}>
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                {item.implementation.map((line) => <li key={line}>{line}</li>)}
              </ul>
              {item.code && item.code.length > 0 && (
                <p className="mt-3 text-xs text-slate-500">Where in the code: {item.code.map((c) => <code key={c} className="mr-2">{c}</code>)}</p>
              )}
            </Card>
          ))}
        </div>
      )}
    </>
  );
}
