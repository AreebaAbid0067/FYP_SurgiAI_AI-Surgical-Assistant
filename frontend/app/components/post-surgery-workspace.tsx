
"use client";

import { useState } from "react";

export default function PostSurgeryWorkspace() {
  const [patientHistory, setPatientHistory] = useState("");
  const [procedure, setProcedure] = useState("");
  const [surgeryDate, setSurgeryDate] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [question, setQuestion] = useState("");
  const [documents, setDocuments] = useState<FileList | null>(null);

  const field =
    "mt-2 w-full border border-[var(--line)] bg-white p-3 text-sm outline-none focus:border-[var(--green)]";

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    alert(
      "Your information has been entered. AI connection will be added in the next step."
    );
  };

  return (
    <form onSubmit={handleSubmit} className="mt-8 space-y-8">
      <section className="space-y-5 border border-[var(--line)] bg-white p-5 sm:p-6">
        <div>
          <p className="eyebrow">01 · Patient information</p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--green-dark)]">
            Patient and surgery details
          </h2>
        </div>

        <label className="block">
          <span className="text-sm font-medium">Surgical procedure</span>
          <input
            className={field}
            value={procedure}
            onChange={(event) => setProcedure(event.target.value)}
            placeholder="e.g. Appendectomy"
            required
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium">Date of surgery</span>
          <input
            className={field}
            type="date"
            value={surgeryDate}
            onChange={(event) => setSurgeryDate(event.target.value)}
            required
          />
        </label>

        <label className="block">
          <span className="text-sm font-medium">
            Patient history, allergies and prescribed medicines
          </span>
          <textarea
            className={field}
            rows={4}
            value={patientHistory}
            onChange={(event) => setPatientHistory(event.target.value)}
            placeholder="Enter relevant patient information..."
            required
          />
        </label>
      </section>

      <section className="space-y-5 border border-[var(--line)] bg-white p-5 sm:p-6">
        <div>
          <p className="eyebrow">02 · Recovery review</p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--green-dark)]">
            Postoperative symptoms
          </h2>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            Record the symptoms reported by the patient, including when they
            started and whether they are getting worse.
          </p>
        </div>

        <label className="block">
          <span className="text-sm font-medium">Current symptoms or concerns</span>
          <textarea
            className={field}
            rows={3}
            value={symptoms}
            onChange={(event) => setSymptoms(event.target.value)}
            placeholder="e.g. pain, swelling, nausea, fever, or no current symptoms"
          />
        </label>
      </section>

      <section className="space-y-5 border border-[var(--line)] bg-white p-5 sm:p-6">
        <div>
          <p className="eyebrow">03 · Medical records</p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--green-dark)]">
            Upload patient documents
          </h2>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            Select relevant discharge summaries, prescriptions, laboratory
            reports, or other postoperative records.
          </p>
        </div>

        <label className="block">
          <span className="text-sm font-medium">Choose documents</span>
          <input
            className="upload-input"
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            multiple
            onChange={(event) => setDocuments(event.target.files)}
          />
        </label>

        {documents && documents.length > 0 && (
          <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--muted)]">
            {Array.from(documents).map((file, index) => (
              <li key={`${file.name}-${index}`}>
                {file.name}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-5 border border-[var(--line)] bg-white p-5 sm:p-6">
        <div>
          <p className="eyebrow">04 · Learning and support</p>
          <h2 className="mt-2 text-xl font-semibold text-[var(--green-dark)]">
            Ask SurgiAI
          </h2>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            Enter a question about postoperative care, recovery monitoring,
            prescribed medication information, or follow-up considerations.
          </p>
        </div>

        <label className="block">
          <span className="text-sm font-medium">Your question</span>
          <textarea
            className={field}
            rows={3}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="e.g. What information should be reviewed at the follow-up appointment?"
          />
        </label>

        <div className="border-l-2 border-amber-500 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
          SurgiAI is an assistive learning tool, not a substitute for a
          qualified clinician or the treating surgeon's instructions. Severe
          pain, breathing difficulty, heavy bleeding, confusion, or other
          urgent warning signs require immediate medical assessment.
        </div>

        <button
          type="submit"
          className="bg-[var(--green-dark)] px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
        >
          Save information
        </button>
      </section>
    </form>
  );
}
