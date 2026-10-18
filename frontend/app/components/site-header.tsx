import Link from "next/link";

const modules = [
  { key: "pre-surgery", label: "Pre-surgery", href: "/" },
  { key: "during-surgery", label: "During surgery", href: "/during-surgery" },
] as const;

type SiteHeaderProps = {
  active: (typeof modules)[number]["key"];
};

export default function SiteHeader({ active }: SiteHeaderProps) {
  return (
    <header className="border-b border-[var(--line)] bg-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-4 sm:px-8">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-sm bg-[var(--green-dark)] text-sm font-bold text-white">
            S
          </div>
          <span className="font-semibold tracking-wide">SurgiAI</span>
        </Link>

        <nav aria-label="Modules" className="flex items-center gap-1 text-sm">
          {modules.map((module) => (
            <Link
              key={module.key}
              href={module.href}
              aria-current={module.key === active ? "page" : undefined}
              className={
                module.key === active
                  ? "border-b-2 border-[var(--green)] px-3 py-2 font-semibold text-[var(--green-dark)]"
                  : "border-b-2 border-transparent px-3 py-2 text-[var(--muted)] transition hover:text-[var(--green-dark)]"
              }
            >
              {module.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
