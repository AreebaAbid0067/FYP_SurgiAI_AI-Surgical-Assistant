"use client";

import { useEffect, useMemo, useState } from "react";
import { LuFileUp, LuSparkles } from "react-icons/lu";
import Link from "next/link";
import { Alert, Card, Chip, ChipGroup, CustomEntry, Field, PageHeader, RadioChips, Report, Section, Spinner, Steps } from "../components/ui";
import { api, ApiError, Catalog, emptyIntake, Intake, postJson } from "../lib/api";

type Suggestion = { id: string; name: string; category: string; score: number };

export default function PreSurgeryPage() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [step, setStep] = useState(0);
  const [label, setLabel] = useState("");
  const [procedureId, setProcedureId] = useState<string | null>(null);
  const [procedureName, setProcedureName] = useState("");
  const [custom, setCustom] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [intake, setIntake] = useState<Intake>(emptyIntake());
  const [notes, setNotes] = useState("");
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [caseId, setCaseId] = useState("");
  const [report, setReport] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => {
    api<Catalog>("procedures").then(setCatalog).catch((e: ApiError) => setError(e.message));
  }, []);

  const allSymptoms = useMemo(
    () => Array.from(new Set(catalog?.procedures.flatMap((p) => p.symptoms) ?? [])),
    [catalog]
  );

  useEffect(() => {
    if (!intake.symptoms.length) { setSuggestions([]); return; }
    postJson<{ suggestions: Suggestion[] }>("procedures/suggest", { symptoms: intake.symptoms })
      .then((r) => setSuggestions(r.suggestions))
      .catch(() => setSuggestions([]));
  }, [intake.symptoms]);

  const set = <K extends keyof Intake>(key: K, value: Intake[K]) => setIntake((prev) => ({ ...prev, [key]: value }));

  const readDocument = async (file: File) => {
    setBusy("Reading document…"); setError(""); setInfo("");
    const form = new FormData();
    form.append("document", file);
    try {
      const data = await api<Partial<Intake> & { other?: string }>("pre-surgery/history-from-document", { method: "POST", body: form });
      setIntake((prev) => ({
        ...prev,
        age: data.age || prev.age,
        sex: data.sex || prev.sex,
        symptoms: Array.from(new Set([...prev.symptoms, ...(data.symptoms ?? [])])),
        comorbidities: Array.from(new Set([...prev.comorbidities, ...(data.comorbidities ?? [])])),
        allergies: Array.from(new Set([...prev.allergies, ...(data.allergies ?? [])])),
        medications: Array.from(new Set([...prev.medications, ...(data.medications ?? [])])),
      }));
      if (data.other) setNotes((n) => (n ? `${n}\n${data.other}` : data.other ?? ""));
      setInfo("History pre-filled from the document. Please review every field before continuing.");
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy("");
    }
  };

  const generate = async () => {
    setBusy("Preparing the pre-operative report…"); setError("");
    try {
      let id = caseId;
      if (!id) {
        const created = await postJson<{ case_id: string }>("cases", {
          patient_label: label, procedure_id: procedureId, procedure_name: procedureName, intake, notes,
        });
        id = created.case_id;
        setCaseId(id);
      }
      const form = new FormData();
      form.append("operation", procedureName);
      form.append("case_id", id);
      for (const [key, file] of Object.entries(files)) if (file) form.append(key, file);
      const result = await api<unknown>("pre-surgery/upload", { method: "POST", body: form });
      setReport(typeof result === "string" ? result : JSON.stringify(result, null, 2));
      setStep(3);
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy("");
    }
  };

  const chooseProcedure = (id: string | null, name: string, isCustom = false) => {
    setProcedureId(id); setProcedureName(name); setCustom(isCustom);
  };

  if (!catalog) return <div>{error ? <Alert tone="error">{error}</Alert> : <Spinner label="Loading…" />}</div>;
  const ci = catalog.common_intake;
  const canNext0 = label.trim() && procedureName.trim().length >= 2;

  return (
    <>
      <PageHeader eyebrow="Step 1 of 3" title="Pre-surgery assessment" description="Just tap the options that apply. Grey text in brackets explains each term." />
      <Steps steps={["Patient", "History", "Records", "Report"]} current={step} />
      <div className="space-y-4">
        {error && <Alert tone="error">{error}</Alert>}
        {info && <Alert tone="info">{info}</Alert>}

        {step === 0 && (
          <Card title="Who is the patient and what is the operation?">
            <Field label="Patient label" hint="initials or bed number only - no full names">
              <input className="input max-w-sm" value={label} maxLength={120} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Bed 12 / A.K." />
            </Field>
            <Field label="Operation">
              {suggestions.length > 0 && (
                <p className="mb-2 flex items-center gap-1.5 text-xs text-teal-700"><LuSparkles /> Best matches for the symptoms you selected are shown first</p>
              )}
              <div className="flex flex-wrap gap-2">
                {[...suggestions, ...catalog.procedures.filter((p) => !suggestions.some((s) => s.id === p.id))].map((p) => (
                  <Chip key={p.id} label={p.name} explain={p.category} selected={procedureId === p.id && !custom} onClick={() => chooseProcedure(p.id, p.name)} />
                ))}
                <Chip label="Other operation" explain="type it yourself" selected={custom} onClick={() => chooseProcedure(null, "", true)} />
              </div>
              {custom && (
                <input className="input mt-3 max-w-md" autoFocus value={procedureName} maxLength={160} onChange={(e) => setProcedureName(e.target.value)} placeholder="Type the operation name" />
              )}
            </Field>
            <Section title="Not sure which operation? Tap the symptoms (optional)" count={intake.symptoms.length}>
              <ChipGroup options={allSymptoms} value={intake.symptoms} onChange={(v) => set("symptoms", v)} />
            </Section>
            <div className="mt-5">
              <button className="btn btn-primary" disabled={!canNext0} onClick={() => setStep(1)}>Continue</button>
            </div>
          </Card>
        )}

        {step === 1 && (
          <>
            <Card title="Quick start" subtitle="Have a referral or history sheet? Upload it and we will fill the form for you.">
              <label className="btn btn-ghost cursor-pointer">
                <LuFileUp /> Upload document (photo, PDF or text)
                <input type="file" hidden accept="image/*,application/pdf,text/plain" onChange={(e) => e.target.files?.[0] && readDocument(e.target.files[0])} />
              </label>
            </Card>
            <Card title="Patient basics">
              <Field label="Age (years)"><input className="input max-w-[8rem]" type="number" min={0} max={120} value={intake.age ?? ""} onChange={(e) => set("age", e.target.value)} /></Field>
              <Field label="Sex"><RadioChips options={ci.sex} value={intake.sex} onChange={(v) => set("sex", v)} /></Field>
              <Field label="How soon is surgery needed?"><RadioChips options={ci.urgency} value={intake.urgency} onChange={(v) => set("urgency", v)} /></Field>
              <Field label="Fitness for anaesthesia (ASA grade)" hint="your anaesthetist's grade"><RadioChips options={ci.asa} value={intake.asa} onChange={(v) => set("asa", v)} /></Field>
            </Card>
            <div className="space-y-3">
              <Section title="Existing medical conditions" count={intake.comorbidities.length + intake.custom_comorbidities.length}>
                <ChipGroup options={ci.comorbidities} value={intake.comorbidities} onChange={(v) => set("comorbidities", v)} />
                <CustomEntry placeholder="Another condition" values={intake.custom_comorbidities} onChange={(v) => set("custom_comorbidities", v)} />
              </Section>
              <Section title="Allergies" count={intake.allergies.length + intake.custom_allergies.length}>
                <ChipGroup tone="danger" options={ci.allergies} value={intake.allergies} onChange={(v) => set("allergies", v)} />
                <CustomEntry placeholder="Another allergy" values={intake.custom_allergies} onChange={(v) => set("custom_allergies", v)} />
              </Section>
              <Section title="Medicines the patient takes" count={intake.medications.length + intake.custom_medications.length}>
                <ChipGroup options={ci.medications} value={intake.medications} onChange={(v) => set("medications", v)} />
                <CustomEntry placeholder="Another medicine" values={intake.custom_medications} onChange={(v) => set("custom_medications", v)} />
              </Section>
              <Section title="Lifestyle and past surgery" count={[intake.smoking, intake.alcohol, intake.prior_surgery].filter(Boolean).length}>
                <Field label="Smoking"><RadioChips options={ci.smoking} value={intake.smoking} onChange={(v) => set("smoking", v)} /></Field>
                <Field label="Alcohol"><RadioChips options={ci.alcohol} value={intake.alcohol} onChange={(v) => set("alcohol", v)} /></Field>
                <Field label="Past operations"><RadioChips options={ci.prior_surgery} value={intake.prior_surgery} onChange={(v) => set("prior_surgery", v)} /></Field>
              </Section>
              <Section title="Anything else (optional notes)" count={notes.trim() ? 1 : 0}>
                <textarea className="input" rows={3} maxLength={8000} value={notes} onChange={(e) => setNotes(e.target.value)} />
              </Section>
            </div>
            <div className="flex gap-2">
              <button className="btn btn-ghost" onClick={() => setStep(0)}>Back</button>
              <button className="btn btn-primary" onClick={() => setStep(2)}>Continue</button>
            </div>
          </>
        )}

        {step === 2 && (
          <Card title="Records (optional)" subtitle="Add images of the prescription, scan or lab report if available.">
            {([["prescription", "Prescription"], ["scan", "Scan"], ["lab_report", "Lab report"]] as const).map(([key, title]) => (
              <Field key={key} label={title}>
                <input type="file" accept="image/*" className="upload-input" onChange={(e) => setFiles((f) => ({ ...f, [key]: e.target.files?.[0] ?? null }))} />
              </Field>
            ))}
            <div className="flex items-center gap-2">
              <button className="btn btn-ghost" onClick={() => setStep(1)} disabled={!!busy}>Back</button>
              <button className="btn btn-primary" onClick={generate} disabled={!!busy}>Generate report</button>
              {busy && <Spinner label={busy} />}
            </div>
          </Card>
        )}

        {step === 3 && (
          <>
            <Card title="Pre-operative report" subtitle={`${procedureName} · ${label}`}>
              <Report>{report}</Report>
            </Card>
            <div className="no-print flex flex-wrap gap-2">
              <Link className="btn btn-primary" href={`/during-surgery?case=${caseId}`}>Continue to during surgery</Link>
              <button className="btn btn-ghost" onClick={() => window.print()}>Print</button>
            </div>
          </>
        )}
        {busy && step !== 2 && <Spinner label={busy} />}
      </div>
    </>
  );
}
