"use client";

import Markdown from "markdown-to-jsx";
import { ReactNode } from "react";
import { LuCircleAlert, LuCircleCheck, LuInfo, LuLoaderCircle, LuPlus } from "react-icons/lu";
import { explain } from "../lib/glossary";

export function Card({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-base font-semibold text-slate-900">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-sm text-slate-500">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm text-slate-500">{description}</p>}
      </div>
      {action}
    </div>
  );
}

type Tone = "error" | "success" | "info" | "warning";
const tones: Record<Tone, { box: string; icon: ReactNode }> = {
  error: { box: "border-red-200 bg-red-50 text-red-800", icon: <LuCircleAlert className="mt-0.5 shrink-0" /> },
  success: { box: "border-emerald-200 bg-emerald-50 text-emerald-800", icon: <LuCircleCheck className="mt-0.5 shrink-0" /> },
  info: { box: "border-sky-200 bg-sky-50 text-sky-800", icon: <LuInfo className="mt-0.5 shrink-0" /> },
  warning: { box: "border-amber-200 bg-amber-50 text-amber-900", icon: <LuCircleAlert className="mt-0.5 shrink-0" /> },
};

export function Alert({ tone = "info", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`flex gap-2.5 rounded-lg border px-3.5 py-3 text-sm ${tones[tone].box}`}>
      {tones[tone].icon}
      <div>{children}</div>
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500">
      <LuLoaderCircle className="animate-spin" /> {label}
    </span>
  );
}

export function Chip({
  label,
  selected,
  onClick,
  tone = "default",
  explain: hint,
}: {
  label: string;
  selected: boolean;
  onClick: () => void;
  tone?: "default" | "danger";
  explain?: string;
}) {
  const on =
    tone === "danger"
      ? "border-red-600 bg-red-600 text-white"
      : "border-teal-700 bg-teal-700 text-white";
  const info = hint ?? explain(label);
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`rounded-xl border px-3.5 py-2 text-left text-sm font-medium leading-tight transition ${
        selected ? on : "border-slate-300 bg-white text-slate-800 hover:border-teal-600"
      }`}
    >
      {label}
      {info && (
        <span className={`mt-0.5 block text-xs font-normal ${selected ? "text-white/80" : "text-slate-500"}`}>({info})</span>
      )}
    </button>
  );
}

// Collapsible block that keeps long forms short. Shows how many answers are selected.
export function Section({
  title,
  count = 0,
  defaultOpen = false,
  children,
}: {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  return (
    <details open={defaultOpen} className="group rounded-xl border border-slate-200 bg-white">
      <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-semibold text-slate-800">
        <span>{title}</span>
        <span className="flex items-center gap-2 text-xs font-medium text-slate-500">
          {count > 0 && <span className="rounded-full bg-teal-100 px-2 py-0.5 text-teal-800">{count} selected</span>}
          <span className="transition group-open:rotate-180">▾</span>
        </span>
      </summary>
      <div className="border-t border-slate-100 px-4 py-4">{children}</div>
    </details>
  );
}

// Multi-select (array) or single-select (string) chip group with an optional custom entry.
export function ChipGroup({
  options,
  value,
  onChange,
  tone,
}: {
  options: string[];
  value: string[];
  onChange: (next: string[]) => void;
  tone?: "default" | "danger";
}) {
  const toggle = (option: string) =>
    onChange(value.includes(option) ? value.filter((v) => v !== option) : [...value, option]);
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((option) => (
        <Chip key={option} label={option} tone={tone} selected={value.includes(option)} onClick={() => toggle(option)} />
      ))}
    </div>
  );
}

export function RadioChips({
  options,
  value,
  onChange,
}: {
  options: string[];
  value?: string;
  onChange: (next: string) => void;
}) {
  return (
    <div role="radiogroup" className="flex flex-wrap gap-2">
      {options.map((option) => (
        <Chip key={option} label={option} selected={value === option} onClick={() => onChange(value === option ? "" : option)} />
      ))}
    </div>
  );
}

export function CustomEntry({
  placeholder,
  values,
  onChange,
}: {
  placeholder: string;
  values: string[];
  onChange: (next: string[]) => void;
}) {
  const add = (input: HTMLInputElement) => {
    const text = input.value.trim();
    if (text && !values.includes(text)) onChange([...values, text]);
    input.value = "";
  };
  return (
    <div className="mt-2">
      <div className="flex gap-2">
        <input
          className="input max-w-xs"
          placeholder={placeholder}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              add(event.currentTarget);
            }
          }}
          onBlur={(event) => add(event.currentTarget)}
        />
        <span className="flex items-center text-xs text-slate-400"><LuPlus className="mr-1" />Other - press Enter</span>
      </div>
      {values.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {values.map((value) => (
            <Chip key={value} label={`${value} ✕`} explain="" selected onClick={() => onChange(values.filter((v) => v !== value))} />
          ))}
        </div>
      )}
    </div>
  );
}

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <div className="mb-5">
      <div className="mb-2 flex items-baseline gap-2">
        <span className="text-sm font-semibold text-slate-800">{label}</span>
        {hint && <span className="text-xs text-slate-400">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

export function Steps({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="mb-6 flex flex-wrap gap-2" aria-label="Progress">
      {steps.map((step, index) => (
        <li
          key={step}
          aria-current={index === current ? "step" : undefined}
          className={`flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-medium ${
            index === current
              ? "bg-teal-700 text-white"
              : index < current
                ? "bg-teal-100 text-teal-800"
                : "bg-slate-200 text-slate-500"
          }`}
        >
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/25 text-xs">{index + 1}</span>
          {step}
        </li>
      ))}
    </ol>
  );
}

export function Report({ children }: { children: string }) {
  return (
    <article className="md-report">
      <Markdown>{children}</Markdown>
    </article>
  );
}
