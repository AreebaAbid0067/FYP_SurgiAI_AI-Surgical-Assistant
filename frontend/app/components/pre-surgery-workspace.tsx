"use client";

import { useState } from "react";
import Markdown from "markdown-to-jsx";
import FileUpload from "./file-upload";
import SiteHeader from "./site-header";
import { uploadPreSurgeryFiles } from "../actions/pre-surgery-file-upload";

type UploadedFiles = Record<string, File | null>;

const stages = [
  {
    number: "01",
    title: "Clinical inputs",
    description: "Prescription, imaging scan, lab report, and patient history.",
  },
  {
    number: "02",
    title: "Document analysis",
    description: "Dedicated analyzers extract findings from each uploaded record.",
  },
  {
    number: "03",
    title: "Planning agents",
    description: "Instrumentation, risk, anesthesia, and emergency planning run in sequence.",
  },
  {
    number: "04",
    title: "Surgical workflow",
    description: "An accumulator brings the findings into one structured report.",
  },
];

const technologyChoices = [
  {
    name: "Next.js, React, TypeScript, and Tailwind CSS",
    reason: "They make a responsive web screen that is quick to build and easier to keep consistent.",
  },
  {
    name: "Python and FastAPI",
    reason: "Python connects naturally to AI tools, and FastAPI receives the uploaded records and returns the report.",
  },
  {
    name: "LangGraph",
    reason: "It lets us run specialist steps in a clear order while passing the same patient information between them.",
  },
  {
    name: "Groq vision model",
    reason: "It can read text and findings from prescription, scan, and lab-report images.",
  },
];

