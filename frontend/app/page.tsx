import Link from "next/link";
import { redirect } from "next/navigation";
import { cookies } from "next/headers";
import { LuHeartPulse, LuScissors, LuStethoscope } from "react-icons/lu";
import AppShell from "./components/app-shell";
import { BACKEND_URL, TOKEN_COOKIE } from "./lib/config";
import { CaseSummary } from "./lib/api";
import { getSession } from "./lib/session";

export const dynamic = "force-dynamic";

const modules = [
  { href: "/pre-surgery", title: "Pre-surgery", text: "Assess the patient and get a pre-operative report.", icon: LuStethoscope },
  { href: "/during-surgery", title: "During surgery", text: "Record the operative summary and ask the assistant.", icon: LuScissors },
  { href: "/post-surgery", title: "Post-surgery", text: "Medications, wound care and monitoring plan.", icon: LuHeartPulse },
];

const stageLabel = { pre: "Pre-op", intra: "Intra-op", post: "Post-op" } as const;

async function loadCases(): Promise<CaseSummary[]> {
  const token = cookies().get(TOKEN_COOKIE)?.value;
  try {
    const response = await fetch(`${BACKEND_URL}/cases`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
    return response.ok ? await response.json() : [];
  } catch {
    return [];
  }
}

export default async function Home() {
  const user = await getSession();
  if (!user) redirect("/login");
  if (user.role === "admin") redirect("/verification");
  const cases = (await loadCases()).slice(0, 6);
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <AppShell user={user}>
      <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">{greeting}, {user.full_name.split(" ")[0]}</h1>
      <p className="mt-1 text-sm text-slate-500">What would you like to do today?</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        {modules.map(({ href, title, text, icon: Icon }) => (
          <Link key={href} href={href} className="card group transition hover:border-teal-600 hover:shadow-md">
            <span className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50 text-xl text-teal-700"><Icon /></span>
            <p className="font-semibold">{title}</p>
            <p className="mt-1 text-sm text-slate-500">{text}</p>
          </Link>
        ))}
      </div>

      <h2 className="mb-3 mt-10 text-lg font-semibold">Your recent patients</h2>
      {cases.length === 0 ? (
        <div className="card text-sm text-slate-500">No patients yet. Start with a <Link className="font-semibold text-teal-700 underline" href="/pre-surgery">pre-surgery assessment</Link>.</div>
      ) : (
        <div className="card divide-y divide-slate-100 p-0">
          {cases.map((c) => (
            <Link key={c.case_id} href={`/${c.stage === "pre" ? "during" : "post"}-surgery?case=${c.case_id}`} className="flex items-center justify-between px-5 py-3 hover:bg-slate-50">
              <div>
                <p className="font-medium">{c.patient_label}</p>
                <p className="text-sm text-slate-500">{c.procedure_name}</p>
              </div>
              <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800">{stageLabel[c.stage]}</span>
            </Link>
          ))}
        </div>
      )}
      <p className="mt-8 text-xs text-slate-400">Decision support only. Final clinical judgement rests with the surgeon. Only you can see your patients.</p>
    </AppShell>
  );
}
