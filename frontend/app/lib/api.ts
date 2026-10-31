export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

// Calls the backend through the authenticated Next.js proxy.
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/backend/${path}`, { ...init, cache: "no-store" });
  } catch {
    throw new ApiError("Network error. Check your connection and try again.", 0);
  }
  if (response.status === 401 && typeof window !== "undefined") {
    window.location.href = "/login";
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const record = (body ?? {}) as { detail?: unknown; message?: unknown };
    const detail =
      typeof record.detail === "string"
        ? record.detail
        : typeof record.message === "string"
          ? record.message
          : `Request failed (HTTP ${response.status}).`;
    throw new ApiError(detail, response.status);
  }
  return body as T;
}

export const postJson = <T,>(path: string, data: unknown) =>
  api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

// ---- shared types ----------------------------------------------------------
export type ProcedureDef = {
  id: string;
  name: string;
  category: string;
  symptoms: string[];
  intraop_extras: Record<string, string[]>;
};

export type Catalog = {
  common_intake: {
    sex: string[]; urgency: string[]; asa: string[]; smoking: string[]; alcohol: string[];
    prior_surgery: string[]; comorbidities: string[]; allergies: string[]; medications: string[];
  };
  common_intraop: Record<string, string[]>;
  procedures: ProcedureDef[];
};

export type Intake = {
  age?: string; sex?: string; urgency?: string; asa?: string; smoking?: string;
  alcohol?: string; prior_surgery?: string;
  symptoms: string[]; comorbidities: string[]; allergies: string[]; medications: string[];
  custom_comorbidities: string[]; custom_allergies: string[]; custom_medications: string[];
};

export type CaseSummary = {
  case_id: string;
  stage: "pre" | "intra" | "post";
  patient_label: string;
  procedure_id: string | null;
  procedure_name: string;
  has_preop: boolean;
  has_intraop: boolean;
  has_postop: boolean;
  updated_at: string;
};

export type CaseDetail = CaseSummary & {
  data: {
    intake: Partial<Intake>;
    notes: string;
    history_text: string;
    preop_report: string;
    intraop: { summary: Record<string, string | string[]> | null; notes: { question: string; answer: string }[] };
    postop: { plan: string; mode: string; status: string } | null;
  };
};

export const emptyIntake = (): Intake => ({
  symptoms: [], comorbidities: [], allergies: [], medications: [],
  custom_comorbidities: [], custom_allergies: [], custom_medications: [],
});
