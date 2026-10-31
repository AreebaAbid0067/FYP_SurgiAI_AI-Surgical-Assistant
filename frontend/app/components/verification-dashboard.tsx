"use client";

import { useEffect, useMemo, useState } from "react";

type ReviewStatus = "pass" | "partial" | "fail" | "needs_expert_review";
type Phase = "preoperative" | "intraoperative" | "postoperative";

type VerificationQuestion = {
  question_id: number;
  phase: Phase;
  prompt: string;
  run_count: number;
  latest_response: string | null;
  latest_run_id: number | null;
  latest_run_at: string | null;
  review_status: ReviewStatus | null;
  reviewer_name: string | null;
  review_comments: string | null;
  harmful_error: number | null;
  reference_answer: string | null;
  source_notes: string | null;
  reference_approved: number | null;
};

type SourceReference = {
  source_id: string;
  title: string;
  version: string;
  url: string;
  review_status: string;
};

type Dashboard = {
  case: {
    case_id: string;
    title: string;
    procedure: string;
    summary: string;
    signoff_reviewer: string | null;
    signoff_at: string | null;
    signoff_attested: number;
  };
  cases?: { case_id: string; title: string; procedure: string; question_count: number; signoff_at: string | null }[];
  questions: VerificationQuestion[];
  sources: SourceReference[];
  metrics: {
    case_count: number;
    case_target: number;
    cases_reviewed: number;
    questions_tested: number;
    questions_reviewed: number;
    pending_reviews: number;
    pass_count: number;
    partial_count: number;
    fail_count: number;
    critical_errors: number;
    approved_references: number;
    reference_count: number;
    expert_approval: string;
    report_status: string;
  };
};

const phases: { id: Phase; label: string }[] = [
  { id: "preoperative", label: "Preoperative" },
  { id: "intraoperative", label: "Intraoperative" },
  { id: "postoperative", label: "Postoperative" },
];

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const message =
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof body.detail === "string"
        ? body.detail
        : `Request failed (HTTP ${response.status}).`;
    throw new Error(message);
  }
  return body as T;
}

async function fetchDashboard(caseId?: string) {
  const query = caseId ? `?case_id=${encodeURIComponent(caseId)}` : "";
  return requestJson<Dashboard>(`/api/backend/verification${query}`);
}

function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string | number;
  detail?: string;
}) {
  return (
    <article className="verification-metric">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </article>
  );
}

function statusLabel(status: ReviewStatus | null) {
  if (!status) return "Pending review";
  return {
    pass: "Pass",
    partial: "Partial",
    fail: "Fail",
    needs_expert_review: "Needs expert review",
  }[status];
}

