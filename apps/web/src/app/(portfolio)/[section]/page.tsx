import type { Metadata } from "next";
import { Suspense } from "react";
import { notFound } from "next/navigation";
import { sections, sectionBySlug, type Project } from "@/content/portfolio";
import { site } from "@/lib/site";
import { GoLink, Stage } from "../_components/stage";
import { ExplainerVideo, type ExplainerMedia } from "../_components/explainer-video";
import portfolioMedia from "@/content/portfolio-media.json";
import portfolioLoops from "@/content/portfolio-loops.json";
import { LoopVideo } from "../_components/loop-video";

export function generateStaticParams() {
  return sections.map((s) => ({ section: s.slug }));
}

export async function generateMetadata({ params }: PageProps<"/[section]">): Promise<Metadata> {
  const s = sectionBySlug((await params).section);
  return s ? { title: `${s.label} — Iván`, description: s.pitch } : {};
}

const MEDIA = portfolioMedia as Record<string, ExplainerMedia>;
const LOOPS = portfolioLoops as Record<string, { src: string; poster: string }>;

function StatusBadge({ status, href }: { status: Project["status"]; href?: string }) {
  const style =
    status === "Live demo" ? "border-glow/40 bg-glow/10 text-glow"
      : status === "In progress" ? "border-lamp/40 bg-lamp/10 text-lamp"
        : "border-line text-muted";
  if (href) {
    // a live demo the visitor can open right away: a real button, not a label
    return (
      <a href={href} target="_blank" rel="noopener"
        className="shrink-0 rounded-full border border-glow/60 bg-glow/15 px-3.5 py-1 text-xs font-medium text-glow shadow-[0_0_18px_-6px_var(--glow)] transition hover:bg-glow hover:text-night">
        {status} <span aria-hidden>↗</span>
      </a>
    );
  }
  return <span className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs ${style}`}>{status}</span>;
}

function LinkButton({ link }: { link: NonNullable<Project["link"]> }) {
  return (
    <a href={link.href} target="_blank" rel="noopener"
      className="mx-1 inline-flex items-center gap-1.5 rounded-full border border-glow/50 px-3 py-0.5 align-baseline text-sm text-glow transition hover:bg-glow/10">
      {link.label} <span aria-hidden>↗</span>
    </a>
  );
}

/** GitHub's mark (Simple Icons, CC0). */
function GitHubMark() {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="h-4 w-4 fill-current">
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  );
}

/** Summary paragraphs; "[[link]]" inside a paragraph places the project's link button right there. */
function Summary({ p }: { p: Project }) {
  const paras = Array.isArray(p.summary) ? p.summary : [p.summary];
  return (
    <div className="mt-3 space-y-3 leading-relaxed text-text-2">
      {paras.map((para, k) => {
        const [before, after] = para.split("[[link]]");
        return (
          <p key={k}>
            {before}
            {after !== undefined && p.link && <LinkButton link={p.link} />}
            {after}
          </p>
        );
      })}
    </div>
  );
}

const linkInline = (p: Project) => (Array.isArray(p.summary) ? p.summary : [p.summary]).some((x) => x.includes("[[link]]"));

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
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-text-2">{Array.isArray(p.summary) ? p.summary.join(" ") : p.summary}</p>
        <ul className="mt-4 flex flex-wrap gap-2">
          {p.stack.map((s) => <li key={s} className="rounded-md bg-ink-2 px-2 py-1 font-mono text-xs text-muted">{s}</li>)}
        </ul>
      </article>
    );
  }
  return (
    <article className="grid items-start gap-6 md:grid-cols-2 md:gap-10">
      <div className={`${flip ? "md:order-2" : ""} ${p.video || p.loop ? "md:sticky md:top-24" : ""}`}>
        {p.loop && LOOPS[p.loop.media] ? (
          <LoopVideo src={LOOPS[p.loop.media].src} poster={LOOPS[p.loop.media].poster} label={p.loop.label} />
        ) : p.video && MEDIA[p.video.media] ? (
          <ExplainerVideo media={MEDIA[p.video.media]} title={p.video.title} />
        ) : (
          <MediaFrame label="Screenshots coming soon" ratio="aspect-[4/3]" />
        )}
      </div>
      <div>
        <div className="flex items-start justify-between gap-4">
          <h3 className="text-2xl font-semibold tracking-tight">{p.title}</h3>
          <StatusBadge status={p.status} href={p.demoHref} />
        </div>
        <Summary p={p} />
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
        {((p.link && !linkInline(p)) || p.repos?.length) && (
          <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm">
            {p.link && !linkInline(p) && (
              <a href={p.link.href} target="_blank" rel="noopener" className="inline-flex items-center gap-1.5 text-glow hover:underline">
                {p.link.label} <span aria-hidden>↗</span>
              </a>
            )}
            {p.repos?.map((r) => (
              <a key={r.href} href={r.href} target="_blank" rel="noopener" aria-label={`${r.label} on GitHub`}
                className="inline-flex items-center gap-1.5 text-text-2 transition hover:text-glow">
                <GitHubMark /> {r.label} <span aria-hidden>↗</span>
              </a>
            ))}
          </div>
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
  const media = s.video?.media ? MEDIA[s.video.media] : undefined;

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

        {s.video && (
          <section id="section-video" aria-label="Explainer video" className="mt-14">
            {media ? (
              <ExplainerVideo media={media} title={s.video.title} />
            ) : (
              <>
                <MediaFrame label="Explainer video · coming soon" />
                <p className="mt-3 text-center text-sm text-muted">{s.video.title}</p>
              </>
            )}
          </section>
        )}

        <section aria-label="Projects" className={`${s.video ? "mt-20" : "mt-14"} space-y-16 sm:space-y-24`}>
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
