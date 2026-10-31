import Link from "next/link";
import { ReactNode } from "react";
import { LuClipboardCheck, LuHouse, LuLock, LuSettings, LuShieldCheck, LuStethoscope, LuHeartPulse, LuScissors } from "react-icons/lu";
import { SessionUser } from "../lib/config";
import LogoutButton from "./logout-button";

const surgeonLinks = [
  { href: "/", label: "Home", icon: LuHouse },
  { href: "/pre-surgery", label: "Pre-surgery", icon: LuStethoscope },
  { href: "/during-surgery", label: "During surgery", icon: LuScissors },
  { href: "/post-surgery", label: "Post-surgery", icon: LuHeartPulse },
];

const adminLinks = [
  { href: "/verification", label: "Verification", icon: LuClipboardCheck },
  { href: "/admin/compliance", label: "NFR compliance", icon: LuShieldCheck },
];

const commonLinks = [
  { href: "/privacy", label: "Privacy & security", icon: LuLock },
  { href: "/settings", label: "Settings", icon: LuSettings },
];

export default function AppShell({ user, children }: { user: SessionUser; children: ReactNode }) {
  const links = [...(user.role === "admin" ? adminLinks : surgeonLinks), ...commonLinks];
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <aside className="flex shrink-0 flex-col bg-teal-950 text-teal-50 md:sticky md:top-0 md:h-screen md:w-64">
        <div className="px-5 py-5">
          <p className="text-xl font-semibold tracking-tight">SurgiAI</p>
          <p className="text-xs text-teal-300">{user.role === "admin" ? "Administration" : "Surgical decision support"}</p>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-1 md:flex-col">
          {links.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} className="flex items-center gap-3 whitespace-nowrap rounded-lg px-3 py-2.5 text-sm font-medium text-teal-100 hover:bg-teal-900">
              <Icon className="text-lg" /> {label}
            </Link>
          ))}
        </nav>
        <div className="border-t border-teal-900 px-5 py-4 text-sm">
          <p className="font-medium">{user.full_name}</p>
          <p className="mb-3 text-xs capitalize text-teal-300">{user.role}</p>
          <LogoutButton />
        </div>
      </aside>
      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8 sm:py-8">
        <div className="mx-auto max-w-5xl">{children}</div>
      </main>
    </div>
  );
}