export default function VerificationDashboard() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [activePhase, setActivePhase] = useState<Phase>("preoperative");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [reviewStatus, setReviewStatus] =
    useState<ReviewStatus>("needs_expert_review");
  const [reviewerName, setReviewerName] = useState("");
  const [comments, setComments] = useState("");
  const [harmfulError, setHarmfulError] = useState(false);
  const [referenceAnswer, setReferenceAnswer] = useState("");
  const [sourceNotes, setSourceNotes] = useState("");
  const [referenceApproved, setReferenceApproved] = useState(false);
  const [clinicianAttested, setClinicianAttested] = useState(false);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [signingOff, setSigningOff] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [caseId, setCaseId] = useState<string | undefined>(undefined);

  async function switchCase(id: string) {
    setCaseId(id);
    setSelectedId(null);
    setActivePhase("preoperative");
    try {
      const result = await fetchDashboard(id);
      setDashboard(result);
      setSelectedId(result.questions.find((q) => q.phase === "preoperative")?.question_id ?? result.questions[0]?.question_id ?? null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load that case.");
    }
  }

  async function refreshDashboard() {
    const result = await fetchDashboard(caseId);
    setDashboard(result);
    setSelectedId((current) =>
      current ?? result.questions.find((question) => question.phase === activePhase)?.question_id ?? null
    );
  }

  useEffect(() => {
    fetchDashboard()
      .then((result) => {
        setDashboard(result);
        setSelectedId(
          result.questions.find((question) => question.phase === "preoperative")
            ?.question_id ?? result.questions[0]?.question_id ?? null
        );
      })
      .catch((cause: unknown) => {
        setError(
          cause instanceof Error
            ? cause.message
            : "Could not load the verification dashboard."
        );
      })
      .finally(() => setLoading(false));
  }, []);

  const visibleQuestions = useMemo(
    () => dashboard?.questions.filter((question) => question.phase === activePhase) ?? [],
    [dashboard, activePhase]
  );
  const selectedQuestion =
    dashboard?.questions.find((question) => question.question_id === selectedId) ??
    visibleQuestions[0] ??
    null;

  useEffect(() => {
    if (!selectedQuestion) return;
    setReviewStatus(selectedQuestion.review_status ?? "needs_expert_review");
    setReviewerName(selectedQuestion.reviewer_name ?? "");
    setComments(selectedQuestion.review_comments ?? "");
    setHarmfulError(Boolean(selectedQuestion.harmful_error));
    setReferenceAnswer(selectedQuestion.reference_answer ?? "");
    setSourceNotes(selectedQuestion.source_notes ?? "");
    setReferenceApproved(Boolean(selectedQuestion.reference_approved));
  }, [selectedQuestion]);

  async function runQuestion() {
    if (!selectedQuestion) return;
    setRunning(true);
    setError("");
    setMessage("");
    try {
      await requestJson(
        `/api/backend/verification/questions/${selectedQuestion.question_id}/run`,
        { method: "POST" }
      );
      await refreshDashboard();
      setMessage("A real SurgiAI response was saved. It is awaiting reviewer assessment.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not run SurgiAI.");
    } finally {
      setRunning(false);
    }
  }

  async function saveReview(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedQuestion?.latest_run_id) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const result = await requestJson<Dashboard>(
        `/api/backend/verification/questions/${selectedQuestion.question_id}/review`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            run_id: selectedQuestion.latest_run_id,
            status: reviewStatus,
            reviewer_name: reviewerName,
            comments,
            harmful_error: harmfulError,
            reference_answer: referenceAnswer,
            source_notes: sourceNotes,
            reference_approved: referenceApproved,
          }),
        }
      );
      setDashboard(result);
      setMessage("Reviewer assessment saved to the local audit record.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save this review.");
    } finally {
      setSaving(false);
    }
  }

  async function signOffCase() {
    if (!dashboard) return;
    setSigningOff(true);
    setError("");
    setMessage("");
    try {
      const result = await requestJson<Dashboard>(
        `/api/backend/verification/cases/${encodeURIComponent(dashboard.case.case_id)}/signoff`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            reviewer_name: reviewerName,
            clinician_attested: clinicianAttested,
          }),
        }
      );
      setDashboard(result);
      setMessage("Case sign-off recorded.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not sign off the case.");
    } finally {
      setSigningOff(false);
    }
  }

  function selectPhase(phase: Phase) {
    setActivePhase(phase);
    const question = dashboard?.questions.find((item) => item.phase === phase);
    if (question) setSelectedId(question.question_id);
  }

  if (loading) {
    return <main className="verification-shell">Loading clinical verification workspace…</main>;
  }

  if (!dashboard) {
    return (
      <main className="verification-shell">
        <p className="verification-alert error">{error || "Verification data is unavailable."}</p>
      </main>
    );
  }

  const { metrics } = dashboard;
  const allReferencesApproved =
    metrics.approved_references === metrics.reference_count;

  return (
    <main className="verification-shell">
      <header className="verification-header">
        <div>
          <p className="eyebrow">Administrator · quality assurance</p>
          <h1>Clinical Verification</h1>
          <p className="verification-subtitle">
            Capture real SurgiAI responses and document clinician review against cited sources.
          </p>
        </div>
        <a className="verification-export" href="/api/backend/verification/report.csv">
          Export report CSV
        </a>
      </header>

      <div className="verification-alert">
        Research and quality-assurance workflow only — not for patient-care decisions.
        Reference answers are blank and unapproved until a qualified clinician writes,
        sources, and approves them. Reviewer identity is self-reported, not authenticated.
      </div>
      {error ? <div className="verification-alert error" role="alert">{error}</div> : null}
      {message ? <div className="verification-alert success" role="status">{message}</div> : null}

      <section className="verification-metrics" aria-label="Verification metrics">
        <MetricCard
          label="Cases reviewed"
          value={`${metrics.cases_reviewed} / ${metrics.case_target}`}
          detail={`${metrics.case_count} verified cases registered · awaiting clinician sign-off`}
        />
        <MetricCard label="Questions tested" value={metrics.questions_tested} />
        <MetricCard
          label="Reviewer assessments"
          value={metrics.questions_reviewed}
          detail={`${metrics.pending_reviews} pending`}
        />
        <MetricCard label="Pass" value={metrics.pass_count} />
        <MetricCard label="Partial" value={metrics.partial_count} />
        <MetricCard label="Fail" value={metrics.fail_count} />
        <MetricCard label="Flagged harmful errors" value={metrics.critical_errors} />
      </section>

      {dashboard.cases && dashboard.cases.length > 0 && (
        <nav className="flex flex-wrap gap-2" aria-label="Verification cases">
          {dashboard.cases.map((c) => (
            <button
              key={c.case_id}
              type="button"
              onClick={() => switchCase(c.case_id)}
              aria-pressed={c.case_id === dashboard.case.case_id}
              className={`rounded-full border px-3.5 py-1.5 text-sm font-medium ${
                c.case_id === dashboard.case.case_id ? "border-teal-700 bg-teal-700 text-white" : "border-slate-300 bg-white text-slate-700"
              }`}
            >
              {c.procedure}{c.signoff_at ? " ✓" : ""}
            </button>
          ))}
        </nav>
      )}

      <section className="verification-card case-card">
        <div>
          <p className="eyebrow">Pilot case · {dashboard.case.procedure}</p>
          <h2>{dashboard.case.title}</h2>
          <p>{dashboard.case.summary}</p>
        </div>
        <div className="case-progress">
          <span>Approved reference answers</span>
          <strong>{metrics.approved_references} / {metrics.reference_count}</strong>
          <span>Expert sign-off: <b>{metrics.expert_approval}</b></span>
        </div>
      </section>

      <section className="verification-card workflow-card">
        <h2>Pilot workflow</h2>
        <ol className="workflow-steps">
          <li className="complete"><span>1</span><div><b>Case registered</b><small>Complete</small></div></li>
          <li className={metrics.approved_references > 0 ? "active" : ""}><span>2</span><div><b>Reference answers</b><small>{metrics.approved_references} / {metrics.reference_count} approved</small></div></li>
          <li className={metrics.questions_tested > 0 ? "active" : ""}><span>3</span><div><b>AI responses</b><small>{metrics.questions_tested} questions tested</small></div></li>
          <li className={dashboard.case.signoff_at ? "complete" : ""}><span>4</span><div><b>Expert sign-off</b><small>{metrics.expert_approval}</small></div></li>
        </ol>
      </section>

      <div className="verification-workspace">
        <aside className="verification-card question-browser">
          <div className="section-heading">
            <div><p className="eyebrow">Case checklist</p><h2>Questions</h2></div>
            <span className="question-count">{dashboard.questions.length}</span>
          </div>
          <div className="phase-tabs" role="tablist" aria-label="Clinical phase">
            {phases.map((phase) => (
              <button
                type="button"
                role="tab"
                aria-selected={activePhase === phase.id}
                className={activePhase === phase.id ? "selected" : ""}
                key={phase.id}
                onClick={() => selectPhase(phase.id)}
              >
                {phase.label}
              </button>
            ))}
          </div>
          <div className="question-list">
            {visibleQuestions.map((question, index) => (
              <button
                type="button"
                key={question.question_id}
                onClick={() => setSelectedId(question.question_id)}
                className={`question-item ${selectedId === question.question_id ? "selected" : ""}`}
              >
                <span className="question-number">{String(index + 1).padStart(2, "0")}</span>
                <span className="question-item-body">
                  <span>{question.prompt}</span>
                  <small>{statusLabel(question.review_status)} · {question.run_count} run{question.run_count === 1 ? "" : "s"}</small>
                </span>
              </button>
            ))}
          </div>
          <div className="source-list">
            <h3>Reference sources</h3>
            {dashboard.sources.map((source) => (
              <a href={source.url} target="_blank" rel="noreferrer" key={source.source_id}>
                <b>{source.title}</b>
                <small>{source.version} · pending clinician review ↗</small>
              </a>
            ))}
          </div>
        </aside>

        <section className="verification-card answer-workspace">
          {selectedQuestion ? (
            <>
              <div className="section-heading selected-question-heading">
                <div>
                  <p className="eyebrow">{selectedQuestion.phase} checklist</p>
                  <h2>{selectedQuestion.prompt}</h2>
                </div>
                <span className={`review-badge ${selectedQuestion.review_status ?? "pending"}`}>
                  {statusLabel(selectedQuestion.review_status)}
                </span>
              </div>

              <div className="answer-section">
                <div className="answer-heading">
                  <div><h3>Actual SurgiAI response</h3><p>Generated by the same backend pipeline as the existing surgery feature.</p></div>
                  <button className="primary-button" type="button" onClick={runQuestion} disabled={running}>
                    {running ? "Running…" : selectedQuestion.run_count ? "Run again" : "Run SurgiAI"}
                  </button>
                </div>
                <div className="ai-answer" aria-live="polite">
                  {selectedQuestion.latest_response ? (
                    <>
                      <p>{selectedQuestion.latest_response}</p>
                      <small>Saved run #{selectedQuestion.latest_run_id} · {selectedQuestion.latest_run_at}</small>
                    </>
                  ) : (
                    <p className="empty-state">No AI answer recorded yet. Run SurgiAI to capture an actual response; generation may require configured Groq and Pinecone services.</p>
                  )}
                </div>
              </div>

              <form className="review-form" onSubmit={saveReview}>
                <div className="answer-heading">
                  <div><h3>Reviewer assessment</h3><p>Only completed reviewer assessments count toward performance metrics.</p></div>
                  <label className="field-label reviewer-field">
                    Reviewer name
                    <input required value={reviewerName} onChange={(event) => setReviewerName(event.target.value)} />
                  </label>
                </div>
                <div className="form-grid">
                  <label className="field-label">
                    Decision
                    <select value={reviewStatus} onChange={(event) => setReviewStatus(event.target.value as ReviewStatus)}>
                      <option value="pass">Pass</option>
                      <option value="partial">Partial</option>
                      <option value="fail">Fail</option>
                      <option value="needs_expert_review">Needs expert review</option>
                    </select>
                  </label>
                  <label className="check-field harmful-check">
                    <input type="checkbox" checked={harmfulError} onChange={(event) => setHarmfulError(event.target.checked)} />
                    Flag a potentially harmful error
                  </label>
                </div>
                <label className="field-label">
                  Reviewer comments / errors / omissions
                  <textarea rows={3} value={comments} onChange={(event) => setComments(event.target.value)} placeholder="Record discrepancies, missing information, or why expert review is needed." />
                </label>
                <label className="field-label">
                  Clinician-authored reference answer <span className="pending-inline">Not approved by default</span>
                  <textarea rows={4} value={referenceAnswer} onChange={(event) => setReferenceAnswer(event.target.value)} placeholder="Enter an evidence-based reference answer after clinical review." />
                </label>
                <label className="field-label">
                  Supporting sources and pinpoint citations
                  <textarea rows={2} value={sourceNotes} onChange={(event) => setSourceNotes(event.target.value)} placeholder="Cite source title/version and relevant section, page, or recommendation." />
                </label>
                <label className="check-field approval-check">
                  <input type="checkbox" checked={referenceApproved} onChange={(event) => setReferenceApproved(event.target.checked)} />
                  I am a qualified clinician and have verified this reference answer against the cited source(s).
                </label>
                <div className="form-actions">
                  <span>Saving creates an audit entry; earlier runs and assessments are retained.</span>
                  <button className="primary-button" type="submit" disabled={saving || !selectedQuestion.latest_run_id}>
                    {saving ? "Saving…" : "Save assessment"}
                  </button>
                </div>
              </form>

              <section className="signoff-panel">
                <div>
                  <h3>Case sign-off</h3>
                  <p>Requires a reviewed, sourced reference and a completed AI assessment for every checklist question.</p>
                  {dashboard.case.signoff_at ? (
                    <small>Signed by {dashboard.case.signoff_reviewer} · {dashboard.case.signoff_at} · self-attested</small>
                  ) : null}
                </div>
                <div className="signoff-controls">
                  <label className="check-field">
                    <input type="checkbox" checked={clinicianAttested} onChange={(event) => setClinicianAttested(event.target.checked)} />
                    I am a qualified clinician and approve the completed pilot review.
                  </label>
                  <button className="secondary-button" type="button" onClick={signOffCase} disabled={signingOff || !allReferencesApproved || metrics.questions_reviewed !== metrics.reference_count || !clinicianAttested}>
                    {signingOff ? "Signing off…" : dashboard.case.signoff_at ? "Record updated sign-off" : "Sign off pilot case"}
                  </button>
                </div>
              </section>
            </>
          ) : (
            <p className="empty-state">No questions are registered for this case.</p>
          )}
        </section>
      </div>
    </main>
  );
}

