import SiteHeader from "../components/site-header";
import DuringSurgeryWorkspace from "../components/during-surgery-workspace";

export default function DuringSurgeryPage() {
  return (
    <div className="min-h-screen">
      <SiteHeader active="during-surgery" />
      <main className="mx-auto max-w-3xl px-5 pb-16 pt-10 sm:px-8">
        <p className="eyebrow mb-4">Intra-operative assistant · 02</p>
        <h1 className="text-4xl font-semibold leading-tight text-[var(--green-dark)]">
          Ask the surgical assistant.
        </h1>
        <p className="mt-4 text-base leading-7 text-[var(--muted)]">
          Enter patient history, then type or speak a question for guidance.
        </p>
        <DuringSurgeryWorkspace />
      </main>
    </div>
  );
}
