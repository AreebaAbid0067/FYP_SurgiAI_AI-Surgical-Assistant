
import SiteHeader from "../components/site-header";
import PostSurgeryWorkspace from "../components/post-surgery-workspace";

export default function PostSurgeryPage() {
  return (
    <div className="min-h-screen">
      <SiteHeader active="post-surgery" />

      <main className="mx-auto max-w-3xl px-5 pb-16 pt-10 sm:px-8">
        <p className="eyebrow mb-4">Post-operative assistant · 03</p>

        <h1 className="text-4xl font-semibold leading-tight text-[var(--green-dark)]">
          Post-surgery care and support.
        </h1>

        <p className="mt-4 text-base leading-7 text-[var(--muted)]">
          Review postoperative information, organize patient records, and ask
          questions about recovery and follow-up using available medical
          resources.
        </p>

        <PostSurgeryWorkspace />
      </main>
    </div>
  );
}