export default function PreSurgeryWorkspace() {
  const [files, setFiles] = useState<UploadedFiles>({
    prescription: null,
    scan: null,
    labReport: null,
  });
  const [operation, setOperation] = useState("");
  const [patientHistory, setPatientHistory] = useState("");
  const [report, setReport] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleGenerateReport = async () => {
    if (!operation.trim()) {
      setError("Enter the planned procedure before generating a report.");
      return;
    }
    if (!files.prescription || !files.scan || !files.labReport) {
      setError("Upload all three records to continue.");
      return;
    }

    setError("");
    setReport("");
    setIsLoading(true);
    try {
      const result = await uploadPreSurgeryFiles(files, operation, patientHistory);
      if (result.status === "error") {
        setError(result.message);
        return;
      }

      setReport(
        typeof result.data === "string"
          ? result.data
          : JSON.stringify(result.data, null, 2)
      );
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "The report could not be generated. Check the backend connection and try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <SiteHeader active="pre-surgery" />

      <div className="mx-auto max-w-6xl px-5 pb-16 pt-10 sm:px-8 sm:pt-14">
        <section className="reveal grid gap-8 border-b border-[var(--line)] pb-10 md:grid-cols-[1.2fr_0.8fr] md:items-end">
          <div>
            <p className="eyebrow mb-4">Clinical preparation · 01</p>
            <h1 className="max-w-2xl text-4xl font-semibold leading-tight text-[var(--green-dark)] sm:text-5xl">
              A clearer picture before the procedure.
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-[var(--muted)]">
              Bring key patient records together and generate a structured
              pre-operative planning report.
            </p>
          </div>
          <div className="border-l-2 border-[var(--green)] pl-5 text-sm leading-6 text-[var(--muted)]">
            <span className="eyebrow">Built as a multi-step agent workflow</span>
            <p className="mt-2">
              Separate document analyzers feed specialist planning steps, then
              converge into a single surgical workflow report.
            </p>
          </div>
        </section>

        <section className="grid gap-12 py-10 lg:grid-cols-[minmax(0,1.15fr)_minmax(300px,0.85fr)]">
          <div className="reveal" style={{ animationDelay: "80ms" }}>
            <div className="mb-6 flex items-baseline justify-between gap-4">
              <div>
                <p className="eyebrow">Generate a report</p>
                <h2 className="mt-2 text-2xl font-semibold text-[var(--green-dark)]">
                  Patient preparation
                </h2>
              </div>
              <span className="text-xs text-[var(--muted)]">All records required</span>
            </div>

            <label className="mb-2 block text-sm font-medium" htmlFor="operation">
              Planned procedure
            </label>
            <input
              id="operation"
              value={operation}
              onChange={(event) => setOperation(event.target.value)}
              placeholder="e.g. Laparoscopic cholecystectomy"
              className="mb-6 w-full border border-[var(--line)] bg-white px-3 py-3 text-sm outline-none transition focus:border-[var(--green)]"
            />

            <div className="mb-6 border-y border-[var(--line)] py-5">
              <FileUpload onFilesChange={setFiles} />
            </div>

            <label className="mb-2 block text-sm font-medium" htmlFor="history">
              Patient history
            </label>
            <textarea
              id="history"
              value={patientHistory}
              onChange={(event) => setPatientHistory(event.target.value)}
              placeholder="Relevant history, allergies, and existing conditions"
              rows={4}
              className="mb-5 w-full resize-y border border-[var(--line)] bg-white px-3 py-3 text-sm leading-6 outline-none transition focus:border-[var(--green)]"
            />

            {error && (
              <p role="alert" className="mb-4 border-l-2 border-red-600 bg-red-50 px-3 py-2 text-sm text-red-800">
                {error}
              </p>
            )}
            <button
              type="button"
              onClick={handleGenerateReport}
              disabled={isLoading}
              className="w-full bg-[var(--green-dark)] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[var(--green)] disabled:cursor-wait disabled:opacity-60 sm:w-auto"
            >
              {isLoading ? "Analyzing records..." : "Generate pre-surgery report"}
            </button>

            {(isLoading || report) && (
              <section aria-live="polite" className="mt-8 border-t border-[var(--line)] pt-6">
                <p className="eyebrow">Generated output</p>
                {isLoading ? (
                  <p className="mt-3 animate-pulse text-sm text-[var(--muted)]">
                    Analyzing records and assembling the workflow...
                  </p>
                ) : (
                  <article className="prose prose-sm mt-4 max-w-none leading-7">
                    <Markdown>{report}</Markdown>
                  </article>
                )}
              </section>
            )}
          </div>

          <aside className="border-t border-[var(--line)] pt-6 lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
            <p className="eyebrow">How it was developed</p>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--green-dark)]">
              From records to plan
            </h2>
            <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
              The pre-surgery agent is assembled as a directed workflow. Each
              stage adds a focused clinical perspective to shared patient state.
            </p>

            <ol className="mt-7">
              {stages.map((stage, index) => (
                <li key={stage.number} className="relative flex gap-4 pb-7 last:pb-0">
                  {index < stages.length - 1 && (
                    <span className="absolute left-[15px] top-8 h-[calc(100%-2rem)] w-px bg-[var(--line)]" />
                  )}
                  <span className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center border border-[var(--green)] bg-[var(--background)] text-xs font-semibold text-[var(--green)]">
                    {stage.number}
                  </span>
                  <div className="pt-0.5">
                    <h3 className="text-sm font-semibold">{stage.title}</h3>
                    <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
                      {stage.description}
                    </p>
                  </div>
                </li>
              ))}
            </ol>

            <div className="mt-8 border-t border-[var(--line)] pt-5">
              <p className="eyebrow">Implementation</p>
              <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
                FastAPI receives the records, image analyzers extract their
                contents, and a LangGraph state graph coordinates the planning
                nodes before returning the final workflow.
              </p>
            </div>

            <div className="mt-8 border-t border-[var(--line)] pt-5">
              <p className="eyebrow">Technology choices</p>
              <ul className="mt-4 space-y-4">
                {technologyChoices.map((choice) => (
                  <li key={choice.name}>
                    <h3 className="text-sm font-semibold">{choice.name}</h3>
                    <p className="mt-1 text-sm leading-6 text-[var(--muted)]">
                      {choice.reason}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          </aside>
        </section>
      </div>
    </div>
  );
}