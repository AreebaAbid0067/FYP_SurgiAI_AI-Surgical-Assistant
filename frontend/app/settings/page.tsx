"use client";

import { ReactNode } from "react";
import { Card, PageHeader } from "../components/ui";
import { Settings, useSettings } from "../lib/settings";

function Choice<T extends string | number>({ options, value, onChange }: { options: { value: T; label: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((o) => (
        <button key={String(o.value)} type="button" onClick={() => onChange(o.value)} aria-pressed={value === o.value}
          className={`btn ${value === o.value ? "btn-primary" : "btn-ghost"}`}>{o.label}</button>
      ))}
    </div>
  );
}

const Row = ({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) => (
  <div className="border-b border-slate-200 py-4 last:border-0">
    <p className="font-semibold text-slate-800">{label}</p>
    {hint && <p className="mb-2 text-sm text-slate-500">{hint}</p>}
    {children}
  </div>
);

export default function SettingsPage() {
  const { settings, update } = useSettings();
  return (
    <>
      <PageHeader eyebrow="Preferences" title="Settings" description="Saved on this device only." />
      <Card>
        <Row label="Theme" hint="Dark mode is easier on the eyes in a dim operating room.">
          <Choice<Settings["theme"]> value={settings.theme} onChange={(theme) => update({ theme })}
            options={[{ value: "light", label: "Light" }, { value: "dark", label: "Dark" }, { value: "system", label: "Match device" }]} />
        </Row>
        <Row label="Text size">
          <Choice<Settings["textSize"]> value={settings.textSize} onChange={(textSize) => update({ textSize })}
            options={[{ value: "normal", label: "Normal" }, { value: "large", label: "Large" }, { value: "xlarge", label: "Extra large" }]} />
        </Row>
        <Row label="Voice language" hint="Language used to understand your voice and to read answers.">
          <Choice value={settings.voiceLang} onChange={(voiceLang) => update({ voiceLang })}
            options={[{ value: "en-US", label: "English (US)" }, { value: "en-IN", label: "English (India)" }, { value: "en-GB", label: "English (UK)" }]} />
        </Row>
        <Row label="Speaking speed">
          <Choice value={settings.speechRate} onChange={(speechRate) => update({ speechRate })}
            options={[{ value: 0.8, label: "Slow" }, { value: 1, label: "Normal" }, { value: 1.25, label: "Fast" }]} />
        </Row>
        <Row label="Read answers aloud automatically" hint="Used by hands-free mode during surgery.">
          <Choice<string> value={settings.autoRead ? "on" : "off"} onChange={(v) => update({ autoRead: v === "on" })}
            options={[{ value: "on", label: "On" }, { value: "off", label: "Off" }]} />
        </Row>
      </Card>
    </>
  );
}
