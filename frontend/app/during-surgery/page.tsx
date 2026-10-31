"use client";

import { ReactNode, Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { LuBrain, LuEar, LuMic, LuMicOff, LuSend, LuVolume2 } from "react-icons/lu";
import { COMMANDS, useHandsFree, VoiceState } from "../components/use-hands-free";
import { useSettings } from "../lib/settings";
import { CasePicker, useCases } from "../components/case-picker";
import { Alert, Card, ChipGroup, Field, PageHeader, RadioChips, Report, Spinner } from "../components/ui";
import { api, ApiError, Catalog, postJson } from "../lib/api";

function DuringSurgery() {
  const { settings } = useSettings();
  const { cases, current, error, reload, select } = useCases();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [summary, setSummary] = useState<Record<string, string | string[]>>({});
  const [saved, setSaved] = useState("");
  const [query, setQuery] = useState("");
  const [answers, setAnswers] = useState<{ q: string; a: string }[]>([]);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState("");

  useEffect(() => { api<Catalog>("procedures").then(setCatalog).catch(() => undefined); }, []);
  useEffect(() => {
    setSummary((current?.data.intraop.summary as Record<string, string | string[]>) ?? {});
    setAnswers((current?.data.intraop.notes ?? []).map((n) => ({ q: n.question, a: n.answer })));
  }, [current]);

  const procedure = catalog?.procedures.find((p) => p.id === current?.procedure_id);
  const groups: Record<string, string[]> = { ...(catalog?.common_intraop ?? {}), ...(procedure?.intraop_extras ?? {}) };
  const multi = new Set(["findings", "events"]);
  const title = (k: string) => k.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

  const saveSummary = async () => {
    if (!current) return;
    try {
      await postJson(`cases/${current.case_id}/intraop-summary`, { summary });
      setSaved("Operative summary saved."); setProblem(""); reload();
    } catch (e) { setProblem((e as ApiError).message); }
  };

  const ask = async (text = query) => {
    if (!current || !text.trim()) return;
    setBusy(true); setProblem("");
    try {
      const result = await postJson<unknown>("surgery", { surgeon_query: text, case_id: current.case_id });
      setAnswers((a) => [...a, { q: text, a: typeof result === "string" ? result : JSON.stringify(result) }]);
      setQuery("");
    } catch (e) { setProblem((e as ApiError).message); }
    finally { setBusy(false); }
  };

  const voice = useHandsFree({
    lang: settings.voiceLang,
    rate: settings.speechRate,
    autoRead: settings.autoRead,
    onQuestion: async (text) => {
      if (!current) return "Please open a patient first.";
      try {
        const result = await postJson<unknown>("surgery", { surgeon_query: text, case_id: current.case_id });
        const answer = typeof result === "string" ? result : JSON.stringify(result);
        setAnswers((a) => [...a, { q: text, a: answer }]);
        return answer;
      } catch (e) {
        return (e as ApiError).message;
      }
    },
  });
  const speak = (text: string) => { void voice.speak(text); };
  const banner: Record<VoiceState, { cls: string; icon: ReactNode; title: string; hint: string }> = {
    off: { cls: "bg-slate-100 text-slate-700", icon: <LuMicOff />, title: "Hands-free is off", hint: "Press Start once, then control everything by voice." },
    waiting: { cls: "bg-sky-100 text-sky-900", icon: <LuEar />, title: "Listening for your command", hint: `Say “${COMMANDS.wake}”` },
    recording: { cls: "bg-red-600 text-white animate-pulse", icon: <LuMic />, title: "RECORDING your question", hint: `Say “${COMMANDS.done}” when finished, or “${COMMANDS.cancel}”` },
    thinking: { cls: "bg-amber-100 text-amber-900", icon: <LuBrain />, title: "Finding the answer…", hint: "Please wait" },
    speaking: { cls: "bg-emerald-100 text-emerald-900", icon: <LuVolume2 />, title: "Speaking", hint: "The answer is being read aloud" },
    error: { cls: "bg-red-100 text-red-800", icon: <LuMicOff />, title: "Voice problem", hint: voice.error },
  };
  const b = banner[voice.state];

  return (
    <>
      <PageHeader eyebrow="Step 2 of 3" title="During surgery" description="Record the operative summary and ask the assistant hands-free." />
      {!current ? (
        <CasePicker cases={cases} error={error} onSelect={select} emptyHint="No patients yet." />
      ) : (
        <div className="space-y-4">
          <Card title={current.patient_label} subtitle={current.procedure_name}>
            <p className="whitespace-pre-line text-sm text-slate-600">{current.data.history_text}</p>
          </Card>

          <Card title="Operative summary" subtitle="Used to tailor the post-operative plan.">
            {Object.entries(groups).map(([key, options]) => (
              <Field key={key} label={title(key)}>
                {multi.has(key) ? (
                  <ChipGroup options={options} value={(summary[key] as string[]) ?? []} onChange={(v) => setSummary({ ...summary, [key]: v })} />
                ) : (
                  <RadioChips options={options} value={(summary[key] as string) ?? ""} onChange={(v) => setSummary({ ...summary, [key]: v })} />
                )}
              </Field>
            ))}
            <div className="flex items-center gap-3">
              <button className="btn btn-primary" onClick={saveSummary}>Save summary</button>
              {saved && <span className="text-sm text-emerald-700">{saved}</span>}
            </div>
          </Card>

          <Card title="Surgical assistant" subtitle="Hands-free: no touching needed once started.">
            {voice.supported ? (
              <div className={`mb-4 rounded-xl p-5 ${b.cls}`} role="status" aria-live="polite">
                <div className="flex items-center gap-4">
                  <span className="text-4xl">{b.icon}</span>
                  <div className="flex-1">
                    <p className="text-xl font-bold">{b.title}</p>
                    <p className="text-sm opacity-90">{b.hint}</p>
                  </div>
                  {voice.state === "off" || voice.state === "error" ? (
                    <button className="btn btn-primary" onClick={() => void voice.start()}>Start hands-free</button>
                  ) : (
                    <div className="flex gap-2">
                      {voice.state === "speaking" && <button className="btn btn-ghost" onClick={voice.skipReading}>Skip</button>}
                      <button className="btn btn-ghost" onClick={voice.stop}>Stop</button>
                    </div>
                  )}
                </div>
                {voice.transcript && <p className="mt-3 rounded-lg bg-white/20 p-3 text-lg">“{voice.transcript}”</p>}
              </div>
            ) : (
              <Alert tone="error">Voice needs Google Chrome or Microsoft Edge. You can still type below.</Alert>
            )}
            <div className="mb-3 flex gap-2">
              <input className="input" value={query} maxLength={4000} placeholder="Or type: e.g. Appendix perforated, what should I do?" onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask()} />
              <button className="btn btn-primary" onClick={() => ask()} disabled={busy} aria-label="Ask"><LuSend /></button>
            </div>
            {busy && <Spinner label="Thinking…" />}
            {problem && <Alert tone="error">{problem}</Alert>}
            <div className="mt-3 space-y-4">
              {[...answers].reverse().map((item, i) => (
                <div key={i} className="rounded-lg border border-slate-200 p-3">
                  <p className="mb-2 text-sm font-semibold text-slate-800">{item.q}</p>
                  <Report>{item.a}</Report>
                  <button className="mt-2 flex items-center gap-1 text-xs text-teal-700" onClick={() => speak(item.a)}><LuVolume2 /> Read aloud</button>
                </div>
              ))}
            </div>
          </Card>

          <Link className="btn btn-primary no-print" href={`/post-surgery?case=${current.case_id}`}>Continue to post-surgery</Link>
        </div>
      )}
    </>
  );
}

export default function Page() {
  return <Suspense fallback={<Spinner label="Loading…" />}><DuringSurgery /></Suspense>;
}
