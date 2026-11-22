import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { sections, sectionBySlug, type Project } from "@/content/portfolio";
import { site } from "@/lib/site";
import { GoLink, Stage } from "../_components/stage";
import { ExplainerVideo, type ExplainerMedia } from "../_components/explainer-video";
import portfolioMedia from "@/content/portfolio-media.json";

export function generateStaticParams() {
  return sections.map((s) => ({ section: s.slug }));
}

export async function generateMetadata({ params }: PageProps<"/[section]">): Promise<Metadata> {
  const s = sectionBySlug((await params).section);
  return s ? { title: `${s.label} — Iván`, description: s.pitch } : {};
}

function StatusBadge({ status }: { status: Project["status"] }) {
  const style =
    status === "Live demo" ? "border-glow/40 bg-glow/10 text-glow"
      : status === "In progress" ? "border-lamp/40 bg-lamp/10 text-lamp"
        : "border-line text-muted";
  return <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs ${style}`}>{status}</span>;
}

function MediaFrame({ label, ratio = "aspect-video" }: { label: string; ratio?: string }) {
  return (
    <div className={`relative ${ratio} overflow-hidden rounded-2xl border border-line bg-ink-2`}>
      <div aria-hidden className="absolute inset-0 opacity-70"
        style={{ background: "radial-gradient(60% 80% at 30% 70%, rgba(94,234,212,0.10), transparent), radial-gradient(50% 60% at 80% 20%, rgba(242,180,92,0.08), transparent)" }} />
      <div className="absolute inset-0 grid place-items-center p-6 text-center">
        <p className="font-mono text-xs uppercase tracking-widest text-muted">{label}</p>
      </div>
    </div>
  );
}

function ProjectCard({ p, flip }: { p: Project; flip: boolean }) {
  const detailed = Boolean(p.problem);
  if (!detailed) {
    return (
      <article className="rounded-2xl border border-dashed border-line p-6">
        <div className="flex items-start justify-between gap-4">
          <h3 className="text-xl font-semibold tracking-tight">{p.title}</h3>
          <StatusBadge status={p.status} />
        </div>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-text-2">{p.summary}</p>
        <ul className="mt-4 flex flex-wrap gap-2">
          {p.stack.map((s) => <li key={s} className="rounded-md bg-ink-2 px-2 py-1 font-mono text-xs text-muted">{s}</li>)}
        </ul>
      </article>
    );
  }
  return (
    <article className="grid items-start gap-6 md:grid-cols-2 md:gap-10">
      <div className={flip ? "md:order-2" : ""}>
        <MediaFrame label="Screenshots coming soon" ratio="aspect-[4/3]" />
      </div>
      <div>
        <div className="flex items-start justify-between gap-4">
          <h3 className="text-2xl font-semibold tracking-tight">{p.title}</h3>
          <StatusBadge status={p.status} />
        </div>
        <p className="mt-3 leading-relaxed text-text-2">{p.summary}</p>
        <dl className="mt-5 space-y-4 text-sm leading-relaxed">
          {([["The problem", p.problem], ["How I built it", p.how], ["Result", p.result]] as const).map(([k, v]) => (
            <div key={k}>
              <dt className="font-mono text-xs uppercase tracking-widest text-lamp">{k}</dt>
              <dd className="mt-1 text-text-2">{v}</dd>
            </div>
          ))}
        </dl>
        <ul className="mt-5 flex flex-wrap gap-2">
          {p.stack.map((s) => <li key={s} className="rounded-md bg-ink-2 px-2 py-1 font-mono text-xs text-muted">{s}</li>)}
        </ul>
        {p.link && (
          <a href={p.link.href} target="_blank" rel="noopener" className="mt-5 inline-flex items-center gap-1.5 text-sm text-glow hover:underline">
            {p.link.label} <span aria-hidden>↗</span>
          </a>
        )}
      </div>
    </article>
  );
}

export default function SectionPage({ params }: PageProps<"/[section]">) {
  return (
    <Suspense fallback={<main className="min-h-svh" />}>
      <SectionContent params={params} />
    </Suspense>
  );
}

async function SectionContent({ params }: { params: PageProps<"/[section]">["params"] }) {
  const { section } = await params;
  const i = sections.findIndex((s) => s.slug === section);
  if (i < 0) notFound();
  const s = sections[i];
  const prev = sections[(i + sections.length - 1) % sections.length];
  const next = sections[(i + 1) % sections.length];
  const media = (portfolioMedia as Record<string, ExplainerMedia>)[s.slug];

  return (
    <main className="relative z-0 px-4 pb-24 pt-[190px] sm:px-6">
      <Stage delay={550} className="mx-auto max-w-5xl">
        <header className="mx-auto max-w-2xl text-center">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-glow">
            {String(i + 1).padStart(2, "0")} · {s.label}
          </p>
          <h1 className="mt-4 font-serif text-3xl leading-tight sm:text-5xl">{s.pitch}</h1>
          <p className="mt-5 text-text-2 sm:text-lg">{s.intro}</p>
        </header>

        <section aria-label="Explainer video" className="mt-14">
          {media ? (
            <ExplainerVideo media={media} title={s.video.title} />
          ) : (
            <>
              <MediaFrame label="Explainer video · coming soon" />
              <p className="mt-3 text-center text-sm text-muted">{s.video.title}</p>
            </>
          )}
        </section>

        <section aria-label="Projects" className="mt-20 space-y-16 sm:space-y-24">
          {s.projects.map((p, k) => <ProjectCard key={p.title} p={p} flip={k % 2 === 1} />)}
        </section>

        <section className="mt-24 rounded-3xl border border-line bg-ink-2/60 p-8 text-center sm:p-12">
          <h2 className="font-serif text-2xl sm:text-3xl">Have a project like this?</h2>
          <p className="mx-auto mt-3 max-w-xl text-text-2">Tell me what you need on Upwork and I&apos;ll reply with a plan and an estimate.</p>
          {site.upworkUrl && (
            <a href={site.upworkUrl} target="_blank" rel="noopener"
              className="mt-6 inline-block rounded-full bg-glow px-6 py-3 text-sm font-medium text-night transition hover:brightness-110">
              Hire me on Upwork
            </a>
          )}
        </section>

        <nav aria-label="Other areas" className="mt-12 flex items-center justify-between gap-4 text-sm">
          <GoLink to={prev.slug} className="text-muted transition hover:text-text">← {prev.label}</GoLink>
          <GoLink to={null} className="text-muted transition hover:text-text">All work</GoLink>
          <GoLink to={next.slug} className="text-right text-muted transition hover:text-text">{next.label} →</GoLink>
        </nav>
      </Stage>
    </main>
  );
}
