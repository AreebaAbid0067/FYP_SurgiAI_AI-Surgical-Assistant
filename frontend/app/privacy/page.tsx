"use client";

import { useEffect, useState } from "react";
import { LuCircleCheck, LuTriangleAlert } from "react-icons/lu";
import { Alert, Card, PageHeader, Spinner } from "../components/ui";
import { api, ApiError } from "../lib/api";

type Security = {
  case_count: number;
  cases_encrypted: number;
  cases_readable_in_storage: number;
  activity: { action: string; case: string; at: string }[];
};

const protections = [
  ["Passwords", "Stored only as salted scrypt hashes. Nobody, including administrators, can read them.", "backend/security.py"],
  ["Patient records", "Each record is encrypted (AES, Fernet) before it is written to the database.", "backend/security.py, backend/store.py"],
  ["Your patients only", "Every query is filtered by your account. Other surgeons cannot list, open or change your patients.", "backend/store.py"],
  ["Sessions", "Signed tokens in an HttpOnly cookie that scripts cannot read; they expire after 8 hours.", "backend/security.py, frontend/app/api/auth"],
  ["Admin area", "Verification and compliance pages are admin-only and blocked for surgeons, in the browser and on the server.", "frontend/middleware.ts, backend/main.py"],
  ["Abuse protection", "Login and API rate limits, input size limits and security headers.", "backend/main.py"],
  ["Audit trail", "Every access to a patient record is logged with who and when.", "backend/store.py"],
];

const terms = [
  "SurgiAI is a decision-support tool. It does not replace your clinical judgement; the operating surgeon is always responsible for patient care.",
  "AI answers can be wrong. Check important details against guidelines and the patient’s record before acting on them.",
  "Only enter patient information you are allowed to handle. Use identifiers (e.g. initials or a case number) instead of full names where possible.",
  "Do not share your login. Sign out on shared devices.",
  "Verified cases show how the assistant was compared with published guidelines; they are not a regulatory approval.",
];

export default function PrivacyPage() {
  const [data, setData] = useState<Security | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { api<Security>("me/security").then(setData).catch((e: ApiError) => setError(e.message)); }, []);
  const safe = data && data.cases_readable_in_storage === 0;

  return (
    <>
      <PageHeader eyebrow="Trust" title="Privacy & security" description="How patient data is protected, and how you can check it yourself." />
      <div className="space-y-4">
        <Card title="Your data right now" subtitle="Read live from the server for your account only.">
          {error && <Alert tone="error">{error}</Alert>}
          {!data && !error && <Spinner label="Checking…" />}
          {data && (
            <>
              <div className="mb-3 flex items-center gap-2 font-medium">
                {safe ? <LuCircleCheck className="text-xl text-emerald-600" /> : <LuTriangleAlert className="text-xl text-amber-600" />}
                {data.case_count} patient record(s): {data.cases_encrypted} encrypted in storage, {data.cases_readable_in_storage} readable.
              </div>
              <p className="mb-1 text-sm font-semibold text-slate-700">Recent activity on your account</p>
              <ul className="max-h-48 divide-y divide-slate-200 overflow-auto text-sm text-slate-600">
                {data.activity.map((a, i) => <li key={i} className="py-1">{a.at} — {a.action}{a.case && ` (case ${a.case})`}</li>)}
                {!data.activity.length && <li className="py-1">No activity yet.</li>}
              </ul>
            </>
          )}
        </Card>

        <Card title="How patient data is protected">
          <ul className="divide-y divide-slate-200">
            {protections.map(([name, text, where]) => (
              <li key={name} className="py-3">
                <p className="font-semibold text-slate-800">{name}</p>
                <p className="text-sm text-slate-600">{text}</p>
                <p className="mt-1 text-xs text-slate-500">Code: {where}</p>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Check it yourself">
          <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-700">
            <li>Open the “Your data right now” panel above: it must say 0 readable.</li>
            <li>Run <code>python -m unittest discover -s tests</code> in the backend folder. It tests isolation between surgeons, encryption and role blocks.</li>
            <li>Open <code>backend/surgiai_app.sqlite3</code> in any SQLite viewer: patient records appear as scrambled text, passwords as hashes.</li>
            <li>Administrators can run live checks on the “NFR compliance” page.</li>
          </ol>
        </Card>

        <Card title="Terms of use">
          <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">{terms.map((t) => <li key={t}>{t}</li>)}</ul>
        </Card>

        <Card title="Privacy policy">
          <p className="text-sm text-slate-700">
            We store only what you enter for your patients, encrypted, and visible only to your account. We do not sell or share it.
            Text you send to the assistant is processed by our AI provider to produce an answer. Administrators manage the system and
            verification but cannot see surgeons’ patient records through the application.
          </p>
        </Card>
      </div>
    </>
  );
}
